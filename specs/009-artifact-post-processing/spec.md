# Feature Specification: Artifact Post-Processing Tool

**Feature Branch**: `009-artifact-post-processing`  
**Created**: 2026-04-20  
**Status**: Draft  
**Input**: User description: "I want a tool for the post-processing of our artifacts. The post processing includes: - parsing results from multiple test results - generating plots and HTML reports - generating well-defined KPIs for 1/ export to OpenSearch 2/ regression testing /3 visualization on a dashboard - generating well-structured JSON objects for AI agent performance evaluation"

## Clarifications

### Session 2026-04-22

- Q: How should post-processing vary by project, and how should KPI formats relate across projects? → A: Post-processing is **plugin-based per project**: each project defines its own parsing behavior, artifact file locations, plot definitions, report definitions, and KPI-related content. **Code sharing across projects is encouraged** where it makes sense. The **KPI interchange format** (what is exported, indexed, compared in regression, and shown on the dashboard) MUST be **the same for all projects**—only project-specific *content* (which KPIs apply, how values are computed from parsed data) varies, not the shape or semantics of KPI records.
- Q: How should the core discover each project's post-processing plugin? → A: **Manifest-only**: **project configuration** declares the plugin path (or equivalent entry reference). The core loads plugins from those declared references only—not by implicit workspace scanning alone.

### Session 2026-04-23

- Q: How should the engine handle multiple test results and tell them apart? → A: The engine MUST support parsing **multiple test results** in the inputs and MUST provide a **clear way to distinguish** each test result from the others. Test results expose **labels** that identify **which aspect was under test** (for example different **versions**, **deployment flavors**, **models**, **load generators**—and similar facets). Those labels MUST flow through parsing into the unified representation so comparison, reporting, and KPI association can target the correct slice.

### Session 2026-04-24

- Q: Should parsing avoid redoing full work on every invocation? → A: The **parser MUST generate a cache file** (or equivalent persisted cache artifact) that **can be reloaded** so that **full parsing need not run again** when the cache is **valid** for the same inputs—downstream steps (reports, plots, KPI computation) can proceed from the cached unified representation unless invalidation applies.

### Session 2026-04-26

- Q: How does **manifest-only** plugin discovery (2026-04-22) relate to the **`--plugin`** CLI? → A: The **project post-processing manifest** (configuration file) **MUST** declare the **`plugin_module`** (or equivalent entry reference) for that project. The **`--plugin`** option is an **explicit override** for a given invocation (CI, local debugging, A/B of plugin versions). **Resolution order**: if **`--plugin`** is set, use it; **else** load **`plugin_module`** from the manifest; **else** fail with FR-014. **Implicit scanning** of the workspace to guess a plugin is **not** allowed. The manifest file location is defined by implementation (for example optional **`--postprocess-config`**, or a conventional filename under **`--base-dir`**).

### Session 2026-04-25

- Q: Should the engine support exporting **file artifacts** to backends beyond OpenSearch (for KPI records)? → A: The engine MUST support exporting **file artifacts**—including generated outputs such as **plots, HTML report bundles**, and **other plugin-designated files**—to **multiple backends** in a single workflow. **Amazon S3**-compatible object storage and **MLflow** artifact tracking MUST be supported as first-class backends; the operator MUST be able to enable **one or both** (and future backends) per invocation or via configuration. This is **complementary** to KPI export to the search index (FR-008): **file-asset export** addresses object storage and experiment-tracking stores, not replacement of the canonical KPI interchange path unless a backend explicitly consumes KPI files by file export.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parse and Unify Multiple Test Results (Priority: P1)

Engineers and automation can take outputs from more than one test run or source format and produce a consistent internal representation of what happened (metrics, pass/fail signals, and enough context to attribute results). A single ingestion MAY contain **multiple test results** (for example several facets measured in one run); the engine **parses each test result distinctly** and preserves **distinguishing labels** so versions, deployment flavors, models, load generators, and similar aspects are not conflated. The parser **writes a reloadable parse cache** so repeat workflows can **skip full re-parse** when inputs are unchanged and the cache remains valid. **Per-project plugins** supply how raw artifacts are located and parsed; each project **points to its plugin via project configuration**, and the core tool loads that entry and orchestrates invocation and shared conventions. This is the prerequisite for every other post-processing outcome.

**Why this priority**: Without reliable parsing and unification, plots, KPIs, and downstream exports are wrong or incomplete. This story delivers a minimal viable post-processing capability on its own.

**Independent Test**: Can be fully tested by supplying representative artifact bundles from at least two distinct result shapes and verifying that each is parsed into the same conceptual model with correct field mapping and explicit handling of missing or malformed fragments; and by supplying **multiple labeled test results** in one bundle and verifying each remains **distinguishable** after parsing.

**Acceptance Scenarios**:

1. **Given** artifact bundles from multiple completed test runs, **When** the post-processing tool ingests them, **Then** it produces a unified representation that preserves run identity and key measurements needed for analysis
2. **Given** **multiple test results** in the inputs (with labels identifying aspect under test—for example model or load generator), **When** parsing runs, **Then** each test result is represented distinctly and its labels are available for filtering, comparison, and KPI linkage
3. **Given** a result file with an unexpected or partial structure, **When** parsing runs, **Then** the tool reports what was understood and what was skipped or defaulted without silent data loss for fields that were present
4. **Given** multiple runs that belong to the same logical comparison (for example same scenario, different build), **When** users select those runs, **Then** the tool can align them for side-by-side or sequential analysis
5. **Given** a successful parse whose **cache** is still valid for the same inputs, **When** the user requests a downstream action that only needs the unified representation (for example regenerating a report), **Then** the tool **reloads from cache** and does **not** repeat full parsing unless the user forces refresh or the cache is invalid

---

### User Story 2 - Generate Plots and HTML Reports (Priority: P2)

Stakeholders can generate human-readable summaries: charts for trends and comparisons, plus HTML reports suitable for sharing in reviews or attaching to tickets. **Plot and report definitions are project-scoped** (via plugins), while sharing reusable fragments across projects is supported when appropriate. Reports reflect the unified parsed results, not raw files only.

**Why this priority**: Visual and narrative reporting turns parsed data into decisions; it is the main day-to-day deliverable for many teams after a test completes.

**Independent Test**: Can be fully tested by running the tool on a fixed fixture set and verifying that generated plots and HTML contain expected sections, titles, and values consistent with the unified model.

**Acceptance Scenarios**:

1. **Given** unified results for one or more runs, **When** a user requests a standard report, **Then** the tool produces HTML that includes run identification, key metrics, and at least one visual summary where data supports it
2. **Given** comparable runs, **When** a user requests a comparison-oriented report, **Then** the tool highlights differences using the same scales and labels where applicable
3. **Given** a large result set, **When** reports are generated, **Then** generation completes within an acceptable time for interactive use (see Success Criteria)

---

### User Story 3 - Well-Defined KPIs: Export, Regression, and Dashboard (Priority: P3)

Teams can define **which** KPIs apply and how values are derived from parsed data **per project**, but the **canonical KPI record format** used for export, index, regression, and dashboard is **identical across all projects**. Stable names, units, and interpretation (whether higher or lower is better) follow that single format.

**Why this priority**: KPIs connect engineering work to operational visibility; one shared interchange format avoids conflicting numbers across tools, while plugins allow project-specific catalogs and computations.

**Independent Test**: Can be fully tested by defining a small KPI catalog, recording values for two builds, exporting them, running a regression check that flags a deliberate degradation, and confirming the dashboard shows the same values and status as the regression output.

**Acceptance Scenarios**:

1. **Given** a KPI catalog and measured values for a run, **When** export runs, **Then** records are written in a form suitable for the organization’s search index (see Assumptions) with enough fields to filter by run, scenario, and KPI identity
2. **Given** a current run and a historical baseline, **When** regression analysis runs, **Then** the tool flags KPIs that exceed agreed thresholds or directional expectations and attributes them to the correct KPI names
3. **Given** exported or locally stored KPI history, **When** a user opens the dashboard, **Then** they can see trends and current values that match the same KPI definitions used for export and regression

---

### User Story 4 - Structured JSON for AI Agent Performance Evaluation (Priority: P4)

Evaluators and automation can emit well-structured JSON documents that summarize agent-oriented performance (quality, latency, task success, safety-related signals as applicable) so that downstream AI evaluation pipelines or review tools can consume them without ad hoc scraping.

**Why this priority**: Supports standardized evaluation of AI agent behavior; valuable but narrower than core KPI and reporting flows.

**Independent Test**: Can be fully tested by running the tool on a fixture that includes agent-relevant metrics and validating the JSON against the published schema shape and required fields.

**Acceptance Scenarios**:

1. **Given** unified results that include agent evaluation inputs, **When** JSON export for AI evaluation is requested, **Then** output conforms to the agreed structure and includes run identifiers and version metadata
2. **Given** missing optional agent metrics, **When** JSON is generated, **Then** required fields are still present and optional gaps are explicit rather than omitted ambiguously

---

### User Story 5 - Export File Artifacts to S3 and MLflow (Priority: P2)

Operators and automation can **publish file outputs** from post-processing—generated plots, HTML bundles, structured JSON exports on disk, and other **plugin-declared file artifacts**—to **more than one external system** without running separate ad hoc upload scripts for each. At minimum, the engine MUST support **S3-compatible object storage** and **MLflow** as artifact destinations; configuration MUST supply connection parameters (for example bucket/prefix for S3, tracking URI and experiment/run context for MLflow) through environment variables, project configuration, or CLI in a way consistent with FR-014. When multiple backends are enabled, each upload MUST be **attributed** clearly in logs and exit status so partial success is visible.

**Why this priority**: Teams already store run evidence in object storage and experiment trackers; first-class export avoids duplicate tooling and keeps provenance aligned with unified results and labels.

**Independent Test**: Can be fully tested with local or mock S3 and MLflow endpoints: after a `visualize` (or equivalent file-producing step), **file export** places expected objects under the configured prefix and registers artifacts in MLflow without corrupting unrelated runs.

**Acceptance Scenarios**:

1. **Given** generated file artifacts under a known output layout, **When** the operator requests export to **S3** with valid credentials and bucket/prefix, **Then** objects appear at the expected keys and include metadata or tags sufficient to correlate with run identity and distinguishing labels where applicable
2. **Given** MLflow is configured with a valid tracking URI and experiment/run binding, **When** file export runs, **Then** artifacts are registered under the correct run (or equivalent MLflow construct) and are retrievable through MLflow APIs
3. **Given** both **S3** and **MLflow** are enabled, **When** export runs, **Then** both backends receive the intended files unless one fails, in which case the tool reports per-backend status and does not claim full success ambiguously
4. **Given** a backend is temporarily unavailable, **When** export runs, **Then** the failure is actionable (clear error, optional retry policy if specified) and other enabled backends may still complete if the design allows independent uploads

---

### Edge Cases

- What happens when two runs use different naming conventions for the same logical KPI?
- What happens when two **projects** register overlapping KPI identifiers or incompatible plugin defaults?
- How does the tool behave when artifact size or cardinality is large enough to risk timeouts or memory pressure?
- What occurs when the search index or dashboard is temporarily unavailable during export or visualization?
- How are ties or negligible changes handled in regression rules (noise versus signal)?
- What happens when HTML or plot generation fails for one chart but others succeed?
- What happens when a **project plugin** fails partially (for example parse succeeds, one plot fails): are other projects or other steps in the same run affected?
- What happens when **project configuration** references a missing, invalid, or unloadable plugin path?
- What happens when **multiple test results** carry **overlapping or conflicting labels**, or when labels needed to distinguish them are **missing**?
- What happens when two result files use the **same label keys** with different semantics?
- What happens when the **parse cache** is **missing**, **corrupted**, or **stale** relative to source artifacts?
- What happens when **source artifacts change** after a cache was written?
- What happens when two operators or jobs **write the same cache** concurrently?
- What happens when **S3** or **MLflow** credentials are missing, expired, or scoped too narrowly for the requested paths?
- What happens when **multi-backend export** partially succeeds (for example S3 completes, MLflow fails): what is the overall status and how are reruns handled idempotently?
- What happens when **artifact paths collide** in the target bucket or MLflow run (same key or artifact name)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept multiple heterogeneous test result artifacts and produce a unified, documented internal representation suitable for downstream steps. When **multiple test results** appear in the inputs, the system MUST parse each distinctly and MUST **preserve distinguishing labels** (and any required identity fields) so facets such as **version**, **deployment flavor**, **model**, **load generator**, and analogous aspects remain **separable** in the unified model and in downstream plots, reports, KPIs, and exports
- **FR-002**: System MUST support a **project-scoped plugin model** so each project can define how artifacts are located, parsed, and turned into unified results, while allowing **shared reusable building blocks** across projects where appropriate. **Plugin module resolution** MUST NOT use implicit workspace scanning to discover plugin code. The **project post-processing manifest** (configuration file for the project) MUST declare **`plugin_module`** (or an equivalent importable entry reference). The operator MAY pass **`--plugin`** on the CLI; when provided, it **overrides** the manifest for that invocation. When **no** manifest-provided module and **no** `--plugin` yield a resolvable module, the system MUST fail per FR-014
- **FR-003**: System MUST generate static visual summaries (plots) derived from unified results using **project-supplied plot definitions** where the underlying data supports visualization
- **FR-004**: System MUST generate HTML reports that identify runs, summarize outcomes, and support comparison when multiple runs are selected, using **project-supplied report definitions** where applicable
- **FR-005**: System MUST support a catalog of KPI definitions including stable identifiers, human-readable names, units, and whether higher or lower values are better; **catalog content and derivations are project-specific**, but records conform to the **single canonical KPI format** (FR-007)
- **FR-006**: System MUST compute KPI values from unified results and associate them with run, project, and scenario context, **and with distinguishing labels (facet)** when KPIs apply to a specific test result among several
- **FR-007**: System MUST enforce one **canonical KPI interchange format** shared by **all** projects for export, indexing, regression comparison, and dashboard display; projects MUST NOT introduce alternate shapes for the same logical KPI record
- **FR-008**: System MUST export KPI records in a form consumable by the organization’s centralized search and analytics index for discovery and filtering
- **FR-009**: System MUST support regression analysis that compares current KPI values to historical values using the same KPI definitions and surfacing regressions according to configurable rules
- **FR-010**: System MUST provide a dashboard experience for visualizing KPI trends and current values consistent with exported KPI data
- **FR-011**: System MUST produce structured JSON suitable for AI agent performance evaluation, including schema-level documentation of required and optional fields; **project plugins** supply project-relevant content within the shared schema expectations
- **FR-012**: System MUST validate outputs where schemas apply and surface validation errors clearly to the operator
- **FR-013**: System MUST treat sensitive content in artifacts according to organization policy (for example redaction or exclusion from exports when configured)
- **FR-014**: System MUST surface clear, actionable errors when project configuration omits a plugin reference, or when the referenced plugin cannot be loaded or does not satisfy required contracts
- **FR-015**: System MUST propagate **distinguishing labels** from source test results into the unified representation and into **canonical KPI records** (and other exports) so operators can filter and compare by facet consistently end to end
- **FR-016**: System MUST **emit a parse cache** (persistent file or equivalent) capturing the **unified representation** after parsing, and MUST **reload** from that cache when it is **valid** for the current inputs so that **full parsing is not repeated** unnecessarily; the system MUST define **cache validity** (for example input fingerprints, versions, or timestamps) and MUST **invalidate or refresh** when sources change or when the operator requests a full re-parse
- **FR-017**: System MUST support exporting **file artifacts** (generated plots, HTML report bundles, structured JSON files on disk, and other paths **designated by the project plugin** as exportable) to **multiple backends** selected by configuration or operator intent. **S3-compatible object storage** and **MLflow** MUST be supported; the system MUST allow **one or more** backends to run in a single export operation. Per-backend outcomes MUST be **reported distinctly** (success, failure, skipped); a failure on one backend MUST NOT be presented as overall success unless explicitly defined by a documented policy. File export MUST respect **sensitive content** rules (FR-013) for uploaded objects

### Key Entities

- **Test run**: A single executed test instance with identity, timing, build or version references, and links to source artifacts; MAY encompass **multiple labeled test results** when the harness emits several facets in one run
- **Test result (facet)**: One of possibly **several** parsed outcomes within a run’s inputs, distinguished by **distinguishing labels** (see below); MUST NOT be collapsed with sibling test results unless the operator explicitly requests aggregation
- **Distinguishing labels**: Labels attached to each test result identifying **which aspect was under test** (for example software **version**, **deployment flavor**, **model**, **load generator**); used to separate, filter, compare, and attribute KPIs
- **Unified result record**: Normalized capture of metrics and outcomes after parsing, independent of original file layout; MUST retain association to **distinguishing labels** (or equivalent facet identity) when multiple test results exist
- **Parse cache**: Persistent artifact produced by the parser holding **reloadable** unified results for a bounded set of inputs; used to **avoid repeating full parse** when still valid
- **Post-processing plugin reference**: Entry declared in **project configuration** (for example path or id) that points to the **project post-processing plugin** implementation
- **Project post-processing plugin**: Project-scoped extension that contributes artifact location rules, parsing, plot and report definitions, KPI catalog content, and optional shared building blocks used across projects; **loaded via the post-processing plugin reference**
- **KPI definition**: Stable identifier, description, unit, optimization direction, and applicability scope; **which KPIs exist per project** is plugin/catalog content, subject to global uniqueness rules where required
- **Canonical KPI record**: The single interchange shape for KPI data used for export, index, regression, and dashboard (must not vary by project)
- **KPI value**: A measured value for a KPI definition bound to a test run and optional scenario dimensions, **serialized only as canonical KPI records**
- **Report bundle**: Generated HTML, embedded or linked visuals, and metadata for sharing
- **Regression finding**: A KPI-level outcome describing change versus baseline with severity or classification
- **AI evaluation payload**: Structured JSON document for downstream evaluation of agent performance
- **File artifact export**: A set of files (generated or plugin-listed) intended for upload to external storage; distinct from **canonical KPI records** streamed to the search index (FR-008), though a plugin MAY include KPI files in export if declared
- **File export backend**: A pluggable destination for file artifacts (for example **S3**, **MLflow**); configuration includes credentials and path or run binding

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a standard benchmark-sized fixture set, operators can produce a unified representation and an HTML report in under 10 minutes on typical analyst hardware
- **SC-002**: At least 95% of KPI values shown on the dashboard match the values in the corresponding export for the same run under normal conditions
- **SC-003**: Regression detection correctly classifies deliberate degradations and non-regressions on a fixed golden dataset in at least 90% of controlled cases
- **SC-004**: AI evaluation JSON outputs pass structural validation for 100% of runs that complete without user-canceled configuration errors
- **SC-005**: Three-quarters of surveyed internal users report that they can find a given run’s KPIs via the search index or dashboard within 5 minutes of training
- **SC-006**: For a fixed fixture, a **second** end-to-end pass that only needs the unified model and **reuses a valid parse cache** completes in **less than half** the wall-clock time of the **first** full parse-and-report pass on the same hardware profile
- **SC-007**: On a representative fixture, **multi-backend file export** (S3 and MLflow both enabled) completes without manual intervention when valid credentials and endpoints are provided, and produces **observable per-backend success** in operator output

## Assumptions

- “OpenSearch” in the original request is treated as the organization’s preferred search index for KPI export; equivalent index products are acceptable if they meet FR-008
- **Plugin packaging** follows the repository’s multi-project layout and sharing conventions (projects may expose shared library-style components for reuse); **which** plugin runs for a project is always determined by **project configuration**, not by scanning the tree
- Artifact formats are those produced by the existing test harness or documented partners; truly novel formats may require follow-up parsers
- Dashboard and export credentials and network access are provided by the platform team; this specification does not mandate a particular hosting model
- AI agent evaluation JSON schema will be versioned and kept backward compatible within a major version where possible
- **Parse cache** storage location, on-disk format, and exact invalidation algorithm are implementation choices; the specification requires **existence**, **reload behavior**, and **correctness when valid** (see FR-016)
- **S3** access uses the organization’s standard credential mechanism (for example IAM roles, environment variables, or vault-injected keys); **MLflow** uses a configurable **tracking URI** and standard MLflow client semantics; exact SDK or library choices are implementation details
