import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import env

logger = logging.getLogger(__name__)


class Parallel:
    """
    Context manager for parallel execution of tasks with immediate cancellation on failure.

    Uses ThreadPoolExecutor for multithreaded execution with thread-safe artifact directory handling.
    When any task fails, all remaining tasks are immediately cancelled rather than waiting
    for completion.

    Each parallel task runs with its own dedicated artifact directory accessible via env.ARTIFACT_DIR,
    allowing tasks to write artifacts without conflicts. The dedicated directory is created as:
    env.ARTIFACT_DIR / f"{next_count:03d}__{name}"

    Usage:
        with run_parallel.Parallel("task_name") as parallel:
            parallel.delayed(function1, arg1, arg2)
            parallel.delayed(function2, arg3, kwarg=value)
            # Tasks execute in parallel when exiting the context
            # Each task can access its dedicated directory via env.ARTIFACT_DIR
    """

    def __init__(self, name, exit_on_exception=True, dedicated_dir=True):
        """
        Initialize parallel execution context.

        Args:
            name: Name for the parallel execution (used for artifact directory)
            exit_on_exception: If True, kill process group on exception
            dedicated_dir: If True, create dedicated artifact directory for this parallel execution
        """
        self.name = name
        self.parallel_tasks = None
        self.exit_on_exception = exit_on_exception
        self.dedicated_dir = dedicated_dir

    def __enter__(self):
        """Enter the parallel context."""
        self.parallel_tasks = []
        return self

    def delayed(self, function, *args, **kwargs):
        """
        Add a function to be executed in parallel.

        Args:
            function: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        # Simple task container - no joblib needed
        from collections import namedtuple

        DelayedTask = namedtuple("DelayedTask", ["func", "args", "keywords"])
        task = DelayedTask(func=function, args=args, keywords=kwargs)
        self.parallel_tasks.append(task)

    def __exit__(self, ex_type, ex_value, exc_traceback):
        """Execute all delayed tasks in parallel with immediate cancellation on failure."""
        if ex_value:
            logger.warning(
                f"An exception occured while preparing the '{self.name}' Parallel execution ..."
            )
            return False

        if self.dedicated_dir:
            # Create dedicated directory without modifying global ARTIFACT_DIR
            # to avoid race conditions in multithreaded execution.
            # Each parallel task will inherit the current ARTIFACT_DIR context.
            next_count = env.next_artifact_index()
            parallel_dir = env.ARTIFACT_DIR / f"{next_count:03d}__{self.name}"
            parallel_dir.mkdir(exist_ok=True)
            logger.debug(f"Created parallel execution directory: {parallel_dir}")
        else:
            parallel_dir = None

        def _run_with_artifact_dir(func, artifact_dir, *args, **kwargs):
            """Wrapper to run function with specific ARTIFACT_DIR for this thread."""
            if artifact_dir:
                # Ensure thread has its own copy of ARTIFACT_DIR, then set it to dedicated directory
                try:
                    original_artifact_dir = env.ensure_thread_artifact_dir()
                except ValueError:
                    # No global ARTIFACT_DIR to inherit from
                    original_artifact_dir = None

                try:
                    env._set_tls_artifact_dir(artifact_dir)
                    return func(*args, **kwargs)
                finally:
                    if original_artifact_dir is not None:
                        env._set_tls_artifact_dir(original_artifact_dir)
            else:
                # No dedicated directory, ensure thread has its own copy of main ARTIFACT_DIR
                try:
                    env.ensure_thread_artifact_dir()
                except ValueError:
                    pass  # Continue without thread-local copy
                return func(*args, **kwargs)

        # Use ThreadPoolExecutor for better cancellation control
        max_workers = min(len(self.parallel_tasks), os.cpu_count() or 1)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks with artifact directory context
            futures = []
            for delayed_func in self.parallel_tasks:
                # Wrap each function to run with the dedicated artifact directory
                future = executor.submit(
                    _run_with_artifact_dir,
                    delayed_func.func,
                    parallel_dir,
                    *delayed_func.args,
                    **delayed_func.keywords,
                )
                futures.append(future)

            try:
                # Wait for all tasks to complete
                for future in as_completed(futures):
                    future.result()  # This will raise any exception that occurred

            except Exception as e:
                # Cancel all remaining tasks immediately
                logger.error("Exception in parallel task, cancelling remaining tasks...")
                for future in futures:
                    future.cancel()

                # Give a short time for cancellation to take effect
                time.sleep(0.1)

                if not self.exit_on_exception:
                    raise e

                traceback.print_exc()
                logger.error(f"Exception caught during the '{self.name}' Parallel execution.")
                raise SystemExit(1) from e

        return False  # If we returned True here, any exception would be suppressed!
