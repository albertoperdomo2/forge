# Research: FORGE Toolbox DSL (008-toolbox-dsl)

**Date**: 2026-04-16

## 1. “Annotations” for task properties: decorators vs `typing.Annotated`

### Decision

Use **decorators** on task **functions** as the **canonical** way to attach task properties (`task` registration, conditional `@when`, bounded `@retry`, `@always`). Document this explicitly as the project’s Python-native metadata pattern.

### Rationale

- **Expressive factories**: `@when(lambda: …)` and `@retry(attempts=…, delay=…)` need runtime callables and numeric parameters; PEP 484 **return** annotations alone do not carry that ergonomically without a parallel builder API.
- **Established codebase**: `projects.core.dsl.task` already implements composable decorators with `@task_only` validation and registry updates (`_task_info` for late-applied metadata).
- **Python alignment**: Decorators are a standard language feature for attaching metadata to functions; they match the planning directive “functions + properties” without introducing a second parser.

### Alternatives considered

| Alternative | Why not chosen (for current phase) |
|-------------|-----------------------------------|
| **`typing.Annotated[..., RetryPolicy]`** on parameters/return | Attractive for static analyzers; requires new metadata types, introspection at import time, and migration of every toolbox script; defer unless team mandates mypy-driven contracts. |
| **YAML sidecar per command** | Splits behavior from code; hurts “standalone script” and code review locality. |
| **Class-based tasks** | Heavier than functions; conflicts with “use functions to define tasks” unless limited to `@staticmethod` patterns. |

### Follow-up (optional)

- Prototype **optional** `Annotated` mirror types for IDE hints only, without changing runtime registration, if PSAP wants stricter static checks.

## 2. Decorator application order

### Decision

Document and enforce stacks as today:

- `@retry(...)` / `@when(...)` **above** `@task` (closer to `def`), i.e. applied **after** `@task` at runtime—`@task` runs first on the bare function, then outer decorators mutate metadata / `_task_info`.
- `@always` may appear **above or below** `@task` per `always()` docstring; both orders supported.

### Rationale

Matches CPython evaluation order and existing tests (`projects/core/tests/test_dsl_toolbox.py` patterns).

## 3. Task function contract

### Decision

Each registered task body implements `(readonly_args, context) -> Any`, wrapped by `@task` for logging and `TaskResult` capture. Shared context merges public attributes back after each step.

### Rationale

Keeps cluster side effects and orchestration parameters separate: immutable-ish args vs mutable cross-step context.

## 4. Observability and CI

### Decision

Retain file logging + console DSL logger, completion banners, skip lines, retry banners; keep pytest coverage for failure/always, `when`, retry truthy/falsy, retry-on-exception exhaustion, and shared-context return.

### Rationale

Directly maps to constitution **Observable** and **CI-First** principles.
