from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import projects.core.library.config as core_config
import projects.core.library.env as env


@pytest.fixture(autouse=True)
def _reset_project_config():
    core_config.project = None
    yield
    core_config.project = None


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_init_consolidates_config_chunks_into_top_level_sections(tmp_path: Path) -> None:
    orchestration_dir = tmp_path / "orchestration"
    _write_yaml(
        orchestration_dir / "config.yaml",
        {
            "runtime": {
                "keep": "from-base",
                "nested": {"base_value": 1},
            },
            "shared": {"source": "config-file"},
        },
    )
    _write_yaml(
        orchestration_dir / "config.d" / "runtime.yaml",
        {
            "nested": {"chunk_value": 2},
            "override": "from-chunk",
        },
    )
    _write_yaml(
        orchestration_dir / "config.d" / "platform.yaml",
        {"name": "rhoai", "channel": "stable"},
    )

    core_config.init(orchestration_dir)

    assert core_config.project.get_config("runtime.keep", print=False) == "from-base"
    assert core_config.project.get_config("runtime.override", print=False) == "from-chunk"
    assert core_config.project.get_config("runtime.nested.base_value", print=False) == 1
    assert core_config.project.get_config("runtime.nested.chunk_value", print=False) == 2
    assert core_config.project.get_config("platform.name", print=False) == "rhoai"

    consolidated = yaml.safe_load((env.ARTIFACT_DIR / "config.yaml").read_text())
    assert consolidated["runtime"]["nested"] == {"base_value": 1, "chunk_value": 2}
    assert consolidated["platform"] == {"name": "rhoai", "channel": "stable"}


def test_init_supports_projects_defined_only_with_config_d(tmp_path: Path) -> None:
    orchestration_dir = tmp_path / "orchestration"
    _write_yaml(
        orchestration_dir / "config.d" / "runtime.yaml",
        {"default_preset": "smoke"},
    )
    _write_yaml(
        orchestration_dir / "config.d" / "platform.yaml",
        {"namespace": "test-ns"},
    )

    core_config.init(orchestration_dir)

    assert core_config.project.get_config("runtime.default_preset", print=False) == "smoke"
    assert core_config.project.get_config("platform.namespace", print=False) == "test-ns"

    consolidated = yaml.safe_load((env.ARTIFACT_DIR / "config.yaml").read_text())
    assert consolidated["runtime"]["default_preset"] == "smoke"
    assert consolidated["platform"]["namespace"] == "test-ns"
