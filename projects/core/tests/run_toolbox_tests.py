#!/usr/bin/env python3
"""
Test runner for all toolbox script tests.

This script runs both the unit tests and integration tests for the
unified toolbox script to ensure it's working correctly.
"""

import subprocess
import sys
from pathlib import Path


def run_script(script_path):
    """Run a test script and return success status."""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Test timed out"
    except Exception as e:
        return False, "", str(e)


def main():
    """Run all toolbox tests."""
    print("Running FORGE Toolbox Tests")
    print("=" * 40)

    test_dir = Path(__file__).parent
    tests = [
        ("Basic functionality tests", test_dir / "simple_test_toolbox.py"),
        ("Integration tests", test_dir / "test_run_toolbox_integration.py"),
    ]

    total_passed = 0
    total_failed = 0

    for test_name, test_script in tests:
        print(f"\nRunning {test_name}...")
        print("-" * 30)

        if not test_script.exists():
            print(f"❌ Test script not found: {test_script}")
            total_failed += 1
            continue

        success, stdout, stderr = run_script(test_script)

        if success:
            print(f"✅ {test_name} PASSED")
            total_passed += 1
            # Show brief output
            if stdout:
                lines = stdout.strip().split("\n")
                if len(lines) > 5:
                    print("   Output (last 5 lines):")
                    for line in lines[-5:]:
                        print(f"   {line}")
                else:
                    print(f"   Output: {stdout.strip()}")
        else:
            print(f"❌ {test_name} FAILED")
            total_failed += 1
            if stderr:
                print(f"   Error: {stderr}")
            if stdout:
                print(f"   Output: {stdout}")

    print("\n" + "=" * 40)
    print(f"Test Summary: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return False
    else:
        print("\n🎉 All tests passed!")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
