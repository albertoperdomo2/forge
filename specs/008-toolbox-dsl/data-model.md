# Data Model: Toolbox DSL

**Feature**: 008-toolbox-dsl  
**Scope**: Logical entities for task registration, execution, and traces (not a SQL schema).

## Entity: `ScriptManager` (registry)

| Field / concept | Description |
|-----------------|-------------|
| `_task_registry` | Map `source_file` → ordered list of **task records** defined in that file |
| `_task_results` | Map `task_name` → **TaskResult** for last completed run of that name |

**Rules**

- `source_file` key is the path used at **registration** (`os.path.relpath` of defining file) and must match the path `execute_tasks` uses when resolving tasks for the caller module.
- Registration order defines default execution order for non-failure paths.

## Entity: Task record (`task_info` dict)

| Key | Type (conceptual) | Description |
|-----|-------------------|-------------|
| `name` | `str` | Python function name (stable trace id) |
| `func` | callable | `@task` wrapper (logs + invokes body) |
| `condition` | callable \| `None` | Zero-arg callable; falsy → skip step |
| `retry_config` | dict \| `None` | `attempts`, `delay`, `backoff`, `retry_on_exceptions` |
| `always_execute` | `bool` | If true, eligible to run after a prior step failure (pending slice) |

**Transitions**

1. **Registered** at import when `@task` runs (and outer decorators update `_task_info`).
2. **Pending** — not yet reached in the current run.
3. **Skipped** — condition false or aborted as non-always after failure.
4. **Running / finished** — runtime invokes wrapper; result stored on `TaskResult`.

## Entity: `TaskResult`

| Field | Description |
|-------|-------------|
| `task_name` | Identifier |
| `return_value` | Last body return (read by `@when` lambdas) |
| `_executed` | Internal flag set when a value is recorded |

## Entity: Run arguments (`args`)

| Source | Description |
|--------|-------------|
| Entrypoint `locals()` | Converted to `SimpleNamespace` for the run |
| `artifact_dir` | Injected by `execute_tasks` under `NextArtifactDir` |

Read-only view: **ReadOnlyArgs** (blocks attribute assignment).

## Entity: Shared context

| Concept | Description |
|---------|-------------|
| `shared_context` | `SimpleNamespace` persisting across tasks |
| Per-task `TaskContext` | Copy-in / merge-back of public attributes (no `_` prefix) after each step |

## Entity: On-disk trace (per run)

| Artifact | Purpose |
|----------|---------|
| `_meta/metadata.yaml` | Command, timestamp, args snapshot, artifact path |
| `_meta/restart.sh` | Replay helper |
| `task.log` | DSL logger file copy |

## Validation rules (from spec)

- **FR-004**: After failure at index `i`, indices `> i` that are not `always_execute` are never invoked; `always_execute` tasks among pending are invoked in file order.
- **FR-005–006**: Retry bounded by `attempts`; exhaustion raises a classified error chain suitable for operators.
