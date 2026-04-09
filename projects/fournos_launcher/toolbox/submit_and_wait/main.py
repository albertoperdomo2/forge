#!/usr/bin/env python3

"""
FOURNOS job submission and monitoring using task-based DSL
Parameters are passed from the entrypoint that reads the configuration
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

from projects.core.library import env
from projects.core.dsl import task, retry, when, always, execute_tasks, clear_tasks, shell, toolbox, template
from projects.core.dsl.utils.k8s import sanitize_k8s_name


def run(
    cluster_name: str,
    project: str,
    *,
    args: list = None,
    variables_overrides: dict = None,
    job_name: str = "",
    namespace: str = "fournos-jobs",
    owner: str = "",
    display_name: str = "",
    pipeline_name: str = "",
    env: dict = None,
):
    """
    Submit a FOURNOS job and wait for completion

    Args:
        cluster_name: Name of the target cluster for the FOURNOS job
        project: The project name to execute (e.g., 'llm_d', 'skeleton')
        args: List of arguments to pass to the project (default: empty list)
        variables_overrides: Dictionary of config variables to override (default: empty dict)
        job_name: Custom name for the FOURNOS job (auto-generated if empty)
        namespace: Kubernetes namespace for the FOURNOS job (default: "fournos-jobs")
        owner: Owner of the FOURNOS job (default: empty)
        display_name: Human-readable display name for the job (default: empty)
        pipeline_name: Name of the pipeline to execute (default: empty)
        env: Dictionary of environment variables to set (default: empty dict)

    Examples:
        # Called by entrypoint with config values:
        run(
            cluster_name="my-cluster",
            project="llm_d",
            args=["test", "--verbose"],
            variables_overrides={"model": "mistral", "replicas": 2},
            namespace="my-fournos-jobs",
            owner="user@example.com",
            display_name="LLM Testing Job",
            pipeline_name="test-pipeline",
            env={"DEBUG": "1", "LOG_LEVEL": "info"}
        )
    """
    # Set defaults
    if args is None:
        args = []
    if variables_overrides is None:
        variables_overrides = {}
    if env is None:
        env = {}

    # Execute all registered tasks in order
    return execute_tasks(locals())


@task
def validate_inputs(args, ctx):
    """Validate input parameters"""

    if not args.cluster_name:
        raise ValueError("cluster_name is required")

    if not args.project:
        raise ValueError("project is required")

    if not isinstance(args.args, list):
        raise ValueError("args should be a list")

    if not isinstance(args.variables_overrides, dict):
        raise ValueError("variables_overrides should be a dict")

    if not isinstance(args.env, dict):
        raise ValueError("env should be a dict")

    return f"Inputs validated"


@task
def generate_job_name(args, ctx):
    """Generate job name if not provided and ensure K8s compatibility"""

    if args.job_name:
        # Sanitize user-provided job name
        raw_name = args.job_name
    else:
        # Generate and sanitize auto job name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        raw_name = f"forge-{args.project}-{timestamp}"

    ctx.final_job_name = sanitize_k8s_name(raw_name)

    return f"Job name: {ctx.final_job_name}"


@task
def ensure_oc(args, ctx):
    """ Ensure oc is available and connected"""

    shell.run("which oc || (echo 'oc not found in PATH' && exit 1)")
    shell.run("oc whoami")


@task
def create_job_manifest(args, ctx):
    """Create FOURNOS job manifest"""

    # Render job manifest from template
    ctx.manifest_file = args.artifact_dir / "src" / f"{ctx.final_job_name}-manifest.yaml"
    shell.mkdir(ctx.manifest_file.parent)

    template.render_template_to_file("job.yaml.j2", ctx.manifest_file)

    return f"Job manifest created: {ctx.manifest_file}"


@task
def submit_fournos_job(args, ctx):
    """Submit the FOURNOS job"""

    # Apply the job manifest
    result = shell.run(f"oc apply -f {ctx.manifest_file}")

    if not result.success:
        raise RuntimeError(f"Failed to submit FOURNOS job: {result.stderr}")

    return f"Successfully submitted FOURNOS job: {ctx.final_job_name}"


@retry(attempts=120, delay=30, backoff=1.0)
@task
def wait_for_job_completion(args, ctx):
    """Wait for FOURNOS job to complete"""

    # Check job status
    status_result = shell.run(
        f'oc get fournosjob {ctx.final_job_name} -n {args.namespace} -o jsonpath="{{.status.phase}}"',
        check=False,
        log_stdout=False
    )

    if not status_result.success:
        # Failed to get status, will retry
        print(f"Failed to get job status, retrying...")
        raise RuntimeError("Failed to get job status")

    status = status_result.stdout.strip()

    if status == "Completed":
        return f"Job {ctx.final_job_name} completed successfully"
    elif status == "Failed":
        # Get failure details
        failure_result = shell.run(
            f'oc get fournosjob {ctx.final_job_name} -n {args.namespace} -o jsonpath="{{.status.message}}"',
            check=False,
            log_stdout=False
        )
        failure_msg = failure_result.stdout.strip() if failure_result.success else "Unknown failure"
        raise RuntimeError(f"Job {ctx.final_job_name} failed: {failure_msg}")
    elif status in ["Running", "Pending"]:
        print(f"Job {ctx.final_job_name} status: {status}")
        # Job still running, will retry
        raise RuntimeError("Job still running")
    else:
        print(f"Job {ctx.final_job_name} status: {status}")
        # Unknown status, will retry
        raise RuntimeError(f"Unknown job status: {status}")


@task
def retrieve_job_logs(args, ctx):
    """Retrieve and save job logs"""

    # Get job logs
    logs_result = shell.run(
        f'oc logs -l "fournos.job={ctx.final_job_name}" -n {args.namespace} --all-containers=true',
        check=False,
        stdout_dest=args.artifact_dir / f"{ctx.final_job_name}-logs.txt"
    )

    if logs_result.success:
        return f"Job logs saved to {ctx.final_job_name}-logs.txt"
    else:
        return "No logs available or failed to retrieve logs"


@task
def capture_final_job_status(args, ctx):
    """Capture final job status and details"""

    # Get full job details
    shell.run(
        f'oc get fournosjob {ctx.final_job_name} -n {args.namespace} -o yaml',
        stdout_dest=args.artifact_dir / f"{ctx.final_job_name}-final-status.yaml",
        check=False
    )

    return f"Final job status captured to {ctx.final_job_name}-final-status.yaml"


@always
@task
def cleanup_job_manifest(args, ctx):
    """Clean up temporary files"""

    if hasattr(ctx, 'manifest_file') and ctx.manifest_file.exists():
        ctx.manifest_file.unlink()
        return f"Cleaned up manifest file: {ctx.manifest_file}"

    return "No manifest file to clean up"


# Create the main function using the toolbox library
main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
