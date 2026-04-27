# Quickstart: Caliper (artifact post-processing)

**Feature**: 009-artifact-post-processing

## Prerequisites

- Python 3.11+
- FORGE installed in editable mode with optional `[caliper]` extras (OpenSearch/S3/MLflow backends)
- OpenSearch reachable for KPI import/export (optional for parse/visualize)
- For **file export**: S3-compatible endpoint and/or MLflow tracking server (optional until `artifacts export` is used)

## 1. Mark test directories

Add `__test_labels__.yaml` under each test base directory you want labeled (see [contracts/test_labels.md](./contracts/test_labels.md)).

## 2. Implement a plugin module

Create a Python module (package) that implements the plugin protocol (see [plan.md](./plan.md)).

Register `plugin_module` in **`caliper.yaml`** (or legacy `forge-postprocess.yaml`) under `--base-dir`, per FR-014.

## 3. Run commands

```bash
# Parse only (populate cache)
# Either set plugin_module in caliper.yaml under --base-dir, or pass --plugin:
caliper --base-dir /path/to/artifacts parse
caliper --plugin my_project.postprocess_plugin --base-dir /path/to/artifacts parse

# Visualize: explicit report list
caliper --plugin ... --base-dir ... visualize --reports throughput,latency

# Visualize: group from config + label filters
caliper --plugin ... --base-dir ... visualize \
  --report-group nightly \
  --visualize-config ./visualize-groups.yaml \
  --include-label deployment=multi-zone \
  --exclude-label flavor=cpu

# KPI pipeline
caliper --plugin ... --base-dir ... kpi generate --output ./kpis.jsonl
caliper kpi import --snapshot ./baseline.jsonl   # OpenSearch
caliper kpi export --input ./kpis.jsonl
caliper kpi analyze --current ./kpis.jsonl --baseline ./baseline.jsonl --output ./regression.json

# File artifacts → S3 and MLflow (after visualize or standalone)
caliper --plugin ... --base-dir ... artifacts export \
  --from ./report-output \
  --backend s3 --backend mlflow \
  --s3-bucket my-bucket --s3-prefix runs/2026-04-16/
# MLflow connection via env or flags (see contracts/cli.md)
```

## 4. Artifacts location

- HTML reports: under `--output-dir` for `visualize` (default TBD).
- Parse cache: under `--base-dir` in `.caliper_cache/` (plugin + schema version).
- **File export**: S3 keys and MLflow run artifacts per **FR-017** in [spec.md](../spec.md) and project configuration.

## See also

- [spec.md](./spec.md)
- [data-model.md](./data-model.md)
- [contracts/](./contracts/)
