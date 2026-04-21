# Contract: Post-processing manifest (project configuration)

**Feature**: 009-artifact-post-processing  
**Related**: FR-002, FR-014

## Purpose

Declares the **canonical** `plugin_module` for a project. The CLI may override with `--plugin` for a single invocation.

## Discovery (implementation)

- If **`--postprocess-config PATH`** is set, load that file.
- Else search under **`--base-dir`** for a conventional name (e.g. `caliper.yaml`, `forge-postprocess.yaml`, `postprocess.yaml`)—exact list is implementation-defined and should be documented in `projects/caliper/README.md`.

## Minimal YAML shape (example)

```yaml
plugin_module: "my_project.postprocess_plugin"
# Optional fields (versioning, extra hooks) may be added later
```

## Rules

- **`plugin_module`** MUST be a dotted Python import path unless **`--plugin`** is supplied on the CLI (overrides).
- Invalid YAML, missing file when required, or missing `plugin_module` when `--plugin` is absent → **FR-014** error.
