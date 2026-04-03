#!/usr/bin/env python3
"""
Shared CI utilities for FORGE projects

Provides common CI functionality including error handling, logging,
and tooling setup for consistent behavior across all projects.
"""

import sys
import traceback
import logging

from projects.core.library import env

logger = logging.getLogger(__name__)


def handle_ci_exception(e: Exception) -> None:
    """
    Handle CI exceptions with comprehensive logging and failure file creation.

    Args:
        e: The exception that occurred
    """
    logger.exception(f"FAILED: {e}")

    # Write exception stack trace to FAILURE file
    failure_file = env.ARTIFACT_DIR / "FAILURE"
    try:
        content = f"""CI failed with exception:
Exception: {type(e).__name__}: {e}

Full stack trace:
{traceback.format_exc()}"""
        failure_file.write_text(content)
        logger.info(f"Exception details written to: {failure_file}")
    except Exception as write_error:
        logger.error(f"Failed to write exception details to file: {write_error}")


def safe_ci_command(command_func):
    """
    Decorator/wrapper for CI commands to provide consistent error handling.

    Args:
        command_func: Function to execute safely
    """
    def wrapper(*args, **kwargs):
        try:
            exit_code = command_func(*args, **kwargs)
            sys.exit(exit_code)
        except Exception as e:
            handle_ci_exception(e)
            sys.exit(1)

    # Preserve original function metadata
    wrapper.__name__ = command_func.__name__
    wrapper.__doc__ = command_func.__doc__
    wrapper.__module__ = command_func.__module__
    wrapper.__qualname__ = command_func.__qualname__

    return wrapper
