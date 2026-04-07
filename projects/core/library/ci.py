#!/usr/bin/env python3
"""
Shared CI utilities for FORGE projects

Provides common CI functionality including error handling, logging,
and tooling setup for consistent behavior across all projects.
"""

import sys
import traceback
import logging
import inspect
import os
import yaml
from pathlib import Path

from projects.core.library import env

logger = logging.getLogger(__name__)


def handle_ci_exception(e: Exception) -> None:
    """
    Handle CI exceptions with comprehensive logging and failure file creation.

    Args:
        e: The exception that occurred
    """
    # Collect detailed error context
    error_context = _collect_error_context(e)

    # Display error on screen and write to FAILURES file
    _display_error_summary(error_context)


def _collect_error_context(e: Exception) -> dict:
    """Collect comprehensive error context from the exception and stack trace."""

    # Get the full stack trace
    tb_lines = traceback.format_exc().splitlines()
    stack_frames = traceback.extract_tb(e.__traceback__)

    # Find the orchestration entry point (likely in orchestration/ directory)
    orchestration_frame = None
    toolbox_frame = None
    current_frame = None

    for frame in stack_frames:
        if 'orchestration/' in frame.filename or '/orchestration/' in frame.filename:
            orchestration_frame = frame
        if 'toolbox/' in frame.filename or '/toolbox/' in frame.filename:
            toolbox_frame = frame
        current_frame = frame

    # Get relative paths for better readability
    def get_relative_path(filepath):
        try:
            # Try to make relative to current working directory
            return os.path.relpath(filepath)
        except ValueError:
            # If that fails, just use the filename
            return os.path.basename(filepath)

    context = {
        'exception_type': type(e).__name__,
        'exception_message': str(e),
        'full_traceback': traceback.format_exc(),
        'stack_summary': traceback.format_list(stack_frames),
        'current_location': {
            'file': get_relative_path(current_frame.filename) if current_frame else 'Unknown',
            'line': current_frame.lineno if current_frame else 'Unknown',
            'function': current_frame.name if current_frame else 'Unknown',
        },
        'orchestration_context': None,
        'toolbox_context': None,
        'task_info': _extract_task_info(e),
    }

    if orchestration_frame:
        context['orchestration_context'] = {
            'file': get_relative_path(orchestration_frame.filename),
            'line': orchestration_frame.lineno,
            'function': orchestration_frame.name,
            'code': orchestration_frame.line,
        }

    if toolbox_frame:
        context['toolbox_context'] = {
            'file': get_relative_path(toolbox_frame.filename),
            'line': toolbox_frame.lineno,
            'function': toolbox_frame.name,
            'code': toolbox_frame.line,
        }

    return context


def _extract_task_info(e: Exception) -> dict:
    """Extract task information from the exception if available."""
    task_info = {}

    # Get the actual exception to analyze (unwrap TaskExecutionError if needed)
    actual_exception = e
    if hasattr(e, 'original_exception'):
        actual_exception = e.original_exception

    # Check if it's our custom TaskExecutionError
    if hasattr(e, 'task_name'):
        task_info['name'] = getattr(e, 'task_name', 'Unknown')
        task_info['description'] = getattr(e, 'task_description', 'No description')
        task_info['task_args'] = getattr(e, 'task_args', None)

    # Try to extract command information from shell errors
    if hasattr(actual_exception, 'cmd'):
        task_info['command'] = actual_exception.cmd
    if hasattr(actual_exception, 'returncode'):
        task_info['exit_code'] = actual_exception.returncode
    if hasattr(actual_exception, 'stdout'):
        task_info['stdout'] = getattr(actual_exception, 'stdout', '')
    if hasattr(actual_exception, 'stderr'):
        task_info['stderr'] = getattr(actual_exception, 'stderr', '')

    # Only include original_error for exceptions we haven't structurally parsed
    import subprocess
    if not isinstance(actual_exception, subprocess.CalledProcessError):
        # For non-command errors, include the original error message
        if hasattr(e, 'original_exception'):
            task_info['original_error'] = str(e.original_exception)
        elif not any(key in task_info for key in ['command', 'exit_code']):
            # Only include if we don't have structured command info
            task_info['original_error'] = str(e)

    return task_info


def _display_error_summary(context: dict) -> None:
    """Display a comprehensive error summary on screen and write to FAILURES file."""

    # Build the error summary as a list of lines
    summary_lines = [
        "",
        "=" * 80,
        "🚨 CI EXECUTION FAILED",
        "=" * 80,
        "",
        f"💥 ERROR: {context['exception_type']}: {context['exception_message']}",
    ]

    # Add task information if available
    if context['task_info']:
        summary_lines.append("")
        summary_lines.append("📋 TASK INFORMATION:")

        # Show artifact_dir prominently first
        task_args = context['task_info'].get('task_args', {})
        if task_args and 'artifact_dir' in task_args:
            summary_lines.append(f"   artifact_dir: {task_args['artifact_dir']}")

        for key, value in context['task_info'].items():
            if key == 'task_args' and value:
                summary_lines.append(f"   {key}:")
                try:
                    # Convert PosixPath objects to strings for YAML serialization
                    cleaned_args = {}
                    for k, v in value.items():
                        if isinstance(v, Path):
                            cleaned_args[k] = str(v)
                        else:
                            cleaned_args[k] = v

                    yaml_output = yaml.dump(cleaned_args, default_flow_style=False, sort_keys=True)
                    for line in yaml_output.splitlines():
                        summary_lines.append(f"      {line}")
                except Exception:
                    # Fallback to string representation if YAML fails
                    summary_lines.append(f"      {value}")
            elif value and key != 'task_args':
                summary_lines.append(f"   {key}: {value}")

    # Add the full stacktrace
    summary_lines.append("")
    summary_lines.append("📍 STACKTRACE:")
    summary_lines.append("-" * 40)
    # Add each line of the stacktrace with proper indentation
    for line in context['full_traceback'].splitlines():
        summary_lines.append(f"   {line}")

    summary_lines.append("")
    summary_lines.append(f"📄 Full details written to: {env.ARTIFACT_DIR / 'FAILURES'}")
    summary_lines.append("=" * 80)

    # Display on screen
    for line in summary_lines:
        print(line)

    # Write to FAILURES file
    _write_error_summary_to_file(summary_lines)


def _write_error_summary_to_file(summary_lines: list) -> None:
    """Write the error summary to FAILURES file."""
    failures_file = env.ARTIFACT_DIR / "FAILURES"
    try:
        content = "\n".join(summary_lines)
        failures_file.write_text(content)
        logger.info(f"Error summary written to: {failures_file}")
    except Exception as write_error:
        logger.error(f"Failed to write error summary to file: {write_error}")



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
