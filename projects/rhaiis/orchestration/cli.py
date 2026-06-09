#!/usr/bin/env python3
"""RHAIIS CLI - Interactive CLI for KServe InferenceService benchmarking.

Examples:
    # Quick test with defaults (qwen3-0.6b, balanced workload)
    python -m projects.rhaiis.orchestration.cli test \
        --namespace kserve-e2e-perf

    # Specific model and workload
    python -m projects.rhaiis.orchestration.cli test \
        --model llama-3-1-8b-fp8 \
        --workload short \
        --namespace kserve-e2e-perf \
        --image-pull-secret npalaska-image-pull

    # Dry run
    python -m projects.rhaiis.orchestration.cli test \
        --model qwen3-0_6b --dry-run

    # Cleanup only
    python -m projects.rhaiis.orchestration.cli cleanup \
        --deployment-name rhaiis-bench \
        --namespace kserve-e2e-perf
"""

import logging
import types

import click

from projects.core.library import config
from projects.rhaiis.orchestration import runtime_config

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    """RHAIIS CLI - KServe InferenceService benchmarking."""
    ctx.ensure_object(types.SimpleNamespace)
    runtime_config.init()


@cli.command()
@click.option(
    "--preset", "-p", multiple=True, help="Preset name(s) from presets.d/ (e.g. llama-8b profile1)"
)
@click.option("--model", "-m", default=None, help="Model key from config.yaml")
@click.option("--workload", "-w", default=None, help="Workload profile name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace")
@click.option("--deployment-name", default=None, help="Deployment name (defaults to model name)")
@click.option("--accelerator", type=click.Choice(["nvidia", "amd"]), default=None)
@click.option("--vllm-image", help="vLLM container image override")
@click.option("--tensor-parallel", "-tp", type=int, help="Tensor parallel size override")
@click.option("--replicas", "-r", type=int, default=None)
@click.option("--storage-source", type=click.Choice(["hf", "pvc"]), default=None)
@click.option("--storage-pvc", help="PVC name for model storage")
@click.option("--image-pull-secret", help="Image pull secret name")
@click.option("--service-account-name", help="Service account name for predictor")
@click.option("--max-seconds", type=int, help="Max benchmark duration per rate")
@click.option("--rates", help="Comma-separated rates (e.g. 1,50,100)")
@click.option("--dry-run", is_flag=True, help="Print what would be done")
@click.pass_context
def test(
    ctx,
    preset: tuple[str, ...],
    model: str | None,
    workload: str | None,
    namespace: str | None,
    deployment_name: str | None,
    accelerator: str | None,
    vllm_image: str | None,
    tensor_parallel: int | None,
    replicas: int | None,
    storage_source: str | None,
    storage_pvc: str | None,
    image_pull_secret: str | None,
    service_account_name: str | None,
    max_seconds: int | None,
    rates: str | None,
    dry_run: bool,
):
    """Run KServe InferenceService benchmark."""
    for name in preset:
        config.project.apply_preset(name)

    model_key = model or runtime_config.get_test_model_key()
    workload_key = workload or runtime_config.get_test_workload_key()

    model_cfg = runtime_config.get_model(model_key)
    workload_cfg = runtime_config.get_workload(workload_key)
    deploy_cfg = runtime_config.get_deploy_config()
    benchmark_cfg = runtime_config.get_benchmark_config()

    if not deployment_name:
        deployment_name = runtime_config.derive_deployment_name(model_cfg["hf_model_id"])

    accelerator = accelerator or runtime_config.get_accelerator()
    namespace = namespace or runtime_config.get_namespace()
    vllm_image = vllm_image or runtime_config.get_vllm_image(accelerator)

    # Apply CLI overrides to deploy_cfg
    if replicas is not None:
        deploy_cfg["replicas"] = replicas
    if storage_source:
        deploy_cfg["storage_source"] = storage_source
    if storage_pvc:
        deploy_cfg["storage_pvc"] = storage_pvc
    if image_pull_secret:
        deploy_cfg["image_pull_secret"] = image_pull_secret
    if service_account_name:
        deploy_cfg["service_account_name"] = service_account_name

    vllm_defaults = runtime_config.get_vllm_defaults()
    vllm_args = runtime_config.merge_vllm_args(vllm_defaults, model_cfg, workload_cfg)
    env_vars = runtime_config.merge_env_vars(accelerator, model_cfg)

    if tensor_parallel is not None:
        vllm_args["tensor-parallel-size"] = tensor_parallel

    rate_list = [int(r) for r in rates.split(",")] if rates else workload_cfg.get("rates", [1])
    max_seconds_val = max_seconds or workload_cfg.get("max_seconds", 180)

    if dry_run:
        click.echo("[DRY-RUN] RHAIIS Benchmark Test")
        click.echo(f"  Model: {model_key} ({model_cfg['hf_model_id']})")
        click.echo(f"  Workload: {workload_key}")
        click.echo(f"  Namespace: {namespace}")
        click.echo(f"  Deployment: {deployment_name}")
        click.echo(f"  Accelerator: {accelerator}")
        click.echo(f"  Image: {vllm_image}")
        click.echo(f"  vLLM args: {vllm_args}")
        click.echo(f"  Env vars: {env_vars}")
        click.echo(f"  Replicas: {deploy_cfg.get('replicas', 1)}")
        click.echo(
            f"  Storage: {deploy_cfg.get('storage_source', 'hf')} (pvc={deploy_cfg.get('storage_pvc', '')})"
        )
        click.echo(f"  Image pull secret: {deploy_cfg.get('image_pull_secret') or '(none)'}")
        click.echo(f"  Service account: {deploy_cfg.get('service_account_name') or '(none)'}")
        click.echo(f"  Rates: {rate_list}")
        click.echo(f"  Max seconds: {max_seconds_val}")
        return

    from projects.rhaiis.orchestration import test_phase

    try:
        test_phase.run(
            deployment_name=deployment_name,
            namespace=namespace,
            model_cfg=model_cfg,
            vllm_image=vllm_image,
            accelerator=accelerator,
            vllm_args=vllm_args,
            env_vars=env_vars,
            deploy_cfg=deploy_cfg,
            benchmark_cfg=benchmark_cfg,
            workload_data=workload_cfg["data"],
            rates=rate_list,
            max_seconds=max_seconds_val,
        )
    except Exception as exc:
        click.echo(f"Run failed: {exc}")
        raise SystemExit(1) from exc

    click.echo("Benchmark completed successfully.")


@cli.command()
@click.option("--deployment-name", required=True, help="InferenceService name")
@click.option("--namespace", "-n", default="forge-rhaiis", help="Kubernetes namespace")
@click.pass_context
def cleanup(ctx, deployment_name: str, namespace: str):
    """Cleanup InferenceService deployment."""
    from projects.rhaiis.toolbox.capture_isvc_state.main import run as capture_isvc_state
    from projects.rhaiis.toolbox.cleanup_isvc.main import run as cleanup_isvc

    click.echo(f"Capturing state for {deployment_name}...")
    try:
        capture_isvc_state(name=deployment_name, namespace=namespace)
    except Exception as exc:
        click.echo(f"Warning: capture failed: {exc}")

    click.echo(f"Cleaning up {deployment_name}...")
    cleanup_isvc(name=deployment_name, namespace=namespace)

    click.echo("Cleanup completed.")


if __name__ == "__main__":
    cli()
