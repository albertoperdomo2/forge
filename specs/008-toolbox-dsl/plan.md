# Implementation Plan: FORGE Toolbox Command DSL

**Branch**: `008-toolbox-dsl` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification plus planning note: *The DSL should rely on the Python language, but use functions to define tasks. Python annotations should be used to define the task properties.*

**Note**: Filled by `/speckit.plan`. Workflow: `.specify/templates/plan-template.md`.

## Summary

Deliver and harden a **Python-native** toolbox DSL: each **task** is an ordinary **function** participating in a sequential pipeline; **task properties** (scheduling, retries, always-run, conditional skip) are attached to those functions using **Python-level metadata** in the form of **decorators** (the project’s chosen attachable-annotation pattern), with a single **public entrypoint** per command and **CLI parity** from that entrypoint’s signature. **Documentation** and **automated tests** keep semantics CI-stable and observable per the FORGE constitution.

## Technical Context

**Language/Version**: Python 3.11+ (matches `pyproject.toml` / FORGE runtime)  
**Primary Dependencies**: Standard library (`inspect`, `functools`, `types`, `logging`, `pathlib`); PyYAML for run metadata; existing `projects.core.library.env`, `projects.core.dsl.*` modules  
**Storage**: Per-run artifact directories (files under `ARTIFACT_DIR`: logs, `_meta/metadata.yaml`, `restart.sh`); no new database  
**Testing**: `pytest` with `testpaths = projects/core/tests`  
**Target Platform**: Linux (toolbox / CI runners invoking FORGE)  
**Project Type**: Library-style DSL inside monorepo (`projects/core/dsl/`) consumed by `projects/*/toolbox/` commands  
**Performance Goals**: Task dispatch overhead negligible vs cluster I/O; retry sleeps author-configurable  
**Constraints**: Tasks remain **pure two-parameter callables** `(readonly_args, context)` for the runtime wrapper; decorator **order** must match documented rules; cooperative cancel (`KeyboardInterrupt` / signal wrapper) must not be retried  
**Scale/Scope**: One command file = one registry bucket; global script manager state isolated in tests via `reset_script_manager`

### Authoring model (from planning input)

| Concept | Approach |
|--------|----------|
| Host language | **Python** — no alternate grammar or embedded DSL parser |
| Task shape | **Functions** — each step is a `def` with the shared task signature |
| Task properties | **Metadata on functions** — implemented today as **decorators** (`@task`, `@when(...)`, `@retry(...)`, `@always`) that set attributes / registry entries; see `research.md` for why decorators satisfy “annotations” and how `typing.Annotated` could evolve later |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|--------|
| **I. CI-First** | Pass | FR-009: DSL semantics covered by `projects/core/tests`; run in CI with rest of harness |
| **II. Reproducible** | Pass | `execute_tasks` writes metadata + restart helper under deterministic artifact layout |
| **III. Observable** | Pass | FR-007: banners, per-task headers, skip/retry logging, `task.log` |
| **IV. Scale-Aware** | N/A | DSL orchestration layer; does not change cluster scale test design |
| **V. AI Platform Specificity** | N/A | Toolbox DSL is workload-agnostic |

**Post–Phase 1 re-check**: Contracts and quickstart reinforce CI + observability; no new gates.

## Project Structure

### Documentation (this feature)

```text
specs/008-toolbox-dsl/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   └── toolbox_dsl_authoring.md
├── spec.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
projects/core/dsl/
├── __init__.py          # Public exports (task, when, retry, always, execute_tasks, …)
├── task.py              # Decorators / retry engine / task_only validation
├── runtime.py           # execute_tasks, TaskExecutionError, always vs skip sweep
├── script_manager.py    # Per-file task registry, TaskResult
├── context.py           # ReadOnlyArgs, TaskContext
├── toolbox.py           # CLI factory from entrypoint signature
├── log.py               # Banners / task headers
└── …                    # shell, template, cli helpers

projects/core/tests/
├── conftest.py          # FORGE_HOME, ARTIFACT_DIR, script manager reset
└── test_dsl_toolbox.py  # Decorator + execute_tasks semantics

docs/toolbox/
└── dsl.md               # Author-facing documentation
```

**Structure Decision**: All implementation lives under `projects/core/dsl/` with tests in `projects/core/tests/` and author docs under `docs/toolbox/`, matching existing FORGE layout.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 — Research

See [research.md](./research.md) (decorators vs type annotations, decorator ordering, failure sweep semantics).

## Phase 1 — Design outputs

- [data-model.md](./data-model.md) — registry entities, task lifecycle, context merge rules  
- [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md) — authoring contract for command files  
- [quickstart.md](./quickstart.md) — minimal command + task example  

## Phase 2

`tasks.md` is produced by `/speckit.tasks` (not this command).
