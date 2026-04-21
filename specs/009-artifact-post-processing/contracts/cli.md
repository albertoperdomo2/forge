# CLI contract: `caliper`

**Feature**: 009-artifact-post-processing  
**Status**: design

## Global options

Applies to most commands; **`--base-dir` is omitted** for subcommands that do not parse an artifact tree (e.g. **`kpi import`**, **`kpi export`**, **`kpi analyze`**, **`artifacts export`**).

| Option | Required | Description |
|--------|----------|-------------|
| `--plugin MODULE` | **Conditional** | Dotted Python module path implementing the project plugin protocol. **Required** if the post-processing manifest does not declare `plugin_module` (or equivalent). If **both** manifest and `--plugin` are present, **`--plugin` wins** (override for CI/ad-hoc runs). Not used when no plugin is loaded (e.g. `artifacts export`). |
| `--postprocess-config PATH` | no | Path to the **project manifest** (YAML/JSON). If omitted, the engine searches conventional locations under `--base-dir` (for example `caliper.yaml`, `forge-postprocess.yaml`, `postprocess.yaml`—exact names are implementation-defined). |
| `--base-dir PATH` | **Conditional** | Root directory containing the artifact hierarchy. **Required** for `parse`, `visualize`, `kpi generate`, `ai-eval-export`; **not** for `kpi import` / `kpi export` / `kpi analyze` / `artifacts export`. |

## Commands

### `parse`

Perform **only** parsing (directory walk, marker discovery, plugin parse, optional cache write).

| Option | Description |
|--------|-------------|
| `--no-cache` | Force full parse; do not read or write parse cache |
| `--cache-dir PATH` | Override default cache location |

### `visualize`

Parse (or load cache) then generate **plots and HTML reports** per plugin.

| Option | Description |
|--------|-------------|
| `--reports ID[,ID...]` | Comma-separated report ids from the plugin (mutually exclusive with `--report-group`) |
| `--report-group ID` | Id defined in visualize config mapping groups → report lists |
| `--visualize-config PATH` | YAML/JSON file for report groups; if omitted, search default under `--base-dir` |
| `--include-label KEY=VALUE` | Repeatable; only include test nodes matching all include rules (semantics TBD in impl) |
| `--exclude-label KEY=VALUE` | Repeatable; exclude matching nodes |
| `--output-dir PATH` | Where to write HTML/assets (default under base dir or CWD) |

### `kpi generate`

Parse (or load cache) then emit **canonical KPI records** (stdout or file).

| Option | Description |
|--------|-------------|
| `--output PATH` | Write KPI JSONL or JSON array |

### `kpi import`

Download **historical KPIs** from OpenSearch into a local snapshot (for analyze or audit).

| Option | Description |
|--------|-------------|
| `--snapshot PATH` | Output file for imported records |
| Query filters | TBD: time range, run id, label filters (align with FR-009) |

### `kpi export`

Export **new KPIs** (from `kpi generate` output or unified run) to OpenSearch.

| Option | Description |
|--------|-------------|
| `--input PATH` | KPI file to export |
| `--dry-run` | Validate only |

### `kpi analyze`

Analyze KPIs for **regression** (current vs historical).

| Option | Description |
|--------|-------------|
| `--current PATH` | Current KPI set |
| `--baseline PATH` | Imported snapshot or query reference |
| `--output PATH` | Regression report JSON + summary text |

### `artifacts export`

Upload **file artifacts** (generated plots, HTML bundles, plugin-listed files) to **one or more** backends (FR-017). Distinct from **`kpi export`** (OpenSearch KPI documents).

| Option | Description |
|--------|-------------|
| `--from PATH` | Directory or manifest of files to export (often `visualize` `--output-dir`) |
| `--backend NAME` | Repeatable: `s3`, `mlflow` (at least one) |
| `--s3-bucket`, `--s3-prefix` | S3 destination (when `s3` enabled); or from env/config |
| `--mlflow-tracking-uri` / `--mlflow-endpoint` | MLflow server URI when `--backend mlflow`; defaults to **`MLFLOW_TRACKING_URI`** env if unset |
| `--mlflow-experiment`, `--mlflow-run-id` | MLflow context (when `mlflow` enabled); may use env vars |
| `--dry-run` | Resolve paths and validate credentials without uploading |

Per-backend outcomes are printed or written to a structured log; exit code reflects overall policy (for example non-zero if any enabled backend fails unless `--continue-on-partial` is set—exact policy TBD in implementation).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (bad args, missing marker file) |
| 2 | Plugin or parse failure |
| 3 | OpenSearch / KPI export failure |
| 4 | File artifact export failure (S3/MLflow); partial failure may use distinct sub-exit or structured output (TBD) |
