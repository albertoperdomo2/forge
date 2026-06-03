#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from projects.core.dsl import entrypoint, execute_tasks, retry, task
from projects.core.dsl.utils import write_json, write_text
from projects.core.dsl.utils.k8s import (
    oc,
    oc_apply,
    oc_get_json,
    oc_resource_exists,
)
from projects.guidellm.toolbox.run_smoke_request.utils import render_smoke_request_job_from_parts


@entrypoint
def run(
    *,
    namespace: str,
    endpoint_url: str,
    job_name: str = "llm-d-smoke",
    client_image: str = "curlimages/curl:8.11.1",
    endpoint_path: str = "/v1/completions",
    request_retries: int = 30,
    request_retry_delay_seconds: int = 10,
    request_timeout_seconds: int = 60,
    served_model_name: str,
    prompt: str = "San Francisco is a",
    max_tokens: int = 50,
    temperature: float = 0.7,
) -> dict[str, object]:
    """
    Run the llm_d smoke request job against a resolved endpoint.

    Args:
        namespace: Namespace used by llm_d
        endpoint_url: Gateway endpoint URL returned by the deploy command
        job_name: Name for the smoke test job
        client_image: Container image for making HTTP requests
        endpoint_path: API endpoint path to test
        request_retries: Number of retry attempts
        request_retry_delay_seconds: Delay between retries
        request_timeout_seconds: Timeout for each request
        served_model_name: Model name to use in API requests
        prompt: Test prompt to send
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
    """

    context = execute_tasks(locals())
    return context.response


@task
def prepare_smoke_request(args, ctx):
    """Prepare smoke request payload"""

    ctx.job_name = args.job_name

    payload = {
        "model": args.served_model_name,
        "prompt": args.prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    ctx.payload = payload

    # Ensure artifacts directory exists
    artifacts_dir = args.artifact_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    write_json(artifacts_dir / "smoke.request.json", payload)
    return f"Prepared smoke request for job {args.job_name}"


@task
def delete_existing_smoke_job(args, ctx):
    """Delete existing smoke job"""

    oc(
        "delete",
        "job",
        ctx.job_name,
        "-n",
        args.namespace,
        "--ignore-not-found=true",
        check=False,
    )
    return f"Initiated deletion of job {ctx.job_name}"


@retry(attempts=24, delay=5, backoff=1.0)
@task
def wait_smoke_job_deleted(args, ctx):
    """Wait for smoke job deletion to complete"""

    if not oc_resource_exists("job", ctx.job_name, namespace=args.namespace):
        return f"Job {ctx.job_name} deleted"
    return False  # Retry


@task
def create_smoke_job(args, ctx):
    """Create the smoke request job"""

    # Ensure the src directory exists
    src_dir = args.artifact_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    oc_apply(
        src_dir / "smoke-job.yaml",
        render_smoke_request_job_from_parts(
            namespace=args.namespace,
            job_name=args.job_name,
            client_image=args.client_image,
            endpoint_path=args.endpoint_path,
            request_retries=args.request_retries,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            endpoint_url=args.endpoint_url,
            payload=ctx.payload,
        ),
    )
    return f"Created smoke job {ctx.job_name}"


@retry(attempts=60, delay=5, backoff=1.0)
@task
def wait_smoke_job_completion(args, ctx):
    """Wait for smoke job completion"""

    # Check job status
    payload = oc_get_json(
        "job",
        name=ctx.job_name,
        namespace=args.namespace,
        ignore_not_found=True,
    )
    if not payload:
        return (False, f"Job {ctx.job_name} not found, retrying...")

    status = payload.get("status", {})

    # Check if succeeded
    if status.get("succeeded", 0):
        return f"Smoke job {ctx.job_name} completed successfully"

    # Check if failed
    failed_count = status.get("failed", 0)
    for condition in status.get("conditions", []):
        if condition.get("type") == "Failed" and condition.get("status") == "True":
            raise RuntimeError(
                f"job/{ctx.job_name} failed: {condition.get('reason') or 'unknown reason'}"
            )
    if failed_count:
        raise RuntimeError(f"job/{ctx.job_name} failed after {failed_count} attempt(s)")

    # Still running
    return (False, f"Smoke job {ctx.job_name} still running, retrying...")


@task
def capture_smoke_response(args, ctx):
    """Capture and validate smoke response"""

    try:
        capture_smoke_state(
            artifact_dir=args.artifact_dir,
            namespace=args.namespace,
            smoke=args.smoke,
        )

        result = oc(
            "logs",
            f"job/{ctx.job_name}",
            "-n",
            args.namespace,
            check=False,
            capture_output=True,
        )

        if result.returncode != 0 or not result.stdout:
            raise RuntimeError(
                f"Smoke request job {ctx.job_name} completed but response logs could not be read: {result.stderr}"
            )

        response = json.loads(result.stdout)
        if not response.get("choices"):
            raise RuntimeError(f"Invalid smoke response payload: {result.stdout}")

        ctx.response = response
        write_json(args.artifact_dir / "artifacts" / "smoke.response.json", response)
        return f"Captured smoke response for job {ctx.job_name}"

    finally:
        capture_smoke_state(
            artifact_dir=args.artifact_dir,
            namespace=args.namespace,
            smoke=args.smoke,
        )


def capture_smoke_state(*, artifact_dir: Path, namespace: str, smoke: dict) -> None:
    job_name = smoke["job_name"]
    artifacts_dir = artifact_dir / "artifacts"

    capture_get("job", job_name, namespace, "yaml", artifacts_dir / "smoke_job.yaml")
    capture_get(
        "pods",
        None,
        namespace,
        "yaml",
        artifacts_dir / "smoke_job.pods.yaml",
        selector=f"job-name={job_name}",
    )
    result = oc(
        "logs",
        f"job/{job_name}",
        "-n",
        namespace,
        check=False,
        capture_output=True,
    )
    if result.returncode == 0 and result.stdout:
        write_text(artifacts_dir / "smoke_job.logs", result.stdout)


def capture_get(
    kind: str,
    name: str | None,
    namespace: str,
    output: str,
    destination: Path,
    *,
    selector: str | None = None,
) -> None:
    args = ["get", kind]
    if name:
        args.append(name)
    args.extend(["-n", namespace])
    if selector:
        args.extend(["-l", selector])
    args.extend(["-o", output])
    result = oc(*args, check=False, capture_output=True)
    if result.returncode == 0 and result.stdout:
        write_text(destination, result.stdout)


if __name__ == "__main__":
    run.main()
