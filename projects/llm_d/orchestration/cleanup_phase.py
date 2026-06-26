from __future__ import annotations

import logging

from projects.core.dsl.utils.k8s import oc_resource_exists
from projects.llm_d.toolbox.cleanup_test_resources import main as cleanup_test_resources_command

logger = logging.getLogger(__name__)


def run(*, namespace: str | None = None) -> int:
    """Delete llm_d runtime leftovers from a namespace."""

    cleanup_namespace(namespace=namespace)
    return 0


def cleanup_namespace(*, namespace: str | None = None) -> None:
    # Load config where it's consumed
    from projects.llm_d.orchestration import runtime_config

    if namespace is None:
        namespace = runtime_config.get_namespace()
    platform = runtime_config.get_platform_config()
    inference_service_name = platform["inference_service"]["name"]
    benchmark_job_names = runtime_config.get_benchmark_job_names()
    # Multiple benchmarks may share a job_name (defaults to "guidellm-benchmark");
    # the broad labeled sweep below deletes every forge-labeled job/pod/pvc
    # regardless, so a single representative name is enough for the named pass.
    benchmark_name = benchmark_job_names[0] if benchmark_job_names else None

    if not oc_resource_exists("namespace", namespace):
        return

    cleanup_test_resources_command.run(
        namespace=namespace,
        inference_service_name=inference_service_name,
        smoke_pod_name=None,  # No specific smoke pod name for runtime cleanup
        benchmark_job_name=benchmark_name,
        cleanup_all_llm_d_resources=True,  # Enable broad cleanup for runtime
    )
