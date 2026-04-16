#!/usr/bin/env python3

"""
Shipwright Build Image Toolbox

Creates and manages Shipwright builds for container images. Ensures ImageStream exists,
creates the build definition, triggers the build, and waits for completion.
"""

import json
import logging

from projects.core.dsl import (
    always,
    execute_tasks,
    retry,
    shell,
    task,
    template,
    toolbox,
)

logger = logging.getLogger("TOOLBOX")


def _capture_all_container_logs(pod_name: str, namespace: str, artifact_dir):
    """
    Capture logs from all containers in a pod

    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        artifact_dir: Directory to save log files
    """
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


def run(
    repo_name: str,
    commit: str,
    imagestream_name: str,
    tag_name: str,
    *,
    dockerfile_path: str = "projects/core/image/Containerfile",
    namespace: str = "psap-automation-wip",
    timeout_minutes: int = 30,
):
    """
    Build container image using Shipwright Build

    Args:
        repo_name: Git repository name (e.g., 'openshift-psap/fournos')
        commit: Git commit SHA or reference to build
        imagestream_name: Target ImageStream name
        tag_name: Target image tag
        dockerfile_path: Path to Dockerfile/Containerfile within the repository (default: projects/core/image/Containerfile)
        namespace: Kubernetes namespace for resources (default: psap-automation-wip)
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
    """Validate input parameters"""

    if not args.repo_name:
        raise ValueError("repo_name is required")
    if not args.commit:
        raise ValueError("commit is required")
    if not args.imagestream_name:
        raise ValueError("imagestream_name is required")
    if not args.tag_name:
        raise ValueError("tag_name is required")

    # Parse repository URL
    if "/" in args.repo_name:
        ctx.repo_owner, ctx.repo_name = args.repo_name.split("/", 1)
        ctx.git_url = f"https://github.com/{args.repo_name}.git"
    else:
        raise ValueError("repo_name should be in format 'owner/repo'")

    ctx.build_name = f"build-{args.imagestream_name}-{args.tag_name}"
    ctx.image_tag = f"{args.imagestream_name}:{args.tag_name}"

    logger.info("=== Build Parameters ===")
    logger.info(f"Git URL: {ctx.git_url}")
    logger.info(f"Commit/Revision: {args.commit}")
    logger.info(f"Dockerfile Path: {args.dockerfile_path}")
    logger.info(f"Build Name: {ctx.build_name}")
    logger.info(f"Image Tag: {ctx.image_tag}")
    logger.info(f"Namespace: {args.namespace}")

    return f"Validated parameters for repo: {ctx.git_url}, commit: {args.commit}"


@task
def ensure_imagestream_exists(args, ctx):
    """Ensure the ImageStream exists, create if not"""

    # Check if ImageStream exists
    result = shell.run(
        f"oc get imagestream {args.imagestream_name} -n {args.namespace}",
        check=False,
        log_stdout=False,
    )

    if result.success:
        return f"ImageStream {args.imagestream_name} already exists"

    # Render ImageStream manifest from template
    is_manifest_file = args.artifact_dir / "src" / f"{args.imagestream_name}-imagestream.yaml"
    template.render_template_to_file("imagestream.yaml.j2", is_manifest_file)

    # Apply the ImageStream
    shell.run(f"oc apply -f {is_manifest_file}")

    return f"Created ImageStream {args.imagestream_name}"


@task
def create_shipwright_build(args, ctx):
    """Create Shipwright Build definition"""

    # Render Build manifest from template
    build_manifest_file = args.artifact_dir / "src" / f"{ctx.build_name}-build.yaml"
    template.render_template_to_file("build.yaml.j2", build_manifest_file)

    # Check if build already exists and delete if it does
    shell.run(
        f"oc delete build {ctx.build_name} -n {args.namespace} --ignore-not-found",
    )

    # Apply the Build
    shell.run(
        f"oc apply -f {build_manifest_file}",
    )

    return f"Created Shipwright Build {ctx.build_name}"


@task
def trigger_build(args, ctx):
    """Trigger the Shipwright build"""

    # Render BuildRun manifest from template
    buildrun_manifest_file = args.artifact_dir / "artifacts" / f"{ctx.build_name}-buildrun.yaml"
    template.render_template_to_file("buildrun.yaml.j2", buildrun_manifest_file)

    # Create the BuildRun (use create instead of apply because of generateName)
    result = shell.run(
        f"oc create -f {buildrun_manifest_file} -ojson",
        log_stdout=False,
    )

    if not result.success:
        raise RuntimeError("Failed to create BuildRun the")

    buildrun_info = json.loads(result.stdout)
    ctx.buildrun_name = buildrun_info["metadata"]["name"]

    return f"Triggered build with BuildRun: {ctx.buildrun_name}"


@retry(attempts=60, delay=30)  # 30 minutes total
@task
def wait_for_build_completion(args, ctx):
    """Wait for the build to complete"""

    # Get BuildRun status
    result = shell.run(
        f"oc get buildruns.shipwright.io {ctx.buildrun_name} -n {args.namespace} -o jsonpath='{{.status.conditions[?(@.type==\"Succeeded\")].status}}'",
        check=False,
        log_stdout=False,
    )

    if not result.success:
        return False  # Retry on command failure

    status = result.stdout.strip().lower()
    if status in ("true", "false"):
        # Build succeeded
        shell.run(
            f"oc get buildruns.shipwright.io {ctx.buildrun_name} -n {args.namespace} -oyaml",
            stdout_dest=args.artifact_dir / "artifacts" / f"{ctx.buildrun_name}-final-status.yaml",
        )

        # Capture logs from all containers in the build pod
        _capture_all_container_logs(ctx.buildrun_name, args.namespace, args.artifact_dir)

        if status == "false":
            raise RuntimeError(f"Build {ctx.buildrun_name} failed")

        return f"Build {ctx.buildrun_name} completed successfully"

    return False  # Retry


@always
@task
def capture_build_artifacts(args, ctx):
    """Capture build-related artifacts and status"""

    build_run_name = getattr(ctx, "buildrun_name", None)
    # Get final BuildRun status
    if build_run_name:
        shell.run(
            f"oc describe buildrun {build_run_name} -n {args.namespace}",
            stdout_dest=args.artifact_dir / "artifacts" / "buildrun-describe.txt",
            check=False,
        )

        # Get BuildRun YAML for detailed inspection
        shell.run(
            f"oc get buildruns.shipwright.io {build_run_name} -n {args.namespace} -o yaml",
            stdout_dest=args.artifact_dir / "artifacts" / f"{build_run_name}-buildrun.yaml",
            check=False,
        )

        # Capture logs from all containers in the build pod
        _capture_all_container_logs(build_run_name, args.namespace, args.artifact_dir)
    else:
        logger.warning("No BuildRun name available")

    # Get Build definition
    shell.run(
        f"oc get builds.shipwright.io {ctx.build_name} -n {args.namespace} -o yaml",
        stdout_dest=args.artifact_dir / "artifacts" / f"{ctx.build_name}-build-definition.yaml",
        check=False,
    )

    # Get ImageStream status
    shell.run(
        f"oc describe imagestream {args.imagestream_name} -n {args.namespace}",
        stdout_dest=args.artifact_dir / "artifacts" / "imagestream-status.txt",
        check=False,
    )

    return "Build artifacts captured"


@always
@task
def generate_build_summary(args, ctx):
    """Generate a summary of the build process"""

    args.artifact_dir / "artifacts" / "build_summary.txt"

    logger.info("=== Shipwright Build Summary ===")
    logger.info(f"Generated at: {getattr(ctx, 'build_timestamp', 'unknown')}")
    logger.info(f"Repository: {args.repo_name}")
    logger.info(f"Commit: {args.commit}")
    logger.info(f"Namespace: {args.namespace}")
    logger.info(f"ImageStream: {args.imagestream_name}")
    logger.info(f"Tag: {args.tag_name}")
    logger.info(f"Build Name: {getattr(ctx, 'build_name', 'unknown')}")
    logger.info(f"BuildRun Name: {getattr(ctx, 'buildrun_name', 'unknown')}")
    logger.info(f"Target Image: {getattr(ctx, 'image_tag', 'unknown')}")


# Create the main function using the toolbox library
main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
