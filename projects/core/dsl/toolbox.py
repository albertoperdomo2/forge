#!/usr/bin/env python3
"""
Shared utilities for toolbox commands

Provides common functionality for toolbox command entry points,
including argument parsing, environment setup, and error handling.
"""

import sys
import logging
import inspect
from typing import Callable, List, Optional
import traceback
import yaml

from projects.core.library import env
from .cli import create_dynamic_parser
from .runtime import TaskExecutionError


def _get_positional_args(func: Callable) -> List[str]:
    """
    Introspect a function to determine which parameters should be positional.

    Returns parameters that are POSITIONAL_OR_KEYWORD and come before
    any VAR_POSITIONAL (*) or KEYWORD_ONLY parameters.
    """
    sig = inspect.signature(func)
    positional_args = []

    for param_name, param in sig.parameters.items():
        if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            positional_args.append(param_name)
        elif param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.KEYWORD_ONLY):
            # Stop collecting once we hit * or keyword-only parameters
            break

    return positional_args


def run_toolbox_command(
    command_func: Callable,
    positional_args: Optional[List[str]] = None,
    success_message: str = "✅ Command completed successfully",
    interrupted_message: str = "\n🚫 Operation interrupted by user",
    error_prefix: str = "❌ Error"
) -> None:
    """
    Run a toolbox command with standard argument parsing and error handling.

    Args:
        command_func: The main function to execute (e.g., run, submit_and_wait, etc.)
        positional_args: List of argument names to treat as positional (auto-detected if None)
        success_message: Message to display on successful completion
        interrupted_message: Message to display on keyboard interrupt
        error_prefix: Prefix for error messages

    Examples:
        # Auto-detect positional args from function signature
        run_toolbox_command(run)

        # Explicit positional args
        run_toolbox_command(run, ['cluster_name', 'project'])

        # Custom messages
        run_toolbox_command(
            command_func=run,
            success_message="✅ FOURNOS job completed successfully",
            error_prefix="❌ FOURNOS Error"
        )
    """
    # Auto-detect positional args if not provided
    if positional_args is None:
        positional_args = _get_positional_args(command_func)

    # Create parser dynamically from function signature
    parser = create_dynamic_parser(
        command_func,
        positional_args=positional_args
    )
    args = parser.parse_args()

    # Convert args to kwargs for function call
    kwargs = vars(args)
    env.init(daily_artifact_dir=True)

    try:
        # Execute the command function
        command_func(**kwargs)
        print(success_message)
    except KeyboardInterrupt:
        print(interrupted_message)
        sys.exit(1)
    except Exception as e:
        # Check if this is a TaskExecutionError to provide better formatting
        if isinstance(e, TaskExecutionError):
            for line in get_task_execution_error(e):
                logging.error(line)
            logging.error("")

            traceback.print_exception(e.original_exception)

        else:
            # Show the full exception with stack trace
            logging.exception(f"{error_prefix}: {e}")
        sys.exit(1)


def get_task_execution_error(e):
    def clean_args(value):
        import pathlib
        # Convert PosixPath objects to strings for YAML serialization
        cleaned_args = {}
        for k, v in value.items():
            cleaned_args[k] = str(v) \
                if isinstance(v, pathlib.Path) \
                   else v
        return cleaned_args

    yield "x" * 80
    yield f"~~ {e.task_location}"
    yield f"~~ TASK: {e.task_name}: {e.task_description}"
    yield f"~~ ARTIFACT_DIR: {e.artifact_dir}"
    yield f"~~ LOG_FILE: {e.artifact_dir}/task.log"
    yield f"~~ ARGS:"
    for line in yaml.dump(clean_args(e.task_args), default_flow_style=False, sort_keys=False).splitlines():
        yield f"~~     {line}"
    yield "~~"
    yield f"~~ EXCEPTION: {e.original_exception.__class__.__name__}"
    yield f"~~     {e.original_exception}"
    yield "x" * 80


def create_toolbox_main(
    command_func: Callable,
    positional_args: Optional[List[str]] = None,
    success_message: str = "✅ Command completed successfully",
    **kwargs
) -> Callable:
    """
    Create a main() function for a toolbox command.

    Args:
        command_func: The main function to execute
        positional_args: List of argument names to treat as positional (auto-detected if None)
        success_message: Message to display on successful completion
        **kwargs: Additional arguments to pass to run_toolbox_command

    Returns:
        A main() function that can be used as the entry point

    Example:
        def run(cluster_name: str, project: str, *, args: list = None, ...):
            # Command implementation
            return execute_tasks(locals())

        # Auto-detect positional args from signature (cluster_name, project)
        main = create_toolbox_main(run)

        # Or with custom configuration
        main = create_toolbox_main(
            run,
            success_message="✅ FOURNOS job completed successfully"
        )

        if __name__ == "__main__":
            main()
    """
    def main():
        """CLI entrypoint with dynamic argument discovery"""
        run_toolbox_command(
            command_func=command_func,
            positional_args=positional_args,
            success_message=success_message,
            **kwargs
        )

    return main
