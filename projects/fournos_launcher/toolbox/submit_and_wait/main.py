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
from projects.core.dsl import task, retry, when, always, execute_tasks, clear_tasks, shell, toolbox

def run(
    cluster_name: str,
    project: str,
    *,
    args: list = None,
    variables_overrides: dict = None,
    job_name: str = "",
    namespace: str = "fournos-jobs",
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

    Examples:
        # Called by entrypoint with config values:
        run(
            cluster_name="my-cluster",
            project="llm_d",
            args=["test", "--verbose"],
            variables_overrides={"model": "mistral", "replicas": 2},
            namespace="my-fournos-jobs"
        )
    """
    # Set defaults
    if args is None:
        args = []
    if variables_overrides is None:
        variables_overrides = {}

    # Execute all registered tasks in order
    return execute_tasks(locals())


@task
def validate_inputs(args):
    """Validate input parameters"""

    if not args.cluster_name:
        raise ValueError("cluster_name is required")

    if not args.project:
        raise ValueError("project is required")

    # Store processed arguments
    args.args_list = args.args if isinstance(args.args, list) else []
    args.variables_dict = args.variables_overrides if isinstance(args.variables_overrides, dict) else {}

    return f"Validated inputs: cluster={args.cluster_name}, project={args.project}, args={args.args_list}"


@task
def generate_job_name(args):
    """Generate job name if not provided"""

    if args.job_name:
        args.final_job_name = args.job_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.final_job_name = f"forge-{args.project}-{timestamp}"

    return f"Job name: {args.final_job_name}"


@task
def ensure_oc(args):
    """ Ensure oc is available and connected"""

    shell.run("which oc || (echo 'oc not found in PATH' && exit 1)")
    shell.run("oc whoami")


@task
def create_job_manifest(args):
    """Create FOURNOS job manifest"""

    # Prepare the job specification
    job_spec = {
        "apiVersion": "fournos.example.com/v1",
        "kind": "FournosJob",
        "metadata": {
            "name": args.final_job_name,
            "namespace": args.namespace
        },
        "spec": {
            "targetCluster": args.cluster_name,
            "project": args.project,
            "args": args.args_list,
            "variableOverrides": args.variables_dict,
        }
    }

    # Write manifest to file
    manifest_file = args.artifact_dir / "src" / f"{args.final_job_name}-manifest.yaml"
    shell.mkdir(manifest_file.parent)

    with open(manifest_file, 'w') as f:
        import yaml
        yaml.dump(job_spec, f, default_flow_style=False)

    args.manifest_file = manifest_file

    return f"Job manifest created: {manifest_file}"


@task
def submit_fournos_job(args):
    """Submit the FOURNOS job"""

    # Apply the job manifest
    result = shell.run(f"oc apply -f {args.manifest_file}")

    if not result.success:
        raise RuntimeError(f"Failed to submit FOURNOS job: {result.stderr}")

    return f"Successfully submitted FOURNOS job: {args.final_job_name}"


@retry(attempts=120, delay=30, backoff=1.0)
@task
def wait_for_job_completion(args):
    """Wait for FOURNOS job to complete"""

    # Check job status
    status_result = shell.run(
        f'oc get fournosjob {args.final_job_name} -n {args.namespace} -o jsonpath="{{.status.phase}}"',
        check=False,
        log_stdout=False
    )

    if not status_result.success:
        # Failed to get status, will retry
        print(f"Failed to get job status, retrying...")
        raise RuntimeError("Failed to get job status")

    status = status_result.stdout.strip()

    if status == "Completed":
        return f"Job {args.final_job_name} completed successfully"
    elif status == "Failed":
        # Get failure details
        failure_result = shell.run(
            f'oc get fournosjob {args.final_job_name} -n {args.namespace} -o jsonpath="{{.status.message}}"',
            check=False,
            log_stdout=False
        )
        failure_msg = failure_result.stdout.strip() if failure_result.success else "Unknown failure"
        raise RuntimeError(f"Job {args.final_job_name} failed: {failure_msg}")
    elif status in ["Running", "Pending"]:
        print(f"Job {args.final_job_name} status: {status}")
        # Job still running, will retry
        raise RuntimeError("Job still running")
    else:
        print(f"Job {args.final_job_name} status: {status}")
        # Unknown status, will retry
        raise RuntimeError(f"Unknown job status: {status}")


@task
def retrieve_job_logs(args):
    """Retrieve and save job logs"""

    # Get job logs
    logs_result = shell.run(
        f'oc logs -l "fournos.job={args.final_job_name}" -n {args.namespace} --all-containers=true',
        check=False,
        stdout_dest=args.artifact_dir / f"{args.final_job_name}-logs.txt"
    )

    if logs_result.success:
        return f"Job logs saved to {args.final_job_name}-logs.txt"
    else:
        return "No logs available or failed to retrieve logs"


@task
def capture_final_job_status(args):
    """Capture final job status and details"""

    # Get full job details
    shell.run(
        f'oc get fournosjob {args.final_job_name} -n {args.namespace} -o yaml',
        stdout_dest=args.artifact_dir / f"{args.final_job_name}-final-status.yaml",
        check=False
    )

    return f"Final job status captured to {args.final_job_name}-final-status.yaml"


@always
@task
def cleanup_job_manifest(args):
    """Clean up temporary files"""

    if hasattr(args, 'manifest_file') and args.manifest_file.exists():
        args.manifest_file.unlink()
        return f"Cleaned up manifest file: {args.manifest_file}"

    return "No manifest file to clean up"


# Create the main function using the toolbox library
main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
