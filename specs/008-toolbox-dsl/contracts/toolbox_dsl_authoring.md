# Contract: Toolbox DSL authoring

**Feature**: 008-toolbox-dsl  
**Audience**: Toolbox command authors and orchestration integrators.

## 1. Command entrypoint

- Exactly **one** public function per command module (e.g. `run`) documented for operators and orchestration.
- Typical tail: `return execute_tasks(locals())` (or a filtered dict of parameters).
- CLI: generated from the entrypoint signature via `projects.core.dsl.toolbox` helpers (`create_toolbox_main`, etc.).

## 2. Task functions

- Each task is a **Python function** with signature:

  ```text
  (readonly_args, context) -> result | None
  ```

- `readonly_args`: command parameters + `artifact_dir` (read-only facade).
- `context`: mutable per-step object; public attributes merge into shared context after the step.

## 3. Task properties (metadata)

Properties are attached using **decorators** on the task function (Python metadata pattern):

| Decorator | Semantics |
|-----------|-----------|
| `@task` | Registers the function as a step; wraps execution for logging and results. **Required** base for other task decorators. |
| `@when(lambda: …)` | Zero-arg predicate evaluated at scheduling time; falsy skips the step with a visible skip record. |
| `@retry(attempts=, delay=, backoff=, retry_on_exceptions=)` | Bounded retries: default retry on falsy return; optional retry on raised exceptions; never retries cooperative cancel. |
| `@always` | Marks teardown / finalization steps that remain in the pending queue after a failure. |

**Stacking order (normative)**

- Write `@retry` / `@when` **closer to the `def`** than `@task` (i.e. above `@task` in source).
- `@always` may appear immediately above or below `@task` per project docs.

**Validation**

- `@retry` and `@when` require an inner `@task`; mis-ordered decorators raise `TypeError` with actionable text.

## 4. Execution visibility

- Each step emits structured log boundaries; skips and retries are explicit in logs and `task.log`.
- Failures include task name, description, location, and artifact directory pointer where available.

## 5. Testing contract

- Semantic regressions are caught by automated tests under `projects/core/tests/` covering success, conditional skip, retry paths, failure + always sweep, and decorator validation.
