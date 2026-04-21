# Contract: `__test_labels__.yaml`

**Feature**: 009-artifact-post-processing

## Purpose

Marks a directory as a **test base** and supplies **distinguishing labels** for that subtree (FR-001, FR-015).

## Location

- Filename: **`__test_labels__.yaml`**
- Placement: any directory under `--base-dir` that should be treated as a labeled test root.

## Format (YAML)

Recommended shape (flexible superset; engine normalizes to string map where possible):

```yaml
# Example
version: "1"
labels:
  deployment: "single-zone"
  model: "llama-3"
  load_generator: "k6"
  flavor: "gpu"
```

## Rules

- If the file exists it MUST be valid YAML.
- `labels` SHOULD be a flat map of string → string for filtering and KPI dimensions; nested structures are plugin-defined and may be flattened by the plugin.
- Multiple test bases MAY exist in one hierarchy; each file scopes labels to its directory subtree.
