"""
Kubernetes utilities for orchestration tasks
"""

from projects.core.dsl.utils.k8s import oc, oc_resource_exists


def ensure_namespace(namespace: str, *, labels: dict[str, str] | None = None) -> None:
    """Ensure a namespace exists, creating it if necessary.

    Args:
        namespace: Namespace name
        labels: Labels to apply to the namespace
    """
    if not oc_resource_exists("namespace", namespace):
        oc("create", "namespace", namespace)

    if labels:
        oc("label", "namespace", namespace, "--overwrite", *[f"{k}={v}" for k, v in labels.items()])
