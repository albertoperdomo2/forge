# Implementation Plan: Artifact Post-Processing Tool

**Branch**: `009-artifact-post-processing` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/009-artifact-post-processing/spec.md`  
**Planning input (CLI & traversal)**: Main engine exposes the commands below; each accepts a **Python module path** for the project plugin and a **base directory** for the artifact/source tree. The parser **walks the directory hierarchy** and uses **`__test_labels__.yaml`** as a **marker file** in each test base directory; that file supplies **test labels** for the current directory. **`visualize`** accepts either an explicit **report list** or a **group id** (defined in config) naming which reports to generate, plus **include/exclude filters** on test labels.

## Summary

Build a **Python CLI engine** (**Caliper**) under `projects/caliper/` that:

1. **Parses** heterogeneous test artifacts into a **unified model** with **distinguishing labels**, **per-project plugins** (loaded by module path), **directory traversal** guided by **`__test_labels__.yaml`**, and a **parse cache** (FR-016).
2. **Visualizes** (parse + plots + HTML reports) with **report selection** (explicit list or config **group id**) and **label filters**.
3. **KPI pipeline**: generate canonical KPIs; **import** historical KPIs from OpenSearch; **export** new KPIs to OpenSearch; **analyze** for regression—aligned with FR-007–FR-010 and spec clarifications.
4. **File artifact export**: upload generated or plugin-listed files to **multiple backends**—**S3-compatible** storage and **MLflow** (FR-017)—with per-backend status reporting.

See [research.md](./research.md) for technology choices and [contracts/](./contracts/) for CLI and data shapes.

## Technical Context

**Language/Version**: Python 3.11+ (matches repository `pyproject.toml`)  
**Primary Dependencies**: `click` (CLI), `PyYAML` (config and `__test_labels__.yaml`), `jsonschema` (validation), OpenSearch client library for KPI import/export (e.g. `opensearch-py`), **S3** access (e.g. `boto3` or compatible), **MLflow** client for artifact logging, plotting/report stack TBD in implementation (e.g. Plotly/Matplotlib + HTML templates—see research.md)  
**Storage**: Local filesystem for artifact trees, **parse cache** files, generated reports; OpenSearch for KPI index; optional **S3** buckets and **MLflow** artifact stores for file export (FR-017)  
**Testing**: `pytest` under `projects/caliper/tests/` or feature-local tests  
**Target Platform**: Linux (CI and developer workstations)  
**Project Type**: CLI library + engine modules (FORGE `projects/` layout)  
**Performance Goals**: Second pass with valid parse cache materially faster than full parse (SC-006); interactive parse+report under ~10 minutes on benchmark fixture (SC-001)  
**Constraints**: Canonical KPI format identical across projects (FR-007); **no full re-parse** when cache valid (FR-016); sensitive data handling per FR-013  
**Scale/Scope**: Large directory trees and multi-facet test results; filters must scale to many labeled directories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|--------|
| **I. CI-First** | **Pass** | All commands are non-interactive and scriptable; suitable for CI with env-provided OpenSearch credentials |
| **II. Reproducible** | **Pass** | Parse cache + versioned plugin module path + labeled directory model; inputs and plugin pin outputs |
| **III. Observable** | **Pass** | Unified model and canonical KPI records are machine-readable; regression and export produce auditable artifacts |
| **IV. Scale-Aware** | **Pass** | Traversal + filters + cache address large trees; detailed perf tuning deferred to implementation |
| **V. AI Platform** | **Pass** | KPIs and agent JSON (FR-011) align with AI workload evaluation |

**Post-design re-check**: No new violations; contracts and data model preserve reproducibility and observability.

## Phase 0 — Research

**Output**: [research.md](./research.md) — decisions on CLI shape, plugin loading, cache invalidation strategy, OpenSearch usage, and visualization stack.

## Phase 1 — Design

**Outputs**:

- [data-model.md](./data-model.md) — entities, relationships, validation rules  
- [contracts/](./contracts/) — CLI command contracts, canonical KPI record, `__test_labels__.yaml`  
- [quickstart.md](./quickstart.md) — operator examples  

**Agent context**: Run `.specify/scripts/bash/update-agent-context.sh claude` from repository root after this plan is saved.

## Project Structure

### Documentation (this feature)

```text
specs/009-artifact-post-processing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── postprocess_manifest.md
│   ├── kpi_record.md
│   └── test_labels.md
└── tasks.md              # Created by /speckit.tasks (not this command)
```

### Source Code (repository root)

```text
projects/caliper/
├── __init__.py
├── cli/
│   └── main.py                 # Click group: parse, visualize, kpi ...
├── engine/
│   ├── plugin_config.py        # Manifest load + merge with --plugin override (FR-002, FR-014)
│   ├── traverse.py             # Directory walk, __test_labels__.yaml discovery
│   ├── parse.py                # Orchestration, cache read/write
│   ├── visualize.py            # Plots + HTML from unified model + plugin
│   ├── kpi/
│   │   ├── generate.py
│   │   ├── import_export.py    # OpenSearch download/upload
│   │   └── analyze.py          # Regression vs historical
│   ├── file_export/            # S3, MLflow, pluggable backends
│   │   ├── s3.py
│   │   └── mlflow_backend.py
│   └── cache.py
├── schemas/                    # JSON Schema copies at runtime
├── dash_app/
└── README.md

projects/caliper/tests/
├── stub_plugin.py
├── fixtures/
└── ...
```

**Structure Decision**: Implement **Caliper** as **`projects/caliper/`** (standalone package under `projects/`). Per-project **plugins** live in their owning projects (e.g. `projects/<name>/post_processing/plugin.py`). **Plugin resolution (FR-002)**: load **`plugin_module`** from the **manifest** (see `plugin_config.py`); the CLI **`--plugin`** **overrides** the manifest when set. **No** implicit repo-wide scanning for plugins.

## Complexity Tracking

No constitution violations requiring justification. (Optional shared KPI schema module may live under `projects/caliper/` to enforce FR-007.)

## Command Matrix (planning input)

| Command | Behavior |
|---------|----------|
| `parse` | Traverse base dir, discover `__test_labels__.yaml`, run plugin parse only, **write parse cache** |
| `visualize` | Parse (or load cache) + generate plots and HTML per plugin **and** selection: **report list** *or* **group id** from config; apply **include/exclude** label filters |
| `kpi generate` | Parse (or cache) + compute canonical KPIs per plugin |
| `kpi import` | Download **historical** KPIs from OpenSearch (for regression baseline) |
| `kpi export` | **Export new** KPIs to OpenSearch |
| `kpi analyze` | Regression analysis **vs** imported/historical baseline |
| `artifacts export` | Upload **file artifacts** (from `visualize` output dir or plugin manifest) to one or more backends: **S3**, **MLflow** (FR-017) |

**Common parameters**: `--base-dir <path>` (required); `--postprocess-config <path>` (optional); `--plugin <python.module.path>` (required if manifest omits `plugin_module`; overrides manifest when both set).
