#!/usr/bin/env python3
"""
Skeleton Example Project CI Operations

This is a skeleton/template project that demonstrates how to create a new project
within the FORGE test harness framework. Use this as a starting point for
building your own projects.
"""

import types

import click
import prepare_skeleton
import test_skeleton

from projects.core.library import ci as ci_lib


@click.group()
@click.pass_context
@ci_lib.safe_ci_function
def main(ctx):
    """Skeleton example project CI operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    # for the time being, FOURNOS doesn't provide the secrets ':-)
    strict_vault_validation = False
    test_skeleton.init(strict_vault_validation=strict_vault_validation)


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def prepare(ctx):
    """Prepare phase - Set up environment and dependencies."""
    return prepare_skeleton.prepare()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def test(ctx):
    """Test phase - Execute the main testing logic."""
    return test_skeleton.test()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def pre_cleanup(ctx):
    """Cleanup phase - Clean up resources and finalize."""
    return prepare_skeleton.cleanup()


if __name__ == "__main__":
    main()
