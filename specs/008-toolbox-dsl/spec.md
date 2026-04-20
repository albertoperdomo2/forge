# Feature Specification: FORGE Toolbox Command DSL

**Feature Branch**: `008-toolbox-dsl`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Extend, document and test the DSL of the FORGE toolbox" (FORGE test harness: domain-specific language for toolbox commands controlling OpenShift; public entrypoint; CLI from entrypoint signature; sequential tasks; `@always` for post-failure steps; `@retry` for bounded retries until success or abort.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author a standalone toolbox command (Priority: P1)

A toolbox command author defines a single public entrypoint (a documented callable with explicit parameters) that orchestration or operators can invoke. The same entrypoint is exposed consistently to the upper orchestration layer and to human operators without duplicating parameter definitions. The author breaks cluster work into ordered steps that run one after another, with clear outcomes per step.

**Why this priority**: Without a single, well-defined entrypoint and ordered steps, commands become fragile, hard to reuse, and difficult to drive from automation or from the shell.

**Independent Test**: A new or updated command can be reviewed for a single entry surface, declared parameters, and a linear step list with no hidden global ordering dependencies.

**Acceptance Scenarios**:

1. **Given** a command author is implementing a toolbox flow, **When** they define the public entrypoint and its parameters, **Then** orchestration can invoke that entrypoint with the same parameter contract used for interactive execution.
2. **Given** a command defines multiple steps, **When** the command runs successfully, **Then** each step executes in declared order and later steps can rely on outcomes of earlier steps without ad hoc coupling.
3. **Given** an operator or automation needs to run the command, **When** they supply arguments matching the entrypoint contract, **Then** execution starts without requiring duplicate argument wiring in a second place.

---

### User Story 2 - Recover context after partial failure (Priority: P2)

When a mid-pipeline step fails, designated cleanup or reporting steps still run so that artifacts and logs remain useful for post-mortem analysis. Steps that were not meant to run after an abort are skipped rather than executed in an undefined state.

**Why this priority**: OpenShift operations fail often for transient reasons; operators need trustworthy traces and teardown without guessing which steps actually ran.

**Independent Test**: A failing scenario can be exercised where a step raises; observers verify that mandatory follow-up steps ran and that remaining normal steps were skipped intentionally.

**Acceptance Scenarios**:

1. **Given** a pipeline with normal steps and designated always-run follow-up steps, **When** a normal step fails, **Then** pending normal steps are skipped and each designated follow-up step still runs in order.
2. **Given** a pipeline failure, **When** an operator opens the run’s recorded trace, **Then** they can see which step failed and which steps were skipped versus executed afterward.
3. **Given** a successful pipeline with designated follow-up steps, **When** the run completes, **Then** follow-up steps still execute as defined in command order (for example finalization or artifact packaging).

---

### User Story 3 - Tolerate flaky steps with bounded retries (Priority: P3)

Some steps depend on the cluster or external systems eventually reaching a ready state. The command author can mark those steps to retry within configured limits until they succeed or the command aborts with a clear, attributable failure.

**Why this priority**: Reduces noise from transient readiness issues while keeping runs bounded so CI and operators do not wait indefinitely.

**Independent Test**: A step that fails or returns “not yet” a limited number of times and then succeeds completes without manual re-run; exhaustion produces a single clear failure classification.

**Acceptance Scenarios**:

1. **Given** a step configured for bounded retries, **When** the step repeatedly indicates non-success within the limit, **Then** the command eventually stops with a failure that identifies retry exhaustion.
2. **Given** a step configured for bounded retries, **When** the step succeeds before the limit, **Then** the pipeline continues without manual intervention.
3. **Given** an operator reviews a retrying run, **When** they read the trace, **Then** they can see retry attempts and delays (or equivalent structured progress) for that step.

---

### User Story 4 - Discover behavior from documentation (Priority: P3)

New contributors and orchestration integrators can read maintained documentation that explains the command shape (entrypoint, steps, markers for always-run and retry, and how traces are produced) without reading implementation code first.

**Why this priority**: Lowers onboarding cost and reduces misuse of markers or execution order.

**Independent Test**: A reviewer with no prior context can answer basic “how do I add a step / a retry / a cleanup step?” questions using only the published documentation.

**Acceptance Scenarios**:

1. **Given** a contributor opens the toolbox DSL documentation, **When** they follow it, **Then** they can construct a valid command outline (entrypoint, sequential steps, optional markers) aligned with project conventions.
2. **Given** an orchestration engineer needs the integration contract, **When** they read the documentation, **Then** they understand how the public entrypoint relates to automation versus shell use.

---

### Edge Cases

- A step fails after some steps succeeded: remaining non–always-run steps must not run in an inconsistent order; always-run steps defined after the failure point still run.
- User interrupt or cooperative cancel signal: execution stops without corrupting the requirement that cancel is not treated as a retriable failure where unsafe.
- Retry configuration with zero delay versus production-like delays: behavior remains bounded by attempt count and documented semantics for “success” versus “retry again”.
- Conditional steps that should run only when a prior outcome or environment predicate holds: if the predicate fails, the step is skipped and recorded as skipped (no silent no-op without trace).
- Nested or duplicate step names across files: trace identity remains unambiguous for the command file being executed.
- Always-run step itself fails after a main failure: the original failure remains primary unless no prior failure existed, in which case the always-run failure is surfaced.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each toolbox command MUST expose exactly one documented public entrypoint representing its parameters and behavior contract for the orchestration layer.
- **FR-002**: The same parameter contract MUST be usable from automation invoking the entrypoint directly and from command-line invocation without maintaining a second divergent option list.
- **FR-003**: A command MUST define an ordered sequence of steps; the execution engine MUST run those steps in the order they appear in the command definition for successful runs unless a step is skipped by an explicit documented gating rule.
- **FR-004**: Steps marked as always-run MUST execute after a prior step failure for any still-pending always-run steps in file order, while pending normal steps after the failure MUST NOT execute.
- **FR-005**: Steps MAY support bounded retries with configurable attempt count, initial wait, and backoff multiplier until success or until attempts are exhausted.
- **FR-006**: On retry exhaustion, the failure MUST be attributable to the retrying step with enough trace context for post-mortem review.
- **FR-007**: Each run MUST produce a verbose execution trace suitable for post-mortem observation (including step boundaries, skip decisions, and retry progress where applicable).
- **FR-008**: Published documentation MUST describe the entrypoint model, sequential steps, always-run semantics, retry semantics, and trace layout at a level sufficient for new command authors and integrators.
- **FR-009**: Automated verification MUST cover the primary semantics in FR-003 through FR-007 (success path, failure with always-run, skip gating, retry success path, retry exhaustion) so regressions are detected in continuous integration.
- **FR-010**: Commands MUST remain standalone with respect to parameters: required inputs are declared on the entrypoint rather than implied by undeclared environment coupling, except where the platform already defines global conventions documented for authors.

### Key Entities

- **Toolbox command**: A deliverable unit with one public entrypoint, ordered steps, optional markers (always-run, retry, conditional gate), and a predictable trace.
- **Step (task)**: A single unit of work in the ordered list, with a stable name in traces and optional markers affecting scheduling and retries.
- **Run trace**: Time-ordered record of execution including parameters (excluding secrets policy per platform norms), step outcomes, skips, retries, and artifact locations for investigation.
- **Orchestration invocation**: Use of the public entrypoint by a higher layer with the same contract as interactive execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least three independent user stories above (P1–P3) have corresponding automated checks that fail if semantics regress.
- **SC-002**: Documentation answers, without reference to private tribal knowledge, (a) what the single entrypoint is, (b) how steps are ordered, (c) what always-run implies after failure, and (d) what retry bounds mean—validated by a peer review checklist with 100% items passed.
- **SC-003**: For a representative failing run, an operator can identify the failing step and distinguish skipped steps from executed steps within five minutes using only the trace and metadata produced by the harness.
- **SC-004**: Retry exhaustion for a representative flaky step is reported as a single classified failure (not an unhandled generic error) in 100% of exhaustion scenarios covered by automated checks.
- **SC-005**: New command authors report (via team review or pilot) that they can scaffold a minimal compliant command in one working session using only documentation and templates.

## Out of scope

- Redesign of unrelated harness subsystems (for example unrelated dashboard or CI orchestration products) except where required to surface DSL traces or parameters.
- Defining new OpenShift APIs; the feature assumes existing cluster interaction patterns remain unchanged behind steps.
- Internationalization of operator-facing messages beyond existing project norms.

## Assumptions

- Orchestration already has a stable way to invoke the documented entrypoint with structured arguments; this feature tightens the toolbox contract rather than inventing a new orchestration product.
- “Success” for a retriable step is defined by the command author’s return convention documented for authors (truthy versus structured success), and retries never apply to cooperative cancel signals.
- Artifact storage locations and retention follow existing FORGE environment conventions.
- Contributors accept English-language documentation for this iteration.
