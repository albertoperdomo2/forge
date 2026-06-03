"""
Utilities for the GuideLL-M benchmark toolbox module.
"""

from __future__ import annotations

from typing import Any

import yaml

from projects.core.dsl import template


def render_guidellm_pvc_from_parts(*, namespace: str, name: str, pvc_size: str) -> dict[str, Any]:
    """Render a GuideLL-M PVC manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job and PVC
        pvc_size: Size of the PVC

    Returns:
        PVC manifest as dict
    """
    rendered_yaml = template.render_template(
        "guidellm_pvc.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "pvc_size": pvc_size,
        },
    )
    return yaml.safe_load(rendered_yaml)


def render_guidellm_job_from_parts(
    *,
    namespace: str,
    name: str,
    image: str,
    endpoint_url: str,
    guidellm_args: list[str],
) -> dict[str, Any]:
    """Render a GuideLL-M job manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job
        image: Container image for GuideLLM
        endpoint_url: Gateway endpoint URL
        guidellm_args: Additional arguments for GuideLLM

    Returns:
        Job manifest as dict
    """
    rendered_yaml = template.render_template(
        "guidellm_job.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "image": image,
            "endpoint_url": endpoint_url,
            "guidellm_args": guidellm_args,
        },
    )
    return yaml.safe_load(rendered_yaml)


def render_guidellm_copy_pod_from_parts(
    *,
    namespace: str,
    name: str,
    pvc_size: str,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Render a GuideLL-M copy pod manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job (used for copy pod naming)
        pvc_size: Size of the PVC (not used directly, but kept for interface consistency)
        node_name: Optional node name to pin the pod to

    Returns:
        Pod manifest as dict
    """
    rendered_yaml = template.render_template(
        "guidellm_copy_pod.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "node_name": node_name,
        },
    )
    return yaml.safe_load(rendered_yaml)
