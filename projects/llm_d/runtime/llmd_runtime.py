from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

# Import generic K8s utilities from core DSL
from projects.core.dsl.utils.k8s import (
    CommandError,
    apply_manifest,
    condition_status,
    ensure_namespace,
    job_pod_names,
    oc,
    oc_get_json,
    resource_exists,
    run_command,
    wait_for_crd,
    wait_for_job_completion,
    wait_for_namespace_deleted,
    wait_for_pvc_bound,
    wait_until,
)
from projects.llm_d.runtime.runtime_config import (
    CONFIG_DIR,
    ORCHESTRATION_DIR,
    ModelCacheSpec,
    ResolvedConfig,
    derive_namespace,
    ensure_artifact_directories,
    init,
    load_run_configuration,
    load_yaml,
    normalize_gpu_count,
    resolve_model_cache,
    resolve_model_cache_spec,
    slugify_identifier,
    truncate_k8s_name,
    version_tuple,
    write_json,
    write_text,
    write_yaml,
)
from projects.llm_d.runtime.runtime_manifests import (
    load_manifest_template,
    render_datasciencecluster,
    render_gateway,
    render_guidellm_copy_pod,
    render_guidellm_copy_pod_from_parts,
    render_guidellm_job,
    render_guidellm_job_from_parts,
    render_guidellm_pvc,
    render_guidellm_pvc_from_parts,
    render_inference_service,
    render_inference_service_from_parts,
    render_model_cache_pvc,
    render_smoke_request_job,
    render_smoke_request_job_from_parts,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CONFIG_DIR",
    "ORCHESTRATION_DIR",
    "CommandError",
    "ModelCacheSpec",
    "ResolvedConfig",
    "annotate_model_cache_pvc",
    "apply_manifest",
    "condition_status",
    "derive_namespace",
    "desired_subscription",
    "ensure_artifact_directories",
    "ensure_namespace",
    "ensure_operator_group",
    "ensure_subscription",
    "init",
    "job_pod_names",
    "load_manifest_template",
    "load_run_configuration",
    "load_yaml",
    "model_cache_pvc_ready",
    "normalize_gpu_count",
    "oc",
    "oc_get_json",
    "operator_spec_by_package",
    "pvc_access_mode_matches",
    "render_datasciencecluster",
    "render_gateway",
    "render_guidellm_copy_pod",
    "render_guidellm_copy_pod_from_parts",
    "render_guidellm_job",
    "render_guidellm_job_from_parts",
    "render_guidellm_pvc",
    "render_guidellm_pvc_from_parts",
    "render_inference_service",
    "render_inference_service_from_parts",
    "render_model_cache_job",
    "render_model_cache_pvc",
    "render_smoke_request_job",
    "render_smoke_request_job_from_parts",
    "resource_exists",
    "resolve_default_serviceaccount_image_pull_secret",
    "resolve_model_cache",
    "resolve_model_cache_spec",
    "run_command",
    "slugify_identifier",
    "subscription_spec_matches",
    "truncate_k8s_name",
    "version_tuple",
    "wait_for_crd",
    "wait_for_job_completion",
    "wait_for_namespace_deleted",
    "wait_for_operator_csv",
    "wait_for_pvc_bound",
    "wait_until",
    "write_json",
    "write_text",
    "write_yaml",
]


def wait_for_operator_csv(package: str, namespace: str, timeout_seconds: int) -> dict[str, Any]:
    """Wait for an operator CSV to be ready in the specified namespace.

    This is LLM-D specific as it deals with operator lifecycle management.
    """
    selector = f"operators.coreos.com/{package}.{namespace}"

    def _csv_ready() -> dict[str, Any] | None:
        data = oc_get_json("csv", namespace=namespace, selector=selector, ignore_not_found=True)
        if not data:
            return None
        items = data.get("items", [])
        if not items:
            return None
        csv = items[0]
        if csv.get("status", {}).get("phase") == "Succeeded":
            return csv
        return None

    return wait_until(
        f"{package} CSV in {namespace}",
        timeout_seconds=timeout_seconds,
        interval_seconds=15,
        predicate=_csv_ready,
    )


def ensure_operator_group(namespace: str, package: str) -> None:
    data = oc_get_json("operatorgroup", namespace=namespace, ignore_not_found=True)
    if data and data.get("items"):
        for item in data["items"]:
            targets = item.get("spec", {}).get("targetNamespaces") or [namespace]
            if namespace in targets:
                return
        raise RuntimeError(
            f"Existing OperatorGroup objects in {namespace} do not target {namespace}"
        )

    operator_group = {
        "apiVersion": "operators.coreos.com/v1",
        "kind": "OperatorGroup",
        "metadata": {"name": package, "namespace": namespace},
        "spec": {"targetNamespaces": [namespace]},
    }
    oc("apply", "-f", "-", input_text=yaml.safe_dump(operator_group, sort_keys=False))


def ensure_subscription(operator_spec: dict[str, Any]) -> None:
    namespace = operator_spec["namespace"]
    package = operator_spec["package"]

    ensure_namespace(namespace)
    ensure_operator_group(namespace, package)

    subscription = desired_subscription(operator_spec)
    current = oc_get_json(
        "subscription.operators.coreos.com",
        name=package,
        namespace=namespace,
        ignore_not_found=True,
    )
    if current and not subscription_spec_matches(current.get("spec", {}), subscription["spec"]):
        logger.info("Reconciling subscription drift for %s in %s", package, namespace)

    oc("apply", "-f", "-", input_text=yaml.safe_dump(subscription, sort_keys=False))

    def _subscription_reconciled() -> dict[str, Any] | None:
        payload = oc_get_json(
            "subscription.operators.coreos.com",
            name=package,
            namespace=namespace,
        )
        if subscription_spec_matches(payload.get("spec", {}), subscription["spec"]):
            return payload
        return None

    wait_until(
        f"subscription/{package} reconciliation in {namespace}",
        timeout_seconds=60,
        interval_seconds=5,
        predicate=_subscription_reconciled,
    )


def desired_subscription(operator_spec: dict[str, Any]) -> dict[str, Any]:
    namespace = operator_spec["namespace"]
    package = operator_spec["package"]
    return {
        "apiVersion": "operators.coreos.com/v1alpha1",
        "kind": "Subscription",
        "metadata": {"name": package, "namespace": namespace},
        "spec": {
            "channel": operator_spec["channel"],
            "installPlanApproval": "Automatic",
            "name": package,
            "source": operator_spec["source"],
            "sourceNamespace": operator_spec.get("source_namespace", "openshift-marketplace"),
        },
    }


def subscription_spec_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    keys = ("channel", "installPlanApproval", "name", "source", "sourceNamespace")
    return all(actual.get(key) == expected.get(key) for key in keys)


def operator_spec_by_package(platform: dict[str, Any], package: str) -> dict[str, Any]:
    operators = platform["operators"]
    if isinstance(operators, dict):
        if package in operators:
            return {"package": package, **operators[package]}
        raise KeyError(f"Unknown operator package in llm_d platform config: {package}")

    for operator_spec in operators:
        if operator_spec["package"] == package:
            return operator_spec
    raise KeyError(f"Unknown operator package in llm_d platform config: {package}")


def pvc_access_mode_matches(actual_modes: list[str], expected_mode: str) -> bool:
    return expected_mode in actual_modes


def resolve_default_serviceaccount_image_pull_secret(namespace: str) -> str | None:
    payload = oc_get_json(
        "serviceaccount", name="default", namespace=namespace, ignore_not_found=True
    )
    if not payload:
        return None

    for item in payload.get("imagePullSecrets", []):
        name = item.get("name")
        if name:
            return name
    return None


def load_runtime_script(name: str) -> str:
    script_path = Path(__file__).resolve().parent / "scripts" / name
    return script_path.read_text(encoding="utf-8")


def render_model_cache_job(config: ResolvedConfig, spec: ModelCacheSpec) -> dict[str, Any]:
    common_env = [
        {"name": "MODEL_SOURCE", "value": spec.source_uri},
        {"name": "MODEL_TARGET_DIR", "value": f"/cache/{spec.model_path}"},
        {"name": "MARKER_FILE", "value": spec.marker_path},
        {"name": "CACHE_KEY", "value": spec.cache_key},
    ]
    volumes: list[dict[str, Any]] = [
        {"name": "cache", "persistentVolumeClaim": {"claimName": spec.pvc_name}}
    ]

    if spec.source_scheme == "hf":
        command = load_runtime_script("download_hf_model.sh")
        volume_mounts = [{"name": "cache", "mountPath": "/cache"}]
        if spec.hf_token_secret_name:
            volumes.append(
                {"name": "hf-token", "secret": {"secretName": spec.hf_token_secret_name}}
            )
            volume_mounts.append(
                {
                    "name": "hf-token",
                    "mountPath": "/var/run/forge/hf-token",
                    "readOnly": True,
                }
            )
            common_env.append(
                {
                    "name": "HF_TOKEN_FILE",
                    "value": f"/var/run/forge/hf-token/{spec.hf_token_secret_key}",
                }
            )

        container = {
            "name": "hf-model-downloader",
            "image": config.model_cache["hf"]["downloader_image"],
            "imagePullPolicy": config.model_cache["download"]["pod_image_pull_policy"],
            "command": ["/bin/bash", "-ceu", command],
            "env": common_env,
            "volumeMounts": volume_mounts,
        }
    elif spec.source_scheme == "oci":
        registry_auth_secret_name = (
            spec.oci_registry_auth_secret_name
            or resolve_default_serviceaccount_image_pull_secret(spec.namespace)
        )
        command = load_runtime_script("extract_oci_model.sh")
        volume_mounts = [{"name": "cache", "mountPath": "/cache"}]
        common_env.append({"name": "OCI_IMAGE_PATH", "value": spec.oci_image_path or "/"})
        if registry_auth_secret_name:
            volumes.append(
                {"name": "registry-auth", "secret": {"secretName": registry_auth_secret_name}}
            )
            volume_mounts.append(
                {
                    "name": "registry-auth",
                    "mountPath": "/var/run/forge/registry-auth",
                    "readOnly": True,
                }
            )
            common_env.append(
                {
                    "name": "REGISTRY_AUTH_FILE",
                    "value": f"/var/run/forge/registry-auth/{spec.oci_registry_auth_secret_key}",
                }
            )

        container = {
            "name": "oci-model-extractor",
            "image": config.model_cache["oci"]["extractor_image"],
            "imagePullPolicy": config.model_cache["download"]["pod_image_pull_policy"],
            "command": ["/bin/bash", "-ceu", command],
            "env": common_env,
            "volumeMounts": volume_mounts,
        }
    else:  # pragma: no cover - guarded by resolve_model_cache
        raise ValueError(f"Unsupported model cache source scheme: {spec.source_scheme}")

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": spec.download_job_name,
            "namespace": spec.namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "forge",
                "forge.openshift.io/project": "llm_d",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": config.model_cache["download"]["wait_timeout_seconds"],
            "template": {
                "metadata": {
                    "labels": {
                        "job-name": spec.download_job_name,
                        "app.kubernetes.io/managed-by": "forge",
                        "forge.openshift.io/project": "llm_d",
                    }
                },
                "spec": {
                    "serviceAccountName": "default",
                    "restartPolicy": "Never",
                    "containers": [container],
                    "volumes": volumes,
                },
            },
        },
    }


def model_cache_pvc_ready(spec: ModelCacheSpec) -> bool:
    payload = oc_get_json(
        "persistentvolumeclaim",
        name=spec.pvc_name,
        namespace=spec.namespace,
        ignore_not_found=True,
    )
    if not payload:
        return False

    annotations = payload.get("metadata", {}).get("annotations", {})
    return (
        annotations.get("forge.openshift.io/model-cache-ready") == "true"
        and annotations.get("forge.openshift.io/model-cache-key") == spec.cache_key
        and annotations.get("forge.openshift.io/model-source-uri") == spec.source_uri
    )


def annotate_model_cache_pvc(spec: ModelCacheSpec) -> None:
    oc(
        "annotate",
        "persistentvolumeclaim",
        spec.pvc_name,
        "-n",
        spec.namespace,
        "--overwrite",
        "forge.openshift.io/model-cache-ready=true",
        f"forge.openshift.io/model-cache-key={spec.cache_key}",
        f"forge.openshift.io/model-source-uri={spec.source_uri}",
        f"forge.openshift.io/model-uri={spec.model_uri}",
    )
