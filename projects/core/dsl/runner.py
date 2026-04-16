"""
Command runner for DSL tasks
"""

import subprocess
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger('DSL')
logger.propagate = False  # Don't show logger prefix

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

def run(command: str, check: bool = True, capture_output: bool = True, shell: bool = True) -> CommandResult:
    """
    Execute a shell command

    Args:
        command: Command to execute
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout/stderr
        shell: Execute through shell

    Returns:
        CommandResult with execution details
    """
    # Print command in verbose format
    logger.info(f"== command == {command}")

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

        # Print output in verbose format
        if result.stdout:
            print(f"| <stdout> {result.stdout.strip()}")
        if result.stderr:
            print(f"| <stderr> {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"| <exit_code> {result.returncode}")

        print()

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return cmd_result

    except Exception as e:
        print(f"<error> {e}")
        print()
        raise
