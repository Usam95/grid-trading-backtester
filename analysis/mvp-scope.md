# First MVP scope

Status: accepted validation-first MVP boundary; remaining details tracked below  
Wayfinder map: [Comprehensive grid-trading system](../.scratch/comprehensive-grid-trading-system/map.md)

## Purpose

This document is the canonical readable summary of what belongs in the first MVP, why each capability belongs, what remains to be specified, and what is deliberately deferred. Detailed decisions continue to live in their Wayfinder tickets and linked specifications; this document presents them as one product boundary.

At the operator's request, every recommendation recorded here retains its behavior, examples, consequences, and declined alternatives rather than only an option number.

The MVP backtest is evidence-complete, not a generalized quantitative-research platform. Every included capability must trace to an accepted promotion gate, invariant, parity requirement, or named failure scenario and must be the smallest implementation that produces the required deterministic evidence. Speculative analytics and future-strategy behavior remain deferred behind deliberate extension seams.

## Accepted MVP boundary

Selected by the operator on 2026-07-14: build a vertically complete **validation-first MVP**. Its first deployable release supports fast historical backtesting, deterministic recorded-event replay, and a Production-Data Paper Run through one shared strategy decision core. The production Binance adapter and safety boundary are designed and tested as part of the MVP, but executable production order submission remains locked until mandatory promotion evidence and explicit operator activation exist.

This avoids two misleading products:

- a backtest-only tool that cannot demonstrate order-state, recovery, and reconciliation safety;
- a real-money-first bot that discovers accounting or runtime defects with actual capital.

Real-money activation is therefore a gated milestone of the same MVP architecture, not a separate engine and not an automatic deployment consequence.

## Architecture and engineering-quality boundary

The MVP is deliberately narrow in features but is not throwaway software. The accepted [architecture and quality requirements](architecture-quality-requirements.md) require one deterministic domain core, explicit context and adapter boundaries, inward dependency direction, durable evidence, typed state, controlled schema evolution, comprehensive automated verification, and observable/recoverable operation.

In particular, the first implementation must preserve declared seams for later adaptive strategies, Interactive Brokers, additional strategies and symbols, compounded sizing, and different persistence or deployment adapters. Those later behaviors remain deferred and require their own validation; preserving a seam does not authorize speculative implementation of the feature or a generic plugin framework.

Maintainability, extensibility, understandability, safety, security, reliability, reproducibility, portability, performance efficiency, observability, and change compatibility must be expressed as reviewable quality scenarios and automated architecture fitness rules. The completed runtime, observability, and Azure specifications fix their operational and deployment thresholds; the verification and security investigations will fix the remaining release and protection details. A minimal single-node Azure deployment does not weaken the software boundaries and does not require microservices.

## Product and venue scope

- Personal/professional workstation for one operator.
- Binance Spot is the only executable venue.
- One configured symbol and at most one active live grid.
- Existing Binance account with an explicit grid allocation isolated from manual and other-algorithm activity.
- Owned inventory only: no borrowing, shorting, leverage, margin, futures, options, or venue liquidation.
- `gridlab` and `gridlab-studio` are the canonical foundation. Useful legacy behavior and the preferred SaaS UI patterns are selectively migrated rather than keeping parallel engines.

## Strategy scope

- One static grid with arithmetic and geometric spacing; geometric is the default.
- Fixed quote sizing and non-compounded MVP profit. Compounding is specified only as a later increment.
- Neutral Spot bootstrap through a real, obligation-backed acquisition.
- Activation price must be strictly inside the configured lower and upper bounds.
- Exact rung-count and activation-rung semantics.
- One cumulative managed order per rung.
- Normal grid orders are post-only maker orders; a marketable post-only order is rejected rather than becoming taker.
- Aggressive execution is reserved for explicitly approved bootstrap and global stop-loss behavior.
- Partial fills transfer ownership immediately and create cumulative paired quantities.
- Paired rung orders cycle within the static range.
- No exposure or automatic range expansion beyond the outer rungs.
- Range-exhausted behavior retains only valid recovery-side obligations.
- Configurable global stop-loss is part of the MVP; ordinary paired sells are not a global take-profit.
- Pause, reconciled resume, operator stop, emergency stop, and retained-holding behavior are explicit lifecycle states.
- Every run uses one immutable strategy configuration version and can remain open indefinitely until a terminal condition occurs.

## Operating modes and parity

All modes consume canonical events and use the same deterministic strategy decision core:

1. **Candle simulation:** fast broad research with conservative, explicit intrabar assumptions.
2. **Event replay:** higher-fidelity validation from recorded market and account evidence.
3. **Production-Data Paper Run:** public production market data with locally simulated orders, fills, balances, and risk transitions.
4. **Live trading:** the same decisions translated to real Binance Spot commands only after promotion and manual activation.

The first deployable MVP exposes modes 1–3. Mode 4 is implemented behind a fail-closed authorization boundary so it can be tested without being accidentally enabled. Backtest, replay, paper, and live do not promise identical fills; they promise equivalent decisions from equivalent canonical inputs and state.

## Market-data and storage scope

- Binance historical one-minute candles for broad searches and regime coverage.
- One-second candles and trade data where available for higher-fidelity validation.
- Captured live trades, best bid/offer, and targeted order-book depth for paper operation, replay, and incident evidence.
- Immutable dataset manifests with source lineage, scope, validation findings, and derivation relationships.
- Parquet for historical and captured market datasets.
- SQLite in WAL mode for the single-node operational journal indexes, projections, and control state.
- Durable canonical event ordering, identities, event time, received time, and processing sequence.
- Targeted rather than continuous complete full-depth capture.

## Accounting and reconciliation scope

The accepted [accounting and reconciliation specification](accounting-and-reconciliation-spec.md) is mandatory for the MVP:

- exact source-decimal native-asset postings;
- isolated per-grid ownership, availability, reservations, pending quantities, and retained holdings;
- actual fee asset and quantity rather than quote-only inferred fees;
- paired-lot provenance for ordinary grid cycles and separate terminal disposal results;
- current grid equity and conservative liquidation equity;
- exact replay and asset-conservation identities;
- fail-closed invariant evaluation after each atomic accounting batch;
- fact-specific authority across configuration, journal, Binance evidence, subledger, market observations, and venue rules;
- explicit durable reconciliation states;
- idempotent handling of duplicate delivery, missing acknowledgements, partial fills, fees, and late fills;
- evidence-preserving repairs and operator approval for material allocation or ownership changes;
- foreign-activity isolation and aggregate allocation-coverage checks.

No reconciled resume, promotion, or live continuation may contain an unexplained material balance, order, fill, fee, reservation, or ownership difference.

## Risk, recovery, and security scope

The accepted [risk and safety specification](risk-and-safety-spec.md) fixes the MVP state machine and first-live quantitative profile. The MVP includes:

- hard maximum capital allocation and maximum planned inventory;
- per-order, aggregate obligation, drawdown, and daily-loss limits;
- stale-market-data, stream-gap, connectivity, venue-rejection, and accounting-anomaly controls;
- emergency stop and exposure-reducing safety behavior;
- idempotent command identities and no duplicate replacement while an earlier order is uncertain;
- startup and periodic reconciliation;
- safe restart, websocket recovery, missed-event backfill, and degraded modes;
- explicit manual production activation and material-incident resume;
- least-privilege Binance API credentials with withdrawals disabled;
- protected secrets, authenticated operator access, backups, dependency controls, and an audit trail.

## Observability scope

- Append-only trading event journal distinct from diagnostic logs.
- Structured logs with stable correlation across market event, decision, command, order, fill, accounting batch, reconciliation item, and safety transition.
- Metrics, health checks, alerts, and explicit invariant outcomes.
- Decision explanations that show relevant configuration, input evidence, intended action, and rejection or safety reason.
- Durable incident history and targeted market evidence around material events.
- Redaction rules that prevent API credentials and sensitive authentication material from entering logs.
- Retention and backup policies sufficient for deterministic replay and the required audit period.

## Operator workstation scope

The accepted [operator workflow and UI specification](operator-workflows-and-ui-spec.md) defines one Operator Studio with trust-separated Research and Operations workspaces:

- Research provides guided immutable experiment configuration, a durable resumable local job runner, return-led evidence views, interactive trade/grid analysis, bounded comparison, promotion gates, candidate selection, and a sealed candidate handoff;
- Operations provides purpose-separated Paper and Testnet qualification, separate promotion approval and re-authenticated live activation, the Command Canvas, case-based reconciliation and incidents, causal evidence/audit download, and graduated safety controls;
- a persistent two-layer authority header distinguishes workspace, environment, target, freshness, lifecycle, safety posture, reconciliation, readiness, incidents, and applicable capital authority;
- the Command Canvas keeps safety/capital first, a large evidence-linked trade/grid chart beside current rung obligations, and exact orders, fills, paired cycles, accounting, reconciliation, and causal events below;
- selected evidence opens an investigation inspector, while a plain-language current-focus explanation teaches what requires attention without inventing an aggregate confidence score;
- local research evidence remains local; authoritative Azure Paper/Testnet/live evidence is retrieved through the gateway as sealed, checksum-verified, immutable complete or referential bundles into a rebuildable local cache;
- contextual explanations, a dedicated Learn area, and the canonical domain glossary support an unfamiliar operator without changing authority or creating separate beginner semantics; and
- full control is desktop/laptop only, with WCAG 2.2 AA as the accessibility baseline and narrow/mobile views limited to read-only status and alerts.

`gridlab-studio` remains the canonical product foundation. Its FastAPI/Python services retain authority while the vanilla frontend is incrementally modernized into a typed React/TypeScript SPA built by Vite. Useful `grid-backtest-saas` interaction patterns are selectively reimplemented; its obsolete strategy semantics and multi-user/distributed topology are not adopted.

## Validation and promotion boundary

The accepted [validation and promotion specification](validation-and-promotion-spec.md) keeps real-money activation locked until the following non-compensating evidence passes:

- accounting and deterministic replay invariants pass without unexplained differences;
- equivalent canonical inputs produce comparable strategy decisions across modes;
- walk-forward and out-of-sample results remain positive after realistic fees, spread, slippage, post-only rejection, partial fills, and other execution costs;
- performance is robust across multiple market regimes, symbols, and periods rather than one favorable sample;
- the deliberately started Production-Data Paper Run qualification continues for at least 30 consecutive days on one immutable candidate without unreconciled orders, missed or duplicate fills, unsupported obligations, or unsafe recovery;
- risk limits, emergency stop, restart recovery, stream gaps, late fills, rejected orders, and exchange reconciliation are deliberately fault-tested;
- the operator reviews the evidence and explicitly authorizes activation;
- the first real-money run uses a hard, small capital allocation and daily-loss limit with a rollback rule.

## Minimal Azure boundary

The target is a low-cost single-node deployment, not application-level high availability:

- one always-on compute instance capable of the Python runtime and websocket connections;
- durable attached state, automated backups, and tested restoration;
- automatic process restart without automatic unsafe trading resume;
- secure secret storage and private authenticated operator access;
- basic platform and application monitoring and alerts;
- enough retained storage for the selected journal, logs, and targeted market evidence.

The accepted starting baseline is one B1ms, a 64-GiB E6 LRS Standard SSD managed disk, a Standard static public IPv4, GPv2 Hot ZRS Blob evidence/recovery objects transitioning eligible data to Cool, managed identity with Key Vault Standard, and bounded Azure Monitor/Log Analytics, currently estimated at approximately EUR 24-30/month before VAT. A 24-hour representative Paper/Testnet resource benchmark must prove B1ms or trigger resize/retest. Deployment-time subscription quota/capacity and the actual invoice remain checks rather than specification assumptions; detailed authentication, credential permissions, cryptographic policy and security hardening remain in the security investigation.

## Mandatory remaining MVP investigations

These are required to make the MVP implementation-ready, in dependency order:

1. **Current Binance Spot contract — completed.** The accepted [primary-source research](binance-spot-contract.md) and [code-gap audit](binance-adapter-code-gap-audit.md) require post-only `LIMIT_MAKER`, generation-specific command identity, exact live filters and commissions, unknown-outcome recovery, rate-limit backoff, finite-stream rotation and gap recovery, and strict separation of paper simulation from periodically reset Testnet protocol integration.
2. **Risk model and safety state machine — completed.** The accepted [risk and safety specification](risk-and-safety-spec.md) fixes allocation-isolated economic authority, the deterministic safety-posture overlay, conservative-equity loss controls, bounded maker and terminal execution, decision-based anomaly/materiality rules, frozen recovery, acceptance cases, and the `250 USDT` qualifying-paper/first-live profile.
3. **Validation and promotion gates — completed.** The accepted [validation and promotion specification](validation-and-promotion-spec.md) fixes data quality/fidelity, five-year nested chronological evidence, cross-symbol/regime/search governance, return/DSR/activity/parity/stress thresholds, production-data paper and Testnet qualification, two-step activation, first-live probation, rollback, freshness, and impact-based requalification while deferring statistical block-resampling from the MVP.
4. **Event journal, diagnostics, monitoring, and retention — completed.** The accepted [event-journal and observability specification](event-journal-observability-spec.md) defines atomic causal evidence, deterministic replay/recovery, structured redacted diagnostics, metrics/health/incidents/alerts, targeted market capture and exact compaction, tiered Blob retention, B1ms resource/recovery objectives, graded failure behavior, and mandatory fault-injection gates. Current Azure price evidence is recorded in the [monthly cost estimate](azure-mvp-monthly-cost-estimate.md).
5. **Online runtime and recovery — completed.** The accepted [online runtime and recovery specification](online-runtime-and-recovery-spec.md) fixes the laptop/Azure boundary, isolated single-writer runtimes, durable event and command processing, explicit stream continuity and recurring reconciliation, paper/Testnet/live adapters, authenticated operator controls, frozen restart, B1ms scheduling/degradation, and the staged runtime implementation and acceptance handoff.
6. **Operator workflows and UI — completed.** The accepted [operator workflow and UI specification](operator-workflows-and-ui-spec.md) fixes the trust-separated Studio, guided research and evidence handoff, qualification/activation, Command Canvas, reconciliation/incidents/audit, contextual learning/accessibility, and incremental React/TypeScript/Vite architecture. A verified throwaway three-variant prototype selected the final Command Canvas composition.
7. **Minimal Azure deployment — completed.** The accepted [Azure deployment specification](azure-minimal-deployment-spec.md) selects the B1ms-first three-process node, E6 LRS disk, static IPv4, ZRS Blob recovery/evidence, Key Vault/managed identity, bounded monitoring, native `systemd`, Bicep, local qualified releases, SSH delivery, recovery/acceptance drills, cost controls, and the explicit maintenance-security exception.
8. **Security and secret management.** Finalize API-key permissions, network boundary, secret rotation, encryption, access, dependency, backup, and audit controls.
9. **Verification, release, and migration.** Define automated and property tests, venue contracts, replay fixtures, fault injection, security and end-to-end coverage, resource budgets, database and configuration migrations, build provenance, release approvals, compatibility, deployment checks, and rollback.
10. **System-specification synthesis.** Consolidate all accepted decisions into the implementation contract and staged delivery plan.

Reviewing the completed accounting specification is optional quality assurance, not a blocking investigation. It should be revisited if Binance research, risk modeling, or runtime design exposes a contradiction; otherwise work should proceed to the Binance contract.

## Deferred from the first MVP

- Interactive Brokers integration.
- Multiple simultaneous live grids or symbols.
- Adaptive or dynamically expanding grids.
- Compounding sizing.
- Futures, options, leverage, margin, borrowing, and short exposure.
- Multi-user SaaS tenancy, billing, and public-product administration.
- Automatic real-money activation.
- Continuous complete full-depth market-data capture.
- Application-level high availability.
- A global take-profit unless a later validated requirement justifies it.

## Declined MVP shapes

### Real-money-first MVP

This provides immediate executable orders but discovers accounting, recovery, and reconciliation defects using actual assets. It conflicts with the mandatory promotion and manual-activation boundary.

### Backtest-only MVP

This is quicker to demonstrate but cannot validate live market ingestion, exchange order state, partial fills, stream gaps, cancellation races, restart recovery, account reconciliation, or operational reliability. It is a research component, not a trustworthy trading-system MVP.
