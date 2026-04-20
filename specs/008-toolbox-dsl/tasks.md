# Tasks: FORGE Toolbox Command DSL

**Input**: Design documents from `/specs/008-toolbox-dsl/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md), [quickstart.md](./quickstart.md)

**Tests**: **Required** per spec FR-009 / SC-001 — each user story phase includes explicit test maintenance or extension tasks under `projects/core/tests/`.

**Organization**: Phases follow user story priority (P1 → P4); paths are repo-root-relative.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different files, no ordering dependency within the same phase subsection
- **[USn]**: Maps to **User Story n** in [spec.md](./spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align implementers with locked design decisions before touching code.

- [x] T001 Review [specs/008-toolbox-dsl/plan.md](./plan.md), [specs/008-toolbox-dsl/spec.md](./spec.md), and [specs/008-toolbox-dsl/contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md) for scope and authoring rules
- [x] T002 [P] Review [specs/008-toolbox-dsl/research.md](./research.md) and [specs/008-toolbox-dsl/data-model.md](./data-model.md) for registry keys, context merge, and decorator-vs-Annotated decision

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirm core DSL modules match the data model and contracts — **blocks all user story work**.

**⚠️ CRITICAL**: No user story phase may close until T003–T005 are satisfied.

- [x] T003 Verify `source_file` keys from `projects/core/dsl/task.py` registration match the relative path logic used in `projects/core/dsl/runtime.py` when calling `get_script_manager().get_tasks_from_file(rel_filename)`
- [x] T004 [P] Verify public exports in `projects/core/dsl/__init__.py` include `task`, `when`, `retry`, `always`, `execute_tasks`, `RetryFailure`, and match [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md) section 3
- [x] T005 [P] Confirm `projects/core/tests/conftest.py` sets `FORGE_HOME`, `ARTIFACT_DIR`, and `reset_script_manager()` so `projects/core/tests/test_dsl_toolbox.py` remains isolated

**Checkpoint**: Foundation verified — user story work can proceed (prefer P1 → P4 order).

---

## Phase 3: User Story 1 — Author a standalone toolbox command (Priority: P1) 🎯 MVP

**Goal**: Single public entrypoint, ordered task functions, CLI parity from signature (spec FR-001, FR-002, FR-003).

**Independent Test**: From repo root, `python -m pytest projects/core/tests/test_dsl_toolbox.py::test_execute_tasks_success_returns_shared_context -q` passes; at least one reference toolbox module uses `execute_tasks(locals())` with ordered `@task` functions.

### Tests for User Story 1

- [x] T006 [P] [US1] Maintain or extend success-path coverage for ordered steps and `shared_context` / `artifact_dir` in `projects/core/tests/test_dsl_toolbox.py` (align with spec acceptance scenarios for US1)

### Implementation for User Story 1

- [x] T007 [US1] Audit `projects/core/dsl/toolbox.py` and `projects/core/dsl/cli.py` so generated CLI options stay in lockstep with the public entrypoint signature (FR-002); fix gaps in `projects/core/dsl/cli.py` if found
- [x] T008 [P] [US1] Spot-check a reference command (e.g. `projects/skeleton/toolbox/cluster_info/main.py`) against [specs/008-toolbox-dsl/quickstart.md](./quickstart.md) for single entrypoint + ordered `@task` usage; open follow-up issue if patterns diverge from contract

**Checkpoint**: US1 satisfied by tests + at least one real command pattern consistent with quickstart.

---

## Phase 4: User Story 2 — Recover context after partial failure (Priority: P2)

**Goal**: Pending normal steps skipped after failure; pending `@always` steps still run; trace distinguishes skipped vs executed (FR-004, FR-007).

**Independent Test**: `python -m pytest projects/core/tests/test_dsl_toolbox.py::test_failure_skips_pending_but_runs_always -q` passes.

### Tests for User Story 2

- [x] T009 [P] [US2] Keep `test_failure_skips_pending_but_runs_always` in `projects/core/tests/test_dsl_toolbox.py` aligned with `projects/core/dsl/runtime.py` skip/always sweep; add assertions on skip log lines if product requires stricter FR-007 proof

### Implementation for User Story 2

- [x] T010 [US2] Review `projects/core/dsl/runtime.py` failure path (`task_index`, pending slice, `always_execute`) against [specs/008-toolbox-dsl/data-model.md](./data-model.md) and spec edge cases; patch `projects/core/dsl/runtime.py` if any divergence

**Checkpoint**: US2 independently testable via pytest and trace semantics.

---

## Phase 5: User Story 3 — Tolerate flaky steps with bounded retries (Priority: P3)

**Goal**: Bounded retries on falsy outcome and optional exception retries; exhaustion classified for operators (FR-005, FR-006, SC-004).

**Independent Test**: `python -m pytest projects/core/tests/test_dsl_toolbox.py -k retry -q` passes (covers falsy/truthy, exception retry, exhaustion, decorator validation).

### Tests for User Story 3

- [x] T011 [P] [US3] Maintain `test_retry_falsy_then_truthy`, `test_retry_on_exceptions`, `test_retry_on_exceptions_exhausted`, and `test_retry_decorator_requires_task` in `projects/core/tests/test_dsl_toolbox.py`; extend `projects/core/tests/test_dsl_toolbox.py` if SC-004 chain (`RetryFailure` / `TaskExecutionError.__cause__`) regresses

### Implementation for User Story 3

- [x] T012 [US3] Review `projects/core/dsl/task.py` (`retry`, `_execute_with_retry`, `RetryFailure`) against [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md) section 3; adjust `projects/core/dsl/task.py` or `projects/core/dsl/runtime.py` only if contract/spec drift is found

**Checkpoint**: US3 independently testable via pytest retry suite.

---

## Phase 6: User Story 4 — Discover behavior from documentation (Priority: P3)

**Goal**: Authors and integrators can learn entrypoint + task + decorator model without reading implementation first (FR-008, SC-002).

**Independent Test**: Peer can answer US4 acceptance questions using only `docs/toolbox/dsl.md` and [quickstart.md](./quickstart.md).

### Implementation for User Story 4

- [x] T013 [US4] Update `docs/toolbox/dsl.md` so decorator stacks, test location (`projects/core/tests/test_dsl_toolbox.py`), failure/always semantics, and retry options match [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md)
- [x] T014 [P] [US4] Update [specs/008-toolbox-dsl/quickstart.md](./quickstart.md) code blocks to match enforced decorator order documented in `projects/core/dsl/task.py` and `docs/toolbox/dsl.md`

**Checkpoint**: US4 documentation independently reviewable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CI hygiene, checklist, quickstart execution.

- [x] T015 [P] Run `python -m pytest` from repository root (`pyproject.toml` testpaths → `projects/core/tests`) and fix any failures in `projects/core/dsl/*.py` or `projects/core/tests/*.py`
- [x] T016 [P] Run `python -m ruff check projects/core/dsl` and resolve findings in `projects/core/dsl/`
- [x] T017 Execute manual steps in [specs/008-toolbox-dsl/quickstart.md](./quickstart.md) using a scratch module under `projects/core/tests/` or a non-production toolbox path; fix doc or code drift
- [x] T018 Update [specs/008-toolbox-dsl/checklists/requirements.md](./checklists/requirements.md) checkboxes if spec/plan/tasks completion changes validation status

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1**: No prerequisites — start immediately.
- **Phase 2**: Depends on Phase 1 — **blocks all user stories**.
- **Phases 3–6 (US1–US4)**: All depend on Phase 2. Recommended sequence: US1 → US2 → US3 → US4 (P1 first for MVP); US3 and US4 can overlap after US2 if staffed.
- **Phase 7**: Depends on desired user stories being complete (minimum **US1** for a thin MVP).

### User story dependencies

- **US1**: No dependency on other stories — **MVP**.
- **US2**: Independent in tests; shares `runtime.py` with US1 but no story-order dependency.
- **US3**: Independent in tests; touches `task.py` / runtime retry wiring — after US2 if minimizing merge conflicts, or parallel if files coordinated.
- **US4**: Depends on stable behavior from US1–US3 (docs should describe shipped semantics).

### Within each story

- Listed **[P]** tasks may run in parallel within the same subsection.
- Prefer **tests first** when extending behavior (spec FR-009).

### Parallel opportunities

| Phase | Parallel bundle |
|-------|-----------------|
| 1 | T002 while T001 is read-only summary |
| 2 | T004, T005 in parallel after T003 scoped |
| 3 | T006 and T008 in parallel before T007 deep audit |
| 4 | T009 parallel with prep for T010 |
| 5 | T011 parallel read before T012 |
| 6 | T014 parallel with T013 if different owners |
| 7 | T015, T016 in parallel |

---

## Parallel Example: User Story 1

```bash
# After T003–T005 complete, two developers could:
# Dev A: extend success-path tests
python -m pytest projects/core/tests/test_dsl_toolbox.py::test_execute_tasks_success_returns_shared_context -q

# Dev B: audit reference toolbox module vs quickstart
sed -n '1,80p' projects/skeleton/toolbox/cluster_info/main.py
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Complete Phase 1–2 (T001–T005).  
2. Complete Phase 3 (T006–T008).  
3. Run `python -m pytest projects/core/tests/test_dsl_toolbox.py::test_execute_tasks_success_returns_shared_context -q`.  
4. **Stop / demo** if only entrypoint + ordering + CLI parity were the urgent gap.

### Incremental delivery

1. Add Phase 4 (US2) — failure + always + skip trace.  
2. Add Phase 5 (US3) — retry semantics + exhaustion classification.  
3. Add Phase 6 (US4) — documentation + quickstart sync.  
4. Finish Phase 7 — full pytest + ruff + checklist.

### Parallel team strategy

- After Phase 2: Developer A on US1 tests + toolbox CLI audit; Developer B on US2 runtime review; Developer C on US4 docs (accepts occasional rebase once US1 behavior stabilizes).

---

## Summary

| Metric | Value |
|--------|------|
| **Total tasks** | 18 (T001–T018) |
| **US1** | 3 (T006–T008) |
| **US2** | 2 (T009–T010) |
| **US3** | 2 (T011–T012) |
| **US4** | 2 (T013–T014) |
| **Setup + Foundation + Polish** | 9 (T001–T005, T015–T018) |
| **Parallel-friendly** | Tasks marked `[P]` |

**Suggested MVP scope**: Phase 1–3 (T001–T008) + T015 minimal pytest slice.

**Format validation**: Every line uses `- [ ] Tnnn` with optional `[P]` and `[USn]` only on user-story phase tasks; descriptions include concrete file paths.

**Next command**: `/speckit.implement` (or `/speckit.analyze` per handoff).
