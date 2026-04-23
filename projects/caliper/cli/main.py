"""Caliper CLI — file artifact export only (trimmed)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

import click
import yaml

from projects.caliper.engine.file_export.artifacts_export_run import run_artifacts_export
from projects.caliper.engine.file_export.mlflow_config import load_mlflow_config_yaml


def _exit_with_help(ctx: click.Context, message: str, code: int = 1) -> NoReturn:
    click.echo(f"Error: {message}\n", err=True)
    click.echo(ctx.get_help(), err=True)
    ctx.exit(code)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Caliper — file artifact export."""


@main.group("artifacts")
def artifacts_group() -> None:
    """File artifact export."""


@artifacts_group.command("export")
@click.option(
    "--from",
    "from_path",
    type=click.Path(path_type=Path, exists=True),
    required=True,
    help="File or directory to upload (artifact path).",
)
@click.option("--backend", multiple=True, type=str, help="Repeat: s3, and/or mlflow.")
@click.option("--s3-bucket", default=None, envvar="CALIPER_S3_BUCKET")
@click.option("--s3-prefix", default="", envvar="CALIPER_S3_PREFIX")
@click.option(
    "--mlflow-tracking-uri",
    "--mlflow-endpoint",
    "mlflow_tracking_uri",
    default=None,
    envvar="MLFLOW_TRACKING_URI",
    help="MLflow tracking server URI (for mlflow backend).",
)
@click.option("--mlflow-experiment", default=None, envvar="MLFLOW_EXPERIMENT_NAME")
@click.option("--mlflow-run-id", default=None, envvar="MLFLOW_RUN_ID")
@click.option(
    "--mlflow-run-name",
    default=None,
    envvar="CALIPER_MLFLOW_RUN_NAME",
    help="Display name for a new MLflow run.",
)
@click.option(
    "--mlflow-insecure-tls",
    is_flag=True,
    help="Do not verify TLS for the MLflow tracking server.",
)
@click.option(
    "--mlflow-secrets",
    "mlflow_secrets_path",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="YAML with credentials: tracking_uri, token or username/password, TLS options.",
)
@click.option(
    "--mlflow-config",
    "mlflow_config_path",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="YAML with non-secret MLflow settings (experiment, run_name, run_id, ...).",
)
@click.option("--dry-run", is_flag=True)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Print detailed progress on stderr (no secrets).",
)
@click.option(
    "--status-yaml",
    "status_yaml_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Write a YAML summary of export outcomes per backend.",
)
@click.option(
    "--upload-workers",
    type=click.IntRange(min=1, max=64),
    default=10,
    show_default=True,
    help="Parallel upload threads (S3 / MLflow).",
)
@click.pass_context
def artifacts_export(
    ctx: click.Context,
    from_path: Path,
    backend: tuple[str, ...],
    s3_bucket: str | None,
    s3_prefix: str,
    mlflow_tracking_uri: str | None,
    mlflow_experiment: str | None,
    mlflow_run_id: str | None,
    mlflow_run_name: str | None,
    mlflow_insecure_tls: bool,
    mlflow_secrets_path: Path | None,
    mlflow_config_path: Path | None,
    dry_run: bool,
    verbose: bool,
    status_yaml_path: Path | None,
    upload_workers: int,
) -> None:
    """Upload file artifacts to S3 and/or MLflow."""
    backends = [b.strip().lower() for b in backend if b.strip()]
    if not backends:
        _exit_with_help(
            ctx,
            "Specify at least one --backend: s3 and/or mlflow "
            "(e.g. --from ./out --backend mlflow --mlflow-endpoint http://...).",
            code=1,
        )
    mlflow_config_data: dict | None = None
    if mlflow_config_path is not None:
        try:
            mlflow_config_data = load_mlflow_config_yaml(mlflow_config_path)
        except (OSError, ValueError, TypeError, yaml.YAMLError) as e:
            click.echo(f"Invalid MLflow settings file ({mlflow_config_path}): {e}", err=True)
            sys.exit(1)

    code = run_artifacts_export(
        from_path=from_path,
        backend=backends,
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_experiment=mlflow_experiment,
        mlflow_run_id=mlflow_run_id,
        mlflow_run_name=mlflow_run_name,
        mlflow_insecure_tls=mlflow_insecure_tls,
        mlflow_secrets_path=mlflow_secrets_path,
        mlflow_config_data=mlflow_config_data,
        dry_run=dry_run,
        verbose=verbose,
        status_yaml_path=status_yaml_path,
        upload_workers=upload_workers,
        click_context=ctx,
    )
    if code != 0:
        sys.exit(code)


def run_cli() -> None:
    try:
        rv = main.main(standalone_mode=False, prog_name="caliper")
        if isinstance(rv, int) and rv != 0:
            sys.exit(rv)
    except click.MissingParameter as exc:
        msg = exc.format_message()
        sub = getattr(exc, "ctx", None)
        click.echo(f"Error: {msg}\n", err=True)
        if sub is not None:
            click.echo(sub.get_help(), err=True)
        ec = getattr(exc, "exit_code", 2)
        sys.exit(2 if ec is None else int(ec))
    except SystemExit:
        raise


if __name__ == "__main__":
    run_cli()
