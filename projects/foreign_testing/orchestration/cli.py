#!/usr/bin/env python3
"""
Foreign Testing Project CLI Operations
"""

import logging
import pathlib
import types

import click
import foreign_testing

from projects.core.library.cli import safe_cli_command

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def main(ctx):
    """Foreign Testing Project CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    foreign_testing.init()


@main.command()
@click.option(
    "--project-path",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    help="Path to the project source directory",
)
@click.pass_context
@safe_cli_command
def submit(ctx, project_path):
    """Launch a foreign test."""

    return foreign_testing.submit(project_path=project_path)


if __name__ == "__main__":
    main()
