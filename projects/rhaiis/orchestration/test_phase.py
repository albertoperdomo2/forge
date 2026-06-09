from __future__ import annotations

import logging

from projects.rhaiis.orchestration import runtime_config

logger = logging.getLogger(__name__)


def run(
    *,
    deployment_name: str,
    namespace: str,
    model_cfg: dict,
    vllm_image: str,
    accelerator: str,
    vllm_args: dict,
    env_vars: dict,
    deploy_cfg: dict,
    benchmark_cfg: dict,
    workload_data: str,
    rates: list[int],
    max_seconds: int,
) -> None:
    from projects.guidellm.toolbox.run_guidellm_benchmark.main import (
        run as run_guidellm_benchmark,
    )
    from projects.rhaiis.toolbox.deploy_kserve_isvc.main import run as deploy_kserve_isvc
    from projects.rhaiis.toolbox.wait_isvc_ready.main import run as wait_isvc_ready

    benchmark_timeout = benchmark_cfg.get("timeout", 14400)

    try:
        logger.info("Deploying %s to %s/%s", model_cfg["hf_model_id"], namespace, deployment_name)
        deploy_kserve_isvc(
            deployment_name=deployment_name,
            namespace=namespace,
            model_id=model_cfg["hf_model_id"],
            vllm_image=vllm_image,
            accelerator=accelerator,
            vllm_args=vllm_args,
            env_vars=env_vars,
            replicas=deploy_cfg.get("replicas", 1),
            cpu_request=deploy_cfg.get("cpu_request", "4"),
            memory_request=deploy_cfg.get("memory_request", "16Gi"),
            storage_source=deploy_cfg.get("storage_source", "hf"),
            storage_pvc=deploy_cfg.get("storage_pvc", ""),
            image_pull_secret=deploy_cfg.get("image_pull_secret", ""),
            service_account_name=deploy_cfg.get("service_account_name", ""),
        )

        logger.info("Waiting for InferenceService to be ready")
        wait_isvc_ready(
            name=deployment_name,
            namespace=namespace,
            timeout_seconds=deploy_cfg.get("ready_timeout", 3600),
            health_check_timeout=deploy_cfg.get("health_check_timeout", 120),
        )

        endpoint_url = f"http://{deployment_name}-predictor.{namespace}.svc.cluster.local:8080"

        rates_str = ",".join(str(r) for r in rates)
        logger.info("Running benchmark at rates=%s", rates_str)

        benchmark_image = benchmark_cfg.get("image", "ghcr.io/vllm-project/guidellm:v0.6.0")
        image, version = runtime_config.split_image_tag(benchmark_image)

        guidellm_args = runtime_config.build_guidellm_args(
            benchmark_cfg=benchmark_cfg,
            model_id=model_cfg["hf_model_id"],
            data=workload_data,
            rates_str=rates_str,
            max_seconds=max_seconds,
        )

        run_guidellm_benchmark(
            endpoint_url=f"{endpoint_url}/v1",
            name=f"guidellm-{deployment_name}",
            namespace=namespace,
            image=image,
            version=version,
            timeout=benchmark_timeout,
            pvc_size=benchmark_cfg.get("pvc_size", "5Gi"),
            guidellm_args=guidellm_args,
        )
    finally:
        _capture_and_cleanup(deployment_name, namespace)


def _capture_and_cleanup(deployment_name: str, namespace: str) -> None:
    from projects.rhaiis.toolbox.capture_isvc_state.main import run as capture_isvc_state

    logger.info("Capturing state")
    try:
        capture_isvc_state(name=deployment_name, namespace=namespace)
    except Exception:
        logger.warning("Capture failed, continuing with cleanup")

    from projects.rhaiis.toolbox.cleanup_isvc.main import run as cleanup_isvc

    logger.info("Cleaning up")
    try:
        cleanup_isvc(name=deployment_name, namespace=namespace)
    except Exception:
        logger.warning("Cleanup failed")
