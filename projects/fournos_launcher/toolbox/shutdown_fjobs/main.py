#!/usr/bin/env python3

"""
FOURNOS job shutdown toolbox using DSL

Gracefully shutdown FournosJobs by setting spec.shutdown=Stop
"""

import logging
import shlex

from projects.core.dsl import (
    entrypoint,
    execute_tasks,
    shell,
    task,
)

logger = logging.getLogger(__name__)


@entrypoint
def run(
    namespace: str = "psap-automation",
    ci_label: str = None,
    job_name: str = None,
    all_jobs: bool = False,
    shutdown_value: str = "Stop",
):
    """
    Shutdown FournosJobs by setting spec.shutdown to a configurable value

    Args:
        namespace: Kubernetes namespace where FournosJobs are located (default: "psap-automation")
        ci_label: CI run label to filter jobs (e.g., "pr123_b456"). If not provided, will try to generate from env vars.
        job_name: Specific job name to shutdown (takes precedence over ci_label)
        all_jobs: Shutdown all FournosJobs in the namespace (dangerous - use with caution)
        shutdown_value: Value to set for spec.shutdown (default: "Stop")

    Examples:
        # Shutdown jobs for current CI run (auto-detect from env vars):
        run()

        # Shutdown jobs for specific CI run:
        run(ci_label="pr123_b456")

        # Shutdown specific job:
        run(job_name="forge-llm-d-20241203-143022")

        # Shutdown all jobs in namespace (use with caution):
        run(all_jobs=True)

        # Shutdown with custom shutdown value:
        run(ci_label="pr123_b456", shutdown_value="Terminate")
    """
    # Execute all registered tasks in order
    return execute_tasks(locals())


@task
def validate_inputs(args, ctx):
    """Validate input parameters"""

    if not args.namespace:
        raise ValueError("namespace is required")

    # Check that we have some way to identify which jobs to shutdown
    if not any([args.ci_label, args.job_name, args.all_jobs]):
        raise ValueError("Must specify one of: ci_label, job_name, or all_jobs=True. ")

    if args.all_jobs and (args.ci_label or args.job_name):
        raise ValueError("Cannot use all_jobs=True together with ci_label or job_name")

    SHUTDOWN_VALUES = ("Stop", "Terminate")
    if args.shutdown_value not in SHUTDOWN_VALUES:
        raise ValueError(
            f"Shutdown value ({args.shutdown_value}) not in the allowed values ({', '.join(SHUTDOWN_VALUES)})"
        )

    return "Inputs validated"


@task
def ensure_oc(args, ctx):
    """Ensure oc is available and connected"""

    shell.run("which oc || (echo 'oc not found in PATH' && exit 1)")
    shell.run("oc whoami")


@task
def find_target_jobs(args, ctx):
    """Find FournosJobs to shutdown"""

    if args.job_name:
        # Shutdown specific job
        ctx.target_selector = f"metadata.name={args.job_name}"
        ctx.description = f"job '{args.job_name}'"

    elif args.ci_label:
        # Shutdown jobs with CI label
        ctx.target_selector = f"ci-run={args.ci_label}"
        ctx.description = f"jobs with CI label '{args.ci_label}'"

    elif args.all_jobs:
        # Shutdown all jobs (no selector)
        ctx.target_selector = ""
        ctx.description = "ALL jobs in namespace (dangerous!)"

    # Get list of matching jobs
    if ctx.target_selector and not ctx.target_selector.startswith("metadata.name="):
        # Use label selector
        cmd = f'oc get fournosjobs -n {args.namespace} -l "{ctx.target_selector}" -o jsonpath="{{.items[*].metadata.name}}"'
    elif ctx.target_selector.startswith("metadata.name="):
        # Specific job name
        job_name = ctx.target_selector.replace("metadata.name=", "")
        cmd = f'oc get fournosjobs -n {args.namespace} {job_name} -o jsonpath="{{.metadata.name}}"'
    else:
        # All jobs
        cmd = f'oc get fournosjobs -n {args.namespace} -o jsonpath="{{.items[*].metadata.name}}"'

    result = shell.run(cmd, check=False)

    if not result.success:
        if "not found" in result.stderr.lower():
            ctx.job_names = []
            return f"No FournosJobs found for {ctx.description}"
        else:
            raise RuntimeError(f"Failed to list FournosJobs: {result.stderr}")

    job_names = result.stdout.strip().split() if result.stdout.strip() else []
    ctx.job_names = job_names

    if not job_names:
        return f"No FournosJobs found for {ctx.description}"

    return f"Found {len(job_names)} FournosJobs to shutdown: {', '.join(job_names)}"


@task
def confirm_shutdown(args, ctx):
    """Confirm shutdown operation"""

    if not ctx.job_names:
        return "No jobs to shutdown - skipping confirmation"

    if args.all_jobs:
        logger.warning("⚠️  WARNING: You are about to shutdown ALL FournosJobs in the namespace!")
        logger.warning(f"   Namespace: {args.namespace}")
        logger.warning(f"   Jobs to shutdown: {', '.join(ctx.job_names)}")

    logger.info(f"Will shutdown {len(ctx.job_names)} FournosJob(s): {', '.join(ctx.job_names)}")
    logger.info(f"Method: Set spec.shutdown={args.shutdown_value} for shutdown")

    return f"Ready to shutdown {len(ctx.job_names)} job(s)"


@task
def shutdown_jobs(args, ctx):
    """Shutdown the FournosJobs by setting spec.shutdown to the configured value"""

    if not ctx.job_names:
        return "No jobs to shutdown"

    successful_shutdowns = []
    failed_shutdowns = []

    for job_name in ctx.job_names:
        try:
            logger.info(f"Shutting down FournosJob: {job_name}")

            # Set spec.shutdown to the configured value
            patch_cmd = [
                "oc",
                "patch",
                "fournosjob",
                job_name,
                "-n",
                args.namespace,
                "--type=merge",
                "--patch",
                f'{{"spec":{{"shutdown":"{args.shutdown_value}"}}}}',
            ]

            result = shell.run(shlex.join(patch_cmd), check=False)

            if result.success:
                successful_shutdowns.append(job_name)
                logger.info(f"✅ Successfully shutdown FournosJob: {job_name}")
            else:
                failed_shutdowns.append(job_name)
                logger.error(f"❌ Failed to shutdown FournosJob {job_name}: {result.stderr}")

        except Exception as e:
            failed_shutdowns.append(job_name)
            logger.error(f"❌ Exception while shutting down FournosJob {job_name}: {e}")

    # Summary
    total_jobs = len(ctx.job_names)
    success_count = len(successful_shutdowns)
    fail_count = len(failed_shutdowns)

    if fail_count > 0:
        logger.warning(
            f"Shutdown summary: {success_count}/{total_jobs} successful, {fail_count} failed"
        )
        logger.warning(f"Failed jobs: {', '.join(failed_shutdowns)}")
    else:
        logger.info(f"Shutdown summary: {success_count}/{total_jobs} successful")

    return f"Shutdown complete: {success_count} successful, {fail_count} failed"


@task
def capture_final_status(args, ctx):
    """Capture final status of shutdown jobs"""

    if not ctx.job_names:
        return "No jobs to capture status for"

    # Create artifacts directory
    shell.mkdir("artifacts")

    for job_name in ctx.job_names:
        # Get job status after shutdown
        shell.run(
            f"oc get fournosjob {job_name} -n {args.namespace} -o yaml",
            stdout_dest=args.artifact_dir / "artifacts" / f"{job_name}-shutdown-status.yaml",
            check=False,
        )

    return f"Captured status for {len(ctx.job_names)} jobs in artifacts/ directory"


if __name__ == "__main__":
    run.main()
