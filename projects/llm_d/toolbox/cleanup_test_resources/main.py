#!/usr/bin/env python3

from __future__ import annotations

import logging
import subprocess

from projects.core.dsl import entrypoint, execute_tasks, retry, task
from projects.core.dsl.utils.k8s import oc, oc_get_json, resource_exists

logger = logging.getLogger("DSL")


@entrypoint
def run(
    *,
    namespace: str,
    inference_service_name: str,
    smoke_job_name: str,
    benchmark_job_name: str | None = None,
    cleanup_timeout_seconds: int = 900,
) -> int:
    """
    Clean up test resources including jobs, PVCs, and llminferenceservice.

    Args:
        namespace: Namespace containing the resources
        inference_service_name: Name of the LLM inference service
        smoke_job_name: Name of the smoke test job
        benchmark_job_name: Name of the benchmark job (optional)
        cleanup_timeout_seconds: Maximum time to wait for deletions
    """

    execute_tasks(locals())
    return 0


@task
def setup_directories(args, ctx):
    """Create artifact directories"""

    artifacts_dir = args.artifact_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ctx.benchmark_name = args.benchmark_job_name or "guidellm-benchmark"
    return f"Prepared cleanup for namespace {args.namespace}"


@task
def delete_test_resources(args, ctx):
    """Delete smoke test job, benchmark job and related resources"""

    _best_effort_delete(
        "smoke helper job",
        "delete",
        "job",
        args.smoke_job_name,
        "-n",
        args.namespace,
        "--ignore-not-found=true",
    )
    _best_effort_delete(
        "benchmark helper job and pvc",
        "delete",
        "job,pvc",
        ctx.benchmark_name,
        "-n",
        args.namespace,
        "--ignore-not-found=true",
    )
    _best_effort_delete(
        "benchmark helper copy pod",
        "delete",
        "pod",
        f"{ctx.benchmark_name}-copy",
        "-n",
        args.namespace,
        "--ignore-not-found=true",
    )

    return "Deleted test helper resources"


@task
def delete_inference_service(args, ctx):
    """Delete the LLM inference service"""

    _best_effort_delete(
        "llminferenceservice",
        "delete",
        "llminferenceservice",
        args.inference_service_name,
        "-n",
        args.namespace,
        "--ignore-not-found=true",
    )

    return f"Deleted llminferenceservice {args.inference_service_name}"


@retry(attempts=90, delay=10, backoff=1.0)
@task
def wait_for_inference_service_deletion(args, ctx):
    """Wait for the llminferenceservice to be deleted"""

    if not resource_exists(
        "llminferenceservice", args.inference_service_name, namespace=args.namespace
    ):
        return f"llminferenceservice/{args.inference_service_name} deleted from {args.namespace}"

    return (
        False,
        f"Waiting for llminferenceservice/{args.inference_service_name} deletion in {args.namespace}",
    )


@retry(attempts=90, delay=10, backoff=1.0)
@task
def wait_for_workload_pods_deletion(args, ctx):
    """Wait for all llm-d workload pods to be deleted"""

    if _llm_d_pods_gone(args.namespace, args.inference_service_name):
        return f"All llm-d workload pods deleted from {args.namespace}"

    return (False, f"Waiting for llm-d workload pods deletion in {args.namespace}")


def _best_effort_delete(description: str, *oc_args: str) -> None:
    """Best effort deletion of Kubernetes resources with timeout"""
    try:
        oc(*oc_args, check=False)
    except subprocess.TimeoutExpired:
        logger.warning("Timed out deleting %s: oc %s", description, " ".join(oc_args))


def _llm_d_pods_gone(namespace: str, inference_service_name: str) -> bool:
    """Check if all llm-d workload pods are gone"""
    payload = oc_get_json(
        "pods",
        namespace=namespace,
        selector=f"app.kubernetes.io/name={inference_service_name}",
        ignore_not_found=True,
    )
    return not payload or not payload.get("items")


if __name__ == "__main__":
    run.main()
