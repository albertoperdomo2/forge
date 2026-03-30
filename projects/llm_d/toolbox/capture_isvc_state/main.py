#!/usr/bin/env python3

"""
LLMInferenceService state capture using task-based DSL
Replaces llmd_capture_isvc_state Ansible role
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

from projects.core.library import env
from projects.core.dsl import task, retry, when, always, execute_tasks, clear_tasks, shell
from projects.core.dsl.cli import create_dynamic_parser

def run(
    llmisvc_name: str,
    namespace: str = ""
):
    """
    Capture LLMInferenceService state using task-based DSL

    Args:
        llmisvc_name: Name of the LLMInferenceService to capture
        namespace: Namespace of the LLMInferenceService (empty string auto-detects current namespace)
    """

    # Execute all registered tasks in order, respecting conditions
    return execute_tasks(locals())


@task
def setup_directories(args):
    """Create the artifacts directory"""

    shell.mkdir("artifacts")
    return "Artifacts directory created"


@task
def get_current_timestamp(args):
    """Get current timestamp"""

    result = shell.run("date -Iseconds")
    args.capture_timestamp = result.stdout.strip()
    return f"Timestamp: {args.capture_timestamp}"


@task
def determine_target_namespace(args):
    """Get current namespace if not specified"""
    if args.namespace:
        args.target_namespace = args.namespace
        return f"Using specified namespace: {args.target_namespace}"

    result = shell.run("oc project -q")
    args.target_namespace = result.stdout.strip()
    return f"Using current namespace: {args.target_namespace}"


@task
def capture_llminferenceservice_yaml(args):
    """Capture the LLMInferenceService definition"""
    shell.run(
        f'oc get llminferenceservice {args.llmisvc_name} -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.yaml",
        check=False
    )
    return "LLMInferenceService YAML captured"


@task
def capture_llminferenceservice_json(args):
    """Capture LLMInferenceService status in JSON for easier parsing"""
    shell.run(
        f'oc get llminferenceservice {args.llmisvc_name} -n {args.target_namespace} -ojson',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.json",
        check=False
    )
    return "LLMInferenceService JSON captured"


@task
def capture_related_pods_yaml(args):
    """Capture all pods related to the LLMInferenceService"""
    shell.run(
        f'oc get pods -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.pods.yaml",
        check=False
    )
    return "Related pods YAML captured"


@task
def capture_related_deployments(args):
    """Capture deployments related to the LLMInferenceService"""
    shell.run(
        f'oc get deployments -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.deployments.yaml",
        check=False
    )
    return "Related deployments captured"


@task
def capture_related_replicasets(args):
    """Capture replicasets related to the LLMInferenceService"""
    shell.run(
        f'oc get replicasets -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.replicasets.yaml",
        check=False
    )
    return "Related replicasets captured"


@task
def capture_namespace_pods(args):
    """Capture all pods in the namespace with wide output"""
    shell.run(
        f'oc get pods -owide -n {args.target_namespace}',
        stdout_dest=args.artifact_dir / "artifacts/namespace.pods.status",
        check=False
    )
    return "Namespace pods status captured"


@task
def capture_namespace_services(args):
    """Capture all services in the namespace"""
    shell.run(
        f'oc get svc -n {args.target_namespace}',
        stdout_dest=args.artifact_dir / "artifacts/namespace.services.status",
        check=False
    )
    return "Namespace services captured"


@task
def capture_servicemonitors(args):
    """Capture ServiceMonitors for monitoring"""
    shell.run(
        f'oc get servicemonitor -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.servicemonitors.yaml",
        check=False
    )
    return "ServiceMonitors captured"


@task
def capture_podmonitors(args):
    """Capture PodMonitors for monitoring"""
    shell.run(
        f'oc get podmonitor -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -oyaml',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.podmonitors.yaml",
        check=False,
    )
    return "PodMonitors captured"


@task
def capture_pod_logs(args):
    """Capture logs from LLMInferenceService pods"""
    # Get list of pod names
    result = shell.run(
        f'oc get pods -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -o jsonpath="{{.items[*].metadata.name}}"',
        check=False,
        log_stdout=False,
    )

    pod_names = result.stdout.strip().split()
    if not pod_names or not result.stdout.strip():
        return "No pods found to capture logs"

    log_file = args.artifact_dir / "artifacts/llminferenceservice.pods.logs"

    # Capture logs for each pod
    with open(log_file, 'w') as f:  # Start with empty file
        for pod_name in pod_names:
            f.write(f"=== Logs for pod: {pod_name} ===\n")

            # Get logs for this pod
            log_result = shell.run(
                f'oc logs {pod_name} -n {args.target_namespace} --all-containers=true',
                check=False,
                log_stdout=False,
            )
            f.write(log_result.stdout)
            f.write("\n")

    return f"Pod logs captured for {len(pod_names)} pods"


@task
def capture_pod_previous_logs(args):
    """Capture previous logs from LLMInferenceService pods if available"""
    # Get list of pod names
    result = shell.run(
        f'oc get pods -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -o jsonpath="{{.items[*].metadata.name}}"',
        check=False
    )

    pod_names = result.stdout.strip().split()
    if not pod_names or not result.stdout.strip():
        return "No pods found to capture previous logs"

    log_file = args.artifact_dir / "artifacts/llminferenceservice.pods.previous.logs"

    # Capture previous logs for each pod
    with open(log_file, 'w') as f:  # Start with empty file
        for pod_name in pod_names:
            f.write(f"=== Previous logs for pod: {pod_name} ===\n")

            # Get previous logs for this pod
            log_result = shell.run(
                f'oc logs {pod_name} -n {args.target_namespace} --previous --all-containers=true',
                check=False,
                log_stdout=False,
            )
            f.write(log_result.stdout)
            f.write("\n")

    return f"Pod previous logs captured for {len(pod_names)} pods"


@task
def capture_llminferenceservice_describe(args):
    """Capture describe output for the LLMInferenceService"""
    shell.run(
        f'oc describe llminferenceservice {args.llmisvc_name} -n {args.target_namespace}',
        stdout_dest=args.artifact_dir / "artifacts/llminferenceservice.describe.txt",
        check=False
    )
    return "LLMInferenceService describe captured"


@task
def capture_pods_describe(args):
    """Capture describe output for related pods"""
    # Get list of pod names
    result = shell.run(
        f'oc get pods -l "app.kubernetes.io/name={args.llmisvc_name}" -n {args.target_namespace} -o jsonpath="{{.items[*].metadata.name}}"',
        check=False
    )

    pod_names = result.stdout.strip().split()
    if not pod_names or not result.stdout.strip():
        return "No pods found to describe"

    describe_file = args.artifact_dir / "artifacts/llminferenceservice.pods.describe.txt"

    # Capture describe output for each pod
    with open(describe_file, 'w') as f:  # Start with empty file
        for pod_name in pod_names:
            f.write(f"=== Describe for pod: {pod_name} ===\n")

            # Get describe output for this pod
            describe_result = shell.run(
                f'oc describe pod {pod_name} -n {args.target_namespace}',
                log_stdout=False,
                check=False
            )
            f.write(describe_result.stdout)
            f.write("\n")

    return f"Pod describe output captured for {len(pod_names)} pods"


def main():
    """CLI entrypoint with dynamic argument discovery"""

    # Create parser dynamically from function signature
    parser = create_dynamic_parser(
        capture_isvc_state,
        positional_args=['llmisvc_name']
    )
    args = parser.parse_args()

    # Convert args to kwargs for function call
    kwargs = vars(args)
    env.init(daily_artifact_dir=True)
    try:
        capture_isvc_state(**kwargs)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
