"""
Utilities for the ensure gateway toolbox module.
"""

from __future__ import annotations

from typing import Any

from projects.llm_d.runtime.runtime_config import ResolvedConfig, load_yaml


def render_gateway(config: ResolvedConfig) -> dict[str, Any]:
    """Render a Gateway manifest from configuration.

    Args:
        config: Resolved configuration

    Returns:
        Gateway manifest as dict
    """
    template_path = config.config_dir / config.platform["gateway"]["manifest_template"]
    manifest = load_yaml(template_path)
    manifest["metadata"]["name"] = config.platform["gateway"]["name"]
    manifest["metadata"]["namespace"] = config.platform["gateway"]["namespace"]
    manifest["spec"]["gatewayClassName"] = config.platform["gateway"]["gateway_class_name"]
    return manifest
