#!/usr/bin/env python3
"""
Skeleton Project PR Arguments Parser

Parses skeleton-specific directives from PR trigger comments.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_supported_skeleton_directives() -> dict[str, str]:
    """
    Get a dictionary of supported skeleton-specific directives and their descriptions.

    Returns:
        Dictionary mapping directive names to detailed descriptions
    """
    return {
        "/skel.ns": """Set skeleton namespace for test execution.
                      Format: /skel.ns NAME
                      Example: /skel.ns test-namespace
                      Effect: Sets skeleton.namespace in configuration.""",
    }


def handle_skel_ns_directive(line: str) -> dict[str, Any]:
    """
    Handle /skel.ns directive for setting skeleton namespace.

    Format: /skel.ns NAME

    Args:
        line: The directive line

    Returns:
        Dictionary with namespace configuration

    Raises:
        ValueError: If namespace name is empty
    """
    namespace_name = line.removeprefix("/skel.ns ").strip()

    if not namespace_name:
        raise ValueError(f"Invalid /skel.ns directive: namespace name cannot be empty in '{line}'")

    return {"skeleton.namespace": namespace_name}


def get_skeleton_directive_handlers() -> dict[str, callable]:
    """
    Get a mapping of skeleton directive prefixes to their handler functions.

    Returns:
        Dictionary mapping directive prefixes to handler functions
    """
    return {
        "/skel.ns": handle_skel_ns_directive,
    }


def parse_project_directives(comment_text: str) -> tuple[dict[str, Any], list[str]]:
    """
    Parse skeleton-specific directives from PR trigger comment.

    Args:
        comment_text: Text from PR trigger comment

    Returns:
        Tuple of (configuration overrides dict, list of parsed directive lines)
    """
    directive_handlers = get_skeleton_directive_handlers()
    config_overrides = {}
    parsed_directives = []

    # Parse lines looking for skeleton directives
    for line in comment_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Check if this line matches any skeleton directive
        for prefix, handler in directive_handlers.items():
            if line.startswith(prefix):
                try:
                    result = handler(line)
                    config_overrides.update(result)
                    parsed_directives.append(line)
                    logger.info(f"Parsed skeleton directive: {line}")
                except Exception as e:
                    logger.error(f"Failed to parse skeleton directive '{line}': {e}")
                break

    return config_overrides, parsed_directives
