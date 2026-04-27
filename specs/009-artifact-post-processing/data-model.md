# Data Model: Artifact Post-Processing Engine

**Feature**: 009-artifact-post-processing  
**Spec**: [spec.md](./spec.md)

## Entity relationship (high level)

```text
BaseDirectory
  └── TestBaseNode (one per directory containing __test_labels__.yaml)
        ├── labels: map[string, string | ...]
        └── ParsedFacet[] (from plugin; multiple facets per node if plugin emits them)
UnifiedRunModel
  ├── plugin_module: string
  ├── base_directory: path
  ├── test_nodes: TestBaseNode[]
  ├── parse_cache_ref: optional path + validity metadata
  └── unified_result_records: UnifiedResultRecord[]
CanonicalKPIRecord[]   # identical shape for all projects (FR-007)
RegressionFinding[]    # output of kpi analyze
FileExportManifest     # paths + metadata for multi-backend upload (FR-017)
FileExportBackendResult[]  # per-backend success/failure (FR-017)
```

## Entities

### Base directory

| Field | Description |
|-------|-------------|
| `path` | Root path passed as `--base-dir` |
| `plugin_module` | Dotted Python module for project plugin |

### Test base node

| Field | Description |
|-------|-------------|
| `directory` | Absolute path to directory containing the marker file |
| `labels` | Parsed contents of `__test_labels__.yaml` (see [contracts/test_labels.md](./contracts/test_labels.md)) |
| `artifacts` | Opaque handles or paths discovered by plugin under this node |

### Unified result record

| Field | Description |
|-------|-------------|
| `test_base_path` | Links to a **Test base node** |
| `distinguishing_labels` | Effective label set for filtering and KPI attribution (FR-001, FR-015) |
| `metrics` | Plugin-defined normalized metrics (must map to plugin schema) |
| `run_identity` | Build/version/run id as available |

### Parse cache

| Field | Description |
|-------|-------------|
| `schema_version` | Engine cache format version |
| `input_fingerprint` | Hash or manifest of inputs used to invalidate (FR-016) |
| `plugin_module` | Module path at time of parse |
| `unified_model` | Serialized **UnifiedRunModel** snapshot |

### Canonical KPI record (logical)

See [contracts/kpi_record.md](./contracts/kpi_record.md). Must be stable for OpenSearch and dashboard (FR-007, FR-008).

### Regression finding

| Field | Description |
|-------|-------------|
| `kpi_id` | Stable KPI identifier |
| `current_value` | number or typed value |
| `baseline_value` | from import/history |
| `direction` | higher/lower better |
| `status` | ok / regression / improvement / noise (per rules) |

### File export manifest (logical)

| Field | Description |
|-------|-------------|
| `source_paths` | Files or directories to upload (from visualize output or plugin-declared list) |
| `run_identity` | Correlates uploads to CI/run id and labels (FR-015) |
| `backends_enabled` | Subset of `{ s3, mlflow, ... }` |

### File export backend result

| Field | Description |
|-------|-------------|
| `backend` | e.g. `s3`, `mlflow` |
| `status` | success / failure / skipped |
| `detail` | URI prefix, MLflow run id, or error summary (no secrets) |

## Validation rules

- Every **Test base node** MUST have readable `__test_labels__.yaml` or explicit error (plugin may relax with config).
- **Canonical KPI records** MUST validate against shared schema before export (FR-012).
- **Label filters** for `visualize` apply to **distinguishing_labels** / test node labels; include/exclude semantics: default include-all if no filters; exclude wins on conflict if both match (implementation detail documented in CLI contract).

## State transitions

1. **parse**: empty → unified model + cache written  
2. **visualize**: unified model (fresh or cache) → report artifacts  
3. **kpi generate**: unified model → KPI records  
4. **kpi import**: OpenSearch → local/history snapshot  
5. **kpi export**: KPI records → OpenSearch  
6. **kpi analyze**: current KPIs + historical → regression findings  
7. **artifacts export**: file manifest → S3 and/or MLflow (per-backend results) (FR-017)  
