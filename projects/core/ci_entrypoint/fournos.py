#!/usr/bin/env python3
"""
FOURNOS CI Integration Module

This module handles FOURNOS-specific CI operations including environment
variable processing and configuration transformation.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def process_fournos_environment():
    """
    Process FOURNOS environment variables from forge_config.env file.

    If $ARTIFACT_DIR/forge_config.env exists:
    - Parse it (key=value format)
    - Update environment variables
    - Move the file to CI_METADATA_DIRNAME
    """
    artifact_dir = os.environ.get('ARTIFACT_DIR')
    if not artifact_dir:
        logger.warning("ARTIFACT_DIR not set, cannot process FOURNOS environment")
        return

    artifact_path = Path(artifact_dir)
    env_config_path = artifact_path / "forge_config.env"

    if not env_config_path.exists():
        logger.warning("forge_config.env not found, skipping FOURNOS environment processing")
        return

    try:
        # Read and parse the environment file
        env_vars = {}
        with open(env_config_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '=' not in line:
                    logger.warning(f"Ignoring invalid line {line_num} in {env_config_path}: {line}")
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key:
                    env_vars[key] = value

        logger.info(f"Loaded {len(env_vars)} environment variables from {env_config_path}")

        # Update environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.debug(f"Set environment variable: {key}={value}")

        from .prepare_ci import CI_METADATA_DIRNAME

        # Create CI metadata directory and move the file
        (artifact_path / CI_METADATA_DIRNAME).mkdir(parents=True, exist_ok=True)
        moved_env_path = artifact_path / CI_METADATA_DIRNAME / "forge_config.env"
        env_config_path.rename(moved_env_path)
        logger.info(f"Moved forge_config.env to {moved_env_path}")

    except Exception as e:
        logger.exception(f"Failed to process FOURNOS environment: {e}")
        raise


def transform_fournos_config_to_variable_overrides(forge_config: dict) -> dict:
    """
    Transform FOURNOS forge_config format to variable_overrides format.

    Args:
        forge_config: Dictionary containing FOURNOS config with keys:
                     - project: project name
                     - args: list of arguments
                     - configOverrides: dict of config overrides

    Returns:
        Dictionary in variable_overrides format:
        - project -> project.name
        - args -> project.args
        - configOverrides entries are flattened directly
    """
    variable_overrides = {}

    # Transform project -> project.name
    if 'project' in forge_config:
        variable_overrides['project.name'] = forge_config['project']

    # Transform args -> project.args
    if 'args' in forge_config:
        variable_overrides['project.args'] = forge_config['args']

    # Add all configOverrides entries directly (flatten them)
    config_overrides = forge_config.get('configOverrides', {})
    variable_overrides.update(config_overrides)

    return variable_overrides


def parse_and_save_pr_arguments_fournos() -> Optional[Path]:
    """
    Parse GitHub PR arguments for FOURNOS CI environment.

    Reads forge_config.yaml and converts it to variable_overrides.yaml format.

    Returns:
        Path to saved file if successful, None otherwise
    """
    artifact_dir = os.environ.get('ARTIFACT_DIR')
    if not artifact_dir:
        logger.warning("ARTIFACT_DIR not set, cannot parse FOURNOS config")
        return None

    artifact_path = Path(artifact_dir)
    forge_config_path = artifact_path / "forge_config.yaml"

    if not forge_config_path.exists():
        logger.warning(f"forge_config.yaml not found at '{forge_config_path}', skipping FOURNOS PR argument parsing")
        return None

    try:
        # Read and parse the FOURNOS config
        with open(forge_config_path, 'r') as f:
            forge_config = yaml.safe_load(f)

        logger.info(f"Loaded FOURNOS config from {forge_config_path}")
        logger.debug(f"Config content: {forge_config}")

        from .prepare_ci import CI_METADATA_DIRNAME
        # Create CI metadata directory
        (artifact_path / CI_METADATA_DIRNAME).mkdir(parents=True, exist_ok=True)

        # Move forge_config.yaml to CI metadata directory
        moved_config_path = artifact_path / CI_METADATA_DIRNAME / "forge_config.yaml"
        forge_config_path.rename(moved_config_path)
        logger.info(f"Moved forge_config.yaml to {moved_config_path}")

        # Transform forge_config to variable_overrides format
        variable_overrides = transform_fournos_config_to_variable_overrides(forge_config)

        output_file = artifact_path / CI_METADATA_DIRNAME / "variable_overrides.yaml"
        with open(output_file, 'w') as f:
            yaml.dump(variable_overrides, f, default_flow_style=False, sort_keys=True)

        logger.info(f"Saved FOURNOS variable overrides to {output_file}")
        logger.info(f"Configuration contains {len(variable_overrides)} override(s)")

        return output_file

    except Exception as e:
        logger.exception(f"Failed to parse FOURNOS config: {e}")
        raise
