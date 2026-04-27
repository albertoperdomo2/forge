# Research: Artifact Post-Processing Engine

**Feature**: 009-artifact-post-processing  
**Date**: 2026-04-24

## 1. CLI framework

**Decision**: Use **Click** for nested command groups (`caliper kpi export`, etc.).

**Rationale**: Already a dependency in FORGE `pyproject.toml`; matches `projects/core/dsl` and other CLIs.

**Alternatives considered**: Typer (adds dependency), argparse (verbose for nested subcommands).

---

## 2. Plugin loading by module path

**Decision**: Resolve plugin via **`importlib.import_module`** using the user-supplied **dotted module path**; plugin exposes a **documented entry protocol** (e.g. `get_plugin()` or module-level registry class) defined in contracts.

**Rationale**: Aligns with spec FR-002/FR-014 and planning input (“Python module path of a plugin”); no implicit filesystem scan for plugin code.

**Alternatives considered**: File path to `.py` file (harder to package); entry points in `pyproject.toml` only (too rigid for ad-hoc CI).

---

## 3. Directory traversal and `__test_labels__.yaml`

**Decision**: Walk **base directory** depth-first or breadth-first; treat each directory containing **`__test_labels__.yaml`** as a **test base** node; parse YAML into a **label map** attached to that subtree’s parsed results.

**Rationale**: Explicit marker file avoids inferring test roots from heuristics; supports multiple test bases under one hierarchy.

**Alternatives considered**: Single root labels file (does not scale to multiple facets); convention-only directory names (fragile).

---

## 4. Parse cache

**Decision**: Write cache as **structured file** (JSON or MessagePack) under a deterministic path derived from **base dir + plugin module + schema version**, with **content hash** or **mtime** of discovered inputs recorded **inside** the cache for invalidation.

**Rationale**: Satisfies FR-016 and SC-006; JSON keeps debugging simple; schema version bump forces refresh.

**Alternatives considered**: SQLite (heavier); no cache (violates spec).

---

## 5. OpenSearch for KPI import/export

**Decision**: Use **`opensearch-py`** with connection parameters from **environment variables** (hosts, index prefix, credentials) consistent with existing vault patterns in FORGE.

**Rationale**: Spec assumes OpenSearch-compatible index; official client is standard.

**Alternatives considered**: Raw HTTP (more boilerplate); Elasticsearch client (diverges from naming in spec).

---

## 6. Visualization and HTML reports

**Decision**: Delegate **plot types and HTML templates** to the **plugin**; core supplies **data hooks** (unified model, filtered facets) and optional **shared helpers** in `projects/caliper/` for common charts.

**Rationale**: FR-003/FR-004 require project-specific definitions; core should not hardcode chart taxonomy.

**Alternatives considered**: Fixed Matplotlib only (too limiting for teams).

---

## 7. `visualize` report selection

**Decision**: Support **mutually exclusive** modes: (a) **`--reports a,b,c`**** list** matching plugin report ids, or (b) **`--report-group <id>`** resolved from a **YAML/JSON config file** path (`--visualize-config` or default under base dir). **Label filters**: **`--include-label key=value`** / **`--exclude-label key=value`** (repeatable).

**Rationale**: Matches user input; group id avoids long CLI for standard bundles.

**Alternatives considered**: Only CLI list (verbose); only config (less flexible for one-off runs).

---

## 8. Regression analysis inputs

**Decision**: **`kpi analyze`** reads **current** KPI set (from generate or cache) and **historical** set from **`kpi import`** output or direct OpenSearch query; output **regression findings** document (JSON + human summary).

**Rationale**: Separates “fetch baseline” (import) from “compare” (analyze).

**Alternatives considered**: Single command that always hits OpenSearch (harder to test offline).

---

## 9. File artifact export (S3 and MLflow)

**Decision**: Implement **`artifacts export`** (or equivalent) with **pluggable backends**; **S3** via **`boto3`** (or compatible client) using standard env/credential chain; **MLflow** via **`mlflow`** client (`set_tracking_uri`, `log_artifact` / run context from config or CLI).

**Rationale**: FR-017 requires both backends; boto3 and MLflow are common in ML/CI stacks; per-backend isolation maps to clear success/failure reporting.

**Alternatives considered**: Rclone subprocess only (weaker integration); MinIO-only (not required—S3 API covers MinIO).
