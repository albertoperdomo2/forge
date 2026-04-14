"""
CLI utilities for FORGE projects

Provides common functionality for CLI commands including error handling,
argument parsing, and consistent output formatting.
"""

import sys
import logging
import traceback
import functools

logger = logging.getLogger(__name__)


def handle_cli_exception(e: Exception) -> None:
    """Handle CLI exceptions with clean error output."""

    logger.error("")
    logger.error("=" * 80)
    logger.error("🚨 EXECUTION FAILED")
    logger.error("=" * 80)
    logger.error("")
    traceback.print_exc()
    logger.error("")
    logger.error("---")
    logger.fatal(f"--- {e.__class__.__name__}: {e}")
    logger.error("---")


def safe_cli_command(command_func):
    """
    Decorator/wrapper for CLI commands to provide consistent error handling.

    Args:
        command_func: Function to execute safely
    """
    @functools.wraps(command_func)
    def wrapper(*args, **kwargs):
        try:
            exit_code = command_func(*args, **kwargs)
            if exit_code is None:
                exit_code = 0
            sys.exit(exit_code)
        except Exception as e:
            handle_cli_exception(e)
            sys.exit(1)

    return wrapper
