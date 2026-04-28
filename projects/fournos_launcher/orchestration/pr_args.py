#!/usr/bin/env python3
"""
FOURNOS PR Arguments Parser

Parses PR trigger comment for FOURNOS-specific directives and applies them to configuration.
"""

import logging

import yaml

from projects.core.ci_entrypoint.prepare_ci import CI_METADATA_DIRNAME
from projects.core.library import env
from projects.core.library.config import VARIABLE_OVERRIDES_FILENAME

logger = logging.getLogger(__name__)


def handle_cluster_directive(line: str) -> dict[str, str]:
    """
    Handle /cluster directive for setting cluster override.

    Format: /cluster cluster_name

    Args:
        line: The directive line

    Returns:
        Dictionary with cluster configuration

    Raises:
        ValueError: If cluster_name is empty
    """
    cluster_name = line[9:].strip()

    if not cluster_name:
        raise ValueError(f"Invalid /cluster directive: cluster name cannot be empty in '{line}'")

    return {"cluster.name": cluster_name}


def parse_fournos_directives(comment_text: str) -> tuple[dict[str, str], list[str]]:
    """
    Parse FOURNOS-specific directives from PR trigger comment.

    Supported directives:
    - /cluster NAME: Sets cluster.name to NAME

    Args:
        comment_text: Text from PR trigger comment

    Returns:
        Tuple of (configuration overrides dict, list of parsed directive lines)
    """
    config_overrides = {}
    parsed_directives = []

    for line in comment_text.split("\n"):
        line = line.strip()

        # Skip empty lines and non-directive lines
        if not line or not line.startswith("/"):
            continue

        # Handle /cluster directive
        if line.startswith("/cluster "):
            try:
                result = handle_cluster_directive(line)
                config_overrides.update(result)
                parsed_directives.append(line)
                logger.info(f"Parsed FOURNOS directive: {line} -> {result}")
            except Exception as e:
                logger.warning(f"Failed to parse cluster directive '{line}': {e}")

    return config_overrides, parsed_directives


def apply_pr_directives() -> bool:
    """
    Apply PR trigger comment directives to configuration.

    Reads pr_trigger_comment.txt from CI metadata directory and writes
    any FOURNOS-specific configuration directives to variable_overrides.yaml.

    Returns:
        True if directives were found and applied, False otherwise
    """
    pr_comment_file = env.ARTIFACT_DIR / CI_METADATA_DIRNAME / "pr_trigger_comment.txt"

    # Guard: Check if file exists
    if not pr_comment_file.exists():
        logger.debug("No PR trigger comment file found")
        return False

    # Guard: Try to read the file
    try:
        with open(pr_comment_file) as f:
            comment_text = f.read()
    except Exception as e:
        logger.warning(f"Failed to read PR trigger comment: {e}")
        return False

    # Parse directives from comment
    config_overrides, parsed_directives = parse_fournos_directives(comment_text)

    if not config_overrides:
        logger.debug("No FOURNOS directives found in PR trigger comment")
        return False

    # Append to variable_overrides.yaml
    variable_overrides_path = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME
    variable_overrides_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing overrides if file exists
    existing_overrides = {}
    if variable_overrides_path.exists():
        try:
            with open(variable_overrides_path) as f:
                existing_overrides = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to read existing variable overrides: {e}")

    # Merge new overrides with existing ones
    existing_overrides.update(config_overrides)

    with open(variable_overrides_path, "w") as f:
        yaml.dump(existing_overrides, f, default_flow_style=False, sort_keys=True)

    # Also append original directive text to pr_config.txt
    pr_config_path = env.ARTIFACT_DIR / CI_METADATA_DIRNAME / "pr_config.txt"
    with open(pr_config_path, "a") as f:
        for directive in parsed_directives:
            f.write(f"{directive}\n")

    logger.info(f"Written {len(config_overrides)} PR directive(s) to {variable_overrides_path}")
    logger.info(f"Written {len(config_overrides)} PR directive(s) to {pr_config_path}")
    for key, value in config_overrides.items():
        logger.info(f"Applied PR directive: {key} = {value}")

    return True
