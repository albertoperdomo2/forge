#!/usr/bin/env python3

"""
Example LLM inference service deployment using task-based DSL
"""

import sys
import logging

from projects.core.library import env
from projects.core.dsl import task, retry, when, always, execute_tasks, clear_tasks, shell
from projects.core.dsl.cli import create_dynamic_parser

# Simplified orchestration function
def deploy_llm_inference_service(
    name: str,
    namespace: str,
    yaml_file: str = None,
):
    """
    Deploy LLM inference service using task-based DSL

    Args:
        name: Name of the LLM inference service
        namespace: Kubernetes namespace
        yaml_file: Path to YAML file for deployment
    """

    # Execute all registered tasks in order, respecting conditions
    return execute_tasks(locals())

@task
def setup_directories(args):
    """Create directory structure"""
    # Use the artifact directory provided by NextArtifactDir
    shell.mkdir("src")
    shell.mkdir("artifacts")

    return "Artifacts dir created"


@task
def check_existing_service(args):
    """Check if LLM inference service already exists"""
    result = shell.run(f"oc get llminferenceservice {args.name} -n {args.namespace} --ignore-not-found")

    if not result.stdout.strip():
        return "doesn't exist"

    # Save existing service
    shell.run(
        f"oc get llminferenceservice {args.name} -n {args.namespace} -oyaml",
        stdout_dest=args.artifact_dir / "artifacts/old_service.yaml"
    )
    return True


@task
@when(lambda: check_existing_service.status.return_value is True)
def delete_existing_service(args):
    """Delete the existing LLM inference service"""

    shell.run(f"oc delete llminferenceservice {args.name} -n {args.namespace} --ignore-not-found")


@task
@when(lambda: check_existing_service.status.return_value is True)
@retry(attempts=30, delay=10)
def wait_for_pods_deleted(args):
    """Wait for all old LLM inference service pods to be deleted"""

    cmd = f"oc get pods -l 'app.kubernetes.io/name={args.name}' -n {args.namespace} --no-headers"
    result = shell.run(cmd)

    if result.stdout.strip():
        raise ValueError("Pods still exist")

    return "LLMISVC pods deleted."


@task
@retry(attempts=5, delay=1)
def wait_for_service_ready(args):
    """Wait for the LLM inference service to be ready"""

    cmd = (f"oc get llminferenceservice {args.name} -n {args.namespace} "
           "-ojsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'")

    result = shell.run(cmd)

    if result.stdout.strip() != "True":
        raise ValueError("LLMISVC not ready yet")

    return "LLMISVC is ready"

@task
@always
def capture_final_state(args):
    """Capture final service state"""

    # Final service state
    shell.run(
        f"oc get llminferenceservice {args.name} -n {args.namespace} -oyaml",
        stdout_dest=args.artifact_dir / "artifacts/final_service.yaml",
        check=False,
    )

    # Pod status
    shell.run(
        f"oc get pods -l 'app.kubernetes.io/name={args.name}' -n {args.namespace} -o wide",
        stdout_dest=args.artifact_dir / "artifacts/pods_status.txt",
        check=False,
    )

    # Deployments
    shell.run(
        f"oc get deployments -l 'app.kubernetes.io/name={args.name}' -n {args.namespace} -oyaml",
        stdout_dest=args.artifact_dir / "artifacts/deployments.yaml",
        check=False,
    )


def main():
    """CLI entrypoint with dynamic argument discovery"""

    # Create parser dynamically from function signature
    # Make name and namespace positional arguments
    parser = create_dynamic_parser(
        deploy_llm_inference_service,
        positional_args=['name', 'namespace']
    )
    args = parser.parse_args()

    # Convert args to kwargs for function call (names should match exactly now)
    kwargs = vars(args)
    env.init(daily_artifact_dir=True)
    try:
        deploy_llm_inference_service(**kwargs)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
