#!/usr/bin/env python3
"""
LLM-D Project CI Operations

"""

from projects.core.library import ci as ci_lib
import test_llmd, prepare_llmd

import types
import click

@click.group()
@click.pass_context
@ci_lib.safe_ci_function
def main(ctx):
    """LLM-D Project CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    test_llmd.init()

@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def prepare(ctx):
    """Prepare phase - Set up environment and dependencies."""
    return prepare_llmd.prepare()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def test(ctx):
    """Test phase - Execute the main testing logic."""
    return test_llmd.test()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def pre_cleanup(ctx):
    """Cleanup phase - Clean up resources and finalize."""
    return prepare_llmd.cleanup()


if __name__ == "__main__":
    main()
