#!/usr/bin/env python3
"""
Integration tests for the unified toolbox script CLI interface.

Tests the actual command line interface behavior by running the script
with different arguments and checking the output.
"""

import subprocess
import sys
from pathlib import Path

try:
    import pytest
except ImportError:
    # pytest not available locally, but will be in CI
    class MockPytest:
        class mark:
            @staticmethod
            def integration(func):
                return func

    pytest = MockPytest()


def run_toolbox_command(args):
    """Run the toolbox script with given arguments and return result."""
    script_path = Path(__file__).parent.parent / "toolbox" / "run_toolbox.py"
    cmd = [sys.executable, str(script_path)] + args

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,  # Prevent hanging
    )

    return result.returncode, result.stdout, result.stderr


@pytest.mark.integration
def test_list_all_commands():
    """Test listing all commands (no arguments)."""
    returncode, stdout, stderr = run_toolbox_command([])

    assert returncode == 0, f"Command failed with stderr: {stderr}"
    assert "Available toolbox commands:" in stdout
    assert "cluster:" in stdout
    assert "llm_d:" in stdout
    assert "Cluster Management Toolbox" in stdout


@pytest.mark.integration
def test_list_commands_explicit():
    """Test explicit list command."""
    returncode, stdout, stderr = run_toolbox_command(["list"])

    assert returncode == 0, f"Command failed with stderr: {stderr}"
    assert "Available toolbox commands:" in stdout
    assert "cluster:" in stdout


@pytest.mark.integration
def test_help_command():
    """Test help command."""
    returncode, stdout, stderr = run_toolbox_command(["--help"])

    assert returncode == 0, f"Command failed with stderr: {stderr}"
    assert "FORGE Toolbox" in stdout
    assert "Usage:" in stdout
    assert "Examples:" in stdout


@pytest.mark.integration
def test_project_specific_listing():
    """Test listing commands for a specific project."""
    returncode, stdout, stderr = run_toolbox_command(["cluster"])

    assert returncode == 0, f"Command failed with stderr: {stderr}"
    assert "Cluster project toolbox commands:" in stdout
    # Check for commands that actually have main.py files
    assert "build-image" in stdout
    assert "Usage: run_toolbox.py cluster <command>" in stdout


@pytest.mark.integration
def test_invalid_project():
    """Test error handling for invalid project."""
    returncode, stdout, stderr = run_toolbox_command(["nonexistent_project"])

    assert returncode == 1, (
        f"Should return error code for invalid project. Got returncode: {returncode}, stdout: {stdout}, stderr: {stderr}"
    )
    assert "Error: Project 'nonexistent_project' not found" in stderr, (
        f"Expected error message not found. stderr: {stderr}"
    )
    # The available projects list goes to stdout
    assert "Available projects:" in stdout, (
        f"Expected 'Available projects:' not found. stdout: {stdout}"
    )
    assert "cluster" in stdout, f"Expected 'cluster' not found. stdout: {stdout}"


@pytest.mark.integration
def test_invalid_command():
    """Test error handling for invalid command within valid project."""
    returncode, stdout, stderr = run_toolbox_command(["cluster", "nonexistent_command"])

    assert returncode == 1, "Should return error code for invalid command"
    assert "Error: Command 'nonexistent_command' not found in project 'cluster'" in stderr
