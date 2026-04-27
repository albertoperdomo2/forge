# Requirements Writing Quality Checklist: Artifact Post-Processing Tool

**Purpose**: Unit tests for **requirements writing** for this feature—evaluating completeness, clarity, consistency, and measurability of what is specified (not implementation behavior).  
**Created**: 2026-04-16  
**Feature**: [spec.md](../spec.md)  
**Related context**: [plan.md](../plan.md), [contracts/](../contracts/) (used only where cross-document consistency is in scope)

**Defaults applied** (no user steering provided): **Standard** depth; **PR reviewer** audience; focus on **plugin/KPI/caching** requirements plus **cross-doc** alignment (spec vs plan vs contracts).

**Note**: Each `/speckit.checklist` run creates a **new** checklist file; older checklists in this folder are retained unless manually removed.

---

## Requirement Completeness

- [ ] CHK001 Are **parse cache validity**, **invalidation**, and **operator-forced refresh** specified with enough precision that two readers would not adopt incompatible rules? [Clarity, Spec §FR-016]
- [ ] CHK002 Are **regression analysis rules** (thresholds, noise vs signal, ties/negligible changes) captured as **normative requirements**, not only as open questions? [Gap, Spec §FR-009, Spec §Edge Cases]
- [ ] CHK003 Is the **canonical KPI interchange format** described in **requirements** with sufficient field-level obligations (not delegated entirely to external artifacts)? [Completeness, Spec §FR-007]
- [ ] CHK004 Are **dashboard** expectations beyond consistency with exported KPIs documented to a level that supports acceptance without filling gaps ad hoc? [Gap, Spec §FR-010]
- [ ] CHK005 Are **plugin contract obligations** implied by FR-014 enumerated or referenced so “required contracts” is not purely circular? [Completeness, Spec §FR-014]
- [ ] CHK006 Does the spec define **project configuration** semantics (what must be present, what errors mean) in prose aligned with FR-002 and FR-014? [Completeness, Spec §FR-002, Spec §FR-014]
- [ ] CHK007 Are **historical baseline acquisition** and **regression inputs** (for example import/analyze boundaries) specified in **requirements**, or acknowledged as deferred with rationale? [Gap, Plan §Command Matrix, Spec §FR-009]
- [ ] CHK008 Are **AI evaluation JSON** versioning and compatibility expectations carried from **Assumptions** into **normative** requirements where appropriate? [Completeness, Spec §FR-011, Spec §Assumptions]

## Requirement Clarity

- [ ] CHK009 Is the **unified internal representation** bounded clearly enough that scope (what must be represented vs optional) is not left to inference? [Clarity, Spec §FR-001]
- [ ] CHK010 Are **distinguishing labels** specified with minimum expectations (shape, keys, uniqueness) so “labels” cannot mean incompatible things across FRs? [Clarity, Spec §FR-001, Spec §FR-015]
- [ ] CHK011 Is **“project configuration”** tied to a concrete artifact class or location pattern, or is it intentionally abstract—and is that abstraction stated explicitly? [Ambiguity, Spec §FR-002, Spec §Assumptions]
- [ ] CHK012 Is **SC-001** (“under 10 minutes”) anchored to **hardware profile** or workload definition in requirements? [Clarity, Spec §SC-001]
- [ ] CHK013 Is **SC-006** (“less than half”) defined with **measurement boundaries** (same fixture, same hardware profile, what counts as “second pass”)? [Clarity, Spec §SC-006]
- [ ] CHK014 Are **index/dashboard unavailability** scenarios classified as **normative** failure semantics or explicitly out of scope? [Clarity, Spec §Edge Cases, Spec §FR-008]
- [ ] CHK015 Is **sensitive content handling** (FR-013) specified with **policy attachment points** (configuration sources, redaction scope) vs examples only? [Clarity, Spec §FR-013]

## Requirement Consistency

- [ ] CHK016 Is **manifest-only plugin discovery** (FR-002) reconciled with **CLI `--plugin` module path** planning input in **requirements** (single authoritative story)? [Consistency, Conflict, Spec §FR-002, Plan §Structure Decision]
- [ ] CHK017 Are **label propagation** rules aligned across FR-001, FR-006, FR-015 without contradictory implications for KPI attribution? [Consistency, Spec §FR-001, Spec §FR-006, Spec §FR-015]
- [ ] CHK018 Do **success criteria** that use percentages or surveys define **populations and denominators** (“same run”, “normal conditions”, “controlled cases”) unambiguously? [Consistency, Spec §SC-002, Spec §SC-003]
- [ ] CHK019 Are **cross-project KPI identifier** conflicts addressed with **normative** global rules, not only as edge-case questions? [Consistency, Spec §Edge Cases, Spec §FR-005]
- [ ] CHK020 Does the spec use **consistent terminology** for **multiple test results / facets / runs** across user stories and FRs? [Consistency, Spec §User Story 1, Spec §FR-001]

## Acceptance Criteria Quality

- [ ] CHK021 Can **SC-002** be measured objectively as written (what counts as a “match”, what fields are compared)? [Measurability, Spec §SC-002]
- [ ] CHK022 Is **SC-005** framed as a **requirements acceptance gate** vs organizational survey work (roles and timing explicit)? [Measurability, Spec §SC-005]
- [ ] CHK023 Do **User Story acceptance scenarios** state **observable outcomes** that can be adjudicated without implementation detail? [Acceptance Criteria, Spec §User Scenarios & Testing]
- [ ] CHK024 Is **SC-004** scoped so “100% validation pass” excludes/excludes-not ambiguous failure classes (for example operator cancelation vs data errors)? [Clarity, Spec §SC-004]

## Scenario Coverage

- [ ] CHK025 Are **end-to-end obligation threads** (labels → unified model → KPI → export → dashboard/regression) reflected coherently across FRs, not only distributed fragments? [Coverage, Spec §FR-001, Spec §FR-007–FR-010, Spec §FR-015]
- [ ] CHK026 Are **alternate operator intents** (reuse valid cache, invalidate cache, selective re-run) captured as explicit requirements where FR-016 implies them? [Coverage, Spec §FR-016]
- [ ] CHK027 Are **partial parse / malformed artifact** expectations stated **normatively** (beyond illustrative acceptance scenarios)? [Coverage, Spec §US1, Spec §FR-012]
- [ ] CHK028 Are **cache missing/corrupt/stale** paths promoted from Edge Cases to **requirements** where user-visible behavior must be guaranteed? [Coverage, Gap, Spec §Edge Cases, Spec §FR-016]
- [ ] CHK029 Does the spec state whether **multi-project orchestration** in one invocation is in scope, given partial-failure edge cases? [Coverage, Spec §Edge Cases]

## Edge Case Coverage

- [ ] CHK030 Are **overlapping/conflicting/missing labels** given **normative** resolution requirements, or is deferral explicit? [Edge Case, Spec §Edge Cases]
- [ ] CHK031 Is **concurrent cache access** explicitly deferred, prohibited, or required to be safe with stated model? [Edge Case, Gap, Spec §Edge Cases]
- [ ] CHK032 Are **partial visualization failures** (one chart/report fails) required to be specified at the requirements level? [Edge Case, Spec §Edge Cases]
- [ ] CHK033 Is **plugin partial failure isolation** defined with clear boundaries (single project vs whole run)? [Edge Case, Spec §Edge Cases]

## Non-Functional Requirements

- [ ] CHK034 Are **large artifact / high cardinality** risks reflected in **requirements** beyond Edge Case questions (for example bounds, streaming expectations)? [Gap, Spec §Edge Cases]
- [ ] CHK035 Are **security and credential handling** obligations for export and index access stated at the requirements level, not only via platform assumptions? [Gap, Spec §FR-008, Spec §FR-013, Spec §Assumptions]

## Dependencies & Assumptions

- [ ] CHK036 Are **platform-provided credentials and network access** (Assumptions) translated into **requirement-level** obligations where operator-facing failure semantics matter? [Dependency, Spec §Assumptions]
- [ ] CHK037 Is **“equivalent index products”** for FR-008 given **acceptance-relevant** compatibility criteria? [Clarity, Spec §FR-008, Spec §Assumptions]

## Ambiguities & Conflicts

- [ ] CHK038 Does FR-012 specify **which deliverables** are schema-validated (KPIs, AI JSON, HTML bundles, all outputs)? [Ambiguity, Spec §FR-012]
- [ ] CHK039 Is the relationship between **Edge Cases** and **normative FRs** clear (which items must be resolved before requirements are implementation-ready)? [Traceability, Spec §Edge Cases]
- [ ] CHK040 Do **contracts** (`contracts/cli.md`, `contracts/kpi_record.md`, `contracts/test_labels.md`) **extend** the spec without **contradicting** FRs (for example CLI-only behaviors not reflected in requirements)? [Consistency, Conflict, Spec §FR-001–FR-016, contracts/]

## Notes

- Check items off as reviewed: `[x]`
- Record findings inline (for example “resolved in spec §…”, “defer to design doc …”)
- Prefer updating **spec.md** (or explicit ADRs) when a CHK item exposes a true gap—this checklist does not replace change control
