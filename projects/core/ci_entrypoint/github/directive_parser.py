#!/usr/bin/env python3
"""
Shared directive parsing utilities for PR comment processing.

Provides common parsing logic that can be used across different systems
(GitHub PR args, FOURNOS launcher, etc.) to handle comment directives.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def parse_directives_generic(
    text: str,
    directive_handlers: dict[str, Callable[[str], dict[str, Any]]],
    system_name: str = "generic",
    required_directives: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """
    Generic directive parsing logic shared across systems.

    Args:
        text: Text containing directives (PR body + comments)
        directive_handlers: Dictionary mapping directive prefixes to handler functions
        system_name: Name of the system for logging (e.g., "GitHub", "FOURNOS")
        required_directives: List of required directive prefixes (e.g., ["/test"])

    Returns:
        Tuple of (configuration dictionary, list of found directive lines)

    Raises:
        ValueError: If any directive has invalid format or required directives are missing
    """
    config = {}
    found_directives = []

    for line in text.split("\n"):
        line = line.strip()

        # Guards: skip what we don't process
        if not line or not line.startswith("/"):
            continue

        # Get directive name and look up handler directly
        directive = line.split()[0]
        handler = directive_handlers.get(directive)

        # Guard: skip unknown directives
        if not handler:
            logger.debug(f"Unknown {system_name} directive ignored: {directive}")
            continue

        # Process directive
        try:
            result = handler(line)
            config.update(result)
            found_directives.append(line)
            logger.debug(
                f"Parsed {system_name} directive: {line} -> {result if result else 'processed'}"
            )
        except Exception as e:
            raise ValueError(f"Error parsing {system_name} directive '{line}': {e}") from e

    # Optional validation for required directives
    if required_directives:
        for req in required_directives:
            if not any(d.startswith(req) for d in found_directives):
                raise ValueError(f"{req} directive not found in the PR last comment")

    return config, found_directives


def create_help_directive_handler(
    directives_dict: dict[str, str],
    system_name: str,
    format_help_func: Callable[[dict[str, str], str], str],
) -> Callable[[str], dict[str, Any]]:
    """
    Factory function to create standard help directive handlers.

    Args:
        directives_dict: Dictionary of supported directives and descriptions
        system_name: Name of the system (e.g., "GitHub", "FOURNOS")
        format_help_func: Function to format help text (e.g., format_help_text)

    Returns:
        Help directive handler function
    """

    def handle_help_directive(line: str) -> dict[str, Any]:
        """Handle /help directive for showing supported directives."""
        help_text = "\n" + format_help_func(directives_dict, f"Supported {system_name} directives")

        # Store help text for pr_config.txt writing
        handle_help_directive._help_text = help_text

        logger.info(
            f"Help directive processed - {system_name} directive information will be written to pr_config.txt"
        )

        return {}

    return handle_help_directive
