#!/usr/bin/env python3
"""
FOURNOS launcher project CI Operations

"""

import sys
import subprocess
import time
from pathlib import Path
import types

import logging
logger = logging.getLogger(__name__)

import click

from projects.core.library import ci as ci_lib
from projects.fournos.orchestration import submit as submit_mod
from projects.fournos.orchestration import utils


@click.group()
@click.pass_context
def main(ctx):
    """FOURNOS Project launcher CI Operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)
    submit_mod.init()
    utils.ensure_oc_available()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def submit(ctx):
    """Submit a CI job to FOURNOS CI entrypoint."""
    return submit_mod.submit()

if __name__ == "__main__":
    main()
