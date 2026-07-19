Label: wayfinder:map

## Destination

A comprehensive, implementation-ready specification for a single-operator grid-trading workstation built on `gridlab` and `gridlab-studio`: trustworthy research, deterministic replay, staged Binance Spot paper/live operation, mandatory promotion gates, and a minimal-cost Azure deployment.

## Notes

- Planning only: tickets resolve decisions and produce specifications; implementation begins after the map is complete.
- Consult `wayfinder`, `grilling`, `domain-modeling`, and the context documents linked from `CONTEXT-MAP.md`.
- Canonical foundation: `gridlab` and `gridlab-studio`. Audit all other projects before archiving; migrate useful engine behavior, tests, documentation, live-runtime concepts, and the preferred SaaS UI patterns.
- Product scope: personal/professional single operator; Binance Spot inventory trading using owned assets only; one active live grid on one symbol initially.
- Strategy scope: one static arithmetic/geometric grid for the validated MVP. Adaptive strategies require later independent validation.
- Modes share one deterministic strategy decision core. Use fast candle simulation for research and recorded-event replay for promotion evidence.
- Online progression: live-data simulation, Binance test environment where representative, then tightly limited real money. Mandatory gates plus explicit manual activation.
- Observability: append-only trading event journal, structured diagnostic logs, metrics, alerts, and targeted market/order-book retention.
- Deployment: the accepted B1ms-first single-node Azure profile uses durable local state, verified ZRS Blob recovery/evidence, frozen recovery, measured resize gates, and no application-level HA.
- Architecture quality: the MVP is small in behavior but production-evolutionary in structure. It must satisfy the [cross-cutting architecture and quality requirements](../../analysis/architecture-quality-requirements.md), preserve declared seams for later strategies, venues, symbols, and deployment adapters, and prove maintainability, extensibility, understandability, safety, and change compatibility with measurable evidence.
- Decision records retain the recommendation, examples, consequences, and declined alternatives supplied during operator review; they must not record only the selected option number.
- Decision questions show the recommended policy as numbered option 1 plus the realistic numbered alternatives and their trade-offs before asking the operator to choose; present only one decision topic at a time.
- Prevent backtest overengineering: an MVP capability must trace directly to a promotion gate, accepted invariant, parity requirement, or named failure scenario; preserve future seams without implementing speculative research-platform features.
- The [first MVP scope](../../analysis/mvp-scope.md) remains a concise product-boundary summary; the completed root specification and detailed decision records supersede its earlier investigation-status wording.
- The completed [comprehensive system specification](spec.md) is the implementation-ready root contract; detailed decision records remain normative for their full edge cases, rationale, alternatives, and test matrices.

## Decisions so far

<!-- Closed tickets are indexed here; answers live in their ticket files. -->

- [Audit codebase capabilities](issues/01-audit-codebase-capabilities.md) — Keep `gridlab` and `gridlab-studio` canonical; selectively reimplement legacy capabilities and SaaS UX, using old live code only as a requirements and failure-scenario source.
- [Define canonical domain and grid semantics](issues/02-define-canonical-domain-and-grid-semantics.md) — Use one immutable, open-ended static Spot grid contract across all modes: real obligation-backed bootstrap, fixed quote sizing, fill-driven cumulative rung pairing, bounded post-only execution, explicit lifecycle states, allocation isolation, and no exposure beyond approved bounds.
- [Specify simulation and execution parity](issues/03-specify-simulation-and-execution-parity.md) — Use a provenance-first tiered data architecture, typed deterministic event core, serialized replayable ordering, conservative promotion fills, exact domain replay equality, and canonical events for decision-changing deadlines.
- [Specify accounting invariants and reconciliation](issues/04-specify-accounting-invariants-and-reconciliation.md) — Use an exact allocation-isolated multi-asset subledger, paired provenance, source-exact arithmetic, fail-closed invariants, fact-specific authority, explicit reconciliation states, and evidence-preserving repair with operator control over material adjustments.
- [Research the current Binance Spot contract](issues/05-research-binance-spot-contract.md) — Design for post-only `LIMIT_MAKER`, exact live filters and native commissions, ambiguous command outcomes, distinct order/execution states, rate limits, finite streams and gap recovery, and a Testnet used only for protocol integration rather than fill evidence.
- [Specify risk model and safety state machine](issues/06-specify-risk-model-and-safety-state-machine.md) — Use allocation-isolated economic limits and a deterministic fail-closed posture overlay with conservative-equity guardrails, bounded maker/terminal execution, evidence-gated recovery, frozen restart, and a `250 USDT` first-live ceiling.
- [Specify validation and promotion gates](issues/07-specify-validation-and-promotion-gates.md) — Use nested chronological development, a sealed minute/event holdout, cross-symbol/regime/statistical/execution robustness gates, qualifying production paper plus Testnet, two-step activation, capped first-live probation, and impact-based requalification.
- [Specify event journal, observability, and retention](issues/08-specify-event-journal-observability-and-retention.md) — Use a decision-complete atomic journal/outbox, deterministic causal evidence and recovery, structured redacted diagnostics and bounded metrics/alerts, targeted exact market capture with tiered Blob retention, B1ms-first measured operation, 15-minute RPO/60-minute RTO with tested restores, graded evidence-protection failure behavior, and a requirement-based fault matrix.
- [Specify online runtime and recovery](issues/09-specify-online-runtime-and-recovery.md) — Use isolated single-writer runtimes around one deterministic core, durable ambiguity-aware commands and stream continuity, recurring authoritative reconciliation, frozen restart, authenticated operator control, measured B1ms scheduling/degradation, and a staged runtime acceptance handoff.
- [Audit and specify operator workflows](issues/10-audit-and-specify-operator-workflows.md) — Use one trust-separated Operator Studio with guided durable research, immutable evidence handoff, purpose-separated qualification, two-step live activation, a Command Canvas operating surface, case-based reconciliation/incidents, local verified audit analysis, contextual learning, and an incremental typed React/TypeScript/Vite frontend over authoritative FastAPI services.
- [Research minimal Azure deployment](issues/11-research-minimal-azure-deployment.md) — Use a B1ms-first three-process Germany West Central node with E6 LRS state, static IPv4, ZRS Blob recovery/evidence, Key Vault/managed identity, bounded monitoring, Bicep, locally qualified SSH-delivered releases, measured resize gates, application recovery, explicit acceptance, and a visible deferred-maintenance security exception.
- [Specify security and secret management](issues/12-specify-security-and-secret-management.md) — Use SSH-rooted single-operator access, typed Studio/Gateway control, Key Vault-only staged venue credentials, secret-safe structured evidence, locally locked/scanned releases, platform encryption, non-live work-laptop access, executable incident recovery, and explicit accepted residual risks.
- [Specify verification, release, and migration](issues/14-specify-verification-release-and-migration.md) — Use three risk-based evidence levels, owner-local and shared parity suites, strict critical-path architecture/quality gates, locked content-identified releases, immutable forward migrations, frozen side-by-side deployment, compatibility-driven rollback, executable extension seams, and measured B1ms qualification.
- [Synthesize system specification](issues/13-synthesize-system-specification.md) — Consolidate every resolved decision into one implementation-ready root contract with four context boundaries, 60 user stories, 33 quantitative acceptance criteria, staged delivery, evolutionary migration, and explicit deferred scope.

## Not yet specified

- None for this destination. Later extension behavior requires a new specification and independent evidence when selected.

## Out of scope

- Multi-user SaaS concerns: tenancy, billing, customer administration, and public product operation.
- Shorting, borrowing, leverage, margin, futures, options, and exchange margin-liquidation mechanics.
- Multiple simultaneous live grids or symbols in the first real-money milestone.
- Automatic activation of real-money trading.
- Application-level high availability for the initial Azure deployment.
- Continuous capture of the complete full-depth exchange feed.
- Interactive Brokers support, adaptive/dynamic grids, compounded sizing, and multiple simultaneous grids or symbols; only their extension seams are part of this destination.
