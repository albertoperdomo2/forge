# Caliper

Artifact post-processing: parse labeled test trees, visualize, KPIs, export to OpenSearch / S3 / MLflow.

**Specification**: [specs/009-artifact-post-processing/spec.md](../../specs/009-artifact-post-processing/spec.md)

## CLI

```bash
caliper --base-dir /path/to/artifacts parse
caliper --plugin my.module --base-dir /path visualize --output-dir ./out --reports default
```

Install optional backends: `pip install -e '.[caliper]'`

## Commands

| Command | Purpose |
|---------|---------|
| `parse` | Traverse, parse, write parse cache |
| `visualize` | Plots + HTML from unified model |
| `kpi generate` / `import` / `export` / `analyze` | Canonical KPI pipeline |
| `artifacts export` | File upload to S3 / MLflow |
| `ai-eval-export` | AI evaluation JSON |

See [quickstart.md](../../specs/009-artifact-post-processing/quickstart.md) and [plan.md](../../specs/009-artifact-post-processing/plan.md).
