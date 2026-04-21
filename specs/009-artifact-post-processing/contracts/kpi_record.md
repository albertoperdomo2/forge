# Contract: Canonical KPI record

**Feature**: 009-artifact-post-processing  
**Related**: FR-007, FR-008, FR-012

## Serialization

- **JSON** lines (JSONL) or JSON array; one record per line in JSONL.
- UTF-8 encoding.

## Required fields (minimal stable set)

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Canonical KPI schema version |
| `kpi_id` | string | Stable identifier (e.g. `latency_p99_seconds`) |
| `value` | number \| string \| object | Typed value; numbers preferred for regression |
| `unit` | string | e.g. `s`, `req/s`, `count` |
| `run_id` | string | Correlates to CI or FORGE run |
| `timestamp` | string (RFC3339) | When KPI was computed |
| `labels` | object | Distinguishing labels (subset of test labels + plugin dimensions) |
| `source` | object | `{ "test_base_path": "...", "plugin_module": "..." }` |

## Validation

- Records MUST pass JSON Schema in implementation (`schemas/kpi_record.schema.json`).
- Export to OpenSearch MUST reject invalid records (FR-012).
