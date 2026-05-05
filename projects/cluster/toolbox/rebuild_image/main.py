#!/usr/bin/env python3

"""
Rebuild Image Toolbox

Triggers a rebuild of an existing Shipwright Build by creating a BuildRun
and waiting for completion.
"""

import json
import logging

from projects.core.dsl import (
    always,
    entrypoint,
    execute_tasks,
    retry,
    shell,
    task,
    template,
)

logger = logging.getLogger("DSL")


def _capture_all_container_logs(buildrun_name: str, namespace: str, artifact_dir):
    """
    Capture logs from all containers in a BuildRun's pod

    Args:
        buildrun_name: Name of the BuildRun (used to find the actual pod)
        namespace: Kubernetes namespace
        artifact_dir: Directory to save log files
    """
    # Find the actual pod name using BuildRun labels
    pod_result = shell.run(
        f"oc get pods -n {namespace} -l buildrun.shipwright.io/name={buildrun_name} -o jsonpath='{{.items[0].metadata.name}}'",
        check=False,
    )

    if not pod_result.success or not pod_result.stdout.strip():
        logger.warning(f"Could not find pod for BuildRun {buildrun_name}")
        return

    pod_name = pod_result.stdout.strip()
    logger.info(f"Found pod {pod_name} for BuildRun {buildrun_name}")

    # Get list of all containers in the pod
    result = shell.run(
        f"oc get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].name}}'",
        check=False,
    )

    if not result.success or not result.stdout.strip():
        logger.warning(f"Could not get container list for pod {pod_name}")
        return

    container_names = result.stdout.strip().split()
    logger.info(f"Capturing logs from {len(container_names)} containers: {container_names}")

    # Capture logs for each container
    for container_name in container_names:
        log_file = artifact_dir / "artifacts" / f"{pod_name}-{container_name}.log"
        shell.run(
            f"oc logs {pod_name} -n {namespace} -c {container_name}",
            stdout_dest=log_file,
            check=False,
        )
        logger.debug(f"Captured logs for container '{container_name}' to {log_file}")

    # Also capture logs from init containers if any
    result = shell.run(
        f"oc get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.initContainers[*].name}}'",
        check=False,
    )

    if not result.success or not result.stdout.strip():
        return

    init_container_names = result.stdout.strip().split()
    logger.info(
        f"Capturing logs from {len(init_container_names)} init containers: {init_container_names}"
    )

    for container_name in init_container_names:
        log_file = artifact_dir / "artifacts" / f"{pod_name}-init-{container_name}.log"
        shell.run(
            f"oc logs {pod_name} -n {namespace} -c {container_name}",
            stdout_dest=log_file,
            check=False,
        )
        logger.debug(f"Captured init container logs for '{container_name}' to {log_file}")


@entrypoint
def run(
    build_name: str,
    *,
    namespace: str = "psap-automation-wip",
    timeout_minutes: int = 30,
):
    """
    Rebuild container image using existing Shipwright Build

    Args:
        build_name: Name of the existing Shipwright Build to rebuild
        namespace: Kubernetes namespace (default: psap-automation-wip)
        timeout_minutes: Maximum time to wait for build completion (default: 30)
    """

    # Execute all registered tasks in order, respecting conditions
    return execute_tasks(locals())


@task
def setup_directories(args, ctx):
    """Create the artifacts directory"""

    shell.mkdir("artifacts")
    shell.mkdir("src")

    return f"Artifacts directory created in {args.artifact_dir}"


@task
def validate_parameters(args, ctx):
    """Validate input parameters and check Build exists"""

    if not args.build_name:
        raise ValueError("build_name is required")

    # Check if the Shipwright Build exists (use FQDN to avoid confusion with OpenShift Builds)
    result = shell.run(
        f"oc get builds.shipwright.io {args.build_name} -n {args.namespace}",
        check=False,
        log_stdout=False,
    )

    if not result.success:
        raise ValueError(
            f"Shipwright Build '{args.build_name}' not found in namespace '{args.namespace}'"
        )

    # Get Build details for logging
    result = shell.run(
        f"oc get builds.shipwright.io {args.build_name} -n {args.namespace} -o jsonpath='{{.spec.output.image}}'",
        log_stdout=False,
    )

    if result.success:
        ctx.output_image = result.stdout.strip()
        logger.info(f"Build output image: {ctx.output_image}")

    logger.info("=== Rebuild Parameters ===")
    logger.info(f"Build Name: {args.build_name}")
    logger.info(f"Namespace: {args.namespace}")
    logger.info(f"Timeout: {args.timeout_minutes} minutes")

    return f"Validated parameters for build: {args.build_name}"


@task
def create_buildrun(args, ctx):
    """Create BuildRun to trigger the rebuild"""

    # Render BuildRun manifest from template
    buildrun_manifest_file = args.artifact_dir / "src" / f"{args.build_name}-buildrun.yaml"
    template.render_template_to_file("buildrun.yaml.j2", buildrun_manifest_file)

    # Create the BuildRun (use create because of generateName)
    result = shell.run(
        f"oc create -f {buildrun_manifest_file} -ojson",
        log_stdout=False,
    )

    if not result.success:
        raise RuntimeError("Failed to create BuildRun")

    buildrun_info = json.loads(result.stdout)
    ctx.buildrun_name = buildrun_info["metadata"]["name"]

    return f"Triggered rebuild with BuildRun: {ctx.buildrun_name}"


@retry(attempts=60, delay=30)  # 30 minutes total
@task
def wait_for_completion(args, ctx):
    """Wait for the BuildRun to complete"""

    # Get BuildRun status
    result = shell.run(
        f"oc get buildruns.shipwright.io {ctx.buildrun_name} -n {args.namespace} -o jsonpath='{{.status.conditions[?(@.type==\"Succeeded\")].status}}'",
        check=False,
    )

    if not result.success:
        return False  # Retry on command failure

    status = result.stdout.strip().lower()
    if status in ("true", "false"):
        # Build completed (either success or failure)
        shell.run(
            f"oc get buildruns.shipwright.io {ctx.buildrun_name} -n {args.namespace} -oyaml",
            stdout_dest=args.artifact_dir / "artifacts" / f"{ctx.buildrun_name}-final-status.yaml",
        )

        # Capture logs from all containers in the build pod
        _capture_all_container_logs(ctx.buildrun_name, args.namespace, args.artifact_dir)

        if status == "false":
            # Get failure reason
            result = shell.run(
                f"oc get buildruns.shipwright.io {ctx.buildrun_name} -n {args.namespace} -o jsonpath='{{.status.conditions[?(@.type==\"Succeeded\")].message}}'",
                check=False,
                log_stdout=False,
            )
            failure_message = result.stdout.strip() if result.success else "Unknown failure"
            raise RuntimeError(f"BuildRun {ctx.buildrun_name} failed: {failure_message}")

        return f"BuildRun {ctx.buildrun_name} completed successfully"

    return False  # Still running, retry


@always
@task
def capture_artifacts(args, ctx):
    """Capture build-related artifacts and status"""

    buildrun_name = getattr(ctx, "buildrun_name", None)
    if buildrun_name:
        shell.run(
            f"oc describe buildrun {buildrun_name} -n {args.namespace}",
            stdout_dest=args.artifact_dir / "artifacts" / "buildrun-describe.txt",
            check=False,
        )

        # Get BuildRun YAML for detailed inspection
        shell.run(
            f"oc get buildruns.shipwright.io {buildrun_name} -n {args.namespace} -o yaml",
            stdout_dest=args.artifact_dir / "artifacts" / f"{buildrun_name}-buildrun.yaml",
            check=False,
        )

        # Capture logs from all containers in the build pod
        _capture_all_container_logs(buildrun_name, args.namespace, args.artifact_dir)
    else:
        logger.warning("No BuildRun name available for artifact capture")

    # Get Shipwright Build definition
    shell.run(
        f"oc get builds.shipwright.io {args.build_name} -n {args.namespace} -o yaml",
        stdout_dest=args.artifact_dir / "artifacts" / f"{args.build_name}-build-definition.yaml",
        check=False,
    )

    return "Build artifacts captured"


@always
@task
def generate_rebuild_summary(args, ctx):
    """Generate a summary of the rebuild process"""

    logger.info("=== Rebuild Summary ===")
    logger.info(f"Build Name: {args.build_name}")
    logger.info(f"Namespace: {args.namespace}")
    logger.info(f"BuildRun Name: {getattr(ctx, 'buildrun_name', 'unknown')}")
    logger.info(f"Output Image: {getattr(ctx, 'output_image', 'unknown')}")
    logger.info(f"Timeout: {args.timeout_minutes} minutes")


if __name__ == "__main__":
    run.main()
