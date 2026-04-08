"""
Logging utilities for the DSL framework
"""

import logging
import inspect
import os
from pathlib import Path
import projects.core.library.env as env
import projects.core.library.config as config

LINE_WIDTH = 80

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def log_task_header(task_name: str, task_doc: str, rel_filename: str, line_no: int):
    """Log the verbose task header with tildes"""
    logger.info("")
    logger.info("~" * LINE_WIDTH)
    logger.info(f"~~ {rel_filename}:{line_no}")
    logger.info(f"~~ TASK: {task_name} : {task_doc or 'No description'}")
    logger.info("~" * LINE_WIDTH)
    logger.info("")


def log_execution_banner(function_args: dict = None, log_file: str = None):
    """Log the execution banner with function info and arguments"""
    # Get the caller's filename and function name for the header
    frame = inspect.currentframe()
    caller_frame = frame.f_back.f_back  # Go back 2 frames (this func -> execute_tasks -> actual caller)
    filename = caller_frame.f_code.co_filename

    rel_filename = _get_forge_relative_path(filename)

    # Use parent directory name as function name for toolbox operations
    function_name = _get_toolbox_function_name(filename)

    # Print execution header
    logger.info("")
    logger.info("===============================================================================")
    logger.info(f"| FILE: {rel_filename}")
    logger.info(f"| COMMAND: {function_name}")

    if function_args:
        # Display arguments in YAML format
        logger.info("| ARGUMENTS:")

        for key, value in function_args.items():
            if key == 'function_args':  # Skip the function_args parameter itself
                continue
            if value is None:
                continue

            logger.info(f"|   {key}: {value}")

    logger.info(f"| ARTIFACT_DIR: {env.ARTIFACT_DIR}")
    logger.info(f"| LOG_FILE: {log_file}")
    logger.info("===============================================================================")
    logger.info("")


def log_completion_banner(function_args: dict = None, status: str = "SUCCESS"):
    """Log the completion banner with function info and completion status"""
    # Get the caller's filename and function name for the header
    frame = inspect.currentframe()
    caller_frame = frame.f_back.f_back  # Go back 2 frames (this func -> execute_tasks -> actual caller)
    filename = caller_frame.f_code.co_filename

    rel_filename = _get_forge_relative_path(filename)

    # Use parent directory name as function name for toolbox operations
    function_name = _get_toolbox_function_name(filename)

    # Print completion header
    logger.info("")
    logger.info("===============================================================================")
    logger.info(f"| COMPLETED: {rel_filename}")
    logger.info(f"| COMMAND: {function_name}")
    logger.info(f"| STATUS: {status}")
    logger.info(f"| ARTIFACTS: {env.ARTIFACT_DIR}")
    logger.info("===============================================================================")
    logger.info("")


def _get_forge_relative_path(filename):
    """Get file path relative to FORGE home directory (forge root)"""
    filename_path = Path(filename)

    return filename_path.relative_to(env.FORGE_HOME)


def _get_toolbox_function_name(filename):
    """Extract toolbox function name from file path (parent directory name)"""
    filename_path = Path(filename)

    # For paths like projects/llm_d/toolbox/capture_isvc_state/main.py
    # Return the parent directory name: capture_isvc_state
    return filename_path.parent.name
