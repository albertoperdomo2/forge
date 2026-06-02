"""
Utilities for the GuideLL-M benchmark toolbox module.
"""

from __future__ import annotations

from typing import Any


def render_guidellm_pvc_from_parts(*, namespace: str, benchmark: dict[str, Any]) -> dict[str, Any]:
    """Render a GuideLL-M PVC manifest from individual components.

    Args:
        namespace: Target namespace
        benchmark: Benchmark configuration

    Returns:
        PVC manifest as dict
    """
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": benchmark["job_name"],
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "forge",
                "forge.openshift.io/project": "llm_d",
            },
        },
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "resources": {"requests": {"storage": benchmark["pvc_size"]}},
        },
    }


def render_guidellm_job_from_parts(
    *,
    namespace: str,
    benchmark: dict[str, Any],
    endpoint_url: str,
) -> dict[str, Any]:
    """Render a GuideLL-M job manifest from individual components.

    Args:
        namespace: Target namespace
        benchmark: Benchmark configuration
        endpoint_url: Gateway endpoint URL

    Returns:
        Job manifest as dict
    """
    args = [
        "benchmark",
        "run",
        f"--target={endpoint_url}",
    ]
    if benchmark.get("rate") is not None:
        args.append(f"--rate={benchmark['rate']}")
    for key, value in benchmark["args"].items():
        if value is None:
            continue
        if isinstance(value, list):
            value = ",".join(str(item) for item in value)
        args.append(f"--{key.replace('_', '-')}={value}")
    args.append("--outputs=json")

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": benchmark["job_name"],
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "forge",
                "forge.openshift.io/project": "llm_d",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "template": {
                "metadata": {
                    "labels": {
                        "app.kubernetes.io/managed-by": "forge",
                        "forge.openshift.io/project": "llm_d",
                    }
                },
                "spec": {
                    "serviceAccountName": "default",
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "guidellm",
                            "image": benchmark["image"],
                            "command": ["/opt/app-root/bin/guidellm"],
                            "args": args,
                            "env": [{"name": "USER", "value": "guidellm"}],
                            "volumeMounts": [
                                {"name": "home", "mountPath": "/home/guidellm"},
                                {"name": "results", "mountPath": "/results"},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "home", "emptyDir": {}},
                        {
                            "name": "results",
                            "persistentVolumeClaim": {"claimName": benchmark["job_name"]},
                        },
                    ],
                },
            },
        },
    }


def render_guidellm_copy_pod_from_parts(
    *,
    namespace: str,
    benchmark: dict[str, Any],
    node_name: str | None = None,
) -> dict[str, Any]:
    """Render a GuideLL-M copy pod manifest from individual components.

    Args:
        namespace: Target namespace
        benchmark: Benchmark configuration
        node_name: Optional node name to pin the pod to

    Returns:
        Pod manifest as dict
    """
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"{benchmark['job_name']}-copy",
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "forge",
                "forge.openshift.io/project": "llm_d",
            },
        },
        "spec": {
            "restartPolicy": "Never",
            "initContainers": [
                {
                    "name": "permission-fixer",
                    "image": benchmark["image"],
                    "command": [
                        "/bin/sh",
                        "-c",
                        "chmod 755 /results && chown -R 1001:1001 /results || true",
                    ],
                    "securityContext": {
                        "runAsUser": 0,
                        "allowPrivilegeEscalation": True,
                    },
                    "volumeMounts": [{"name": "results", "mountPath": "/results"}],
                }
            ],
            "containers": [
                {
                    "name": "copy-helper",
                    "image": benchmark["image"],
                    "command": ["/bin/sleep", "300"],
                    "securityContext": {
                        "runAsUser": 1001,
                        "runAsNonRoot": True,
                        "allowPrivilegeEscalation": False,
                    },
                    "volumeMounts": [{"name": "results", "mountPath": "/results"}],
                }
            ],
            "volumes": [
                {
                    "name": "results",
                    "persistentVolumeClaim": {"claimName": benchmark["job_name"]},
                }
            ],
        },
    }
    if node_name:
        pod["spec"]["nodeName"] = node_name
    return pod
