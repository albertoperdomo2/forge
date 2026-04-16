#!/usr/bin/env python3

from __future__ import annotations

from projects.core.dsl import toolbox
from projects.llm_d.orchestration import llmd_runtime


def run() -> int:
    llmd_runtime.init()
    config = llmd_runtime.load_run_configuration()
    return run_cleanup(config)


def run_cleanup(config: llmd_runtime.ResolvedConfig) -> int:
    delete_run_leftovers(config)
    return 0


def delete_run_leftovers(config: llmd_runtime.ResolvedConfig) -> None:
    if not llmd_runtime.resource_exists("namespace", config.namespace):
        return

    inference_service_name = config.platform["inference_service"]["name"]
    namespace = config.namespace
    cleanup_timeout_seconds = config.platform["cluster"]["cleanup_timeout_seconds"]
    benchmark_names = {"guidellm-benchmark"}
    if config.benchmark:
        benchmark_names.add(config.benchmark["job_name"])

    llmd_runtime.oc(
        "delete",
        "llminferenceservice",
        inference_service_name,
        "-n",
        namespace,
        "--ignore-not-found=true",
        check=False,
    )

    for benchmark_name in sorted(benchmark_names):
        llmd_runtime.oc(
            "delete",
            "job,pvc",
            benchmark_name,
            "-n",
            namespace,
            "--ignore-not-found=true",
            check=False,
        )
        llmd_runtime.oc(
            "delete",
            "pod",
            f"{benchmark_name}-copy",
            "-n",
            namespace,
            "--ignore-not-found=true",
            check=False,
        )

    llmd_runtime.oc(
        "delete",
        "job",
        "-n",
        namespace,
        "-l",
        "forge.openshift.io/project=llm_d",
        "--ignore-not-found=true",
        check=False,
    )
    llmd_runtime.oc(
        "delete",
        "pod",
        "-n",
        namespace,
        "-l",
        "forge.openshift.io/project=llm_d",
        "--ignore-not-found=true",
        check=False,
    )
    llmd_runtime.oc(
        "delete",
        "pvc",
        "-n",
        namespace,
        "-l",
        "forge.openshift.io/project=llm_d,forge.openshift.io/preserve!=true",
        "--ignore-not-found=true",
        check=False,
    )

    llmd_runtime.wait_until(
        f"llminferenceservice/{inference_service_name} deletion in {namespace}",
        timeout_seconds=cleanup_timeout_seconds,
        interval_seconds=10,
        predicate=lambda: not llmd_runtime.resource_exists(
            "llminferenceservice", inference_service_name, namespace=namespace
        ),
    )

    llmd_runtime.wait_until(
        f"llm-d workload pods deletion in {namespace}",
        timeout_seconds=cleanup_timeout_seconds,
        interval_seconds=10,
        predicate=lambda: _llm_d_pods_gone(namespace, inference_service_name),
    )


def _llm_d_pods_gone(namespace: str, inference_service_name: str) -> bool:
    payload = llmd_runtime.oc_get_json(
        "pods",
        namespace=namespace,
        selector=f"app.kubernetes.io/name={inference_service_name}",
        ignore_not_found=True,
    )
    return not payload or not payload.get("items")


main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
