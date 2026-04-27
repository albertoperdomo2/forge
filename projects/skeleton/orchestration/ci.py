#!/usr/bin/env python3
"""
Skeleton Example Project CI Operations

This is a skeleton/template project that demonstrates how to create a new project
within the FORGE test harness framework. Use this as a starting point for
building your own projects.
"""

import logging
import types

import click
import prepare_skeleton
import test_skeleton

from projects.caliper.orchestration.export import run_from_orchestration_config
from projects.core.ci_entrypoint.fournos_resolve import create_fournos_resolve_command
from projects.core.library import ci as ci_lib
from projects.core.library import config, env
from projects.core.library.export import caliper_export_command


def _caliper_export_at_end() -> int:
    """Set ``caliper.export.from`` to ``env.BASE_ARTIFACT_DIR`` and run orchestration export."""
    root = env.BASE_ARTIFACT_DIR
    config.project.set_config("caliper.export.from", str(root), print=False)
    caliper = config.project.get_config("caliper", print=False)
    status = run_from_orchestration_config(caliper)
    logging.info("Caliper export: %s", status)
    return 0


@click.group()
@click.pass_context
@ci_lib.safe_ci_function
def main(ctx):
    """Skeleton example project CI operations for FORGE."""
    ctx.ensure_object(types.SimpleNamespace)

    # Skip vault initialization for resolve_fournos_config command since vaults aren't available yet
    skip_vault_init = ctx.invoked_subcommand == "resolve-fournos-config"

    test_skeleton.init(skip_vault_init=skip_vault_init)


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
    try:
        return test_skeleton.test()
    finally:
        _caliper_export_at_end()


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def pre_cleanup(ctx):
    """Cleanup phase - Clean up resources and finalize."""
    return prepare_skeleton.cleanup()


main.add_command(caliper_export_command)
main.add_command(
    create_fournos_resolve_command(
        vault_list_func=lambda: config.project.get_config("vaults"),
        hardware_resolver_func=test_skeleton.resolve_hardware_request,
    )
)


if __name__ == "__main__":
    main()
