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
from typing import List

import projects.core.library.env as env
from projects.core.library.run import SignalError
from .log import log_execution_banner, log_completion_banner, logger

# Import from task.py to avoid circular imports
from .task import _task_registry, _task_results, ConditionError, RetryFailure


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

    # Use NextArtifactDir for proper storage management
    with env.NextArtifactDir(command_name) as artifact_dir:

        # Convert function arguments to namespace object and add artifact_dir
        args = types.SimpleNamespace(**(function_args or {}))
        args.artifact_dir = env.ARTIFACT_DIR

        # Create _meta directory for metadata files
        meta_dir = env.ARTIFACT_DIR / "_meta"
        meta_dir.mkdir(exist_ok=True)

        # Setup file logging first so all output is captured
        _setup_execution_logging(meta_dir)

        # Log execution banner (now captured in file)
        log_execution_banner(function_args)

        # Generate metadata files
        _generate_execution_metadata(function_args, caller_frame, meta_dir)
        _generate_restart_script(function_args, caller_frame, meta_dir)

        # Separate normal tasks from always tasks
        normal_tasks = [t for t in _task_registry if not t.get('always_execute', False)]
        always_tasks = [t for t in _task_registry if t.get('always_execute', False)]

        execution_error = None

        # Execute normal tasks
        try:
            for task_info in normal_tasks:
                _execute_single_task(task_info, args)
        except (KeyboardInterrupt, SignalError):
            logger.info("")
            logger.fatal("==> INTERRUPTED: Received KeyboardInterrupt (Ctrl+C)")
            logger.info("==> Exiting...")
            # Show completion banner with interrupted status
            log_completion_banner(function_args, status="INTERRUPTED")
            sys.exit(1)

        except ConditionError as e:
            logger.info("")
            logger.exception(f"==> CONDITION Exception {e}")
            sys.exit(1)
        except RetryFailure as e:
            logger.info("")
            logger.fatal(f"==> RETRY failure {e}")
            sys.exit(1)

        except Exception as e:
            execution_error = e
            # catch and execute the ALWAYS tasks

        # Always execute "always" tasks
        try:
            for task_info in always_tasks:
                _execute_single_task(task_info, args)
        except Exception as e:
            # If normal tasks succeeded but always task failed, raise always task error
            if execution_error is None:
                raise
            # If both failed, log always task error but preserve original error
            logger.error(f"==> ALWAYS TASK ALSO FAILED: {e}")
            logger.info("")

        # Re-raise original error if normal tasks failed
        if execution_error:
            raise execution_error

        # Log completion banner if execution was successful
        log_completion_banner(function_args)


def _execute_single_task(task_info, args):
    """Execute a single task with condition checking"""
    task_name = task_info['name']
    task_func = task_info['func']
    condition = task_info['condition']
    task_status = task_info['status'] = {}

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
            logger.error(f"==> CONDITION EXCEPTION raised by {task_name}: {e}")
            logger.info("")
            raise ConditionError(e)

    # Execute the task
    try:
        task_status["ret"] = task_func(args)
        if task_status["ret"] is not None:
            logger.info(f"<task returned value> {task_status['ret']}")

    except (KeyboardInterrupt, SignalError):
        raise
    except Exception as e:
        logger.error(f"==> EXECUTION FAILED for {task_name}: {e}")
        raise


def clear_tasks():
    """Clear the task registry (useful for testing)"""
    global _task_registry, _task_results
    _task_registry = []
    _task_results = {}


def _generate_execution_metadata(function_args: dict, caller_frame, meta_dir):
    """Generate a YAML file with execution metadata"""
    filename = caller_frame.f_code.co_filename

    # Get path relative to FORGE home directory (topsail-ng root)
    rel_filename = _get_forge_relative_path(filename)

    # Use parent directory name as function name for toolbox operations
    function_name = _get_toolbox_function_name(filename)

    metadata = {
        'execution_metadata': {
            'timestamp': datetime.now().isoformat(),
            'file': rel_filename,
            'command': function_name,
            'artifact_dir': str(env.ARTIFACT_DIR),
            'working_directory': str(Path.cwd()),
            'arguments': {}
        }
    }

    # Add function arguments, filtering out internal ones
    for key, value in function_args.items():
        if key not in ['function_args']:  # Skip internal parameters
            metadata['execution_metadata']['arguments'][key] = value

    # Write metadata to YAML file
    metadata_file = meta_dir / "metadata.yaml"
    with open(metadata_file, 'w') as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Generated execution metadata: {metadata_file}")


def _setup_execution_logging(meta_dir):
    """Setup file logging to capture all stdout/stderr during execution"""
    log_file = meta_dir / "execution.log"

    # Create file handler for the DSL logger
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.INFO)

    # Use same format as console output
    file_handler.setFormatter(logging.Formatter('%(message)s'))

    # Add handler to the parent DSL logger so all DSL modules inherit it
    dsl_logger = logging.getLogger('projects.core.dsl')
    dsl_logger.addHandler(file_handler)

    logger.info(f"Execution logging enabled: {log_file}")


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
        if key not in ['function_args'] and value is not None:  # Skip internal parameters and None values
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
    with open(restart_file, 'w') as f:
        f.write(script_content)

    # Make executable
    os.chmod(restart_file, 0o755)

    logger.info(f"Generated restart script: {restart_file}")


def _get_forge_relative_path(filename):
    """Get file path relative to FORGE home directory (topsail-ng root)"""
    filename_path = Path(filename)

    # Look for topsail-ng directory in the path
    for parent in filename_path.parents:
        if parent.name == 'topsail-ng':
            try:
                # Make path relative to topsail-ng parent (so it shows ../forge/...)
                forge_home = parent.parent
                rel_path = filename_path.relative_to(forge_home)
                return str(rel_path)
            except ValueError:
                pass

    # Fallback to relative to current directory
    try:
        return os.path.relpath(filename)
    except ValueError:
        return filename


def _get_toolbox_function_name(filename):
    """Extract toolbox function name from file path (parent directory name)"""
    filename_path = Path(filename)

    # For paths like projects/llm_d/toolbox/capture_isvc_state/main.py
    # Return the parent directory name: capture_isvc_state
    return filename_path.parent.name
