# TOPSAIL-NG Constitution

<!--
Sync Impact Report:
Version change: 1.0.0 → 1.0.1
Updated team reference: Red Hat Performance and Scale for AI Platforms team → PSAP team
Added sections:
- Core Principles (5 principles for performance testing framework)
- Quality Assurance section
- Development Workflow section
Templates requiring updates: ✅ none (minor clarification)
Follow-up TODOs: none
-->

## Core Principles

### I. CI-First Testing (NON-NEGOTIABLE)
All performance and scale tests MUST be automated and integrated into CI/CD pipelines. Tests must run consistently across environments without manual intervention. Every test scenario must be triggered automatically on code changes, scheduled intervals, or environment updates. Manual testing is reserved for exploratory scenarios only - all regression and validation tests must be CI-capable.

**Rationale**: Performance degradation must be caught immediately, not after deployment. Manual testing introduces variability and delays that compromise the reliability of performance assessments.

### II. Reproducible Results
Test environments, data sets, and execution conditions must be deterministic and version-controlled. Every test run must capture sufficient environmental context to enable exact reproduction. Baseline measurements, resource configurations, and test parameters must be immutable for a given test version. Random or time-dependent elements must be controlled with fixed seeds and timestamps.

**Rationale**: Performance results are meaningless without reproducibility. Variance in test conditions invalidates comparisons and trend analysis essential for performance validation.

### III. Observable Measurements
All tests must generate comprehensive telemetry including system metrics, application performance indicators, and resource utilization data. Observability extends beyond simple pass/fail to include latency distributions, throughput measurements, resource consumption patterns, and error rates. Every test execution must produce machine-readable results suitable for automated analysis and alerting.

**Rationale**: Performance testing without detailed observability provides insufficient data for root cause analysis and optimization decisions. Observable data enables trend detection and proactive performance management.

### IV. Scale-Aware Design
Test scenarios must validate performance characteristics across the full operational scale spectrum from minimal configurations to maximum expected load. Scale testing includes both horizontal scaling (increasing instances) and vertical scaling (resource allocation). Tests must identify performance cliff edges, resource bottlenecks, and scaling failure modes before production deployment.

**Rationale**: Performance characteristics often change non-linearly with scale. Systems that perform well at small scale can fail catastrophically at production scale without proper validation.

### V. AI Platform Specificity
Test frameworks must address the unique performance characteristics of AI workloads including GPU utilization, model inference latency, training throughput, and memory consumption patterns. Performance validation must account for AI-specific resource requirements, batch processing patterns, and distributed training behaviors specific to AI platforms.

**Rationale**: AI workloads have distinct performance profiles that differ significantly from traditional applications. Generic performance testing approaches miss critical AI platform performance characteristics.

## Quality Assurance

All test implementations must include automated validation of test correctness, measurement accuracy, and environmental consistency. Test frameworks must self-validate their measurement capabilities and report confidence intervals for all performance metrics. Performance test results must be cross-referenced with independent measurement tools to prevent measurement errors from corrupting performance assessments.

Quality gates include: measurement precision validation, environmental drift detection, test execution consistency verification, and result correlation analysis across measurement tools.

## Development Workflow

Test development follows test-driven development principles where performance requirements are defined first, tests are implemented to validate those requirements, and infrastructure is developed to support the tests. All performance test implementations must be peer-reviewed with focus on measurement validity, reproducibility verification, and CI integration correctness.

Code review requirements include: test scenario validation, measurement accuracy assessment, reproduction procedure verification, and CI pipeline integration testing. Complex test scenarios require demonstration of reproducibility across multiple environments before approval.

## Governance

This constitution supersedes all other performance testing practices and procedures. All performance test implementations, CI pipeline modifications, and measurement framework changes must comply with these principles. Amendments require documented justification, team approval, and migration plan for existing tests.

All code reviews and performance test proposals must verify constitutional compliance. Complexity that violates simplicity principles must be explicitly justified with technical rationale. Performance testing guidance and runtime development procedures are maintained in project documentation.

**Version**: 1.0.1 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23