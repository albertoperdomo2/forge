"""
Config-driven Caliper artifact export for FORGE orchestration projects (e.g. skeleton).

Validates :class:`~projects.caliper.orchestration.export_config.CaliperOrchestrationExportConfig`
and calls
:func:`projects.caliper.engine.file_export.artifacts_export_run.run_artifacts_export`.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from projects.caliper.engine.file_export.artifacts_export_run import run_artifacts_export
from projects.caliper.engine.file_export.mlflow_config import load_mlflow_config_yaml
from projects.caliper.orchestration.export_config import (
    CaliperOrchestrationExportConfig,
)
from projects.core.library import env
from projects.core.library import vault as vault_lib

logger = logging.getLogger(__name__)


def run_from_orchestration_config(
    caliper_cfg: dict[str, Any] | None,
) -> int:
    """
    Run Caliper file export from orchestration config.

    Pass:

    * ``caliper.export`` from :func:`get_config` (inner mapping only), or
    * The full ``caliper`` object with an ``export`` key.

    Backends are selected only via flags such as ``backend.mlflow.enabled`` (not a
    free-form backend name list).

    If ``backend.mlflow.secrets`` uses the ``vault: { name, key }`` form, the process must
    have called :func:`projects.core.library.vault.init` with that vault name (as in the
    top-level ``vaults:`` list in project config) so :func:`vault.get_vault_content_path`
    can return the secrets file path.
    """

    try:
        export_cfg = CaliperOrchestrationExportConfig.model_validate(caliper_cfg["export"])
    except (ValidationError, ValueError) as e:
        logger.error("Invalid caliper export config: %s", e)
        raise

    raw_from = export_cfg.from_path
    if raw_from is None or (isinstance(raw_from, str) and not raw_from.strip()):
        raise ValueError("caliper.export.from is not set")
    from_path = Path(raw_from)
    if not from_path.exists():
        raise FileNotFoundError(f"caliper.export.from does not exist: {from_path}")

    backends = export_cfg.backend_list
    mlflow_backend_cfg = export_cfg.backend.mlflow

    status_yaml = env.ARTIFACT_DIR / "status.yaml"

    if "mlflow" not in backends:
        raise ValueError(
            f"only 'mlflow' backend export is supported at the moment (got '{' '.join(backends)}')."
        )

    vault_name = export_cfg.backend.mlflow.secrets.vault.name
    vault_mlflow_secret = export_cfg.backend.mlflow.secrets.vault.mlflow_secret
    mlflow_secrets_path = vault_lib.get_vault_content_path(vault_name, vault_mlflow_secret)

    if mlflow_secrets_path is None:
        raise ValueError(f"Vault {vault_name}/{vault_mlflow_secret} missing :/")
    elif not mlflow_secrets_path.exists():
        raise FileNotFoundError(f"Vault {vault_name}/{vault_mlflow_secret} file missing :/")

    # Only ``backend.mlflow.config`` (inline mapping or file path) is MLflow settings
    # (``experiment``, ``run_name``, etc.). The whole ``CaliperExportBackendMlflow`` object
    # must not be passed as ``mlflow_config_data`` or the experiment stays nested and is ignored.
    raw_cfg = mlflow_backend_cfg.config
    mlflow_config_data: dict[str, Any] | None = None
    if raw_cfg is None:
        pass
    elif isinstance(raw_cfg, dict):
        mlflow_config_data = copy.deepcopy(raw_cfg)
    else:
        mlflow_config_data = load_mlflow_config_yaml(Path(raw_cfg).expanduser().resolve())

    mlflow_kwargs: dict[str, Any] = {
        "mlflow_experiment": export_cfg.mlflow_experiment,
        "mlflow_run_id": export_cfg.mlflow_run_id,
        "mlflow_run_name": export_cfg.mlflow_run_name,
        "mlflow_secrets_path": mlflow_secrets_path,
    }
    if mlflow_config_data is not None:
        mlflow_kwargs["mlflow_config_data"] = mlflow_config_data

    ret = run_artifacts_export(
        from_path=from_path,
        status_yaml_path=status_yaml,
        dry_run=export_cfg.dry_run,
        verbose=export_cfg.verbose,
        upload_workers=export_cfg.upload_workers,
        backend=backends,
        **mlflow_kwargs,
    )

    if ret != 0:
        raise RuntimeError(f"Caliper export failed (ret code = {ret})")

    with open(status_yaml) as f:
        return yaml.safe_load(f.read())
