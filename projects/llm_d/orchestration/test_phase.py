from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from projects.core.dsl import shell
from projects.guidellm.toolbox.run_guidellm_benchmark import main as run_guidellm_benchmark_command
from projects.guidellm.toolbox.run_smoke_request import main as run_smoke_request_command
from projects.kserve.toolbox.capture_llmisvc_state import main as capture_llmisvc_state
from projects.kserve.toolbox.deploy_llmisvc import main as deploy_llmisvc
from projects.llm_d.orchestration.runtime_config import init as runtime_init
from projects.llm_d.toolbox.cleanup_test_resources import main as cleanup_test_resources_command

logger = logging.getLogger(__name__)


def run(
    *,
    config_dir: str,
    namespace: str,
    inference_service: dict,
    gateway: dict,
    model_key: str,
    model: dict,
    scheduler_profile_key: str,
    scheduler_profile: dict | None,
    model_cache: dict,
    smoke: dict,
    smoke_request: dict,
    benchmark: dict | None = None,
    capture_namespace_events: bool = True,
) -> int:
    artifact_dir = runtime_init()

    endpoint_url: str | None = None
    primary_exc: tuple[type[BaseException], BaseException, Any] | None = None
    finalizer_exc: tuple[type[BaseException], BaseException, Any] | None = None

    try:
        endpoint_url = deploy_inference_service(
            config_dir=config_dir,
            namespace=namespace,
            inference_service=inference_service,
            gateway=gateway,
            model_key=model_key,
            model=model,
            scheduler_profile_key=scheduler_profile_key,
            scheduler_profile=scheduler_profile,
            model_cache=model_cache,
        )
        run_smoke_request(
            namespace=namespace,
            smoke=smoke,
            model=model,
            smoke_request=smoke_request,
            endpoint_url=endpoint_url,
        )
        run_guidellm_benchmark(
            namespace=namespace,
            benchmark=benchmark,
            endpoint_url=endpoint_url,
        )
    except Exception:
        primary_exc = sys.exc_info()
    finally:
        finalizer_exc = _run_finalizer(
            primary_exc,
            finalizer_exc,
            "capture inference-service state",
            capture_inference_service_state,
            namespace=namespace,
            inference_service=inference_service,
        )
        finalizer_exc = _run_finalizer(
            primary_exc,
            finalizer_exc,
            "write endpoint URL",
            write_endpoint_url,
            artifact_dir=artifact_dir,
            endpoint_url=endpoint_url,
        )
        finalizer_exc = _run_finalizer(
            primary_exc,
            finalizer_exc,
            "cleanup runtime resources",
            cleanup_test_resources,
            namespace=namespace,
            inference_service=inference_service,
            smoke=smoke,
            benchmark=benchmark,
        )
        finalizer_exc = _run_finalizer(
            primary_exc,
            finalizer_exc,
            "capture namespace events",
            capture_namespace_events_after_test,
            artifact_dir=artifact_dir,
            namespace=namespace,
            capture_namespace_events=capture_namespace_events,
        )

    if primary_exc is not None:
        raise primary_exc[1].with_traceback(primary_exc[2])
    if finalizer_exc is not None:
        raise finalizer_exc[1].with_traceback(finalizer_exc[2])

    return 0


def deploy_inference_service(
    *,
    config_dir: str,
    namespace: str,
    inference_service: dict,
    gateway: dict,
    model_key: str,
    model: dict,
    scheduler_profile_key: str,
    scheduler_profile: dict | None,
    model_cache: dict,
) -> str:
    return deploy_llmisvc.run(
        config_dir=config_dir,
        namespace=namespace,
        inference_service=inference_service,
        gateway=gateway,
        model_key=model_key,
        model=model,
        scheduler_profile_key=scheduler_profile_key,
        scheduler_profile=scheduler_profile,
        model_cache=model_cache,
    )


def run_smoke_request(
    *,
    namespace: str,
    smoke: dict,
    model: dict,
    smoke_request: dict,
    endpoint_url: str,
) -> dict[str, object]:
    return run_smoke_request_command.run(
        namespace=namespace,
        smoke=smoke,
        model=model,
        smoke_request=smoke_request,
        endpoint_url=endpoint_url,
    )


def run_guidellm_benchmark(*, namespace: str, benchmark: dict | None, endpoint_url: str) -> None:
    if not benchmark:
        return

    run_guidellm_benchmark_command.run(
        namespace=namespace,
        benchmark=benchmark,
        endpoint_url=endpoint_url,
    )


def capture_inference_service_state(*, namespace: str, inference_service: dict) -> None:
    capture_llmisvc_state.run(
        llmisvc_name=inference_service["name"],
        namespace=namespace,
    )


def write_endpoint_url(*, artifact_dir: Path, endpoint_url: str | None) -> None:
    if not endpoint_url:
        return

    endpoint_file = artifact_dir / "artifacts" / "endpoint.url"
    endpoint_file.parent.mkdir(parents=True, exist_ok=True)
    endpoint_file.write_text(f"{endpoint_url}\n", encoding="utf-8")


def cleanup_test_resources(
    *,
    namespace: str,
    inference_service: dict,
    smoke: dict,
    benchmark: dict | None,
) -> None:
    """Cleanup test resources using the toolbox script"""
    benchmark_job_name = benchmark["job_name"] if benchmark else None

    cleanup_test_resources_command.run(
        namespace=namespace,
        inference_service_name=inference_service["name"],
        smoke_job_name=smoke["job_name"],
        benchmark_job_name=benchmark_job_name,
    )


def capture_namespace_events_after_test(
    *,
    artifact_dir: Path,
    namespace: str,
    capture_namespace_events: bool,
) -> None:
    if not capture_namespace_events:
        return

    shell.run(
        f"oc get events -n {namespace} --sort-by=.metadata.creationTimestamp",
        check=False,
        stdout_dest=artifact_dir / "artifacts" / "namespace.events.txt",
    )


def _run_finalizer(
    primary_exc: tuple[type[BaseException], BaseException, Any] | None,
    finalizer_exc: tuple[type[BaseException], BaseException, Any] | None,
    description: str,
    callback,
    **kwargs,
) -> tuple[type[BaseException], BaseException, Any] | None:
    try:
        callback(**kwargs)
    except Exception:
        if primary_exc is None:
            logger.exception("Finalizer failed: %s", description)
            return finalizer_exc or sys.exc_info()
        logger.exception("Ignoring %s failure after primary test failure", description)
    return finalizer_exc
