import subprocess
import logging
from dataclasses import dataclass
from typing import Optional, Union
from pathlib import Path

import projects.core.library.env as env
from projects.core.library.run import SignalError

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    """Result of a command execution"""
    stdout: str
    stderr: str
    returncode: int
    command: str

    @property
    def success(self) -> bool:
        return self.returncode == 0

def run(
        command: str,
        check: bool = True,
        capture_output: bool = True,
        shell: bool = True,
        stdout_dest: Optional[Union[str, Path]] = None,
        log_stdout: bool = True,
        log_stderr: bool = True,
) -> CommandResult:
    """
    Execute a shell command

    Args:
        command: Command to execute
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout/stderr
        shell: Execute through shell
        stdout_dest: Optional file path to write stdout to
        log_stdout: Optional. If False, don't log the content of stdout.
        log_stderr: Optional. If False, don't log the content of stderr.
    Returns:
        CommandResult with execution details
    """
    # Print command in verbose format
    logger.info("==")
    logger.info(f"<command> {command}")

    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=False,  # We handle check ourselves
            capture_output=capture_output,
            text=True
        )

        cmd_result = CommandResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            returncode=result.returncode,
            command=command
        )

        # Write stdout to file if requested
        if stdout_dest and cmd_result.stdout:
            stdout_path = Path(stdout_dest)
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            with open(stdout_path, 'w') as f:
                f.write(cmd_result.stdout)

        # Print output in verbose format
        if result.stdout:
            if log_stdout:
                logger.info(f"<stdout> {result.stdout.strip()}")
            else:
                logger.info(f"<stdout not logged>")

        if result.stderr:
            if log_stderr:
                logger.info(f"<stderr> {result.stderr.strip()}")
            else:
                logger.info(f"<stderr not logged>")

        if not (result.stdout or result.stderr):
            logger.info(f"<no output>")

        if result.returncode != 0:
            logger.info(f"<exit_code> {result.returncode}")

        logger.info("==")
        logger.info("")

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return cmd_result

    except (KeyboardInterrupt, SignalError):
        raise
    except Exception as e:
        logger.error(f"<{e.__class__.__name__}> {e}")
        logger.info("")
        raise

def mkdir(path, *, parents=True, exists_ok=True):
    """Create a directory with default arguments"""
    logger.info(f"<shell> mkdir {path}")

    if not isinstance(path, Path):
        path = Path(path)

    if not path.is_absolute():
        path = env.ARTIFACT_DIR / path

    return path.mkdir(parents=parents, exist_ok=exists_ok)
