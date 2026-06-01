"""
Utilities for the apply DataScienceCluster toolbox module.
"""

from __future__ import annotations

from typing import Any

from projects.llm_d.runtime.runtime_config import ResolvedConfig, load_yaml


def render_datasciencecluster(config: ResolvedConfig) -> dict[str, Any]:
    """Render a DataScienceCluster manifest from configuration.

    Args:
        config: Resolved configuration

    Returns:
        DataScienceCluster manifest as dict
    """
    template_path = config.config_dir / config.platform["rhoai"]["datasciencecluster_template"]
    manifest = load_yaml(template_path)
    manifest["metadata"]["name"] = config.platform["rhoai"]["datasciencecluster_name"]
    manifest["metadata"]["namespace"] = config.platform["rhoai"]["namespace"]
    return manifest
