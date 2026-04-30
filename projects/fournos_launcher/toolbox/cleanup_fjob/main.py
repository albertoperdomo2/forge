#!/usr/bin/env python3

"""
FOURNOS job cleanup using task-based DSL
Cleans up a specific FOURNOS job
"""

import logging

from projects.core.dsl import (
    execute_tasks,
    shell,
    task,
    toolbox,
)

logger = logging.getLogger(__name__)


def run(
    job_name: str,
    namespace: str = "fournos-jobs",
    skip_shutdown_check: bool = False,
):
    """
    Clean up a FOURNOS job

    Args:
        job_name: Name of the FOURNOS job to cleanup
        namespace: Kubernetes namespace where the job is located (default: "fournos-jobs")
        skip_shutdown_check: If True, skip checking for shutdown state and force cleanup (default: False)

    Examples:
        # Basic cleanup:
        run(job_name="forge-llm-d-20241203-143022")

        # Force cleanup regardless of shutdown state:
        run(job_name="forge-llm-d-20241203-143022", skip_shutdown_check=True)
    """
    # Execute all registered tasks in order
    return execute_tasks(locals())


@task
def validate_inputs(args, ctx):
    """Validate input parameters"""

    if not args.job_name:
        raise ValueError("job_name is required")

    if not args.namespace:
        raise ValueError("namespace is required")

    return "Inputs validated"


@task
def ensure_oc(args, ctx):
    """Ensure oc is available and connected"""

    shell.run("which oc || (echo 'oc not found in PATH' && exit 1)")
    shell.run("oc whoami")


@task
def check_job_exists(args, ctx):
    """Check if the job exists"""

    result = shell.run(
        f"oc get fournosjob {args.job_name} -n {args.namespace}",
        check=False,
    )

    if not result.success:
        if "not found" in result.stderr.lower():
            ctx.job_exists = False
            return f"Job {args.job_name} not found - nothing to cleanup"
        else:
            raise RuntimeError(f"Failed to check job existence: {result.stderr}")

    ctx.job_exists = True
    return f"Job {args.job_name} exists"


@task
def check_shutdown_state(args, ctx):
    """Check if shutdown has been requested"""

    if not ctx.job_exists:
        return "Job doesn't exist - skipping shutdown check"

    if args.skip_shutdown_check:
        return "Shutdown check skipped by request"

    shutdown_result = shell.run(
        f'oc get fournosjob {args.job_name} -n {args.namespace} -o jsonpath="{{.spec.shutdown}}"',
        check=False,
    )

    if shutdown_result.success and shutdown_result.stdout.strip():
        shutdown_value = shutdown_result.stdout.strip()
        ctx.should_preserve = True
        ctx.shutdown_reason = shutdown_value
        return f"Job has spec.shutdown={shutdown_value} - should be preserved to let it export artifacts"

    ctx.should_preserve = False
    return "No shutdown detected - safe to cleanup"


@task
def cleanup_fjob(args, ctx):
    """Clean up the FOURNOS job"""

    if not ctx.job_exists:
        return "Job doesn't exist - nothing to cleanup"

    if ctx.should_preserve:
        return f"Job preserved due to shutdown state: {ctx.shutdown_reason}"

    shell.run(
        f"oc delete fournosjob {args.job_name} -n {args.namespace} --ignore-not-found",
    )

    return f"Successfully cleaned up job: {args.job_name}"


# Create the main function using the toolbox library
main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
