"""
Runtime execution engine for the DSL framework
"""

import sys
import inspect
import types
import yaml
import logging
import os
from datetime import datetime
from pathlib import Path

import projects.core.library.env as env
from projects.core.library.run import SignalError
from .log import log_execution_banner, log_completion_banner, logger
from .context import create_task_parameters

# Import from task.py to avoid circular imports
from .task import ConditionError, RetryFailure
from .script_manager import get_script_manager


class TaskExecutionError(Exception):
    """Custom exception that wraps task execution failures with context"""

    def __init__(
        self,
        task_name: str,
        task_description: str,
        original_exception: Exception,
        task_args: dict = None,
        task_location: str = None,
        artifact_dir: str = None,
        task_context: dict = None,
    ):
        self.task_name = task_name
        self.task_description = task_description
        self.original_exception = original_exception
        self.task_args = task_args
        self.task_location = task_location
        self.task_context = task_context
        self.artifact_dir = artifact_dir
        tb = original_exception.__traceback__

        # Skip the first 2 frames of the stack
        if tb and tb.tb_next:
            original_exception.__traceback__ = tb.tb_next.tb_next

        # Create a comprehensive error message with clear task context
        message_parts = [
            f"❌ TASK FAILURE: {task_name}: {task_description or 'No description'}",
            f"   {task_location or 'Unknown'}",
            f"   {original_exception.__class__.__name__}: {original_exception}",
        ]

        message = "\n".join(message_parts)
        super().__init__(message)

        # Preserve the original exception chain to maintain full stack trace
        # This allows the full traceback to be shown in logs


def execute_tasks(function_args: dict = None):
    """
    Execute all registered tasks in order, respecting conditions

    Args:
        function_args: Dictionary of function arguments (from locals())
    """

    # Get the command name from the caller file path for artifact directory naming
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    filename = caller_frame.f_code.co_filename
    command_name = _get_toolbox_function_name(filename)

    # Get relative filename to match task registration
    try:
        rel_filename = str(Path(filename).relative_to(env.FORGE_HOME))
    except ValueError:
        rel_filename = filename

    # Use NextArtifactDir for proper storage management
    with env.NextArtifactDir(command_name) as artifact_dir:
        # Convert function arguments to namespace object and add artifact_dir
        args = types.SimpleNamespace(**(function_args or {}))
        args.artifact_dir = env.ARTIFACT_DIR

        # Create a shared context that persists across all tasks
        shared_context = types.SimpleNamespace()

        # Create _meta directory for metadata files
        meta_dir = env.ARTIFACT_DIR / "_meta"
        meta_dir.mkdir(exist_ok=True)

        # Setup file logging first so all output is captured
        log_file, file_handler = _setup_execution_logging(env.ARTIFACT_DIR)

        try:
            # Log execution banner (now captured in file)
            log_execution_banner(function_args, log_file)

            # Generate metadata files
            _generate_execution_metadata(function_args, caller_frame, meta_dir)
            _generate_restart_script(function_args, caller_frame, meta_dir)

            # Execute tasks only from the calling file
            script_manager = get_script_manager()
            file_tasks = list(script_manager.get_tasks_from_file(rel_filename))

            if not file_tasks:
                logger.error(f"No tasks found for file: {rel_filename}")
                log_completion_banner(function_args, status="NO_TASKS")
                raise RuntimeError(f"No tasks found for file: {rel_filename}")

            execution_error = None

            try:
                while file_tasks:
                    current_task_info = file_tasks.pop(0)
                    _execute_single_task(current_task_info, args, shared_context)

            except (KeyboardInterrupt, SignalError):
                logger.info("")
                logger.fatal("==> INTERRUPTED: Received KeyboardInterrupt (Ctrl+C)")
                logger.info("==> Exiting...")
                # Show completion banner with interrupted status
                log_completion_banner(function_args, status="INTERRUPTED")
                raise

            except (TaskExecutionError, ConditionError, RetryFailure, Exception) as e:
                # Log error but continue to always tasks
                logger.info("")
                logger.fatal(f"==> {e.__class__.__name__}: {e}")
                log_completion_banner(
                    function_args, status=f"EXCEPTION ({e.__class__.__name__})"
                )

                # Save error to re-raise after always tasks execute
                execution_error = e

            # Always execute "always" tasks from this file
            if file_tasks:
                logging.warning("Executing the @always tasks ...")
                while file_tasks:
                    try:
                        current_task_info = file_tasks.pop(0)
                        _execute_single_task(task_info, args, shared_context)

                    except Exception as e:
                        # If normal tasks succeeded but always task failed, raise always task error
                        if execution_error is None:
                            execution_error = e

                        logger.error(f"==> ALWAYS TASK ALSO FAILED: {e}")
                        logger.info("")

            # Re-raise original error if normal tasks failed
            if execution_error:
                log_completion_banner(
                    function_args,
                    status=f"FAILED ({execution_error.__class__.__name__})",
                )
                raise execution_error

            # Log completion banner if execution was successful
            log_completion_banner(function_args)

            # for the time being, return the shared context.  In the
            # future we'll return more info about what has been
            # executed
            shared_context.__dict__["artifact_dir"] = args.artifact_dir

            return shared_context
        finally:
            # Clean up the file handler to prevent leaks
            dsl_logger = logging.getLogger("DSL")
            dsl_logger.removeHandler(file_handler)
            file_handler.close()


def _execute_single_task(task_info, args, shared_context):
    """Execute a single task with condition checking"""
    task_name = task_info["name"]
    task_func = task_info["func"]
    condition = task_info["condition"]
    task_status = task_info["status"] = {}

    # Check condition if present
    if condition is not None:
        try:
            # Condition should be a callable (lambda) for lazy evaluation
            if callable(condition):
                should_run = condition()
            else:
                should_run = bool(condition)

            if not should_run:
                logger.info("")
                logger.info("~" * 80)
                logger.info(f"==> SKIPPING TASK: {task_name} (condition not met)")
                logger.info("~" * 80)
                return
        except Exception as e:
            logger.error(
                f"==> CONDITION EXCEPTION raised by {task_name}: {e.__class__.__name__}: {e}"
            )
            logger.error(
                f"==> Task: {task_name} ({task_func.__doc__ or 'No description'})"
            )
            logger.info("")
            raise ConditionError(e)

    # Execute the task
    try:
        # Create readonly args and mutable context
        readonly_args, context = create_task_parameters(args, shared_context)

        # Check if task has retry configuration
        retry_config = task_info.get("retry_config")
        if retry_config:
            # Import here to avoid circular imports
            from .task import _execute_with_retry

            task_status["ret"] = _execute_with_retry(
                task_func,
                retry_config["attempts"],
                retry_config["delay"],
                retry_config["backoff"],
                readonly_args,
                context,
            )
        else:
            # Call task with readonly args and mutable context
            task_status["ret"] = task_func(readonly_args, context)
        if task_status["ret"] is not None:
            logger.info(f"<task returned value> {task_status['ret']}")

        # Store context values back into shared_context for access by subsequent tasks
        # This allows tasks to communicate through context without polluting args
        for attr_name, attr_value in vars(context).items():
            if not attr_name.startswith("_"):
                setattr(shared_context, attr_name, attr_value)

    except (KeyboardInterrupt, SignalError):
        raise
    except Exception as e:
        co_filename = task_func.original_func.__code__.co_filename
        try:
            co_filename = Path(co_filename).relative_to(env.FORGE_HOME)
        except ValueError as e:
            logging.warning(
                f"Path {co_filename} isn't relative to FORGE_HOME={env.FORGE_HOME} ({e})"
            )
            pass  # Use absolute path if file is outside FORGE_HOME

        task_location = (
            f"{co_filename}:{task_func.original_func.__code__.co_firstlineno}"
        )

        # Wrap in custom exception with context
        task_error = TaskExecutionError(
            task_name=task_name,
            task_description=task_func.__doc__ or "No description",
            original_exception=e,
            task_args=vars(args) if hasattr(args, "__dict__") else None,
            task_context=vars(context) if hasattr(context, "__dict__") else None,
            task_location=task_location,
            artifact_dir=str(env.ARTIFACT_DIR),
        )
        # Don't use 'from None' - preserve the original stack trace
        raise task_error


def clear_tasks(file_path=None):
    """
    Clear the task registry (useful for testing)

    Args:
        file_path: If specified, only clear tasks from this file.
                  If None, clear all tasks from all files.
    """
    script_manager = get_script_manager()
    script_manager.clear_tasks(file_path)


def _generate_execution_metadata(function_args: dict, caller_frame, meta_dir):
    """Generate a YAML file with execution metadata"""
    filename = caller_frame.f_code.co_filename

    # Get path relative to FORGE home directory (forge root)
    rel_filename = _get_forge_relative_path(filename)

    # Use parent directory name as function name for toolbox operations
    function_name = _get_toolbox_function_name(filename)

    metadata = {
        "execution_metadata": {
            "timestamp": datetime.now().isoformat(),
            "file": rel_filename,
            "command": function_name,
            "artifact_dir": str(env.ARTIFACT_DIR),
            "working_directory": str(Path.cwd()),
            "arguments": {},
        }
    }

    # Add function arguments, filtering out internal ones
    for key, value in function_args.items():
        if key not in ["function_args"]:  # Skip internal parameters
            metadata["execution_metadata"]["arguments"][key] = value

    # Write metadata to YAML file
    metadata_file = meta_dir / "metadata.yaml"
    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    logger.debug(f"Generated execution metadata: {metadata_file}")


def _setup_execution_logging(artifact_dir):
    """Setup file logging to capture all stdout/stderr during execution"""
    log_file = artifact_dir / "task.log"

    # Create file handler for the DSL logger
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.INFO)

    # Use same format as console output
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Add handler to the DSL logger so all DSL modules inherit it
    dsl_logger = logging.getLogger("DSL")
    dsl_logger.addHandler(file_handler)

    return log_file, file_handler


def _generate_restart_script(function_args: dict, caller_frame, meta_dir):
    """Generate a shell script to restart the execution with same parameters"""
    filename = caller_frame.f_code.co_filename
    rel_filename = _get_forge_relative_path(filename)

    script_content = "#!/bin/bash\n"
    script_content += "# Auto-generated restart script\n"
    script_content += f"# Generated on: {datetime.now().isoformat()}\n"
    script_content += f"# Original execution artifact dir: {env.ARTIFACT_DIR}\n\n"

    # Build command line with arguments on separate lines
    script_content += f'python "{rel_filename}"'

    # Add arguments, each on a new line with proper indentation
    args_added = False
    for key, value in function_args.items():
        if (
            key not in ["function_args"] and value is not None
        ):  # Skip internal parameters and None values
            if isinstance(value, bool):
                if value:  # Only add flag if True
                    script_content += " \\\n    " + f"--{key.replace('_', '-')}"
                    args_added = True
            else:
                script_content += " \\\n    " + f'--{key.replace("_", "-")} "{value}"'
                args_added = True

    script_content += "\n"

    # Write restart script
    restart_file = meta_dir / "restart.sh"
    with open(restart_file, "w") as f:
        f.write(script_content)

    # Make executable
    os.chmod(restart_file, 0o755)

    logger.debug(f"Generated restart script: {restart_file}")


def _get_forge_relative_path(filename):
    """Get file path relative to FORGE home directory (forge root)"""

    return Path(filename).relative_to(env.FORGE_HOME)


def _get_toolbox_function_name(filename):
    """Extract toolbox function name from file path (parent directory name)"""
    filename_path = Path(filename)

    # For paths like projects/llm_d/toolbox/capture_isvc_state/main.py
    # Return the parent directory name: capture_isvc_state
    return filename_path.parent.name
