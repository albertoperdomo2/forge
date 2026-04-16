"""
Task decorator and retry functionality
"""

import functools
import inspect
import logging
import os
import time

from .log import log_task_header
from .script_manager import get_script_manager

LINE_WIDTH = 80

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("DSL")
logger.propagate = False  # Don't show logger prefix


class ConditionError(Exception):
    pass


class RetryFailure(Exception):
    pass


def _ensure_is_task(func, decorator_name):
    """
    Validate that a function is already decorated with @task.

    Args:
        func: The function to check
        decorator_name: Name of the decorator calling this (for error messages)

    Raises:
        TypeError: If the function is not a task
    """

    if not hasattr(func, "is_dsl_task") or not func.is_dsl_task:
        raise TypeError(
            f"@{decorator_name} can only be applied to functions decorated with @task. \n"
            f"Function '{func.__name__}' is not a task. \n"
            f"Put '@task' BELOW '@{decorator_name}' in your decorator stack."
        )
    return True


def _execute_with_retry(func, attempts, delay, backoff, *args, **kwargs):
    """
    Execute a function with retry logic.

    Args:
        func: The function to execute
        attempts: Number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Result of the function execution

    Raises:
        RetryFailure: If all retry attempts fail
    """
    retry_config = getattr(func, "_retry_config", {})
    retry_attempts = retry_config.get("attempts", attempts)
    retry_delay = retry_config.get("delay", delay)
    retry_backoff = retry_config.get("backoff", backoff)

    current_delay = retry_delay

    for attempt in range(retry_attempts):
        try:
            result = func(*args, **kwargs)

            # Check if result indicates we should retry (falsy values like False, None, [], etc.)
            if not result:
                if attempt < retry_attempts - 1:  # Not the last attempt
                    logger.info("")
                    logger.info("~" * LINE_WIDTH)
                    logger.info(f"~~ TASK: {func.__name__} : {func.__doc__ or 'No description'}")
                    logger.warning(
                        f"~~ RETRY ATTEMPT #{attempt + 1}/{retry_attempts} (returned: {result})"
                    )

                    logger.info(f"~~ RETRY in {current_delay:.0f}s")
                    logger.info("~" * LINE_WIDTH)
                    time.sleep(current_delay)
                    logger.info("")

                    current_delay *= retry_backoff
                else:
                    logger.error(f"==> ALL ATTEMPTS FAILED: {retry_attempts}/{retry_attempts}")
                    logger.info("")
                    raise RetryFailure(
                        f"All {retry_attempts} attempts failed for task {func.__name__} : {func.__doc__ or 'No description'} (last result: {result})"
                    )
            else:
                # Truthy result means success
                return result

        except KeyboardInterrupt:
            # Don't retry on keyboard interrupt, just re-raise immediately
            raise
        except Exception as e:
            # Exception means abort, don't retry
            logger.error(f"==> TASK EXCEPTION: {func.__name__} failed with exception")
            logger.info("")
            raise e

    # This should not be reached due to the logic above, but kept for safety
    raise RetryFailure(f"Unexpected end of retry loop for task {func.__name__}")


def task_only(decorator_func):
    """
    Decorator for decorator functions that should only be applied to @task functions.

    This ensures that decorators like @always, @when, @retry can only be applied
    to functions that are already decorated with @task.

    Handles both simple decorators and decorator factories:

    Simple decorator usage:
        @task_only
        def always(func):
            func._always_execute = True
            return func

    Decorator factory usage:
        @task_only
        def retry(attempts=3, delay=1):
            def decorator(func):
                # decorator logic here
                return func
            return decorator
    """

    @functools.wraps(decorator_func)
    def wrapper(*args, **kwargs):
        # Use the signature of decorator_func to determine if it's a simple decorator or factory
        sig = inspect.signature(decorator_func)
        params = list(sig.parameters.values())

        # Check if this is a simple decorator that takes a single function argument
        if (
            len(params) == 1
            and params[0].annotation in (inspect.Parameter.empty, "func", callable)
            and len(args) == 1
            and len(kwargs) == 0
            and callable(args[0])
            and hasattr(args[0], "__name__")
        ):
            # Simple decorator case: @always
            func = args[0]
            _ensure_is_task(func, decorator_func.__name__)

            return decorator_func(func)
        else:
            # Decorator factory case: @retry(attempts=3) or @when(condition)
            # Return a decorator that validates when applied to a function
            def inner_decorator(func):
                _ensure_is_task(func, decorator_func.__name__)
                # Call the original decorator factory with the parameters,
                # then apply the resulting decorator to the function
                actual_decorator = decorator_func(*args, **kwargs)
                return actual_decorator(func)

            return inner_decorator

    return wrapper


# TaskResult class moved to script_manager.py


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
            script_manager = get_script_manager()
            task_result = script_manager.get_task_result(task_name)
            if task_result:
                task_result._set_result(result)
            return result
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"==> TASK FAILED: {task_name}: {func.__doc__ or 'No description'}")
            logger.error(f"==> {e.__class__.__name__}: {e}")
            logger.info("")
            raise

    # Mark the function as a task
    wrapper.is_dsl_task = True
    wrapper.task_name = func.__name__
    wrapper.original_func = func

    # Register the task with the script manager
    task_info = {
        "name": func.__name__,
        "func": wrapper,
        "condition": getattr(func, "_when_condition", None),
        "retry_config": getattr(func, "_retry_config", None),  # May be updated by @retry
        "always_execute": getattr(func, "_always_execute", False),
    }

    script_manager = get_script_manager()
    script_manager.register_task(task_info, rel_definition_filename)

    # Store reference to task_info so other decorators can update it
    wrapper._task_info = task_info

    # Make the result accessible as an attribute of the function
    wrapper.status = script_manager.get_task_result(func.__name__)

    return wrapper


@task_only
def when(condition):
    """
    Conditional execution decorator with lazy evaluation

    Must be applied to a function that is already decorated with @task.

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

    Can be applied before or after @task decorator.
    """
    func._always_execute = True

    # If this is already a registered task, update its always_execute flag
    if hasattr(func, "_task_info"):
        func._task_info["always_execute"] = True

    return func


def retry(attempts=3, delay=1, backoff=1.0):
    """
    Simple retry decorator

    Must be applied to a function that is already decorated with @task.

    Args:
        attempts: Number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """

    def decorator(func):
        # Store retry config on function (runtime will handle the actual retry)
        retry_config = {"attempts": attempts, "delay": delay, "backoff": backoff}
        func._retry_config = retry_config

        # If this is already a registered task, update its retry config
        if hasattr(func, "_task_info"):
            func._task_info["retry_config"] = retry_config

        return func

    return decorator
