#!/usr/bin/env python3
"""
Skeleton Example Project CI Operations

This is a skeleton/template project that demonstrates how to create a new project
within the FORGE test harness framework. Use this as a starting point for
building your own projects.
"""

from projects.core.library import ci as ci_lib
import foreign_testing

import click
import types


@click.group()
@click.pass_context
@ci_lib.safe_ci_function
def main(ctx):
    """Foreign Testing Project CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    foreign_testing.init()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def submit(ctx):
    """Launch a foreign test."""
    project_path = foreign_testing.prepare()

    return foreign_testing.submit(project_path)


if __name__ == "__main__":
    main()
