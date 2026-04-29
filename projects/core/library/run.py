import logging
import os
import signal
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import env

logger = logging.getLogger(__name__)


def init():
    signal.signal(signal.SIGINT, raise_signal)
    signal.signal(signal.SIGTERM, raise_signal)

    # create new process group, become its leader,
    # except if we're already pid 1 (defacto group leader, setpgrp
    # gets permission denied error)
    if os.getpid() != 1:
        try:
            os.setpgrp()
        except Exception as e:
            logger.warning(f"Cannot call os.setpgrp: {e}")


class SignalError(SystemExit):
    def __init__(self, sig, frame):
        self.sig = sig
        self.frame = frame

    def __str__(self):
        return f"SignalError(sig={self.sig})"


def raise_signal(sig, frame):
    raise SignalError(sig, frame)


def run(
    command,
    capture_stdout=False,
    capture_stderr=False,
    check=True,
    protect_shell=True,
    cwd=None,
    stdin_file=None,
    log_command=True,
    decode_stdout=True,
    decode_stderr=True,
):
    if log_command:
        logger.info(f"run: {command}")

    args = {}

    args["cwd"] = cwd
    args["shell"] = True

    if capture_stdout:
        args["stdout"] = subprocess.PIPE
    if capture_stderr:
        args["stderr"] = subprocess.PIPE
    if check:
        args["check"] = True
    if stdin_file:
        if not hasattr(stdin_file, "fileno"):
            raise ValueError("Argument 'stdin_file' must be an open file (with a file descriptor)")
        args["stdin"] = stdin_file

    if protect_shell:
        command = f"set -o errexit;set -o pipefail;set -o nounset;set -o errtrace;{command}"

    proc = subprocess.run(command, **args)

    if capture_stdout and decode_stdout:
        proc.stdout = proc.stdout.decode("utf8")
    if capture_stderr and decode_stderr:
        proc.stderr = proc.stderr.decode("utf8")

    return proc


def run_and_catch(exc, fct, *args, **kwargs):
    """
    Helper function for chaining multiple functions without swallowing exceptions
    Example:

    exc = None
    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "kserve", "capture_operators_state", run_kwargs=dict(capture_stdout=True),
    )

    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "cluster", "capture_environment", run_kwargs=dict(capture_stdout=True),
    )

    if exc: raise exc
    """
    if not (exc is None or isinstance(exc, Exception)):
        raise ValueError(f"exc={exc} should be None or an Exception ({exc.__class__})")

    try:
        fct(*args, **kwargs)
    except Exception as e:
        logger.error(f"{e.__class__.__name__}: {e}")
        exc = exc or e
    return exc


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
        with run.Parallel("task_name") as parallel:
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
                # Use thread-local storage (thread-safe)
                original_artifact_dir = env.ARTIFACT_DIR
                try:
                    env._set_tls_artifact_dir(artifact_dir)
                    return func(*args, **kwargs)
                finally:
                    env._set_tls_artifact_dir(original_artifact_dir)
            else:
                # No dedicated directory, run normally
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
