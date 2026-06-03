"""
Utilities for the smoke request toolbox module.
"""

from __future__ import annotations

import json
from typing import Any


def render_smoke_request_job_from_parts(
    *,
    namespace: str,
    job_name: str,
    client_image: str,
    endpoint_path: str,
    request_retries: int,
    request_retry_delay_seconds: int,
    request_timeout_seconds: int,
    endpoint_url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Render a smoke request job manifest from individual components.

    Args:
        namespace: Target namespace
        job_name: Name for the smoke test job
        client_image: Container image for making HTTP requests
        endpoint_path: API endpoint path to test
        request_retries: Number of retry attempts
        request_retry_delay_seconds: Delay between retries
        request_timeout_seconds: Timeout for each request
        endpoint_url: Gateway endpoint URL
        payload: Request payload to send

    Returns:
        Job manifest as dict
    """
    command = """
set -eu
attempt=1
while [ "${attempt}" -le "${REQUEST_RETRIES}" ]; do
  if curl -k -sSf --max-time "${REQUEST_TIMEOUT_SECONDS}" \
    "${ENDPOINT_URL}${ENDPOINT_PATH}" \
    -H "Content-Type: application/json" \
    -d "${REQUEST_PAYLOAD}" \
    -o /tmp/smoke-response.json \
    2>/tmp/smoke-error.log; then
    cat /tmp/smoke-response.json
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep "${REQUEST_RETRY_DELAY_SECONDS}"
done
cat /tmp/smoke-error.log >&2 || true
exit 1
"""

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "forge",
                "forge.openshift.io/project": "llm_d",
                "forge.openshift.io/component": "smoke",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": (
                request_retries * (request_timeout_seconds + request_retry_delay_seconds)
            ),
            "template": {
                "metadata": {
                    "labels": {
                        "app.kubernetes.io/managed-by": "forge",
                        "forge.openshift.io/project": "llm_d",
                        "forge.openshift.io/component": "smoke",
                    }
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "smoke",
                            "image": client_image,
                            "command": ["/bin/sh", "-ceu", command],
                            "env": [
                                {"name": "ENDPOINT_URL", "value": endpoint_url},
                                {"name": "ENDPOINT_PATH", "value": endpoint_path},
                                {"name": "REQUEST_PAYLOAD", "value": json.dumps(payload)},
                                {"name": "REQUEST_RETRIES", "value": str(request_retries)},
                                {
                                    "name": "REQUEST_RETRY_DELAY_SECONDS",
                                    "value": str(request_retry_delay_seconds),
                                },
                                {
                                    "name": "REQUEST_TIMEOUT_SECONDS",
                                    "value": str(request_timeout_seconds),
                                },
                            ],
                        }
                    ],
                },
            },
        },
    }
