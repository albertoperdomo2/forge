#!/usr/bin/env python3

import sys
import os
from pathlib import Path
import datetime

def main():
    # Get script directory
    script_dir = Path(__file__).parent
    FORGE_HOME = script_dir.parent.parent.parent.parent

    # Paths
    yaml_file = script_dir / "forge-light.yaml"
    containerfile = script_dir / ".." / "Containerfile.lightweight"
    containerfile_relative = containerfile.resolve().relative_to(FORGE_HOME)

    # Check if files exist
    if not yaml_file.exists():
        print(f"Error: {yaml_file} not found", file=sys.stderr)
        sys.exit(1)

    if not containerfile.exists():
        print(f"Error: {containerfile} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Including {containerfile} into {yaml_file}", file=sys.stderr)

    # Read the Containerfile content
    with open(containerfile, 'r') as f:
        dockerfile_content = f.read()

    # Read the YAML file and process it
    with open(yaml_file, 'r') as f:
        yaml_lines = f.readlines()

    result_lines = []
    skip_next_line = False

    for line in yaml_lines:
        # Look for the placeholder comment
        if line.strip().startswith("# INCLUDE HERE"):
            result_lines.append(f"      # synchronized on {str(datetime.datetime.now().date())} from openshift-psap/forge:{containerfile_relative}\n")
            # Replace with dockerfile content using literal block scalar
            for dockerfile_line in dockerfile_content.splitlines():
                if dockerfile_line:
                    result_lines.append(f"      {dockerfile_line}\n")
                else:
                    result_lines.append("\n")

            result_lines.append("\n")
        else:
            result_lines.append(line)


    # Output the result
    for line in result_lines:
        print(line, end='')

    print("Done! Dockerfile content has been included", file=sys.stderr)

if __name__ == "__main__":
    main()
