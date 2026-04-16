#!/usr/bin/env python3
"""
LLM-D Project CLI Operations
"""

import logging
import sys
import types

import click
import prepare_llmd
import test_llmd

from projects.core.library.cli import safe_cli_command

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def main(ctx):
    """LLM-D Project CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    test_llmd.init()


@main.command()
@click.pass_context
@safe_cli_command
def prepare(ctx):
    """Prepare phase - Set up environment and dependencies."""
    exit_code = prepare_llmd.prepare()
    sys.exit(exit_code)


@main.command()
@click.pass_context
@safe_cli_command
def test(ctx):
    """Test phase - Execute the main testing logic."""
    exit_code = test_llmd.test()
    sys.exit(exit_code)


@main.command()
@click.pass_context
@safe_cli_command
def pre_cleanup(ctx):
    """Cleanup phase - Clean up resources and finalize."""
    exit_code = prepare_llmd.cleanup()
    sys.exit(exit_code)


@main.command()
@click.pass_context
@safe_cli_command
def post_cleanup(ctx):
    """Cleanup phase - Clean up resources and finalize."""
    exit_code = prepare_llmd.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
