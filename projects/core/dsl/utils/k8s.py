"""
Kubernetes utilities for DSL tasks
"""

import json
import logging
import re
import subprocess
import time
from typing import Any

import yaml

from projects.core.dsl import shell

logger = logging.getLogger(__name__)


def oc(
    *args: str,
    check: bool = True,
    capture_output: bool = True,
    input_text: str | None = None,
    timeout_seconds: float | None = 300,
    log_stdout: bool = True,
    log_stderr: bool = True,
) -> shell.CommandResult:
    """Run an oc command.

    Args:
        *args: Arguments to pass to oc
        check: Raise subprocess.CalledProcessError if command fails
        capture_output: Capture stdout/stderr (for compatibility, always True with shell.run)
        input_text: Input to send to command (not supported)
        timeout_seconds: Command timeout (not supported)
        log_stdout: Log stdout to console (default True)
        log_stderr: Log stderr to console (default True)

    Returns:
        CommandResult with execution details
    """
    cmd = ["oc", *args]

    return shell.run(
        cmd,
        check=check,
        shell=False,
        log_stdout=log_stdout,
        log_stderr=log_stderr,
    )


def oc_get_json(
    kind: str,
    *,
    name: str | None = None,
    namespace: str | None = None,
    selector: str | None = None,
    ignore_not_found: bool = False,
) -> dict[str, Any] | None:
    """Get a Kubernetes resource as JSON using oc.

    Args:
        kind: Resource kind (e.g., 'pod', 'deployment')
        name: Resource name (optional)
        namespace: Namespace (optional)
        selector: Label selector (optional)
        ignore_not_found: Return None instead of raising error if not found

    Returns:
        Resource data as dict, or None if not found and ignore_not_found=True

    Raises:
        subprocess.CalledProcessError: If oc command fails
    """
    args = ["get", kind]
    if name:
        args.append(name)
    if namespace:
        args.extend(["-n", namespace])
    if selector:
        args.extend(["-l", selector])
    args.extend(["-o", "json"])

    result = oc(
        *args,
        check=not ignore_not_found,
        capture_output=True,
        log_stdout=False,
        log_stderr=not ignore_not_found,
    )
    if result.returncode != 0:
        if ignore_not_found and _is_oc_not_found_error(result.stderr):
            return None
        raise subprocess.CalledProcessError(
            result.returncode, f"oc {' '.join(args)}", result.stdout, result.stderr
        )
    if not result.stdout:
        raise ValueError(f"oc {' '.join(args)} returned no output")
    return json.loads(result.stdout)


def resource_exists(kind: str, name: str, *, namespace: str | None = None) -> bool:
    """Check if a Kubernetes resource exists.

    Args:
        kind: Resource kind (e.g., 'pod', 'deployment')
        name: Resource name
        namespace: Namespace (optional)

    Returns:
        True if resource exists, False otherwise
    """
    return (
        oc_get_json(
            kind,
            name=name,
            namespace=namespace,
            ignore_not_found=True,
        )
        is not None
    )


def _is_oc_not_found_error(stderr: str | None) -> bool:
    """Check if stderr contains a 'not found' error from oc."""
    if not stderr:
        return False

    normalized = stderr.lower()
    if "error from server (notfound)" in normalized:
        return True
    if "no resources found" in normalized:
        return True

    return bool(re.search(r"\bnot found\b", normalized))


def wait_until(
    description: str,
    *,
    timeout_seconds: int,
    interval_seconds: int,
    predicate,
) -> Any:
    """Wait until a condition is met.

    Args:
        description: Description of what we're waiting for (for logging)
        timeout_seconds: Maximum time to wait
        interval_seconds: Time between predicate checks
        predicate: Function that returns truthy value when condition is met

    Returns:
        The truthy value returned by predicate

    Raises:
        RuntimeError: If timeout is reached
    """
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            value = predicate()
            if value:
                return value
            last_error = None
        except Exception as exc:  # pragma: no cover - exercised in integration paths
            if isinstance(exc, RuntimeError):
                raise
            last_error = exc
            logger.info("waiting for %s: %s", description, exc)
        time.sleep(interval_seconds)

    if last_error:
        raise RuntimeError(f"Timed out waiting for {description}: {last_error}") from last_error
    raise RuntimeError(f"Timed out waiting for {description}")


def wait_for_job_completion(
    job_name: str, namespace: str, *, timeout_seconds: int, interval_seconds: int = 10
) -> dict[str, Any]:
    """Wait for a Job to complete successfully.

    Args:
        job_name: Job name
        namespace: Namespace
        timeout_seconds: Maximum time to wait
        interval_seconds: Time between checks

    Returns:
        Job resource data

    Raises:
        RuntimeError: If job fails or timeout is reached
    """

    def _job_completed() -> dict[str, Any] | None:
        payload = oc_get_json(
            "job",
            name=job_name,
            namespace=namespace,
            ignore_not_found=True,
        )
        if not payload:
            return None
        status = payload.get("status", {})
        if status.get("succeeded", 0):
            return payload
        failed_count = status.get("failed", 0)
        for condition in status.get("conditions", []):
            if condition.get("type") == "Failed" and condition.get("status") == "True":
                raise RuntimeError(
                    f"job/{job_name} failed: {condition.get('reason') or 'unknown reason'}"
                )
        if failed_count:
            raise RuntimeError(f"job/{job_name} failed after {failed_count} attempt(s)")
        return None

    return wait_until(
        f"job/{job_name} completion in {namespace}",
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds,
        predicate=_job_completed,
    )


def job_pod_names(job_name: str, namespace: str) -> list[str]:
    """Get the names of pods created by a Job.

    Args:
        job_name: Job name
        namespace: Namespace

    Returns:
        List of pod names
    """
    payload = oc_get_json(
        "pods",
        namespace=namespace,
        selector=f"job-name={job_name}",
        ignore_not_found=True,
    )
    if not payload:
        return []
    return [item["metadata"]["name"] for item in payload.get("items", [])]


def apply_manifest(artifact_path: Any, manifest: dict[str, Any]) -> None:
    """Apply a Kubernetes manifest.

    Args:
        artifact_path: Path where to write the manifest YAML (for record keeping)
        manifest: Manifest data as dict
    """
    # Write the manifest to the file
    with open(artifact_path, "w") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)

    oc("apply", "-f", str(artifact_path))


def condition_status(resource: dict[str, Any], condition_type: str) -> str | None:
    """Get the status of a specific condition from a Kubernetes resource.

    Args:
        resource: Resource data as dict
        condition_type: Type of condition to look for

    Returns:
        Condition status (e.g., 'True', 'False', 'Unknown') or None if not found
    """
    for condition in resource.get("status", {}).get("conditions", []):
        if condition.get("type") == condition_type:
            return condition.get("status")
    return None


def sanitize_k8s_name(name: str) -> str:
    """
    Sanitize a name to be compatible with Kubernetes object naming requirements.

    Kubernetes object names must:
    - Be lowercase only
    - Only contain alphanumeric characters and hyphens
    - Start and end with alphanumeric characters
    - Be maximum 63 characters long

    Args:
        name: The name to sanitize

    Returns:
        A valid Kubernetes object name

    Examples:
        >>> sanitize_k8s_name("My_Test Job!")
        "my-test-job-x"
        >>> sanitize_k8s_name("forge-llm_d-20260409-143022")
        "forge-llm-d-20260409-143022"
        >>> sanitize_k8s_name("valid-name123")
        "valid-name123"
    """
    # Convert to lowercase and replace invalid characters with hyphens
    sanitized = re.sub(r"[^a-z0-9\-]", "-", name.lower())

    # Remove leading/trailing hyphens and collapse multiple hyphens
    sanitized = re.sub(r"^-+|-+$", "", sanitized)
    sanitized = re.sub(r"-+", "-", sanitized)

    # Ensure it starts and ends with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "x" + sanitized
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + "x"

    # Truncate to 63 characters (K8s limit)
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
        # Make sure it still ends with alphanumeric after truncation
        if not sanitized[-1].isalnum():
            sanitized = sanitized[:-1] + "x"

    return sanitized or "default"


def is_valid_k8s_name(name: str) -> bool:
    """
    Check if a name is valid for Kubernetes objects.

    Args:
        name: The name to validate

    Returns:
        True if the name is valid, False otherwise

    Examples:
        >>> is_valid_k8s_name("valid-name123")
        True
        >>> is_valid_k8s_name("Invalid_Name")
        False
        >>> is_valid_k8s_name("toolongname" * 10)
        False
    """
    if not name:
        return False

    # Check length
    if len(name) > 63:
        return False

    # Check pattern: lowercase alphanumeric and hyphens, start/end with alphanumeric
    pattern = r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$"
    return bool(re.match(pattern, name))
