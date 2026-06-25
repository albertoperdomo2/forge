from __future__ import annotations

from projects.llm_d.orchestration import pr_args


def test_parse_project_directives_does_not_override_framework_test_preset_handling() -> None:
    overrides, directives = pr_args.parse_project_directives("/test fournos llm_d smoke")

    assert overrides == {}
    assert directives == []


def test_parse_project_directives_ignores_test_without_preset() -> None:
    overrides, directives = pr_args.parse_project_directives("/test fournos llm_d")

    assert overrides == {}
    assert directives == []


def test_parse_project_directives_ignores_other_projects() -> None:
    overrides, directives = pr_args.parse_project_directives("/test fournos skeleton smoke")

    assert overrides == {}
    assert directives == []
