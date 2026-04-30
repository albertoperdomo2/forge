"""
Shared Caliper “artifacts export” CLI for FORGE project orchestration.

Registers a :mod:`click` subcommand that reads ``caliper`` from project config and runs
:func:`projects.caliper.orchestration.export.run_from_orchestration_config`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click
import yaml

from projects.caliper.orchestration.export import run_from_orchestration_config
from projects.core.library import ci as ci_lib
from projects.core.library import config

logger = logging.getLogger(__name__)


def run_caliper_orchestration_export(*, artifact_directory: Path | None):
    """Set optional ``caliper.export.from`` and run orchestration export."""

    if artifact_directory is None and "ARTIFACT_BASE_DIR" in os.environ:
        artifact_directory = os.environ["ARTIFACT_BASE_DIR"]

    if artifact_directory is not None:
        config.project.set_config("caliper.export.from", str(artifact_directory))

    # Use FJOB_NAME as fallback for mlflow run_name if not configured
    run_name = config.project.get_config(
        "caliper.export.backend.mlflow.config.run_name", None, print=False, warn=False
    )
    if run_name is None and "FJOB_NAME" in os.environ:
        config.project.set_config(
            "caliper.export.backend.mlflow.config.run_name", os.environ["FJOB_NAME"], print=False
        )

    caliper_cfg = config.project.get_config("caliper", print=False)

    return run_from_orchestration_config(caliper_cfg)


@click.command("export-artifacts")
@click.option(
    "--artifact-directory",
    "artifact_directory",
    type=click.Path(path_type=Path, exists=False, file_okay=True, dir_okay=True),
    default=None,
    help="If set, overrides caliper.export.from (artifact root directory).",
)
@click.pass_context
@ci_lib.safe_ci_command
def caliper_export_command(_ctx, artifact_directory: Path | None):
    """Export the file artifacts."""

    status = run_caliper_orchestration_export(artifact_directory=artifact_directory)
    logger.info("Export status:\n" + yaml.dump(status, indent=4))
    return 0
