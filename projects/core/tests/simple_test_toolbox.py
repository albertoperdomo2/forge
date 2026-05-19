#!/usr/bin/env python3
"""
Simple test script to validate the basic functionality of the toolbox script.
"""

import sys
from pathlib import Path

# Add the forge home to the path so we can import the run_toolbox module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from projects.core.toolbox.run_toolbox import (
    discover_commands,
    discover_projects,
    get_command_description,
    get_project_description,
)


def test_basic_functionality():
    """Test basic functionality works."""
    print("Testing basic functionality...")

    # Test project discovery
    print("  Testing project discovery...")
    projects = discover_projects()
    print(f"    Found {len(projects)} projects: {list(projects.keys())}")

    expected_projects = {"cluster", "llm_d", "fournos_launcher", "skeleton"}
    found_projects = set(projects.keys())

    if not expected_projects.issubset(found_projects):
        print(
            f"    ❌ Missing expected projects. Expected: {expected_projects}, Found: {found_projects}"
        )
        return False
    print("    ✓ All expected projects found")

    # Test command discovery
    print("  Testing command discovery...")
    cluster_commands = discover_commands(projects["cluster"])
    print(f"    Found {len(cluster_commands)} cluster commands: {cluster_commands}")

    if not cluster_commands:
        print("    ❌ No cluster commands found")
        return False
    print("    ✓ Cluster commands found")

    # Test command description extraction
    print("  Testing command description extraction...")
    if "cluster_deploy_operator" in cluster_commands:
        desc = get_command_description("cluster", "cluster_deploy_operator")
        print(f"    cluster_deploy_operator: {desc}")
        if "No description available" in desc:
            print("    ❌ Could not extract command description")
            return False
    print("    ✓ Command description extracted")

    # Test project description extraction
    print("  Testing project description extraction...")
    project_desc = get_project_description("cluster")
    print(f"    cluster project: {project_desc}")
    if not project_desc or project_desc == "":
        print("    ❌ Could not extract project description")
        return False
    print("    ✓ Project description extracted")

    return True


def test_error_handling():
    """Test error handling."""
    print("Testing error handling...")

    # Test invalid project
    desc = get_command_description("nonexistent_project", "some_command")
    if desc != "No description available":
        print(f"    ❌ Expected 'No description available', got '{desc}'")
        return False
    print("    ✓ Invalid project handled correctly")

    # Test invalid command
    desc = get_command_description("cluster", "nonexistent_command")
    if desc != "No description available":
        print(f"    ❌ Expected 'No description available', got '{desc}'")
        return False
    print("    ✓ Invalid command handled correctly")

    # Test invalid project description
    desc = get_project_description("nonexistent_project")
    if desc != "":
        print(f"    ❌ Expected empty string, got '{desc}'")
        return False
    print("    ✓ Invalid project description handled correctly")

    return True


def main():
    """Run all tests."""
    print("Running toolbox script tests...\n")

    tests = [
        ("Basic functionality", test_basic_functionality),
        ("Error handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"Running {test_name}:")
            if test_func():
                print(f"✓ {test_name} PASSED\n")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED\n")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}\n")
            failed += 1

    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
