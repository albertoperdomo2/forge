#!/usr/bin/env python3
"""
Fournos launcher project CLI Operations
"""

import sys
import types

import logging
logger = logging.getLogger(__name__)

import click

from projects.fournos.orchestration import submit as submit_mod


@click.group()
@click.pass_context
def main(ctx):
    """FOURNOS Project launcher CI Operations for FORGE."""

    ctx.ensure_object(types.SimpleNamespace)
    submit_mod.init()


@main.command()
@click.pass_context
def submit(ctx):
    """Submit a CI job to FOURNOS CI entrypoint."""

    sys.exit(submit_mod.submit())


if __name__ == "__main__":
    main()
