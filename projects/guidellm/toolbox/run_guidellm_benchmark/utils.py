"""
Utilities for the GuideLL-M benchmark toolbox module.
"""

from __future__ import annotations

import ast
import re
import shlex
from dataclasses import dataclass
from typing import Any

import yaml

from projects.core.dsl import template


@dataclass(frozen=True)
class GuideLLMRun:
    rate: str | None
    label: str
    args: list[str]


def _sanitize_rate_label(rate: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", rate).strip("._-")
    return sanitized or "rate"


def _format_expression_value(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _evaluate_rate_expression(expression: str, rate: str) -> str:
    rate_value = float(rate)
    parsed = ast.parse(expression, mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "rate":
            return rate_value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub):
            operand = _eval(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            raise ValueError(f"Unsupported rate expression operator: {ast.dump(node.op)}")

        raise ValueError(f"Unsupported rate expression: {expression}")

    return _format_expression_value(_eval(parsed))


def _substitute_rate_expressions(value: str, rate: str) -> str:
    return re.sub(
        r"\{([^{}]+)\}",
        lambda match: _evaluate_rate_expression(match.group(1), rate),
        value,
    )


def _has_rate_expressions(guidellm_args: list[str]) -> bool:
    return any(re.search(r"\{[^{}]*\*rate[^{}]*\}", arg) for arg in guidellm_args)


def expand_guidellm_runs(guidellm_args: list[str]) -> list[GuideLLMRun]:
    rates_arg = next((arg for arg in guidellm_args if arg.startswith("--rates=")), None)
    if not rates_arg:
        return [GuideLLMRun(rate=None, label="default", args=list(guidellm_args))]
    if not _has_rate_expressions(guidellm_args):
        return [GuideLLMRun(rate=None, label="default", args=list(guidellm_args))]

    rate_values = [
        value.strip() for value in rates_arg.split("=", 1)[1].split(",") if value.strip()
    ]
    runs: list[GuideLLMRun] = []
    for rate in rate_values:
        run_args: list[str] = []
        for arg in guidellm_args:
            if arg.startswith("--rates="):
                run_args.append(f"--rate={rate}")
                continue
            run_args.append(_substitute_rate_expressions(arg, rate))

        runs.append(
            GuideLLMRun(
                rate=rate,
                label=f"rate-{_sanitize_rate_label(rate)}",
                args=run_args,
            )
        )

    return runs


def _build_multi_run_script(*, endpoint_url: str, runs: list[GuideLLMRun]) -> str:
    lines = ["set -euo pipefail", "mkdir -p /results"]
    for run in runs:
        lines.append("rm -f /results/benchmarks.json")
        command = [
            "/opt/app-root/bin/guidellm",
            "benchmark",
            "run",
            f"--target={endpoint_url}",
            *run.args,
        ]
        lines.append(shlex.join(command))
        lines.append(
            "test -f /results/benchmarks.json && "
            f"mv /results/benchmarks.json /results/benchmarks-{run.label}.json"
        )

    return "\n".join(lines)


def render_guidellm_pvc_from_parts(*, namespace: str, name: str, pvc_size: str) -> dict[str, Any]:
    """Render a GuideLL-M PVC manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job and PVC
        pvc_size: Size of the PVC

    Returns:
        PVC manifest as dict
    """
    rendered_yaml = template.render_template(
        "guidellm_pvc.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "pvc_size": pvc_size,
        },
    )
    return yaml.safe_load(rendered_yaml)


def render_guidellm_job_from_parts(
    *,
    namespace: str,
    name: str,
    image: str,
    endpoint_url: str,
    guidellm_args: list[str],
) -> dict[str, Any]:
    """Render a GuideLL-M job manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job
        image: Container image for GuideLLM
        endpoint_url: Gateway endpoint URL
        guidellm_args: Additional arguments for GuideLLM

    Returns:
        Job manifest as dict
    """
    runs = expand_guidellm_runs(guidellm_args)
    rendered_yaml = template.render_template(
        "guidellm_job.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "image": image,
            "endpoint_url": endpoint_url,
            "guidellm_args": [],
        },
    )
    manifest = yaml.safe_load(rendered_yaml)
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    if len(runs) == 1 and runs[0].rate is None:
        container["command"] = ["/opt/app-root/bin/guidellm"]
        container["args"] = [
            "benchmark",
            "run",
            f"--target={endpoint_url}",
            *runs[0].args,
        ]
        return manifest

    container["command"] = ["/bin/sh", "-lc"]
    container["args"] = [_build_multi_run_script(endpoint_url=endpoint_url, runs=runs)]
    return manifest


def render_guidellm_copy_pod_from_parts(
    *,
    namespace: str,
    name: str,
    pvc_size: str,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Render a GuideLL-M copy pod manifest from individual components.

    Args:
        namespace: Target namespace
        name: Name of the benchmark job (used for copy pod naming)
        pvc_size: Size of the PVC (not used directly, but kept for interface consistency)
        node_name: Optional node name to pin the pod to

    Returns:
        Pod manifest as dict
    """
    rendered_yaml = template.render_template(
        "guidellm_copy_pod.yaml.j2",
        {
            "namespace": namespace,
            "name": name,
            "node_name": node_name,
        },
    )
    return yaml.safe_load(rendered_yaml)
