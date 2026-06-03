#!/usr/bin/env python3

from __future__ import annotations

import logging

from projects.core.dsl import entrypoint, execute_tasks, retry, task
from projects.core.dsl.utils.k8s import resource_exists

logger = logging.getLogger("DSL")


@entrypoint
def run(
    crd_names: list[str],
    *,
    timeout_seconds: int = 900,
    display_name: str = "",
) -> int:
    """
    Wait for multiple CustomResourceDefinitions to exist.

    Args:
        crd_names: List of CRD names to wait for
        timeout_seconds: Maximum time to wait for each CRD
        display_name: Optional human-friendly name used in logs
    """

    execute_tasks(locals())
    return 0


@task
def setup_directories(args, ctx):
    """Create artifact directories"""

    # Create artifacts directory for capturing CRD states
    artifacts_dir = args.artifact_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ctx.display_name = args.display_name or f"{len(args.crd_names)} CRDs"
    return f"Prepared to wait for {ctx.display_name}"


@task
def validate_parameters(args, ctx):
    """Validate command parameters"""

    if not args.crd_names:
        raise ValueError("crd_names list cannot be empty")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    return f"Will wait for {len(args.crd_names)} CRDs with {args.timeout_seconds}s timeout each"


@retry(attempts=90, delay=10, backoff=1.0)
@task
def wait_for_all_crds(args, ctx):
    """Wait for all specified CRDs to exist"""

    missing_crds = []

    for crd_name in args.crd_names:
        if not resource_exists("crd", crd_name):
            missing_crds.append(crd_name)

    if missing_crds:
        return (False, f"Waiting for CRDs: {', '.join(missing_crds)}")

    return f"All {len(args.crd_names)} CRDs are available"


if __name__ == "__main__":
    run.main()
