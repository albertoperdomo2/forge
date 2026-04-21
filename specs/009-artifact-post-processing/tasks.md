---
description: "Actionable tasks for 009-artifact-post-processing (dependency-ordered)"
---

# Tasks: Artifact Post-Processing Tool

**Input**: Design documents from `/var/home/kpouget/openshift/forge/specs/009-artifact-post-processing/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [research.md](./research.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Not requested in the specification; **no dedicated test tasks**. Validation is covered via polish tasks (CLI/help, quickstart alignment).

**Organization**: Phases follow **user story priority** from [spec.md](./spec.md): **US1 (P1)** → **US2 (P2)** → **US5 (P2)** → **US3 (P3)** → **US4 (P4)** → Polish.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelizable (different files, no ordering dependency within the same phase block)
- **[Story]**: `[US1]` … `[US5]` for user-story phases only; omitted in Setup, Foundational, Polish
- Paths are **absolute from repository root** using `projects/caliper/...` unless noted

## Path Conventions (this feature)

- **Engine**: `projects/caliper/`
- **Tests (optional future)**: `projects/caliper/tests/`
- **Feature spec**: `specs/009-artifact-post-processing/spec.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package layout and declare dependencies so imports and CLI entry resolve.

- [x] T001 Create package skeleton: `projects/caliper/__init__.py`, `projects/caliper/cli/__init__.py`, `projects/caliper/engine/__init__.py`, `projects/caliper/engine/kpi/__init__.py`, `projects/caliper/engine/file_export/__init__.py`
- [x] T002 [P] Add optional dependency group `caliper` in `pyproject.toml` listing `opensearch-py`, `boto3`, `mlflow` (versions compatible with Python ≥3.11) alongside existing core deps used by the engine (`click`, `pyyaml`, `jsonschema` already in base)
- [x] T003 [P] Add `projects/caliper/README.md` describing scope, link to `specs/009-artifact-post-processing/spec.md`, and list CLI entry name `caliper`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types, plugin loading, traversal, cache, schema assets, and CLI shell—**required before any user story** can ship end-to-end.

**⚠️ CRITICAL**: No user story phase should merge until this phase completes.

- [x] T004 Define `UnifiedRunModel`, `TestBaseNode`, `UnifiedResultRecord`, and plugin `Protocol`/ABC in `projects/caliper/engine/model.py` per `specs/009-artifact-post-processing/data-model.md`
- [x] T005 Implement `projects/caliper/engine/plugin_config.py` to locate/load the **post-processing manifest** (optional `--postprocess-config`, else conventional filenames under `--base-dir`), read **`plugin_module`**, apply **`--plugin` override** when set (FR-002), and implement `importlib`-based loading plus contract checks in `projects/caliper/engine/load_plugin.py` with clear FR-014 errors when manifest and CLI both omit a resolvable module
- [x] T006 Implement directory walk and `__test_labels__.yaml` discovery in `projects/caliper/engine/traverse.py` per `specs/009-artifact-post-processing/contracts/test_labels.md`
- [x] T007 Implement parse-cache serialization, fingerprinting, validity, and invalidation in `projects/caliper/engine/cache.py` per FR-016 and `specs/009-artifact-post-processing/research.md`
- [x] T008 [P] Add `projects/caliper/schemas/kpi_record.schema.json` aligned with `specs/009-artifact-post-processing/contracts/kpi_record.md`
- [x] T009 Instantiate Click group with global `--base-dir`, optional `--postprocess-config`, and conditional `--plugin` (override) in `projects/caliper/cli/main.py` per `specs/009-artifact-post-processing/contracts/cli.md`
- [x] T010 Register console script `caliper` → `projects.caliper.cli.main:main` in `pyproject.toml` and ensure `pip install -e .[caliper]` exposes the command

**Checkpoint**: `caliper --help` runs; packages import; no user-story features yet.

---

## Phase 3: User Story 1 — Parse and Unify Multiple Test Results (Priority: P1) 🎯 MVP

**Goal**: Traverse `--base-dir`, discover labeled test bases, invoke plugin parse, emit **unified model** and **reloadable parse cache** (FR-001, FR-002, FR-015, FR-016).

**Independent Test**: Two artifact shapes parse into one conceptual model; multiple labeled facets remain distinguishable; cache reload skips full re-parse when valid (see [spec.md](./spec.md) User Story 1).

### Implementation for User Story 1

- [x] T011 [US1] Implement parse orchestration `run_parse` in `projects/caliper/engine/parse.py` (traverse → plugin → unified records → cache write)
- [x] T012 [US1] Wire `parse` subcommand in `projects/caliper/cli/main.py` with `--no-cache` and `--cache-dir` per `specs/009-artifact-post-processing/contracts/cli.md`
- [x] T013 [US1] Add stub plugin `projects/caliper/tests/stub_plugin.py` implementing the plugin protocol for fixture/demo use
- [x] T014 [US1] Add sample fixture tree under `projects/caliper/tests/fixtures/minimal_tree/` including `caliper.yaml` (or chosen conventional manifest) with `plugin_module` pointing at the stub plugin, at least one `__test_labels__.yaml`, and placeholder artifact files referenced by the stub plugin
- [x] T015 [US1] Ensure partial/malformed artifact handling reports understood vs skipped fields without silent loss (FR-001 acceptance) in `projects/caliper/engine/parse.py` and plugin contract

**Checkpoint**: `caliper --plugin … --base-dir … parse` produces cache + unified JSON or structured output sufficient for downstream stories.

---

## Phase 4: User Story 2 — Generate Plots and HTML Reports (Priority: P2)

**Goal**: From unified model or cache, generate **plots** and **HTML reports** with plugin definitions; support report list **or** group id + label filters (FR-003, FR-004).

**Independent Test**: Fixed fixture yields HTML with run id, metrics, ≥1 chart when data supports it; comparison report uses consistent scales/labels ([spec.md](./spec.md) User Story 2).

### Implementation for User Story 2

- [x] T016 [US2] Implement label include/exclude filtering helpers in `projects/caliper/engine/label_filters.py` per data-model validation rules
- [x] T017 [US2] Implement `run_visualize` in `projects/caliper/engine/visualize.py` (load unified model from cache or parse, apply filters, delegate plot/report rendering to plugin hooks)
- [x] T018 [US2] Wire `visualize` command in `projects/caliper/cli/main.py` with `--reports`, `--report-group`, `--visualize-config`, `--include-label`, `--exclude-label`, `--output-dir` per `specs/009-artifact-post-processing/contracts/cli.md`
- [x] T019 [US2] Implement visualize group-config resolution (explicit `--visualize-config` or search under `--base-dir`) in `projects/caliper/engine/visualize.py` matching `specs/009-artifact-post-processing/research.md` §7

**Checkpoint**: `visualize` writes report bundle under `--output-dir` for stub plugin + fixtures.

---

## Phase 5: User Story 5 — Export File Artifacts to S3 and MLflow (Priority: P2)

**Goal**: Upload generated/plugin-listed **files** to **S3-compatible** storage and **MLflow** with **per-backend** status (FR-017, FR-013, SC-007).

**Independent Test**: With valid endpoints/credentials, files land under expected S3 prefix and MLflow run; partial backend failure surfaces clearly ([spec.md](./spec.md) User Story 5).

### Implementation for User Story 5

- [x] T020 [US5] Define `FileExportManifest` and `FileExportBackendResult` dataclasses in `projects/caliper/engine/file_export/types.py` per `specs/009-artifact-post-processing/data-model.md`
- [x] T021 [P] [US5] Implement S3 upload backend in `projects/caliper/engine/file_export/s3.py` using `boto3` and standard credential chain
- [x] T022 [P] [US5] Implement MLflow artifact logging backend in `projects/caliper/engine/file_export/mlflow_backend.py` using `mlflow` client APIs
- [x] T023 [US5] Implement `run_file_export` coordinator with independent backend execution and aggregated exit policy in `projects/caliper/engine/file_export/runner.py`
- [x] T024 [US5] Add `artifacts export` command group in `projects/caliper/cli/main.py` (`--from`, repeatable `--backend`, S3/MLflow flags, `--dry-run`) per `specs/009-artifact-post-processing/contracts/cli.md`
- [x] T025 [US5] Integrate sensitive-content policy hooks (FR-013) before upload in `projects/caliper/engine/file_export/runner.py` (call shared redaction/exclusion utilities)

**Checkpoint**: Multi-backend export prints structured per-backend results; matches SC-007 operator observability.

---

## Phase 6: User Story 3 — KPIs, OpenSearch, Regression, Dashboard (Priority: P3)

**Goal**: Canonical KPI generation, OpenSearch import/export, regression analysis, and a **minimal** dashboard or data bridge consistent with exported KPIs (FR-005–FR-010, FR-012).

**Independent Test**: Small KPI catalog, two builds, export → index → regression flags deliberate change; dashboard/trend view reads same canonical records ([spec.md](./spec.md) User Story 3).

### Implementation for User Story 3

- [x] T026 [P] [US3] Implement KPI catalog resolution from plugin in `projects/caliper/engine/kpi/catalog.py`
- [x] T027 [US3] Implement `run_kpi_generate` emitting canonical JSONL in `projects/caliper/engine/kpi/generate.py` with `jsonschema` validation using `projects/caliper/schemas/kpi_record.schema.json`
- [x] T028 [US3] Implement OpenSearch bulk/index helpers and env-based client configuration in `projects/caliper/engine/kpi/opensearch_client.py` and `projects/caliper/engine/kpi/import_export.py` (FR-008, FR-012)
- [x] T029 [US3] Implement regression comparison and findings model in `projects/caliper/engine/kpi/analyze.py` with configurable rules in `projects/caliper/engine/kpi/rules.py` (FR-009)
- [x] T030 [US3] Wire `kpi` Click subgroup (`generate`, `import`, `export`, `analyze`) in `projects/caliper/cli/main.py` per `specs/009-artifact-post-processing/contracts/cli.md`
- [x] T031 [US3] Add minimal KPI trend/read-only view as `projects/caliper/dash_app/kpi_view.py` (Dash or data provider only) fed by exported KPI JSON or OpenSearch query—enough to satisfy FR-010 “dashboard experience” baseline without full product UI

**Checkpoint**: End-to-end KPI pipeline operable from CLI; dashboard module demonstrates parity with exported records for a fixture.

---

## Phase 7: User Story 4 — AI Agent Evaluation JSON (Priority: P4)

**Goal**: Emit schema-documented **AI evaluation payload** JSON (FR-011, FR-012, SC-004).

**Independent Test**: Fixture with agent metrics produces JSON passing schema validation; optional fields explicit when missing ([spec.md](./spec.md) User Story 4).

### Implementation for User Story 4

- [x] T032 [P] [US4] Add `projects/caliper/schemas/ai_eval_payload.schema.json` documenting required/optional fields per FR-011
- [x] T033 [US4] Implement `projects/caliper/engine/ai_eval.py` to build/validate payload from unified model + plugin content
- [x] T034 [US4] Add `ai-eval export` subcommand (or equivalent nested command) in `projects/caliper/cli/main.py` writing validated JSON to `--output`

**Checkpoint**: AI eval JSON validates against `ai_eval_payload.schema.json` for stub fixture.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation centralization, exit codes, docs, and quickstart alignment.

- [x] T035 [P] Centralize `jsonschema` validation helpers and user-facing error formatting in `projects/caliper/engine/validation.py` (FR-012)
- [x] T036 Align process exit codes in `projects/caliper/cli/main.py` with `specs/009-artifact-post-processing/contracts/cli.md` (including distinct file-export vs KPI/OpenSearch failures)
- [x] T037 [P] Update `projects/caliper/README.md` with command matrix from `specs/009-artifact-post-processing/plan.md` and operator examples from `specs/009-artifact-post-processing/quickstart.md`
- [x] T038 Walk through `specs/009-artifact-post-processing/quickstart.md` commands and adjust `projects/caliper/cli/main.py` flags/subcommands until examples are accurate (or document temporary gaps inline in README)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 **and** benefits from Phase 3 parse/cache (can mock unified model only after T004–T007 exist).
- **Phase 5 (US5)**: Depends on Phase 2; **practically** after Phase 4 output paths exist but can run against any `--from` directory per contracts.
- **Phase 6 (US3)**: Depends on Phase 2 and Phase 3 (unified model / KPI inputs).
- **Phase 7 (US4)**: Depends on Phase 2 and Phase 3.
- **Phase 8 (Polish)**: Depends on CLI surface from Phases 3–7 as applicable.

### User Story Completion Order (by priority)

1. **US1 (P1)** — MVP: parse + cache + labels  
2. **US2 (P2)** — visualize  
3. **US5 (P2)** — artifacts export (often after US2 in real workflows)  
4. **US3 (P3)** — KPI + OpenSearch + regression + dashboard baseline  
5. **US4 (P4)** — AI eval JSON  

### Within Each User Story

- Foundational models/cache before orchestration (`parse.py`, `visualize.py`, etc.).
- Engine modules before CLI wiring for that story’s commands.
- US5 backends (`s3.py`, `mlflow_backend.py`) can be developed in parallel after `types.py` + export runner interface exist.

---

## Parallel Execution Examples

### Foundational (after T004 defines types)

- **Parallel**: T008 (`schemas/kpi_record.schema.json`) alongside T006 (`traverse.py`) — different files; ensure T004 precedes both if schemas reference model field names.

### User Story 5

- **Parallel**: T021 `projects/caliper/engine/file_export/s3.py` and T022 `projects/caliper/engine/file_export/mlflow_backend.py` after T020 `types.py`.

### User Story 3

- **Parallel**: T026 `catalog.py` and T028 `opensearch_client.py` once KPI schema (T008) exists.

### Polish

- **Parallel**: T035 `validation.py` and T037 `README.md`.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1–2 (Setup + Foundational).  
2. Complete Phase 3 (US1).  
3. **Stop and validate** using stub plugin + `fixtures/minimal_tree/` and cache reload behavior.  

### Incremental Delivery

1. US1 → US2 (reports) → US5 (publish files) → US3 (KPI stack) → US4 (AI JSON) → Polish.  
2. Each phase should leave the CLI in a **demoable** state for its story’s **Independent Test** criteria.

### Parallel Team Strategy

- After Phase 2: Developer A: US1+US2 path; Developer B: US5 backends + runner; Developer C: US3 KPI/OpenSearch (requires unified model from US1 for realistic integration). Coordinate merges at Phase 2 completion and after US1 cache format stabilizes.

---

## Notes

- **[P]** tasks touch **different files**; still respect import dependencies.  
- Story labels **[US1]**–**[US5]** map to [spec.md](./spec.md) user stories (US5 = File artifact export).  
- Revisit `tasks.md` after any spec change to FR inventory (FR-001–FR-017).
