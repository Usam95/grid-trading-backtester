# Architecture and quality requirements

Status: accepted cross-cutting constraint; measurable thresholds continue in the relevant Wayfinder tickets  
Applies to: the first MVP and every later increment built on it

## Intent

The first MVP is small in supported behavior, not disposable in structure. It must be safe and economical for one operator while establishing stable boundaries that allow later strategies, venues, symbols, and deployment shapes to be added without rewriting the trading core or invalidating existing behavior.

“Maintainable”, “extensible”, “understandable”, and “best practice” are not accepted as self-proving labels. Each must be supported by an explicit responsibility boundary, an executable check, a reviewable architecture decision, or a measurable quality scenario.

This requirement does **not** mean building every future feature, a generic plugin platform, distributed services, or high availability in the MVP. It means preserving the identified extension seams and proving that the simple implementation respects them.

## Engineering-standard anchors

The system specification and implementation shall use:

- ISO/IEC 25010 quality characteristics as a checklist for functional suitability, reliability, performance efficiency, compatibility, usability, security, maintainability, and portability;
- ISO/IEC/IEEE 42010-style architecture descriptions: named stakeholders and concerns, explicit views and boundaries, traceable decisions, and recorded rationale;
- RFC 2119 meanings for `MUST`, `MUST NOT`, `SHOULD`, and `MAY` in normative specifications;
- OWASP application-security guidance and least privilege for the operator UI, API credentials, secrets, dependencies, and deployment boundary;
- reproducible-build, schema-migration, semantic-versioning, test-pyramid, property-testing, contract-testing, and observability practices where they address a concrete system risk.

These are relevant baselines, not a claim of formal certification or compliance with every clause of every standard. Any deliberate exception must be documented with its risk, compensating control, owner, and review condition.

## Mandatory architecture principles

### Safety and correctness dominate convenience

Unknown order, asset, accounting, market-continuity, or recovered state fails closed. No UI, adapter, retry, migration, or optimization may bypass the canonical accounting, reconciliation, risk, lifecycle, or command-authorization rules.

### One deterministic domain core

Grid decisions, accounting transitions, risk decisions, and lifecycle consequences are expressed in canonical domain types and are independent of network, wall-clock, database, UI, Binance SDK, and Azure APIs. Backtest, replay, paper, and live modes reuse this core rather than reimplementing strategy semantics.

### Explicit boundaries and dependency direction

The architecture separates at least the trading engine, online runtime, operator studio, venue integration, persistence/data, and infrastructure concerns. Dependencies point toward stable domain contracts; infrastructure and venue details implement ports at the outside. Circular dependencies, hidden global state, and business decisions in controllers, database code, or exchange adapters are prohibited.

### Evidence before mutable projections

Canonical events, immutable configuration identities, dataset manifests, command identities, and authoritative venue evidence are durable sources of explanation. Read models, dashboards, metrics, reports, and caches are rebuildable projections and must not silently become competing authorities.

### Make invalid and ambiguous states explicit

Typed states and validated value objects represent order identity, quantities, fees, allocation, lifecycle, safety posture, reconciliation, dataset identity, and configuration version. Boolean flag combinations, unvalidated dictionaries, binary floating-point asset accounting, and “best effort” inference at safety boundaries are prohibited.

### Evolution is additive and migration-controlled

Persisted events, commands, configurations, manifests, and projections have explicit schema versions. Compatible readers, deterministic migrations, backup/restore tests, and rollback rules are required before a release changes durable formats. Historical evidence is never rewritten in place.

### Simplicity with deliberate seams

The MVP uses the smallest architecture that satisfies the safety and quality scenarios. An abstraction is justified by a known variation point, an external boundary, deterministic testing, or isolation of a material risk. Speculative frameworks, premature microservices, and duplicate “temporary” engines are rejected.

### Operability is part of behavior

Every material decision and state transition is attributable through stable identities across the event journal, diagnostic logs, metrics, alerts, and operator views. Restart, reconciliation, backup restoration, degraded operation, emergency action, and evidence export are designed and tested workflows, not manual archaeology.

## Required extension seams

The MVP architecture shall support these later increments without modification to unrelated domain modules:

1. **Adaptive or dynamic grid:** add a separately versioned strategy family behind the canonical decision contract; reuse market events, accounting, risk, execution, replay, and promotion infrastructure. It receives independent validation and cannot inherit static-grid evidence.
2. **Interactive Brokers:** add a venue adapter and venue-capability mapping behind the execution and market-data ports. Binance-specific states and filters remain in its anti-corruption boundary; the canonical model is extended explicitly where a genuinely shared concept is discovered.
3. **Additional strategies:** add strategy-specific configuration and decision behavior without copying ledgers, reconciliation, risk, journal, or execution state machines.
4. **Multiple grids or symbols:** introduce additional isolated run/allocation instances without changing single-run semantics or relying on process-global trading state.
5. **Compounded sizing:** add a versioned sizing policy without changing fill accounting or retroactively changing a run's immutable configuration.
6. **Different persistence or deployment:** replace outside adapters without importing Azure, SQLite, or filesystem concepts into the domain core.

These are compatibility scenarios, not MVP features. The first implementation may have only one strategy, venue, run, database, and deployment.

## Quality requirements and acceptance evidence

| Quality | Required outcome | Minimum architectural evidence |
| --- | --- | --- |
| Functional correctness | Every admitted event has one deterministic, invariant-checked consequence. | Unit, property, state-machine, accounting-invariant, and golden replay tests. |
| Reliability and recovery | A crash, duplicate, late event, unknown command outcome, stream gap, or dependency outage cannot create duplicate exposure or an unsafe automatic resume. | Fault-injection and restart/reconciliation acceptance cases. |
| Maintainability | A module has one coherent responsibility, a documented public contract, controlled dependencies, and no duplicate domain rule. | Automated dependency checks, contract tests, complexity/coverage review, and architecture review. |
| Extensibility | A known extension uses its declared seam without editing unrelated core responsibilities. | Compile-time contracts plus at least one test double/reference adapter or characterization test for each critical port; later increments must include change-impact evidence. |
| Understandability | A new maintainer can trace market evidence to decision, command, fill, accounting, risk, and displayed result. | Context map, glossary, architecture views, ADRs for hard-to-reverse trade-offs, examples, and stable correlation identities. |
| Testability | Domain behavior runs deterministically without Binance, Azure, a real clock, or a production database. | In-memory/fake port tests, seeded simulations, deterministic timers, and hermetic fixtures. |
| Security | Compromise impact is limited and sensitive material is neither exposed nor logged. | Threat model, least-privilege checks, secret/redaction tests, dependency scanning, authenticated authorization tests, and tested credential rotation. |
| Performance efficiency | Live safety deadlines and research throughput are met inside declared CPU, memory, storage, and network budgets. | Benchmarks and resource-budget tests on the selected minimum Azure profile; no correctness trade-off to meet cost. |
| Portability | Domain and validation logic are independent of OS, cloud, UI, and venue SDK. | Clean dependency boundaries and CI tests of domain packages without infrastructure imports. |
| Reproducibility | A promoted result is reconstructible from identified code, configuration, schemas, dataset, venue rules, costs, and seeds. | Immutable manifests, build provenance, environment lock, and result fingerprints. |
| Observability and auditability | Every material action, refusal, anomaly, and operator intervention is explainable without secrets. | Journal completeness tests, structured-log schema tests, alert tests, and deterministic incident replay. |
| Compatibility and change safety | A release cannot silently change promoted decisions, durable evidence, or recovery behavior. | Versioned contracts, migration tests, replay-diff gates, release approval, backup/restore, and rollback rehearsal. |

Exact numerical thresholds—coverage exceptions, complexity budgets, performance deadlines, recovery objectives, retention, alert timing, dependency severity, and release gates—are resolved by the observability, runtime, Azure, security, and verification/release tickets. Until those values are accepted, implementations may not interpret an unspecified threshold as permission to weaken a safety property.

## Architecture fitness rules for the MVP

The implementation plan must include automated checks that:

- domain packages do not import UI, web framework, database driver, exchange SDK, filesystem, or cloud-provider packages;
- the same canonical event fixtures produce the same decision/state fingerprints in simulation, replay, paper, and live-decision harnesses;
- every venue command passes through one authorization/risk boundary and has a durable managed identity;
- every durable schema and configuration has a version and a tested forward migration;
- forbidden dependency cycles and process-global mutable trading state fail the build;
- duplicate accounting, sizing, fill, lifecycle, or reconciliation rules outside their owning module are rejected in review;
- public contracts and material failure modes have executable contract or acceptance tests;
- resource benchmarks and security checks run as release gates at the frequency defined by the verification specification.

## Change rule

Every proposed feature must identify the owning context, changed public contracts, durable-schema effect, safety and accounting effect, validation evidence affected, migrations, observability additions, tests, and rollback path. If a change crosses several unrelated modules for a capability assigned to one declared extension seam, that is architecture feedback: the boundary must be reviewed before the feature is merged.

## Consequences

- Initial MVP work includes contracts, documentation, tests, versioning, and migration discipline that a throwaway prototype would omit.
- Later features should be cheaper and safer because core responsibilities are not duplicated or coupled to Binance, SQLite, Azure, or the static strategy.
- Some future needs will still require deliberate contract evolution; “extensible” does not promise zero changes.
- The single-node Azure deployment may stay operationally simple while the software remains modular. Modular architecture does not require microservices.

## Declined interpretations

- **Throw away and redesign after MVP:** declined because live evidence, accounting history, and safety behavior would not transfer reliably.
- **Implement all future capabilities now:** declined as overengineering and an unnecessary expansion of safety-critical scope.
- **Generic plugin framework from day one:** declined until more than one real implementation demonstrates the required variation.
- **Microservices for architectural purity:** declined for the first deployment; they add failure modes and operating cost without solving the single-operator requirement.
- **A checklist claiming every best practice:** declined because practices can conflict; requirements must trace to this system's risks and measurable evidence.
