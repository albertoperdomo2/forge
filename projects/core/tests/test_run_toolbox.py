#!/usr/bin/env python3
"""
Tests for the unified toolbox script run_toolbox.py

Validates project discovery, command discovery, description extraction,
and command line argument handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from projects.core.toolbox.run_toolbox import (
    discover_commands,
    discover_projects,
    get_command_description,
    get_project_description,
)


def test_discover_projects():
    """Test project discovery finds expected projects."""
    projects = discover_projects()

    # Should find at least these core projects
    expected_projects = {"cluster", "llm_d", "fournos_launcher", "skeleton"}
    found_projects = set(projects.keys())

    assert expected_projects.issubset(found_projects), (
        f"Missing expected projects. Expected: {expected_projects}, Found: {found_projects}"
    )

    # All discovered projects should have toolbox directories
    for project_name, project_path in projects.items():
        toolbox_dir = project_path / "toolbox"
        assert toolbox_dir.exists(), f"Project {project_name} missing toolbox directory"
        assert toolbox_dir.is_dir(), f"Project {project_name} toolbox is not a directory"


def test_discover_commands():
    """Test command discovery within projects."""
    projects = discover_projects()

    # Test cluster project specifically
    cluster_path = projects.get("cluster")
    assert cluster_path is not None, "cluster project not found"

    commands = discover_commands(cluster_path)
    expected_commands = {"build_image"}  # This one should exist with main.py
    found_commands = set(commands)

    assert expected_commands.issubset(found_commands), (
        f"Missing expected commands in cluster project. "
        f"Expected: {expected_commands}, Found: {found_commands}"
    )

    # Commands should be sorted
    assert commands == sorted(commands), "Commands should be returned in sorted order"


def test_discover_commands_empty_project():
    """Test command discovery with a project that has no commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_project = Path(temp_dir)
        toolbox_dir = temp_project / "toolbox"
        toolbox_dir.mkdir()

        commands = discover_commands(temp_project)
        assert commands == [], "Empty toolbox should return empty command list"


def test_get_command_description_valid():
    """Test extracting description from a valid command."""
    # Test with build_image which should have a docstring
    description = get_command_description("cluster", "build_image")

    assert description != "No description available"
    assert len(description) > 0
    assert description.strip() == description  # Should be stripped


def test_get_command_description_invalid_project():
    """Test command description for non-existent project."""
    description = get_command_description("nonexistent_project", "some_command")
    assert description == "No description available"


def test_get_command_description_invalid_command():
    """Test command description for non-existent command."""
    description = get_command_description("cluster", "nonexistent_command")
    assert description == "No description available"


def test_get_project_description_valid():
    """Test extracting description from a valid project."""
    # Test with cluster project which should have a description
    description = get_project_description("cluster")

    assert description != ""
    assert "Cluster Management Toolbox" in description
    assert description.strip() == description  # Should be stripped


def test_get_project_description_invalid_project():
    """Test project description for non-existent project."""
    description = get_project_description("nonexistent_project")
    assert description == ""


def test_get_project_description_no_docstring():
    """Test project description for project without docstring."""
    # Create a temporary project structure without docstring
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_forge = Path(temp_dir)
        projects_dir = temp_forge / "projects"
        projects_dir.mkdir()

        test_project = projects_dir / "test_project"
        test_project.mkdir()

        toolbox_dir = test_project / "toolbox"
        toolbox_dir.mkdir()

        # Create __init__.py without docstring
        init_file = toolbox_dir / "__init__.py"
        init_file.write_text("# Empty module\n")

        # Mock FORGE_HOME to point to temp directory
        with patch("projects.core.toolbox.run_toolbox.get_forge_home", return_value=temp_forge):
            description = get_project_description("test_project")
            assert description == ""


def test_command_name_conversion():
    """Test that command names are properly discovered with underscores."""
    projects = discover_projects()
    cluster_commands = discover_commands(projects["cluster"])

    # Should have commands with underscores (if any exist with main.py)
    for command in cluster_commands:
        # Test that we can get descriptions for commands
        description = get_command_description("cluster", command)
        # Should not fail, even if no description available
        assert isinstance(description, str)


def test_path_handling():
    """Test that path operations work correctly."""
    projects = discover_projects()

    # All paths should be absolute and exist
    for _project_name, project_path in projects.items():
        assert project_path.is_absolute()
        assert project_path.exists()
        assert project_path.is_dir()


def test_module_imports():
    """Test that the run_toolbox module can be imported and has expected functions."""
    from projects.core.toolbox import run_toolbox

    # Check that key functions exist
    assert hasattr(run_toolbox, "discover_projects")
    assert hasattr(run_toolbox, "discover_commands")
    assert hasattr(run_toolbox, "get_command_description")
    assert hasattr(run_toolbox, "get_project_description")
    assert hasattr(run_toolbox, "main")
