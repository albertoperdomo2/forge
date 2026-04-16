#!/usr/bin/env python3

"""
Skeleton Project Cluster Information Toolbox

Demonstrates basic FORGE toolbox capabilities by gathering cluster information.
This shows the current possibilities available in the FORGE framework.
"""

from projects.core.dsl import (
    execute_tasks,
    shell,
    task,
    toolbox,
)


def run(*, output_format: str = "text"):
    """
    Gather basic cluster and environment information

    Args:
        output_format: Output format for results (text, json, yaml)
    """

    # Execute all registered tasks in order, respecting conditions
    return execute_tasks(locals())


@task
def prepare_ctx(args, ctx):
    if args.output_format == "text" or not args.output_format:
        ctx.ext = "txt"
        ctx.output_format = ""
    elif args.output_format == "yaml":
        ctx.ext = "yaml"
        ctx.output_format = "-oyaml"
    elif args.output_format == "json":
        ctx.output_format = "-ojson"
        ctx.ext = "json"
    else:
        raise ValueError(f"Unexpected output_format='{args.output_format}' value")


@task
def setup_directories(args, ctx):
    """Create the artifacts directory"""

    shell.mkdir("artifacts")
    return "Artifacts directory created"


@task
def check_whoami(args, ctx):
    """Show current user information"""

    # Save to file
    shell.run(
        "oc whoami",
        stdout_dest=args.artifact_dir / "artifacts" / "current_user.txt",
    )


@task
def get_cluster_nodes(args, ctx):
    """List all available nodes in the cluster"""

    ctx.cluster_nodes_dest = (
        args.artifact_dir / "artifacts" / f"cluster_nodes.{ctx.ext}"
    )
    # Get nodes with wide output for more information
    shell.run(
        f"oc get nodes {ctx.output_format}",
        stdout_dest=ctx.cluster_nodes_dest,
    )


# Create the main function using the toolbox library
main = toolbox.create_toolbox_main(run)


if __name__ == "__main__":
    main()
