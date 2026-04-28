#!/usr/bin/env python3
"""
Jump CI Project CI Operations

This is the JumpCI CI entrypoint. It's used to run TOPSAIL-ng remotely inside a VPN cluster"""

import sys
import traceback
from pathlib import Path
import logging

import click

from projects.core.library import env
from projects.core.library import ci as ci_lib
from projects.core.library.export import caliper_export_command
from projects.legacy.library import config
from projects.legacy.library import env as legacy_env
from projects.caliper.orchestration.export import run_from_orchestration_config
from projects.core.library import vault

logger = logging.getLogger(__name__)


def _caliper_export_at_end() -> int:
    """Set ``caliper.export.from`` to ``env.BASE_ARTIFACT_DIR`` and run orchestration export."""
    root = env.BASE_ARTIFACT_DIR
    config.project.set_config("caliper.export.from", str(root), print=False)
    caliper = config.project.get_config("caliper", print=False)
    status = run_from_orchestration_config(caliper)
    logger.info("Caliper export: %s", status)
    return 0


# Add the testing directory to path for imports
testing_dir = Path(__file__).parent.parent / "testing"
if str(testing_dir) not in sys.path:
    sys.path.insert(0, str(testing_dir))

# Import llm_d legacy testing functionality
try:
    import prepare_llmd, test_llmd
    import test as test_mod

except ImportError as e:
    raise RuntimeError(f"Legacy LLM_D testing functionality not available: {e}") from e


def log(message: str, level: str = "info"):
    """Log message with project prefix."""
    project_name = "llm_d"
    icon = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}.get(level, "ℹ️")
    click.echo(f"{icon} [{project_name}] {message}")


@click.group()
@click.pass_context
@ci_lib.safe_ci_function
def main(ctx):
    """Jump CI Project CI Operations for TOPSAIL-NG."""
    ctx.ensure_object(dict)


def init():
    env.init()
    legacy_env.init()

    testing_dir = Path(__file__).parent.parent / "testing"
    config.init(testing_dir)

    presets = config.project.get_config("project.args")
    for preset in presets:
        config.project.apply_preset(preset)

    test_mod.init()
    vault.disable_strict_validation()
    vault.init(config.project.get_config("vaults"))


@main.command()
@click.pass_context
@ci_lib.safe_ci_command
def test(ctx):
    """Test phase - Trigger the project's test method."""
    log("Starting test phase...")

    failed = True
    try:
        init()
        failed = test_llmd.test()
    finally:
        logger.info("[llm-d] running the Caliper export")
        try:
            _caliper_export_at_end()
        except Exception:
            logger.exception("Caliper export failed")
            failed = True

    sys.exit(1 if failed else 0)


main.add_command(caliper_export_command)

if __name__ == "__main__":
    main()
