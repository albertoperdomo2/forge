#!/usr/bin/env python3
"""
llm_d Project PR Arguments Parser

llm_d relies on the framework preset mechanism from `/test fournos llm_d PRESET`.
No llm_d-specific PR directives are currently required.
"""

from __future__ import annotations

from typing import Any


def get_supported_llm_d_directives() -> dict[str, str]:
    """
    Get a dictionary of supported llm_d-specific PR trigger forms.

    Returns:
        Dictionary mapping trigger forms to detailed descriptions
    """
    return {}


def parse_project_directives(comment_text: str) -> tuple[dict[str, Any], list[str]]:
    """
    Parse llm_d-specific behavior from PR trigger comments.

    Args:
        comment_text: Text from PR trigger comment

    Returns:
        Tuple of (configuration overrides dict, list of parsed directive lines)
    """
    _ = comment_text
    return {}, []
