#!/usr/bin/env python3
"""
Foreign Testing Project CLI Operations
"""

import foreign_testing
from projects.core.library.cli import safe_cli_command

import logging

logger = logging.getLogger(__name__)

import click
import sys
import types


@click.group()
@click.pass_context
def main(ctx):
    """Foreign Testing Project CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    foreign_testing.init()


@main.command()
@click.pass_context
@safe_cli_command
def submit(ctx):
    """Launch a foreign test."""

    return foreign_testing.submit()


if __name__ == "__main__":
    main()
