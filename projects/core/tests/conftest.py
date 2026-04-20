"""Shared pytest fixtures for FORGE."""

import pytest

import projects.core.library.env as env
from projects.core.dsl.script_manager import reset_script_manager


@pytest.fixture(autouse=True)
def _dsl_isolation(tmp_path, monkeypatch):
    """
    Task registration is global; artifact layout depends on FORGE_HOME and cwd.

    Tests that register @task and call execute_tasks() must run with cwd at the
    repository root so task paths match ScriptManager keys (same as execute_tasks).
    """
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    monkeypatch.setenv("ARTIFACT_DIR", str(artifact))
    monkeypatch.chdir(env.FORGE_HOME)
    env.init()
    reset_script_manager()
    yield
    reset_script_manager()
