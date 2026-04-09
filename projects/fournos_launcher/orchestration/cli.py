#!/usr/bin/env python3
"""
Fournos launcher project CLI Operations
"""

import sys
import types
import shlex

import logging
logger = logging.getLogger(__name__)

import click

from projects.fournos_launcher.orchestration import submit as submit_mod
from projects.core.library import config
from projects.core.library.cli import safe_cli_command


@click.group()
@click.pass_context
def main(ctx):
    """FOURNOS Project launcher CI Operations for FORGE."""

    ctx.ensure_object(types.SimpleNamespace)
    submit_mod.init()


@main.command()
@click.option('--cluster', help='Target cluster name')
@click.option('--project', help='Project to run (e.g., llm_d)')
@click.option('--args', help='Arguments to pass to the project (space-separated string)')
@click.option('--override', '-o', multiple=True, help='Config overrides in key=value format')
@click.pass_context
@safe_cli_command
def submit(ctx, cluster, project, args, override):
    """Submit a CI job to FOURNOS CI entrypoint."""

    # Parse args string into list
    args_list = []
    if args:
        args_list = shlex.split(args)

    # Parse overrides into dict
    extra_overrides = {}
    for override_str in override:
        if '=' in override_str:
            key, value = override_str.split('=', 1)
            extra_overrides[key] = value
        else:
            logger.warning(f"Ignoring invalid override format: {override_str} (expected key=value)")

    # Override config values if provided
    if cluster:
        config.project.set_config("cluster.name", cluster)
    else:
        cluster = config.project.get_config("cluster.name")
        if not cluster:
            raise ValueError("--cluster or cluster.name is mandatory")
    logging.info(f"Using cluster {cluster}")

    if project:
        config.project.set_config("ci_job.project", project)
    else:
        project = config.project.get_config("ci_job.project")
        if not project:
            raise ValueError("--project or ci_job.project is mandatory")

    logging.info(f"Using project {project}")

    if args_list:
        config.project.set_config("ci_job.args", args_list)
        logging.info(f"Using args {args_list}")

    if extra_overrides:
        config.project.set_config("extra_overrides", extra_overrides)
        logging.info(f"Using overrides {extra_overrides}")

    return submit_mod.submit_job()


if __name__ == "__main__":
    main()
