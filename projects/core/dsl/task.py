"""
Task decorator and retry functionality
"""

import functools
import logging
import time
import inspect
import os
import types
import yaml
from typing import List, Callable, Any, Optional

import projects.core.library.env as env
from .log import log_task_header, log_execution_banner

LINE_WIDTH = 80

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Global task registry
_task_registry: List[dict] = []
_task_results: dict = {}

class ConditionError(Exception): pass

class RetryFailure(Exception): pass

class TaskResult:
    """Container for task results that can be referenced in conditions"""
    def __init__(self, task_name: str):
        self.task_name = task_name
        self._result = None
        self._executed = False

    @property
    def return_value(self):
        """Get the return value of the task"""
        return self._result

    def _set_result(self, result):
        self._result = result
        self._executed = True


def task(func):
    """
    Mark a function as a DSL task and register it
    """
    # Capture file and line info at definition time, not execution time
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    definition_filename = caller_frame.f_code.co_filename
    definition_line_no = caller_frame.f_lineno

    # Make filename relative to current working directory
    try:
        rel_definition_filename = os.path.relpath(definition_filename)
    except ValueError:
        rel_definition_filename = definition_filename

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__

        # Log task header using definition location
        log_task_header(task_name, func.__doc__, rel_definition_filename, definition_line_no)

        try:
            result = func(*args, **kwargs)
            # Store result for conditional execution
            if task_name in _task_results:
                _task_results[task_name]._set_result(result)
            return result
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.exception(f"==> TASK FAILED: {e.__class__.__name__}: {e}")
            logger.info("")
            raise

    # Mark the function as a task
    wrapper.is_dsl_task = True
    wrapper.task_name = func.__name__
    wrapper.original_func = func

    # Register the task
    task_info = {
        'name': func.__name__,
        'func': wrapper,
        'condition': getattr(func, '_when_condition', None),
        'retry_config': getattr(func, '_retry_config', None),
        'always_execute': getattr(func, '_always_execute', False)
    }

    _task_registry.append(task_info)

    # Create result container for this task
    _task_results[func.__name__] = TaskResult(func.__name__)

    # Make the result accessible as an attribute of the function
    wrapper.status = _task_results[func.__name__]

    return wrapper


def when(condition):
    """
    Conditional execution decorator with lazy evaluation

    Args:
        condition: A callable (lambda) that returns True/False
                  Use lambda for lazy evaluation: @when(lambda: some_task.status.return_value is True)

    Examples:
        @when(lambda: check_existing_service.status.return_value is True)
        @when(lambda: some_variable > 5)
        @when(lambda: os.path.exists("/tmp/flag"))
    """
    def decorator(func):
        func._when_condition = condition
        return func
    return decorator


def always(func):
    """
    Mark a task to always execute, even if previous tasks fail
    """
    func._always_execute = True
    return func


def retry(attempts=3, delay=1, backoff=1.0):
    """
    Simple retry decorator

    Args:
        attempts: Number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """
    def decorator(func):
        # Store retry config on function
        func._retry_config = {
            'attempts': attempts,
            'delay': delay,
            'backoff': backoff
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_config = getattr(func, '_retry_config', {})
            retry_attempts = retry_config.get('attempts', attempts)
            retry_delay = retry_config.get('delay', delay)
            retry_backoff = retry_config.get('backoff', backoff)

            last_exception = None
            current_delay = retry_delay

            for attempt in range(retry_attempts):
                try:
                    return func(*args, **kwargs)
                except KeyboardInterrupt:
                    # Don't retry on keyboard interrupt, just re-raise immediately
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < retry_attempts - 1:  # Not the last attempt
                        logger.info("")
                        logger.info("~" * LINE_WIDTH)
                        logger.info(f"~~ TASK: {func.__name__} : {func.__doc__ or 'No description'}")
                        logger.warning(f"~~ FAILED ATTEMPT #{attempt + 1}/{retry_attempts}")

                        logger.info(f"~~ RETRY in {current_delay:.0f}s")
                        logger.info("~" * LINE_WIDTH)
                        time.sleep(current_delay)
                        logger.info("")

                        current_delay *= retry_backoff
                    else:
                        logger.error(f"==> ALL ATTEMPTS FAILED: {retry_attempts}/{retry_attempts}")
                        logger.info("")
                        raise RetryFailure(f"All {retry_attempts} attemps failed for task {func.__name__} : {func.__doc__ or 'No description'}")

            # Re-raise the last exception
            raise last_exception

        return wrapper
    return decorator



