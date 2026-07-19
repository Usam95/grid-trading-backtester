# Event journal, observability, and retention specification

Status: operator-approved  
Applies to: historical event replay, production-data paper trading, Binance venue-integration testing, first-live trading, recovery, reconciliation, and incident analysis

## Purpose

This specification defines the evidence needed to explain, monitor, recover, and deterministically replay every material trading decision without turning diagnostic logging into a competing source of truth. It covers the authoritative trading event journal, diagnostic logs, operational metrics and health signals, traces, correlated incidents and alerts, targeted market-evidence capture, redaction, retention, export, and observability acceptance tests.

The MVP remains a low-cost single-operator system. Every retained field, metric, alert, and trace must serve an accepted replay, accounting, reconciliation, safety, promotion, recovery, security, or operator-debugging requirement. General-purpose data-lake, SIEM, distributed-tracing, and full-depth market-capture features are not included merely for completeness.

## Accepted constraints inherited from earlier specifications

- The trading event journal is append-only, durable, and distinct from diagnostic logs.
- Canonical events, immutable configuration identities, venue-rule observations, command identities, authoritative venue evidence, and invariant results are evidence; dashboards, reports, metrics, caches, and read models are rebuildable projections.
- A canonical event is admitted in one deterministic `processing_sequence`; causation and source order are preserved, and deterministic fallback ordering is explicit.
- Equivalent ordered input events and immutable decision context must reproduce byte-identical decision batches, domain state hashes, ordered domain outputs, rebuilt trading projections, accounting results, and reconciliation outcomes.
- Operational observations such as host identity, process identity, CPU duration, log-write time, and newly measured latency cannot affect deterministic decision serialization or state hashes.
- A venue command has a durable generation-specific managed order identity before transmission. Unknown outcomes, duplicates, partial and late fills, stream gaps, reconciliation evidence, operator actions, and safety transitions remain first-class evidence.
- Accounting batches and invariant outcomes are source-exact, fail closed, idempotent, and reconstructible from journal history.
- Critical conditions require externally detectable alerting; missing process heartbeat for two minutes is already a critical dead-man condition.
- Secrets, signatures, credentials, authentication payloads, and sensitive headers are forbidden from journals, logs, metrics, alerts, traces, and incident evidence. Redaction failures block promotion.
- The accepted single-node storage direction is SQLite in WAL mode for transactional trading evidence and projections, compressed Parquet for completed bulk market captures, and JSONL only for export/interchange.
- Continuous full-depth market capture is out of scope. The active symbol's trades and best bid/offer are retained, with targeted shallow/diff depth during paper/live operation and incident windows.

## Codebase audit

### Canonical foundation

`gridlab` currently returns an in-memory list containing `OrderPlacedEvent`, `OrderFilledEvent`, `OrderCancelledEvent`, and `LiquidationEvent`. These records are useful characterization material, but they use binary floating-point values and bar-local identifiers and do not provide durable event IDs, schema versions, correlation/causation identities, admission sequences, source provenance, transactional persistence, decision batches, invariant evidence, reconciliation history, or online venue facts.

`gridlab-studio` exposes backtest results and research metrics. Those results are valuable future read-model and operator-UX inputs, but they are not a trading event journal and cannot become an authority for orders, fills, balances, or accounting.

### Legacy references

`backtester_old` provides named Python loggers, timestamped text files, console output, and a file handler that periodically flushes and attempts `fsync`. It also contains useful human-readable messages and runtime logger categories. It does not provide structured schemas, stable correlation, causal linkage, deterministic event ordering, redaction enforcement, tamper evidence, retention policy, incident state, metrics/health contracts, or delivery-tested external alerts. The handler deliberately suppresses `fsync` errors, so successful log emission is not evidence of durable trading-state persistence.

The legacy `run_id`, `order_id`, `client_tag`, event list, logger categories, and SaaS job/result views may inform migration and presentation. They must not be imported as the canonical identity, journal, or safety model without redesign.

## Required separation of concerns

| Channel | Purpose | Authority |
| --- | --- | --- |
| Trading event journal | Durable decision-affecting inputs, deterministic outputs, external command/evidence lifecycle, accounting, reconciliation, safety, and operator actions | Authoritative for the exact facts assigned to it |
| Market archive | Immutable source and captured market evidence referenced by journal identities and manifests | Authoritative for retained source market facts |
| Diagnostic logs | Structured technical explanation of adapters, persistence, jobs, UI/API, and failures | Diagnostic only; never repairs or establishes trading state |
| Metrics and health | Bounded operational measurements and current health/availability projections | Diagnostic/control-plane observations; a domain threshold changes state only through an admitted canonical event |
| Traces | Short-lived timing and call-path context across process boundaries or background jobs | Diagnostic only |
| Incidents and alerts | Durable operator-facing lifecycle plus external notifications for material conditions | Incident record is authoritative for acknowledgement/escalation history, not for underlying trading facts |
| Read models and dashboards | Rebuildable current and historical views | Projection only |

## Durable admission and transactional processing

Selected by the operator on 2026-07-16: use a two-stage durable admission and transactional processing/outbox model for every canonical input.

### Stage 1 — durable event admission

The runtime validates and deduplicates the candidate canonical input, assigns its immutable run-local `processing_sequence`, and commits its event envelope and payload or evidence reference before the event is eligible to change domain state. A duplicate source fact links to the already admitted event and cannot receive a second processing position or economic effect.

An admitted event that has no completed processing transaction remains explicitly pending. Startup recovery processes that same event from its recorded prior state; it does not re-ingest, renumber, discard, or replace it.

### Stage 2 — atomic journal processing transaction

For the admitted input, one database transaction durably commits all deterministic consequences as an indivisible set:

- the decision batch, including explicit no-action or refusal reasons;
- ordered canonical domain outputs;
- previous and resulting deterministic state hashes;
- accounting postings and accounting-batch identity where applicable;
- invariant evaluations and their versions/outcomes;
- lifecycle, safety, reconciliation, timer, and incident-domain consequences where applicable;
- every external command outbox entry with its stable command and managed-order identities;
- the processed position/checkpoint needed to distinguish pending from completed admission; and
- the atomic updates to rebuildable local projections needed for safe online operation.

No deterministic consequence becomes visible if this transaction fails. Persistence failure prohibits transmission, selects the already accepted fail-closed safety behavior, and produces a critical incident through a monitoring path that does not depend solely on the failed write.

### Command dispatch boundary

An exchange, notification, or other side-effect adapter may dispatch an outbox command only after the journal processing transaction commits. Dispatch success, refusal, timeout, and outcome-unknown are later facts; each is appended and causally linked rather than used to edit the original intent.

Outbox recovery reuses the exact command and managed-order identities. A crash after commit but before or during transmission therefore causes evidence recovery and idempotent dispatch/reconciliation, never construction of a replacement identity while the original outcome could remain unknown.

### Worked example

Production market event `E1842` is durably admitted at processing sequence `1842`. Its processing transaction records the prior state hash, a decision batch that creates managed buy obligation `O77`, its reason and exact quantized terms, passing invariant results, the resulting state hash, and command outbox item `C77`. Only after commit may the Binance adapter transmit `C77`.

- Crash after admission but before processing: recovery finds `E1842` pending and deterministically produces its one processing transaction; no command has been transmitted.
- Crash after processing commit but before dispatch: recovery finds `C77` pending and dispatches or reconciles that same identity.
- Timeout during dispatch: `C77` becomes outcome-unknown; replacement remains prohibited until authoritative reconciliation resolves it.
- Failure of the processing transaction: no partial accounting, state, or command record becomes visible and no command is sent.

### Consequences

- SQLite WAL transactions are sufficient for the MVP; no distributed transaction coordinator or message broker is required.
- The journal can contain admitted-but-not-yet-processed inputs and committed-but-not-yet-dispatched commands without ambiguity.
- Domain processing remains deterministic and side-effect-free; adapters operate only from committed command records.
- Projections may be updated in the same local transaction for operational efficiency, but they remain rebuildable and cannot supersede journal evidence.
- Notification delivery uses the same durable-outbox principle where losing a critical alert would matter, while the external dead-man path remains independent of the trading process.

### Declined alternatives

- **One transaction for input and all results:** simpler in appearance, but the input is not durably admitted before processing and a crash cannot expose the precise pending-work boundary as clearly.
- **Independent writes for each consequence:** permits a crash to leave a decision without its accounting, invariant, state, or command evidence and makes recovery depend on inference.
- **Record after an external action completes:** can create a real venue order with no durable local intent and is incompatible with unknown-outcome reconciliation.
- **Broker or distributed transaction in the MVP:** adds infrastructure, failure modes, and Azure cost without a second service or throughput requirement that justifies it.

## Typed identities and causal correlation

Selected by the operator on 2026-07-16: use explicit typed identities and a complete causal graph rather than one run-wide correlation value, unrelated random IDs, or database row numbers.

### Identity layers

Every durable record carries only the identifiers applicable to its meaning, drawn from the following layers:

| Identity | Meaning and rule |
| --- | --- |
| `system_id` | Stable identity of this personal trading system; distinguishes restored/exported evidence from unrelated installations without identifying a host process. |
| `run_id` | Immutable identity of one grid run and allocation-isolated lifecycle. Replay of that run retains the domain `run_id`. |
| `event_id` | Globally unique immutable canonical-fact identity used for deduplication and causal links. |
| `processing_sequence` | Gap-detectable, strictly increasing run-local decision order assigned at admission; it is ordering evidence, not a substitute for `event_id`. |
| `source_identity` | Typed producer namespace such as a dataset manifest, Binance stream generation, authenticated query, simulator, domain timer, or operator action. |
| `source_event_key` | Exact source-native identity or deterministic composite key used to recognize repeated delivery of the same source fact. |
| `causation_event_id` | Direct admitted event whose processing caused an output. Later external facts instead point to the command/order/evidence identity they directly answer. |
| `correlation_id` | Stable identity of one business operation or investigation spanning several immediate causes and technical calls. |
| Typed entity IDs | Purpose-specific identities including `decision_batch_id`, `command_id`, `managed_order_id`, `venue_order_id`, `fill_id`, `accounting_batch_id`, `reconciliation_item_id`, `operator_action_id`, `incident_id`, and `alert_delivery_id`. |

Database primary keys, file offsets, host/process identities, trace/span IDs, and UI request IDs may accelerate lookup or diagnose operation, but they cannot replace these durable domain/evidence identities.

### Deterministic and source-derived identity rules

- A source fact with a trustworthy natural identity uses a namespaced deterministic `event_id` derived from its source identity and exact natural key. A payload digest is stored separately. Redelivery with the same key and same digest is a duplicate; the same key with a different material payload is conflicting evidence, not a second independent fact.
- A source record without a venue-native unique ID uses an immutable deterministic composite established by its adapter contract, such as dataset-manifest identity plus record position, or stream generation plus venue sequence/update identity. Arrival order alone is not sufficient where the source exposes stronger identity.
- Deterministic domain outputs derive stable IDs from the immutable run identity, triggering processing sequence/event identity, output type, and ordered output ordinal. Identical replay therefore recreates identical domain IDs and serialized decisions.
- An externally initiated operator or infrastructure fact receives its identity once at durable ingestion; replay reuses the recorded identity rather than generating another.
- A replay execution, export job, process, HTTP request, or diagnostic trace receives a separate operational identity that never changes the replayed domain identities or state hashes.
- Binance client-order identifiers are deterministic venue-safe encodings of the managed-order/attempt identity. Binance order, trade, update, and list identifiers remain separate source facts and never overwrite local identity.
- Every ID format is versioned and bounded for its external target. IDs never embed secrets, account numbers, raw strategy parameters, email addresses, or other sensitive values.

### Causation and correlation rules

- Causation is the immediate directed edge needed to answer “what directly produced this?”; it is mandatory for deterministic outputs and later facts that answer an identified command/evidence request.
- Correlation answers “which complete operation should be inspected together?” One correlation may cover a managed order from the triggering decision through retries, acknowledgement, partial fills, accounting, reconciliation, and closure.
- A run contains many correlations. Using `run_id` as the only correlation is prohibited because it makes a long-running grid one unbounded diagnostic bucket.
- An incident has its own identity and may link several correlations, events, orders, reconciliation items, and alerts without rewriting their original primary correlation.
- Cross-run promotion, deployment, or market-archive analysis uses explicit reference/link records rather than pretending unrelated runs share one trading-operation correlation.

### Worked example

Market event `E1842` in run `R9` causes decision batch `D1842`, which creates managed-order identity `O77` and command attempt `C77`. Binance venue order `B991` acknowledges `C77`; partial fills `F1` and `F2` cause accounting batches `A1` and `A2`. The order-lifecycle correlation retrieves the chain, while each output retains its immediate cause. If `F2` creates reconciliation item `Q4` and critical incident `I3`, the incident links the relevant order correlation plus `Q4`; it does not replace their identities.

### Consequences

- The operator can start at an alert, fill, accounting batch, or UI order and navigate both backward to the evidence/decision and forward to every consequence.
- Deduplication and conflict detection are identity rules rather than text matching or timestamp guesses.
- Exact replay can compare identities as part of byte-equivalent deterministic artifacts.
- Typed IDs add schema fields, but prevent accidental joins between semantically different identifiers and preserve later venue/multi-run extension seams.
- Indexes are required on run/sequence, event identity, source identity/key, causation, correlation, and the typed external identities used for reconciliation.

### Declined alternatives

- **One correlation for the entire run:** easy to attach but too broad to explain one order lifecycle or incident without scanning the whole run.
- **Independent random IDs with optional links:** uniqueness alone does not guarantee a complete causal chain and replay would generate different output identities unless special cases were added later.
- **Database row IDs:** change across rebuild, export, restore, and migration and cannot safely cross the venue or archive boundary.
- **One universal polymorphic ID:** obscures whether a value denotes an event, command, managed order, venue order, fill, posting batch, or incident and makes invalid joins easy.

## Multi-clock event envelope and deterministic ordering

Selected by the operator on 2026-07-16: preserve source occurrence, local observation, durable admission, and processing-commit time separately while using `processing_sequence` as the authoritative replay order.

### Required temporal fields

| Field | Meaning and authority |
| --- | --- |
| `event_time` | Authoritative source occurrence/effective time of the represented fact. It is the domain time carried into canonical processing. |
| `event_time_precision` | Source-declared precision such as second, millisecond, microsecond, or nanosecond; normalization must not imply knowledge the source did not provide. |
| `source_sequence` | Source-native ordered update, trade, stream, query-page, archive-record, or other sequence where available. It proves source continuity/order within its declared scope. |
| `received_time` | UTC time when the runtime first observed the source fact. It supports latency, staleness, and gap diagnosis but cannot replace source occurrence time. |
| `admitted_time` | UTC commit time of the durable event-admission transaction. |
| `processed_time` | UTC commit time of the journal processing transaction for the admitted event. |
| `processing_sequence` | Strictly increasing, gap-detectable run-local order assigned at admission and reproduced exactly during captured replay. It is the final authority for what the runtime processed when. |
| `clock_observation_id` | Reference to the applicable measured venue/runtime clock-offset evidence where a contract or safety rule requires it. |

`event_time` is mandatory. Each adapter contract defines its authoritative source: venue timestamp for exchange facts, manifest/source timestamp for historical market facts, logical due time for domain timers, durable server acceptance time for operator actions, and deterministic simulated time for simulation facts. Missing, invalid, impossible, or out-of-contract source time is rejected or quarantined; the adapter may not silently substitute local receipt time.

### Exact representation

- Canonical timestamps use a signed UTC epoch seconds/nanoseconds representation plus declared source precision; decimal text and ISO-8601 UTC forms are derived for export/display. Binary floating-point timestamps are prohibited.
- Conversion from a source millisecond or microsecond integer is exact. Zero-filled lower digits do not claim greater precision because `event_time_precision` preserves the source boundary.
- Raw source timestamp value/unit and normalizer version remain in provenance when normalization occurred.
- `received_time`, `admitted_time`, and `processed_time` use the same canonical UTC representation and record the runtime clock-observation context needed to interpret skew.
- Monotonic-clock durations may measure in-process queueing, persistence, and adapter latency. They are diagnostic measurements, do not cross process restarts, and do not replace UTC evidence.

### Ordering rules

- The live runtime assigns `processing_sequence` only during durable admission. Once committed, a sequence is never reused, renumbered, backfilled, or reordered.
- Source ordering is preserved and checked inside each declared source scope. Gaps, duplicates, regressions, rotations, and overlaps become explicit continuity evidence.
- When multiple eligible inputs compete for admission, the accepted deterministic source-priority rule, source sequence, event time, and stable identity fallback determine a total order. The exact priority table belongs to the online-runtime specification, but it cannot use thread scheduling or dictionary iteration as a tie-breaker.
- A late or out-of-order source fact retains its original event time and source sequence but receives the next processing sequence. It is classified and reconciled under the accepted safety rules; prior history is never rewritten to make the timeline appear cleaner.
- Historical event replay may establish its sequence deterministically from manifested source order before execution. Captured paper/live replay must use the original admitted processing sequence even if an after-the-fact event-time sort would differ.
- A corrected timestamp or source fact is appended as identified correction/conflicting evidence according to authority rules. It never edits a previously admitted record.
- Passage of time changes domain state only through an admitted domain-timer event with recorded logical due time. Wall-clock polling, dashboard refresh, logging, and metric collection cannot mutate trading state directly.

### Worked example

A Binance fill occurred at `12:00:00.100`, reached the runtime at `12:00:02.400`, committed admission at `12:00:02.410`, and completed processing at `12:00:02.415` as sequence `812`. The envelope proves approximately 2.3 seconds of source-to-receipt delay and 15 milliseconds of local receipt-to-processing delay. Replay processes the fill at sequence `812`, reproducing the state the runtime actually had, while incident analysis can still view it at its original source time.

### Consequences

- Market/venue latency, local queue delay, persistence delay, and processing delay can be distinguished rather than collapsed into one timestamp.
- Deterministic replay remains faithful to live knowledge even for late fills, delayed account events, and recovered stream gaps.
- Source precision and clock-offset evidence prevent false sub-millisecond certainty.
- Storage includes several integer timestamp fields and indexes, a small cost justified by the already accepted staleness, gap, replay, and recovery requirements.
- UI timelines may offer source-time and processing-order views, but must label them and never imply they are interchangeable.

### Declined alternatives

- **Event time and processing sequence only:** supports basic replay but cannot separate network, admission, persistence, and processing delay or prove several operational deadlines.
- **One generic timestamp:** makes occurrence, observation, admission, and processing ambiguous and produces misleading incident timelines.
- **Strict event-time reordering:** rewrites what the live system knew, changes decisions after late facts, and invalidates captured replay.
- **Arrival time as domain time:** hides source delay and makes behavior dependent on network and host scheduling rather than the represented fact.

## Decision-complete journal coverage and payload placement

Selected by the operator on 2026-07-16: retain every fact and deterministic explanation needed to reconstruct what the system knew, decided, intended, observed, accounted for, reconciled, and permitted, while placing bulk immutable source payloads in the market/evidence archive rather than blindly embedding them in SQLite.

### Completeness rule

For every admitted canonical input, the retained evidence must answer all applicable questions without relying on a mutable log line or current projection:

1. What exact source fact and immutable context were available?
2. Was the fact valid, fresh, continuous, unique, and eligible for decision processing?
3. What decision batch resulted, including no-action and refusal reasons?
4. What state, accounting, invariant, lifecycle, reconciliation, and safety consequences committed?
5. What external command or evidence request was intended and under which authority?
6. What dispatch, venue, simulator, operator, or infrastructure fact happened afterward?
7. How was uncertainty classified, escalated, repaired, acknowledged, or closed?

Absence is not an explanation. An empty decision batch records a canonical reason set such as “no rung obligation changed”; a refused intent records the exact rule/version, evaluated boundary, relevant input identities, and resulting permission. Routine deterministic success may use compact typed codes and hashes rather than repeated prose, but it cannot disappear if replay or an accepted invariant consumes it.

### Mandatory event families

| Family | Minimum retained facts |
| --- | --- |
| Run and configuration | Run creation, immutable configuration/semantics/build identities, allocation, venue/rule/fee observations, activation eligibility, approval/authorization, activation attempt, pause/resume/stop/closure, and configuration rejection |
| Market and time | Decision-consumed candle/trade/BBO/depth evidence, source/quality/continuity states, gaps and repairs, valuation observations, clock observations, and every domain timer |
| Decision and permission | Decision batch, prior/result state hashes, intents, no-action/refusal reasons, risk/authorization checks, quantization, obligation/rung consequences, and invariant outcomes |
| Command and venue order | Outbox creation, dispatch attempt, bytes/semantic request digest, response/timeout/transport failure, acknowledgement, post-only rejection, status transitions, cancellation, unknown outcome, retry attempt, and terminal evidence |
| Execution and account | Partial/full/late fill, venue trade, actual fee and fee asset, balance/account observation, account update, foreign activity, and deduplication/conflict classification |
| Paper execution | Paper-order lifecycle, resting eligibility, queue-ahead change, eligible volume and participation consumption, price evidence, simulated fill/refusal, and frozen execution-policy identity |
| Accounting and valuation | Atomic posting batches, reservations, lots/provenance, realized/unrealized/equity values, valuation source/age, invariant version/input digest/outcome, and retained residual/holding classification |
| Reconciliation and repair | Evidence request/query, authoritative response/snapshot identity, item creation and state transitions, expected/observed exact values, deadline, repair proposal/action/approval, compensating posting, and final classification |
| Risk and recovery | Trigger observations, effective posture and latch transitions, command-permission consequences, shutdown/startup checkpoints, persistence/rebuild/replay outcomes, stream recovery, emergency actions, and recovery approval |
| Operator and incident | Authenticated material operator request/approval/refusal, reason and affected evidence digest, incident creation/update/acknowledgement/closure, linked correlations, and alert-delivery lifecycle |
| Schema and evidence administration | Schema/build/normalizer version, migration and verification outcome, snapshot/checkpoint/export identity, archive/backup digest, restoration/rebuild evidence, and integrity failure |

An implementation may split families into typed tables/records and projections. The completeness contract applies to the resulting causal evidence, not to one enormous polymorphic JSON row.

### Inline payload versus immutable reference

- Exact compact canonical inputs, deterministic outputs, decisions, commands, postings, invariant results, reconciliation states, operator actions, and incident state live transactionally in the journal.
- High-rate or bulky raw market trades, book/depth frames, source files, query response bodies, and incident attachments may live in an immutable content-addressed archive.
- A referenced object must be durably stored and verified before journal admission can commit. The reference records archive/object identity, dataset or capture manifest, byte/record range, media/schema/encoding version, uncompressed length where applicable, and cryptographic content digest.
- The journal retains or references the exact normalized canonical fields consumed by the decision core, not merely the raw source body. Normalization version and raw-parent digest make the transformation reproducible.
- A path, URL, object name, database row number, newest-file convention, or log search is not an evidence identity without an immutable digest and manifest relationship.
- Archive unavailability, digest mismatch, undecodable schema, or missing referenced range makes the affected replay incomplete. It is a correctness/integrity failure, not a warning that can be ignored for promotion or recovered live authority.
- Raw authenticated responses are captured only where required, after contract-driven allowlisting/redaction. Secret-bearing request headers, signatures, credentials, and authentication material are never archived.

### Diagnostic-only observations

Routine WebSocket pings, successful retry scheduling, UI refreshes, cache hits, ordinary HTTP access details, CPU samples, garbage collection, and log rotation remain logs/metrics/traces when they cannot change domain behavior. If an operational observation crosses a domain threshold, the admitted timer, gap, persistence, capacity, or safety event and its evidence enter the journal before state changes.

### Worked example

When the operator asks why no buy was placed at rung `90`, the causal view can retrieve the admitted market input or immutable archive record, configuration and venue-rule versions, prior state, decision batch, evaluated obligation/risk/inventory/fee/post-only conditions, explicit no-action or refusal code, invariant results, and resulting state hash. A text log saying “order skipped” is optional explanation, not the evidence.

### Consequences

- Deterministic replay and incident investigation remain possible after diagnostic logs rotate.
- Explicit no-action/refusal evidence makes inactivity debuggable without logging every internal branch as prose.
- Bulk market evidence can be compressed and compacted independently, controlling SQLite size and Azure cost.
- The journal/archive link becomes safety-critical and requires integrity, backup, restoration, and retention tests.
- Event schemas remain typed by family; a generic data-lake or one-table JSON event store is not required.

### Declined alternatives

- **Only state-changing events:** cannot prove why the system correctly did nothing, refused an unsafe command, or evaluated the required invariant.
- **Every raw payload inline in SQLite:** is self-contained but makes high-rate market/depth capture compete with trading-state transactions, inflates backups, and raises recovery cost.
- **Metadata-only journal with payloads in logs or mutable files:** allows rotation, overwrite, path reuse, or partial capture to destroy replay evidence.
- **Journal all technical noise:** increases cost and hides material facts without improving a declared replay, safety, recovery, or promotion requirement.

## Simple journal and artifact integrity

Selected by the operator on 2026-07-17: use the smallest integrity model that supports safe recovery and deterministic evidence verification for a personal MVP. Do not add a journal hash chain, per-event signatures, blockchain, or an independent integrity-anchor service.

### Required controls

- Authoritative journal tables are append-only through the application persistence contract. Ordinary application roles and repository methods expose insertion and reading but no update/delete operation for admitted evidence.
- Database constraints and automated tests reject mutation or reuse of immutable event, sequence, source, command, fill, posting, reconciliation, and evidence identities.
- A correction, conflict classification, redaction marker, superseding observation, or repair is a new causally linked record. It never modifies the original fact.
- SQLite transactionality, foreign-key enforcement, WAL recovery, and `PRAGMA integrity_check` or its accepted equivalent are exercised at startup, before/after backup, after restoration, and when corruption is suspected.
- Immutable market/archive objects, dataset/capture manifests, database-backup artifacts, evidence bundles, and exports carry a versioned SHA-256 checksum and byte length. A referenced artifact is verified before admission, replay, restoration, promotion use, or import.
- Deterministic replay verifies sequence continuity, canonical decisions, state hashes, rebuilt projections, accounting/reconciliation invariants, and referenced artifact checksums. It remains the semantic-integrity test rather than being replaced by a storage checksum.
- Backups are useful only after automated verification and tested restoration. A copied file with no checksum and no successful restore evidence is not a qualified backup.
- Any failed database integrity check, checksum mismatch, missing referenced artifact, broken sequence/identity constraint, failed semantic replay, or unexplained restoration difference selects `FROZEN`, creates a critical incident where applicable, and blocks live resume and promotion.

### Explicit limitation

This model detects ordinary corruption, incomplete copies, missing artifacts, accidental mutation exposed by constraints/replay, and many inconsistent administrative changes. It does not claim cryptographic proof against an administrator or attacker who can rewrite the database, checksums, application, and every backup together. That stronger adversarial tamper-evidence requirement is outside the personal MVP and may be added if the product becomes multi-user, regulated, externally audited, or exposed to a materially stronger threat model.

### Worked example

A completed paper-run market capture has a manifest, exact byte length, and SHA-256 digest. Before replay, the archive checksum and database integrity check pass; sequence continuity and deterministic state/accounting replay then pass. If one archived depth file is truncated, its byte length or digest fails before the replay is treated as evidence. No hash chain is needed to reach the safe conclusion that qualification evidence is incomplete.

### Consequences

- The MVP uses standard SQLite and file/object checks rather than maintaining an additional cryptographic journal protocol.
- Integrity testing remains meaningful because storage checks, artifact checksums, semantic replay, accounting invariants, and restore tests cover different failure classes.
- Access control and backups matter more because the MVP does not attempt adversarial journal non-repudiation.
- A later stronger design can add per-transaction chaining or signed external checkpoints without changing canonical event meaning, provided it is introduced as additive evidence.

### Declined alternatives

- **Hash-chained journal with external checkpoints:** stronger deletion/reordering evidence, but unnecessary transaction, checkpoint, key/storage, migration, and recovery complexity for the accepted personal MVP threat model.
- **Per-event digital signatures:** adds still more key lifecycle and throughput complexity without a regulatory or third-party non-repudiation requirement.
- **Backups without checksums or restoration tests:** simpler in configuration but cannot establish that large archives and evidence exports copied completely or can actually be recovered.

## Immutable schema evolution and database migration

Selected by the operator on 2026-07-17: every durable event family has an explicit schema name and integer version. Historical events are never rewritten to the latest shape; the system implements only the deterministic read conversions required for schema versions that actually exist.

### Event-schema rules

- The event envelope and each payload family declare independent schema names/versions so an unrelated payload change does not require pretending the entire journal changed meaning.
- Canonical serialization is fixed per version. Field names, types, exact-decimal representation, enum meanings, defaults, required/optional status, ordering, and reference semantics are part of the versioned contract.
- Compatible additions still advance the payload version when they change the durable contract. Readers must not infer a schema version from which fields happen to be present.
- A pure deterministic read converter may rename fields, split or combine already recorded structure, normalize a representation exactly, or supply a default only when the earlier version's contract made that value logically certain.
- A converter may not invent a missing fee asset, order/fill identity, source timestamp, operator approval, price, quantity, venue state, causal link, or other economic/safety evidence. If authoritative retained source evidence can establish the fact, it is admitted as linked evidence/correction under current rules; otherwise the affected evidence remains insufficient and any required requalification applies.
- Conversion is side-effect-free, version-to-version tested with golden fixtures, and produces the same current in-memory canonical form on every read. The original bytes/version remain exportable and inspectable.
- Writers emit only the current approved schema. Supporting an old reader does not permit new mixed-version writes except during a deliberately bounded rollback/migration procedure defined by the release specification.

### SQLite migration rules

- Structural database migrations have immutable identities, order, checksums, compatible application/build range, preconditions, and recorded outcomes.
- Before a migration, the application verifies current schema identity and database integrity and creates a checksum-verified recoverable backup. Migrations run transactionally where SQLite permits.
- Journal rows are not updated to adopt a new event payload version. Additive tables/indexes/columns, converters, and new projections are preferred.
- A failed or partially applicable migration leaves trading unauthorized, retains failure evidence outside any transaction that rolled back, and requires restoration or a proven corrective migration. It never falls through to live startup.
- Projection/schema rebuilds are verified against deterministic journal replay and invariant results before becoming current.
- A migration or converter that could change decisions, accounting, risk, reconciliation, replay interpretation, or evidence eligibility triggers the accepted evidence-impact assessment and requalification rules.

### Worked examples

**Safe conversion:** event version 1 calls an exact decimal field `qty`; version 2 calls it `executed_quantity`. The converter maps the existing exact value and preserves the original event identity/version.

**Forbidden invention:** version 2 requires `fee_asset`, but version 1 retained only a quote-valued fee amount. The converter cannot assume quote, base, or BNB. The run is not silently upgraded to exact native-asset accounting; authoritative fill/commission evidence or a newly qualified evidence generation is required.

### Consequences

- Current code can read retained evidence without mutating its historical meaning.
- Compatibility complexity grows only when a real schema version exists; the MVP does not build a generic plugin/migration framework.
- Golden conversion fixtures, migration rollback/restoration tests, and evidence-impact classification become release requirements.
- Snapshots, metrics, and UI projections may be rebuilt into new schemas because they remain non-authoritative.

### Declined alternatives

- **Rewrite historical events into the newest schema:** simplifies current readers but destroys the original durable interpretation and makes migration defects harder to isolate or reverse.
- **Retain every old application runtime:** moves schema compatibility into obsolete dependencies and makes routine incident recovery operationally fragile.
- **Add versioning only at the first break:** leaves the earliest evidence without an explicit interpretation contract and encourages guessed migrations.
- **Prebuild converters for hypothetical future versions:** is speculative framework work with no evidence or compatibility scenario to test.

## Rebuildable recovery snapshots and journal-tail replay

Selected by the operator on 2026-07-17: use small rolling recovery snapshots to bound restart work, but retain the journal as the only authoritative history. Loading a snapshot never authorizes trading; exact tail replay, invariant verification, frozen-startup reconciliation, and the already accepted operator recovery rules remain mandatory.

### Snapshot creation policy

A routine snapshot becomes eligible after the earlier of:

- five elapsed operational minutes since the last successfully sealed routine snapshot; or
- 10,000 additional processed canonical events.

The runtime also seals a snapshot after material committed boundaries: activation/bootstrap completion, pause or stop transition, entry to or recovery from `REDUCE_ONLY`/`FROZEN`/terminal posture, startup or material-incident reconciliation completion, terminal closure, and clean shutdown. Routine 60-second reconciliation success does not require an additional boundary snapshot unless the routine interval/event threshold is also due or material state changed.

Snapshot scheduling is operational-only and cannot change domain decisions. A snapshot reads exactly one already committed processing boundary; it never includes an admitted-but-unprocessed event or a partially committed decision.

### Snapshot contents

Each versioned snapshot contains or identifies:

- snapshot/run identity, creation reason, and exact `processing_sequence` boundary;
- immutable strategy configuration, semantics, venue-rule/fee context, schema, normalizer/execution-model, and application-build identities required to interpret state;
- complete derived strategy/rung/obligation state;
- managed-order, command/outbox, dispatch, and uncertain-outcome projections;
- grid allocation, exact subledger, reservations, lots/provenance, fees, results, valuation context, and invariant state;
- lifecycle, safety posture/latches, risk baselines/high-water marks, timers, reconciliation items/deadlines, incidents, and pending recovery work;
- expected deterministic state hash and the invariant-suite identity/outcome at the boundary; and
- canonical snapshot serialization version, byte length, and SHA-256 checksum.

Ephemeral sockets, database connections, locks, thread state, HTTP sessions, host/process IDs, trace spans, metric accumulators, and secret values are never snapshot domain state.

### Recovery algorithm

1. Enter frozen startup and verify database integrity, journal sequence continuity, required archive references, and candidate snapshot checksum/schema/context.
2. Select the newest compatible verified snapshot. If none qualifies, initialize from immutable run/configuration evidence.
3. Load its derived state and verify the recorded boundary state hash/invariants.
4. Deterministically replay every admitted/processed journal event after the boundary, checking expected per-event outputs, state hashes, accounting, reconciliation, and invariants. Pending admissions/outbox work is recovered under the accepted transaction rules.
5. Rebuild/verify current projections, perform authoritative Binance reconciliation, re-evaluate freshness/risk/control paths, and follow the accepted approval requirements. Successful replay alone never resumes trading.

A damaged, incompatible, incomplete, or divergent snapshot is diagnostic evidence only. Recovery tries an earlier verified snapshot or full replay; it does not repair the journal to agree with the snapshot. Failure to obtain one exact rebuilt state selects `FROZEN` and a critical incident.

### Retention within the active snapshot set

- Keep the newest three verified routine snapshots for each open run.
- Preserve material lifecycle/safety/incident boundary snapshots with their associated run evidence until the later retention policy permits removal.
- Create a new snapshot rather than mutating an existing one; routine snapshots outside the rolling set may be deleted because they are projections, after a newer set and full journal/archive recovery path are verified.
- Snapshot deletion never permits journal or referenced market evidence deletion.

### Consequences

- Typical crash recovery replays at most five minutes or 10,000 processed events from the newest routine snapshot, subject to events arriving during recovery.
- A single active grid keeps snapshot CPU/storage small, while the journal remains fully replayable from the beginning.
- Snapshot compatibility and recovery time are benchmarked on the selected minimum Azure profile; the cadence may be tightened if necessary without changing authority semantics.
- Snapshot generation, corruption, missing snapshot, incompatible version, and crash-during-snapshot become explicit fault tests.

### Declined alternatives

- **Lifecycle/clean-shutdown snapshots only:** saves small background work but leaves an unbounded tail after an unplanned crash in an open-ended run.
- **No MVP snapshots:** keeps persistence simple but makes restart time grow continuously and postpones a required safe-recovery seam.
- **Authoritative snapshot plus journal truncation:** destroys full replay and makes a defective snapshot an unrecoverable source of trading state.
- **Snapshot every event:** adds repeated serialization/write cost while per-event state hashes and the authoritative journal already preserve exact boundaries.

## Manifest-based evidence export

Selected by the operator on 2026-07-17: export one identified run, promotion scope, incident, reconciliation case, or sequence/time window as a sealed manifest-based ZIP bundle. Every bundle declares whether it is self-contained or merely references retained external evidence; the two states cannot share an ambiguous “export succeeded” label.

### Bundle manifest

The canonical UTF-8 `manifest.json` records:

- bundle identity, schema version, purpose, creation actor/time, source system, and export-tool/build identity;
- run/candidate/promotion/incident/reconciliation identities as applicable;
- inclusive/exclusive UTC event-time and exact processing-sequence scope;
- immutable strategy configuration/semantics, application build, normalizer, execution model, venue-rule/fee, invariant-suite, and schema/migration identities;
- journal admission/processing completeness, first/last sequence, expected/actual counts by event family, gap/duplicate/conflict status, and deterministic replay/invariant result;
- every included file's relative path, media/schema/encoding/compression version, byte length, SHA-256 checksum, and role;
- every external dependency's content-addressed evidence reference, location class, required accessibility, checksum, and reason it was not materialized;
- redaction-policy version, excluded-field categories, sensitive-data classification, and verification result; and
- bundle completeness classification, limitations, required compatible reader, and exact verification/replay recipe.

### Portable contents

Depending on declared scope, the ZIP64 bundle contains:

- canonical ordered journal records as versioned JSONL export, preserving exact decimals, timestamps, identities, source versions, and payload/reference relationships;
- required normalized market evidence as Parquet plus original source/capture material where the replay contract requires it;
- relevant configuration, dataset/capture manifests, snapshots, state hashes, invariant results, reconciliation evidence, incident/alert lifecycle, and material operator actions;
- optional derived CSV, JSON, and HTML summaries clearly marked non-authoritative; and
- the manifest plus a checksum inventory that can be verified without executing application code.

JSONL is an interchange representation, not the online source of truth. Export ordering is canonical and deterministic; presentation files may change without changing journal evidence but receive their own identities/checksums.

### Completeness classifications

- **Complete evidence bundle:** includes every journal, market, configuration, schema, rule, and other data dependency required for offline replay of its declared scope. Successful checksum/schema verification establishes transport integrity; deterministic replay remains a separate required result.
- **Referential evidence bundle:** includes the journal/manifest scope and immutable references to one or more dependencies that were not copied, normally to avoid duplicating a large retained archive. It may be useful inside the deployment but is explicitly not independently replayable.
- A missing, inaccessible, mismatched, or unlisted dependency makes the bundle incomplete/invalid. Verification never silently downgrades `complete` to `referential` or treats a partial ZIP as success.

Promotion evidence may use a sealed referential manifest only while every referenced artifact remains verified and available under its retention/backup contract. A portable handoff, independent restoration rehearsal, or offline incident replay requires a complete bundle.

### Consistency, redaction, and import

- Export selects one committed journal boundary using a consistent SQLite read/backup view. Events committed after that boundary belong to a later bundle; admitted-but-unprocessed work is disclosed explicitly.
- Export does not pause or change domain behavior and is not evidence of a new trading action.
- API keys, secret values, signatures, cookies/tokens, authentication headers/payloads, and raw secret-bearing configuration are prohibited. Account/trading evidence that remains sensitive after secret removal is marked and protected by the later security/export-access policy.
- The exporter validates event schemas, sequence continuity, references, checksums, redaction, and manifest counts before sealing. A failed export remains an identified failed job and cannot be relabelled complete.
- Import opens evidence in an isolated read-only analysis/replay namespace after checksum/schema verification. It never merges records into an active live run, dispatches an outbox command, or grants activation authority.
- The bundle file itself receives a sidecar SHA-256 checksum and byte length after sealing.

### Worked example

A late-fill incident export selects an exact processing range covering the precursor market/order state, delayed fill, accounting, reconciliation, safety transition, alert lifecycle, and operator response, plus a declared source-time context window. A complete bundle materializes the referenced trades/BBO/depth evidence; a referential bundle lists their archive digests and clearly states that another machine cannot replay it without retrieving those objects.

### Consequences

- Evidence can be independently verified and inspected without granting access to the live database.
- Complete incident bundles remain bounded; a full 30-day paper bundle may be much larger but cannot hide omitted dependencies.
- One exporter supports promotion sealing, debugging, restoration rehearsal, and future handoff without turning reports into authorities.
- ZIP/JSONL/Parquet and SHA-256 are widely supported and do not require a bespoke evidence service.

### Declined alternatives

- **SQLite copy only:** omits or ambiguously references external market evidence, exposes internal schema, and lacks a portable completeness manifest.
- **CSV/HTML/PDF reports only:** are useful projections but cannot reconstruct event ordering, exact decisions, accounting, or replay.
- **Cloud/dashboard-only evidence:** makes investigation depend on one deployment and its current access, retention, and software state.
- **Always materialize every dependency:** makes even a small index or promotion review duplicate potentially large archives; explicit complete/referential status preserves honesty without forced duplication.

## Structured diagnostic-log contract

Selected by the operator on 2026-07-17: retain diagnostic logs as versioned JSON Lines with stable typed fields and event codes, while rendering those same records as readable text in the console and operator studio. Logs correlate with authoritative evidence but never duplicate or replace it.

### Required base schema

Every retained diagnostic record contains:

- `log_schema_version`;
- source-exact UTC `logged_at` as an operational observation;
- declared severity;
- stable namespaced `event_code` and emitting `component`;
- message template identity plus concise rendered human message;
- application version/build, deployment/environment, process-start identity, and logger identity;
- typed outcome/status, sanitized exception class/error code, retry/attempt number, and measured duration where applicable; and
- an allowlisted structured `attributes` object whose keys/types are defined by the event-code contract.

Applicable durable references are emitted as top-level typed fields rather than embedded in prose: `system_id`, `run_id`, `event_id`, `processing_sequence`, `causation_event_id`, `correlation_id`, `decision_batch_id`, `command_id`, `managed_order_id`, `venue_order_id`, `fill_id`, `accounting_batch_id`, `reconciliation_item_id`, `incident_id`, and diagnostic trace/span identity.

A startup, migration, backup, HTTP request, or other operation with no run context may omit `run_id`; omission is governed by the event-code schema, not by inconsistent logging calls. Null/absent identifiers never use empty strings or guessed placeholders.

### Event-code and message rules

- `event_code` is the machine-searchable contract used for filters, aggregation, tests, and where approved alert rules need diagnostic context. Message wording is for people and may improve without breaking automation.
- Codes are stable, namespaced, documented with severity range, required/optional fields, redaction class, sampling eligibility, and owning component. A semantic change creates a new code rather than silently changing the old meaning.
- Logs explain technical operation: adapter connection/rotation, request/response classification, persistence timing/failure, queue/backpressure, projection rebuild, job progress, UI/API request handling, backup/export work, and exception diagnostics.
- Material journal events are referred to by identity and summarized only when useful. Full canonical payloads, raw accounting state, complete market frames, and authoritative response bodies are not routinely copied into logs.
- Application behavior, safety state, accounting, reconciliation, or alert severity never depends on matching rendered message text.

### Output and consumption

- JSONL is emitted to standard output and to bounded rotating local files through one configured logging pipeline. A later Azure adapter may collect the same records without changing application log semantics.
- The operator studio renders timestamp, severity, component, message, and selected fields as readable rows and supports exact filtering by event code and durable identities.
- Multiline exceptions are represented as structured sanitized stack data inside one logical record rather than breaking JSONL framing. Secret/redaction policy applies to exception text and stack-local values.
- Log writes must not occur inside the deterministic domain model. Boundary/application components receive correlation context explicitly and cannot use process-global mutable trading identity.
- Diagnostic logging failure cannot become proof that a trading action failed or succeeded. Material logging-pipeline health is monitored separately; authoritative journal persistence retains its fail-closed role.

### Worked example

```json
{"log_schema_version":1,"logged_at":"2026-07-17T12:00:02.420000Z","level":"WARNING","event_code":"binance.order.submission_outcome_unknown","component":"venue.binance.command_dispatch","build_id":"build-42","run_id":"R9","command_id":"C77","managed_order_id":"O77","correlation_id":"K31","outcome":"unknown","attempt":1,"message":"Order submission timed out; replacement prohibited pending reconciliation","attributes":{"timeout_ms":3000}}
```

The journal proves the command intent and later reconciliation outcome. This record explains the transport symptom and makes the incident searchable; deleting the log would not change order truth.

### Consequences

- Operators and automated diagnostics can search stable fields instead of parsing human prose.
- One schema supports local files, console rendering, studio views, and a later Azure collector without binding the domain core to a vendor.
- Schema/redaction tests and event-code ownership add modest discipline while avoiding a second event-sourcing system.
- The legacy named logger categories and useful messages can inform component/code vocabulary, but the legacy text format is not retained as the contract.

### Declined alternatives

- **Human-readable retained text only:** is easy to tail but brittle for correlation, validation, redaction, aggregation, and alert context.
- **Journal without diagnostic logs:** preserves truth but makes adapters, persistence, jobs, UI/API, and operational latency unnecessarily opaque.
- **Duplicate full journal payloads into logs:** increases exposure and storage and creates an ambiguous second copy of authoritative evidence.
- **Vendor-specific logging calls throughout the application:** couples operation to Azure and weakens local deterministic testing and portability.

## Balanced log levels, aggregation, and scoped debugging

Selected by the operator on 2026-07-17: run paper/live production at `INFO` by default, retain every material warning/error and operation milestone, and allow time-bounded `DEBUG` capture scoped to the component and causal context under investigation. No `TRACE` level is added to the MVP.

### Level contract

| Log level | Meaning and examples |
| --- | --- |
| `ERROR` | A technical operation failed, required evidence/health may be unavailable, a persistence/export/backup/migration/rebuild failed, an uncaught exception occurred, or an alert delivery exhausted its accepted attempts. |
| `WARNING` | Operation is degraded or unusual but bounded: retry, refusal, approaching deadline/capacity, transient disconnect, rate-limit pressure, stale-but-within-recovery evidence, or unexpected duplicate already handled safely. |
| `INFO` | Material normal milestone: process/run lifecycle, command/outbox/venue milestone, reconciliation/recovery summary, posture/incident transition, operator action, migration/backup/export result, stream rotation, or research/paper job boundary. |
| `DEBUG` | Detailed adapter parsing/transport metadata, queue/backpressure behavior, timing breakdown, source-normalization diagnostics, paper queue/liquidity calculations, projection queries, or branch-level troubleshooting not required in ordinary operation. |

Log level is not incident severity. A critical safety incident normally emits one or more `ERROR` diagnostic records carrying `incident_severity=critical`; machine behavior and notification policy use the durable incident, not the logger's level name.

### Completeness and sampling rules

- `ERROR` and `WARNING` records are never sampled.
- Records for material commands/outcomes, managed-order state, fills/fees, accounting/invariant failures, reconciliation differences/repairs, lifecycle/safety transitions, persistence/migration/backup/recovery, activation/authorization, operator actions, incidents, security-relevant failures, and alert delivery are never randomly sampled at any retained level.
- Repetitive ordinary success records may be deterministically aggregated by exact event code and bounded low-cardinality dimensions over a declared interval. The aggregate records first/last time, exact occurrence count, and representative durable correlation where meaningful.
- High-rate market-update, parser, queue, and timing detail may be sampled or aggregated only at `DEBUG`. The authoritative journal/archive remains complete under its accepted contract.
- Sampling/aggregation configuration has an immutable version. Metrics expose eligible, emitted, aggregated, and dropped counts by component/event-code class, but never by unbounded order/event ID.
- Logging backpressure may discard only sampling-eligible `DEBUG` records according to the configured bounded policy. Loss of a non-sampleable material record is a logging-health failure, not silent normal behavior.

### Diagnostic capture session

An authenticated operator may enable `DEBUG` for an exact component plus optional `run_id`, `correlation_id`, managed-order identity, or `incident_id`. The request records reason, scope, start, expiry, actor, and resulting estimated volume.

- Default and maximum single-session duration are 30 elapsed minutes. An extension is a new recorded operator action, not an unbounded toggle.
- Scope is evaluated before expensive field construction where practical so unrelated high-rate activity remains at INFO.
- The session automatically expires across normal runtime. After restart, frozen startup does not silently restore expired debugging; a still-valid retained request may be reapplied only under its recorded deadline.
- Redaction and field allowlists remain identical at DEBUG. Debugging never authorizes secret or arbitrary raw-payload capture.
- The studio prominently shows active diagnostic capture and estimated/actual record volume.

### Worked example

After command `C77` times out, the operator enables a 30-minute session for component `venue.binance.command_dispatch` and correlation `K31`. Detailed attempts, sanitized transport timing, query/reconciliation calls, and queue behavior are retained for that chain. BTC market parsing and unrelated research jobs remain at their ordinary levels.

### Consequences

- Ordinary operation retains complete material milestones without paying the storage/security cost of permanent verbose transport logging.
- Focused debugging can be activated before reproducing or while investigating a live issue, with automatic expiry limiting accidental disk growth.
- Aggregation and sampling need schema tests and visible counters so “quiet logs” cannot hide unmeasured loss.
- Journal/archive completeness remains independent of diagnostic log verbosity.

### Declined alternatives

- **Permanent DEBUG:** creates large noisy logs, higher Azure ingestion/storage cost, greater backpressure, and larger sensitive-data exposure without improving authoritative replay.
- **WARNING/ERROR only:** omits ordinary command, recovery, operator, backup, and lifecycle context needed to understand a system that appears healthy.
- **Uniform sampling across levels:** can discard the single material warning or operation milestone needed for an incident.
- **Unbounded manual DEBUG toggle:** is easy to forget and can exhaust disk or collector quotas during high-rate market activity.

## Approved event fields plus centralized secret-redaction safety net

Superseded on 2026-07-18 by the operator's security decision: every diagnostic event code has a versioned approved field schema, and one mandatory recursive field-name/value scrubber remains as a second defensive layer in the shared output pipeline. The earlier central-scrubber-only choice was simpler but permitted arbitrary unexpected fields to reach the scrubber; it is retained in history, not as the active contract.

This decision does not weaken the existing prohibition on API secrets, credentials, signatures, authentication payloads/headers, signed query strings, cookies/tokens, passwords, or private keys in the journal, logs, metrics, traces, alerts, exports, and incident evidence. It changes how the diagnostic pipeline attempts to enforce that prohibition.

### Required construction and scrubber behavior

- Each event code declares its approved field names, types, sensitivity class, cardinality bound, and required/optional status. Unknown fields, raw arbitrary objects, complete request/response payloads, local-variable maps, and unclassified free text are rejected before sink emission.
- Schema validation happens before redaction. A validation failure drops the unsafe record and emits only a separate fixed-schema, secret-free logging-pipeline failure event; it never serializes the rejected value for diagnosis.
- Every structured record passes through the same redactor before console, file, studio, test capture, alert context, or external collection. Components cannot bypass it by writing directly to a sink.
- Redaction recursively inspects field names, string values, lists/maps, exception messages, stack text, and URL-like values before JSON serialization.
- The initial version covers case-insensitive credential keys and representations including `api_key`, `apikey`, `secret`, `signature`, `authorization`, `bearer`, `token`, `cookie`, `session`, `password`, private-key markers, Binance signed parameters, and their common header/query variants.
- The runtime registers the exact current credential/token fingerprints with the in-memory redactor so an accidentally interpolated live value is removed even when its surrounding field name is unhelpful. Fingerprints themselves are never persisted or emitted.
- HTTP logs retain method, normalized host/path template, status, timing, request/correlation identity, and safe error classification; complete query strings, authorization headers, cookies, and raw authenticated request bodies are not passed to logging.
- Exception stack capture excludes local-variable dumps. Messages and stack strings are scrubbed before emission.
- A match replaces the entire sensitive value with a constant marker such as `[REDACTED]`; it does not retain prefixes/suffixes that could assist reconstruction. Redaction occurrence counters use bounded categories, never the secret value.
- If redaction or safe serialization throws, the original record is dropped and a separate fixed-schema secret-free logging-pipeline failure signal is emitted through the safest remaining path. The record is never retried without redaction.

### Verification and response

- Automated tests pass synthetic API keys, secrets, signatures, bearer tokens, cookies, passwords, private-key text, signed URLs, nested objects, and exception messages through every configured sink and assert that canary values never appear.
- Tests verify DEBUG sessions, failed HTTP calls, stack traces, alerts, bundles, and logger/redactor failure paths, not only ordinary INFO logs.
- Matching a registered live credential before a sink produces a security warning/metric and prompts code review because upstream code attempted to log it even though redaction succeeded.
- A secret proven to have reached any retained or external sink creates a critical security incident, invalidates affected evidence handling as applicable, contains/deletes non-authoritative copies where safe, and requires emergency credential replacement under the security runbook.
- Redaction rules and tests have a version included in log/export metadata. New venue/client/credential formats require an explicit rule/test update.

### Explicit limitation

Approved schemas and the centralized scrubber materially reduce exposure but cannot prove that an approved ordinary-looking string never equals an unknown, encoded, fragmented, transformed, or newly formatted secret. Prohibiting raw authenticated payloads, registering current secret canaries in memory, and testing every sink remain necessary. Non-serializable secret wrapper types are a later hardening option rather than an MVP dependency.

### Consequences

- One shared schema registry, redactor, and canary suite cover every diagnostic sink.
- Event-code schemas become the primary construction boundary; the centralized scrubber is the mandatory safety net.
- The scrubber becomes security-critical shared infrastructure and cannot fail open.
- Diagnostic capture remains useful, but developers must still avoid passing arbitrary objects and raw payloads because pattern coverage is inherently incomplete.

### Declined alternatives

- **Central scrubber without approved event fields:** was initially selected for simplicity and then superseded because arbitrary unexpected fields create unnecessary leakage risk.
- **Developer convention/code review only:** has no consistent technical boundary and makes one forgotten debug statement sufficient for exposure.
- **Store raw logs encrypted:** reduces storage disclosure but still sends unnecessary secrets through application, collector, export, and viewing paths.
- **No DEBUG in live operation:** reduces exposure but removes the accepted focused diagnostic capability without solving INFO/error-path leakage.

## Bounded local diagnostic-log rotation

Selected by the operator on 2026-07-17: keep a small local JSONL diagnostic buffer in addition to standard output. Rotate by both size and time, compress closed files, and bound the complete local diagnostic directory independently of authoritative evidence retention.

### Rotation and local-retention profile

- Rotate the active file at 50 MiB or 24 elapsed hours after opening, whichever occurs first.
- Rotation closes and validates the JSONL frame boundary, then compresses the closed file. A compression failure retains the uncompressed closed file and reports logging-health degradation; it never deletes the only copy.
- Retain diagnostic files for at most seven elapsed days and enforce a 500 MiB total local diagnostic-log ceiling. The first reached limit deletes the oldest successfully closed files until both constraints hold.
- The active file, rotation metadata, and temporary compression space are included in disk-capacity planning even though the cleanup calculation distinguishes files that are safe to delete.
- Ceiling enforcement can delete only closed diagnostic log files. It cannot delete or compact the trading journal, market/evidence archive, snapshots governed by their policy, incident evidence, database backup, promotion evidence, or unshipped critical alert state.
- File names use UTC open time, deployment/process-start identity, and monotonic segment number. Current/latest symlinks or mutable alias names are convenience only, never evidence references.

### Flush and durability profile

- `ERROR` and `WARNING` records flush immediately through configured local and standard-output handlers.
- `INFO` and `DEBUG` records may be buffered for no longer than one elapsed second. Losing that final diagnostic interval during a power/process failure is accepted because trading truth is journaled separately.
- Diagnostic files are not `fsync`ed per record. Rotation/close performs ordinary flush/close; the system does not confuse diagnostic-file durability with journal transaction durability.
- Standard output receives the same redacted structured record for a later Azure collector. Local retention remains available when collection is delayed or unavailable.
- Duplicate-sink delivery uses the diagnostic log record identity/process sequence where available for investigation; duplicate log collection has no economic effect and need not participate in domain idempotency.

### Health and pressure behavior

Expose current/maximum directory bytes, oldest/newest retained times, active-segment bytes/age, rotation/compression failures, sink write failures, buffered queue depth/oldest age, sampling/aggregation/drop counts, and active diagnostic-session projected/actual volume.

Before enabling or extending DEBUG, the studio estimates whether the remaining local allowance can contain the requested scope/duration from recent observed volume. A warning does not automatically authorize deletion of authoritative evidence; the operator may narrow the diagnostic scope. Exact disk-pressure alert thresholds and response are fixed with the metrics/alert and observability-failure decisions.

### Consequences

- Normal operation retains approximately one week of immediately accessible diagnostics while high-volume DEBUG cannot grow without a hard local bound.
- A long-term Azure log-retention decision can change independently because standard output carries the same schema.
- Up to one second of INFO/DEBUG may be absent after abrupt failure, which is acceptable only because material domain evidence and incidents use durable journal/outbox paths.
- Compression and cleanup jobs need fault tests for crash, permission failure, full disk, corrupt segment, and concurrent reading/export.

### Declined alternatives

- **Daily rotation only:** does not bound one high-volume DEBUG file before disk pressure develops.
- **Size-only rotation:** bounds segments but leaves low-volume files open indefinitely and weakens time-based navigation/cleanup.
- **Standard output only:** makes local investigation dependent on collector/service-output availability.
- **Unbounded local retention:** competes with journal/archive/backups on the small Azure disk and turns debugging into a safety risk.

## Curated low-cardinality operational metrics

Selected by the operator on 2026-07-17: expose a bounded vendor-neutral metric contract across every critical operating concern. Metrics are current/history projections for dashboards, capacity, and alerts; they never become authority for fills, balances, orders, accounting, reconciliation, safety transitions, or promotion evidence.

### Metric-contract rules

Every metric declares its stable name, type, unit, meaning, owner, source, update/reset behavior, allowed labels/values, expected collection interval, staleness interpretation, alert consumers, and whether it is meaningful in research, replay, paper, Testnet, and/or live mode.

- Use monotonic counters for occurrences/bytes, gauges for current bounded state or age, and histograms for latency/size distributions. Summaries with process-local quantiles are avoided because they do not aggregate reliably.
- Names include base units such as `_seconds`, `_bytes`, `_total`, or exact asset/unit metadata where relevant. Ratios declare `0..1` rather than mixing percentages and fractions.
- Financial metric values may use monitoring-compatible floating representation because they are diagnostic projections. Exact source-decimal values and boundary decisions remain in the journal; dashboards link to that evidence.
- Counter reset after restart is valid and visible through process/platform context. A reset is not interpreted as a negative occurrence count.
- Missing/stale metric samples never establish healthy state. Health endpoints and the external dead-man contract use explicit age/status evidence.
- Metric generation cannot run in the deterministic domain core or change a domain decision. Accepted domain thresholds emit canonical timer/trigger events; metrics merely expose the observed state/result.

### Allowed and prohibited labels

Allowed labels are fixed, enumerated, and small: mode, component, bounded source/channel/endpoint class, operation class, outcome class, safety posture, lifecycle state, reconciliation state, incident/alert severity, event family, asset, and configured supported symbol. Free-form values are normalized to an `other`/typed failure class only when that mapping does not hide a material journal fact.

Metric labels must not contain `run_id`, event/decision/command/order/fill/correlation/reconciliation/incident/alert-delivery identity, venue client/order/trade IDs, dataset/file/object identity, exact timestamp, URL/path/query, exception class/message/stack, operator-supplied text, configuration digest, or raw error text. Those values live in journal/log evidence. Research/job detail uses persisted job views and bounded aggregate metrics, not one series per trial/job.

### Minimum MVP metric catalogue

| Area | Required measurements |
| --- | --- |
| Runtime/platform | Process/external heartbeat age; process start/restart count; frozen-startup phase; event-loop lag; CPU time/utilization; resident/virtual memory; open descriptors/handles; thread/task count; disk free/used bytes and inode-equivalent where applicable; runtime/venue clock offset |
| Market streams/archive | Connection and continuity state by bounded channel; last event/receipt age; source-to-receipt delay histogram; gap/duplicate/out-of-order/conflict totals; normalization/validation failures; capture/archive queue depth and oldest age; captured/written bytes/events; archive/checksum failures |
| Venue/control | Authenticated control-path availability/age; REST request duration/count by operation/outcome; WebSocket reconnect/rotation/overlap/gap totals; rate-limit utilization and `429`/`418` totals; command dispatch/outcome totals; unknown-outcome count/oldest age; cancellation and evidence-query backlog |
| Journal/persistence | Admission/processing/commit duration histograms; admitted pending count/oldest age; outbox pending count/oldest age; transaction/busy/lock/integrity failure totals; database/WAL bytes; projection lag; snapshot age/duration/failure; replay event rate/duration/divergence; schema/migration state |
| Trading/lifecycle | Active run presence and lifecycle state; effective managed order count by side/status class; rung obligations/pending paired quantity; range-exhausted state; paper/venue fills and completed cycles totals; bootstrap/terminal attempt state; ordinary refusal/rejection totals by bounded reason |
| Allocation/accounting/risk | Approximate current allocation quantities by supported asset; committed/uncommitted capital; current/conservative liquidation equity; high-water mark; drawdown and daily-loss utilization; live-capital utilization; inventory/fee coverage; invariant evaluation/failure totals; current safety posture/latches; distance/utilization to configured risk boundaries |
| Reconciliation/recovery | Reconciliation duration/success/failure; current item count by accepted state; decision-material/unexplained count; oldest pending age; foreign activity total/current unresolved; last full reconciliation age; startup/recovery phase/duration; repair/approval totals |
| Observability/operator | Log records/bytes by bounded level/component; aggregation/sampling/drop/write/rotation/compression totals; redaction matches/failures; DEBUG session state/bytes; active incident count by severity; alert attempt/delivery/failure/acknowledgement age; backup/export/restore age/duration/result |

Metric names and bucket boundaries are fixed in an implementation catalogue generated from this contract. Bucket selection covers the already accepted millisecond-to-minute deadlines without creating a separate bucket per observed value; the exact collector/Azure mapping belongs to deployment research.

### Worked example

`grid_reconciliation_items{state="pending_evidence"}=1` and `grid_reconciliation_oldest_pending_seconds=7` expose that reconciliation is waiting. The affected `reconciliation_item_id` is intentionally absent from metric labels; the dashboard links to the current journal projection/log correlation for exact investigation.

### Consequences

- One small active grid yields a predictable time-series count suitable for the minimum Azure target and later venue/multi-run expansion.
- Every accepted operational/safety area is visible without exporting one series per event or order.
- Dashboards and alerts can change collectors without changing domain semantics.
- A metric-cardinality budget and automated label tests become release checks; new arbitrary labels are rejected.

### Declined alternatives

- **Metric per journal identity/fact:** creates unbounded series growth and turns a monitoring system into a costly incomplete event store.
- **Infrastructure metrics only:** cannot detect stale decision evidence, unknown commands, reconciliation backlog, accounting failure, or risk posture.
- **Logs as the sole metric source:** makes health/alerts dependent on delayed log ingestion/search and diagnostic retention.
- **Financial metrics as accounting authority:** monitoring floats and sampling cannot replace exact native-asset postings and journal reconstruction.

## Layered health and external dead-man monitoring

Selected by the operator on 2026-07-17: expose distinct process liveness, service readiness, decision readiness, canonical trading posture, and recovery status. No combined green indicator may imply that a responsive process is authorized to trade.

### Health surfaces

| Surface | Question answered | Required evidence and consequence |
| --- | --- | --- |
| Process liveness | Is the process/main event loop responding now? | Minimal local response and event-loop progress; may drive infrastructure restart, never trading permission. |
| Service readiness | Can the API/studio safely serve durable read/control workflows? | Database readable, schema compatible, required migrations complete, API/control application initialized. Readiness may be true while trading is frozen. |
| Decision readiness | Could the next possible canonical event be admitted and processed safely under current deadlines? | Required market/account/control evidence fresh and continuous, journal persistence available, canonical state recovered/reconciled, clock/rules valid, and applicable command authority evaluable. |
| Trading posture | Which commands are canonically permitted? | Direct projection of accepted lifecycle/safety posture, latches, reason codes, and triggering evidence; health code cannot override it. |
| Recovery status | What must finish before consideration of resume? | Frozen-startup phase, snapshot/tail-replay result, journal/invariant result, Binance reconciliation, stream/control freshness, incident state, and required operator approval. |

Responses use stable machine-readable status/reason codes, observation times/ages, applicable deadlines, and evidence identities/links. They do not include secrets, full balances/orders, signed URLs, raw exception messages, or an unauthenticated detailed incident dump. Public/network exposure and authentication belong to the security/deployment specifications; detailed surfaces default to protected access.

### Collection and heartbeat profile

- In-process metric state updates event-driven where material and is exposed/collected at least every 15 seconds in normal operation.
- The trading process emits a generation-identified heartbeat to a monitoring path outside the process every 30 seconds. The payload contains only deployment/process-start identity, current high-level health/posture code, emission time, and counter/sequence needed to detect stale duplicates.
- The external monitor evaluates its own receipt time and creates a critical dead-man alert after two elapsed minutes without a fresh valid heartbeat, matching the accepted risk profile. Four nominal intervals describe the expected detection opportunity; the rule is elapsed time, not merely a counter of four messages.
- Application-reported “healthy” cannot suppress the external missing-heartbeat rule. Conversely, external heartbeat receipt proves only liveness of that path, not decision readiness or safe trading state.
- Health endpoint failure may trigger process/platform action; restart still enters frozen startup and never automatically resumes orders.

### Worked example

After a private user-stream continuity gap, the process and UI respond and SQLite is readable. Health reports liveness/readiness `healthy`, decision readiness `unavailable` with reason `private_stream_continuity_unproven`, canonical posture `FROZEN`, and recovery status `awaiting_authenticated_reconciliation`. A single green `/health` response would be materially misleading.

### Consequences

- Azure restart logic, operator status, and trading authorization cannot accidentally consume one overloaded health boolean.
- External monitoring covers process death and the case where the application cannot emit its own alert.
- Health tests must exercise contradictory combinations, such as live process plus frozen trading, ready UI plus unavailable persistence writes, and recovered journal plus pending operator approval.
- Five surfaces add several small endpoints/projections, not five independent health engines; all derive from the accepted state/evidence contracts.

### Declined alternatives

- **One combined green/red endpoint:** conflates process availability, read service, evidence freshness, recovery, and trading permission.
- **Process liveness only:** supports restart but cannot diagnose whether market/account/control facts are safe for decisions.
- **Dashboard without machine health surfaces:** cannot reliably support external dead-man detection or platform automation.
- **Automatic resume when every health check is green:** bypasses frozen-startup reconciliation and explicit operator authority.

## Minimal safety-aligned service objectives

Selected by the operator on 2026-07-17: use a small operational objective set tied directly to accepted safety/promotion boundaries rather than generic enterprise uptime or low-latency trading targets.

### Qualification availability

The previously accepted qualifying-paper contract remains authoritative:

- at least `99.5%` decision-ready availability across the complete uninterrupted 30-to-90-day qualifying observation interval;
- no single unplanned contiguous decision-unavailable interval longer than 30 minutes;
- planned maintenance, fault drills, recovery, Azure interruptions, and every safety-frozen interval remain in the denominator; and
- continuity/correctness/reset failures remain independently disqualifying even when the percentage passes.

No separate VM-up, process-up, WebSocket-connected, or UI-available percentage may be presented as equivalent qualification evidence.

### Normal-load latency and freshness objectives

| Operation | Objective |
| --- | --- |
| Journal processing transaction commit | p99 duration no greater than 250 ms |
| Runtime receipt of eligible market/account fact through completed processing transaction | p99 duration no greater than 1 elapsed second |
| Committed dispatch-ready command through first dispatch attempt | p99 duration no greater than 1 elapsed second while control path is available and no accepted deliberate backoff/defer condition applies |
| Collected health/metric observation age | no greater than 30 elapsed seconds |
| Protected local/deployment health endpoint response | p95 duration no greater than 500 ms |

Latency distributions are evaluated by mode/component on rolling 15-minute windows and reported at p50/p95/p99 plus maximum/count. An objective breached continuously for five elapsed minutes creates or updates one warning incident. A brief percentile excursion remains measured and visible but does not create repeated alert noise.

Eligibility/exclusion is typed, not manually edited: an accepted rate-limit backoff is excluded from dispatch-ready latency until its due event, while queueing after it becomes dispatch-ready is included. Injected fault intervals carry explicit tags and remain included in decision-ready availability even when excluded from a normal-load latency percentile. Missing/invalid measurement makes the objective unknown, never passing.

### Relationship to safety

- Objective breach is early operational warning. It changes canonical posture only if an accepted freshness, persistence, control-path, deadline, or other safety trigger is also reached through its canonical event.
- Existing first-live limits remain stricter where applicable: executable price/valuation age 5 seconds, strategy input age 15 seconds, authenticated control-path outage 10 seconds, reconciliation at least every 60 seconds, clock offset 500 ms, and external heartbeat loss two minutes.
- Service objectives cannot extend those deadlines, excuse a stale input, or compensate for failed evidence.

### Zero-tolerance correctness requirements

The following are invariant/gate failures rather than SLO percentages or “error budgets”:

- lost, duplicated with repeated effect, reordered, or unexplained material journal evidence;
- any external trading command transmitted before its durable outbox commit;
- missed admitted/authoritative fill or duplicated economic effect;
- unexplained accounting, order, fee, balance, inventory, reservation, or reconciliation difference;
- unsafe automatic recovery/resume, invariant failure, incomplete referenced evidence, or deterministic replay divergence; and
- secret leakage or unproven critical-alert/dead-man delivery required by promotion.

### Consequences

- Five measurable performance guardrails reveal a struggling minimal Azure node before safety deadlines are routinely crossed.
- The system avoids pretending a personal single-node grid needs exchange-colocation latency or enterprise API availability.
- Azure sizing must demonstrate these objectives under expected paper/live load plus bounded research/background contention.
- Objective calculation, missing-sample behavior, deliberate backoff classification, and warning deduplication require executable tests.

### Declined alternatives

- **Aggressive 99.9%/sub-250-ms end-to-end profile:** is unnecessarily brittle and costly for the selected single-node, non-HFT MVP before measured need exists.
- **Safety deadlines only:** detects degradation only when it is already severe enough to restrict/freeze operation.
- **Measurements without thresholds:** produce charts but no consistent warning, qualification context, or capacity evidence.
- **Treat correctness failures as a small allowed error rate:** contradicts exact accounting, replay, and no-duplicate-exposure requirements.

## Lightweight selective diagnostic spans

Selected by the operator on 2026-07-17: trace multi-step technical workflows through structured log span records, without deploying a separate trace database, agent, or Azure/Application Insights dependency in the MVP.

### Mandatory traced workflows

- canonical event admission and journal processing transaction;
- command outbox commit, dispatch, venue response/timeout, and evidence/reconciliation path;
- WebSocket connect, planned rotation/overlap, disconnect, gap detection, backfill, and continuity proof;
- frozen startup, snapshot selection/load, journal-tail replay, projection rebuild, invariants, and recovery reconciliation;
- scheduled/material reconciliation and its authenticated evidence queries;
- protected operator/API control requests, approval, activation confirmation, pause/stop/emergency action, and resulting application workflow;
- database backup/restoration, schema migration, evidence export/import, archive compaction, and promotion-bundle generation; and
- critical/warning alert construction, outbox dispatch, delivery result, and acknowledgement ingestion.

### Span schema and context

Each span has a diagnostic `trace_id`, unique `span_id`, optional `parent_span_id`, stable operation code, component, start/end UTC observation, monotonic duration, typed outcome/error class, sampling/capture reason, and applicable durable run/event/sequence/correlation/command/order/reconciliation/incident identities.

- Trace identity groups one technical call/workflow execution; correlation identity groups the durable business operation. Neither replaces the other.
- Start and completion/failure records are emitted for material workflows so a crash can leave visible incomplete diagnostic work. Ordinary short child spans may emit a single completion record containing start/duration.
- Duration uses a monotonic clock; UTC fields support cross-record navigation but do not determine trading state.
- Span attributes follow the selected central redaction contract and bounded event-code schemas. Request/response bodies, signed queries, credentials, exact secret-bearing configuration, and arbitrary object dumps are prohibited.
- Span/log emission happens outside the deterministic core. Journal processing remains valid even if a diagnostic span is missing; the logging-health contract detects material span loss separately.

### Capture policy

- Retain 100% of spans for trading commands/outcomes, reconciliation/recovery, safety/incident/alert delivery, operator controls/approvals, migration, backup/restore, and evidence export/import.
- Do not create retained per-update spans for ordinary high-rate trade, BBO, depth, or candle input. Their delay/throughput uses histograms and aggregate diagnostics; the journal/archive retains exact decision evidence.
- A diagnostic capture session enables full eligible child spans for its selected component/run/correlation/order/incident for at most the accepted 30-minute duration.
- Research search trials and UI polling use bounded aggregate job/request spans; no trace per market bar or optimization trial is retained by default.
- Trace/span IDs are prohibited metric labels and are stored only in structured logs/diagnostic views.

### Compatibility seam

The application instrumentation facade uses standard trace/span concepts and injectable context but has one MVP sink: the structured JSON logging pipeline. A later OpenTelemetry exporter may consume the same facade if multiple processes, richer Azure operations, or another venue creates genuine cross-process needs. OpenTelemetry propagation/backend configuration is not an MVP dependency.

### Worked example

Trace `T55` starts from journal command `C77`, contains child spans for outbox dequeue, signed-request construction without secret attributes, Binance HTTP attempt, timeout classification, authoritative order query, and reconciliation completion. Durable correlation `K31` still retrieves the complete business order lifecycle; `T55` explains where the technical time was spent.

### Consequences

- Timeout, startup, recovery, and export latency can be decomposed without manually aligning unrelated log timestamps.
- The existing JSONL/local/Azure-log path carries spans, so there is no new service or storage system.
- High-rate market inputs do not create a trace-volume cost center.
- Instrumentation and parent-context tests are required, but a later exporter can be added without modifying domain behavior.

### Declined alternatives

- **Full OpenTelemetry/Azure tracing now:** provides richer visualization but adds SDK/collector/backend/sampling/cost complexity without a distributed system.
- **No tracing:** leaves multi-step timeouts, recovery, and control operations to manual log-timestamp archaeology.
- **Trace every canonical event/market update:** duplicates high-rate evidence and creates disproportionate storage/noise.
- **Use trace identity as business correlation:** diagnostic executions can retry/restart, while the durable order/incident operation must retain one stable correlation across them.

## Durable root-condition incident lifecycle

Selected by the operator on 2026-07-17: create one durable incident for one materially affected root condition and update it across repeated occurrences, acknowledgement, recovery, resolution, and review. Alert deliveries are attempts to notify about that incident, not separate incidents and not the source of safety state.

### Incident identity and fingerprint

Every incident has an immutable `incident_id` and a deterministic fingerprint over the stable trigger/rule identity and version, affected deployment, applicable run/allocation, bounded component/source/channel, and the narrow typed subject identity required to distinguish concurrent material conditions, such as a reconciliation item or managed order. Free-form error text, stack trace, timestamp, trace ID, retry number, and changing message wording are excluded from the fingerprint.

- The fingerprint is for deduplication, not a substitute for causal evidence. Every occurrence links its triggering event, correlation, current evidence, posture, and alert deliveries.
- Conditions with different safety/recovery actions do not share a fingerprint merely because they have the same exception class.
- One causal event may open/update several independently actionable incidents only when their declared rules and recovery/owners genuinely differ; tests prevent accidental alert multiplication.

### Lifecycle states

| State | Meaning |
| --- | --- |
| `OPEN` | The material condition is active or not yet proven cleared and has not been acknowledged. |
| `ACKNOWLEDGED` | An authenticated operator has seen the incident and recorded acknowledgement context; the condition may remain active. |
| `RESOLVED` | Authoritative evidence proves the trigger is no longer active and every required automated recovery/reconciliation/invariant condition has passed. Required operator review may remain. |
| `CLOSED` | The required operator review/disposition is complete and the incident is no longer active. Closure preserves all evidence and maximum severity. |

Resolution and acknowledgement are orthogonal in reality: a condition may recover before the operator sees it. The durable lifecycle records both timestamps/actors independently while presenting the most actionable state. A resolved unacknowledged warning/critical remains pending review and cannot be closed automatically.

### Occurrence and recurrence rules

- Repeated matching triggers update the open incident's exact occurrence count, first/last occurrence, current/maximum severity, current impact/posture, deadline, and newly linked evidence rather than creating another incident or notification storm.
- Severity follows the accepted critical/warning/informational taxonomy and may escalate automatically when new evidence crosses a stronger rule. Maximum-ever severity never decreases or disappears; current impact may show recovered only after evidence proves it.
- Acknowledgement records operator identity, authenticated session/action identity, time, comment/reason, viewed evidence digest, and any declared next action. It cannot change lifecycle/safety posture, clear a latch, repair accounting, mark reconciliation successful, stop notification through an unsafe route, or grant resume/activation authority.
- `RESOLVED` requires the rule-specific authoritative recovery contract. Silence, elapsed time, a green process check, metric disappearance, or a successful retry alone is insufficient unless that exact evidence is the declared recovery proof.
- Recurrence before closure returns the same incident to active state, preserves prior acknowledgement/resolution history, increments recurrence/occurrence data, and applies the alert repetition/escalation policy.
- Recurrence after `CLOSED` creates a new incident linked through `previous_incident_id`/fingerprint history so distinct operating episodes remain measurable.
- Critical and warning incidents require explicit closure review. Expected informational transitions remain journal facts/notifications and do not create incidents unless a declared rule requires operator follow-up or evidence collection.

### Incident contents

Retain trigger/rule version, fingerprint inputs, first/last/acknowledged/resolved/closed times, occurrence and recurrence counts, current/maximum severity, affected scope, current/required posture, causal/correlation/evidence links, metrics/log/trace navigation, alert attempts/deliveries, recovery checklist/state, authoritative resolution evidence, operator actions/comments, promotion/qualification consequence, and immutable transition history.

### Worked example

An outcome-unknown order causes reconciliation to retry 50 times while waiting for authoritative venue proof. One incident records 50 occurrences, the first/last times, current deadline, related command/order/reconciliation identities, notifications, and recovery. It does not generate 50 incidents. If it is resolved and reviewed/closed, a later unrelated occurrence creates a new incident linked to the earlier episode.

### Consequences

- The operator sees actionable conditions rather than an unbounded notification stream.
- Incident duration, recurrence, acknowledgement delay, recovery delay, and maximum severity become measurable without parsing logs.
- Rule-specific resolution and safety remain authoritative; incident UI buttons cannot manufacture recovery.
- A fingerprint catalogue and state-machine tests are required for every material risk/observability rule.

### Declined alternatives

- **Incident per occurrence:** creates storms, fragments recovery history, and makes acknowledgement meaningless during repeated failure.
- **Manual incident creation from logs:** can miss process death and failures that prevent normal UI/log inspection.
- **One global system incident:** lets unrelated security, persistence, market, and order conditions overwrite one another's evidence and recovery.
- **Auto-close when a metric returns to normal:** can hide unresolved accounting/reconciliation, missed evidence, and required operator review.

## Severity-routed external alert destinations

Selected by the operator on 2026-07-17: critical incidents notify both email and a mobile channel and remain prominent in the authenticated studio. Warnings use email/studio initially and add mobile notification when persistence/escalation rules require it. Informational facts remain in the studio timeline and an optional daily digest.

### Destination policy

| Severity/use | Required destinations |
| --- | --- |
| Critical incident | Immediate email, immediate mobile push or SMS, prominent persistent studio indication, and durable incident/alert-delivery history |
| Warning incident | Immediate email and studio indication; mobile delivery when the accepted repetition/persistence/escalation rule triggers |
| Informational notification | Studio timeline; optional batched daily email digest, without mobile interruption by default |
| External dead-man | Generated from a monitoring path outside the trading process/VM and delivered through the critical email/mobile policy even when the application cannot report |

The exact Azure service, push/SMS provider, email route, quotas, and monthly cost are selected in current Azure/deployment research. The application depends only on a versioned notification port and durable delivery/outcome contract. At least one tested critical path must remain external to the process and VM; configuring two destinations inside a failed application process does not satisfy the rule.

### Notification payload

Every external notification contains only:

- current and maximum incident severity plus stable incident/event code;
- incident identity and high-level bounded affected scope, including symbol/run label only when the accepted privacy policy permits it;
- canonical trading posture and whether exposure/state is known;
- first/current occurrence time and concise reason/action summary;
- delivery sequence/update reason; and
- a protected authenticated studio URL/navigation identity for details.

Notifications exclude credentials, signatures, headers, tokens, signed links with trading authority, exact balances/equity, complete quantities/orders/fills, account identifiers, raw exception/payload text, reconciliation values, and operator comments. The studio/journal supplies exact evidence after authentication.

### Control and delivery rules

- Every external notification is a durable alert-outbox command linked to one incident, destination class, redaction-policy version, attempt identity, and idempotency key. Provider acceptance and confirmed/failed delivery where available are appended facts.
- Acknowledgement, resolution, closure, resume, activation, disposal, allocation repair, and any other control action occur only through the authenticated operator studio/API. Replying to email, tapping a push action, or following an unauthenticated/magic trading link cannot change state.
- An external link may navigate to the incident only after normal authentication and authorization; it carries no secret or reusable control authority.
- Failure of one destination does not cancel the other. Exhaustion of all required critical delivery paths creates/updates a separate critical observability incident and remains visible to the external dead-man path.
- Destination configuration and test results are versioned, protected operator settings. Changes are audited and require a test notification before being considered qualified.
- Before paper qualification and real activation, email, mobile, external dead-man, provider failure, duplicate delivery, delayed delivery, acknowledgement ingestion, and secret-redaction cases are deliberately tested.

### Consequences

- A sleeping/away operator has two practical opportunities to see a critical condition without keeping the studio open.
- Email carries context/history while mobile provides urgency; the studio remains the only control surface.
- Provider-specific integration and cost stay outside the domain core and can be replaced later.
- Mobile escalation must be carefully deduplicated/repeated to avoid notification fatigue; its schedule is the next decision.

### Declined alternatives

- **Email only:** is cheap but may be delayed or silently filtered and depends on mail-client notification configuration.
- **Mobile only:** gives urgency but weaker durable context and one device/provider failure path.
- **Studio only:** cannot notify when the studio is closed or the trading process/VM is dead.
- **Actionable email/push trading controls:** expands attack surface and bypasses the authenticated evidence/review workflow.

## Bounded alert repetition and escalation schedule

Selected by the operator on 2026-07-17: repeat unacknowledged critical alerts quickly and then hourly, use slower reminders after acknowledgement, and escalate persistent warnings to mobile without automatically changing their canonical incident severity.

### Critical schedule

- Initial email and mobile delivery are queued immediately when the critical incident opens/escalates/reopens.
- While active and unacknowledged, queue reminder deliveries at 5, 15, and 30 elapsed minutes from the initial qualifying occurrence, then every elapsed hour.
- After acknowledgement, stop the urgent unacknowledged sequence and send one reminder every four elapsed hours while the condition remains active.
- New evidence that worsens impact, creates/expands exposure uncertainty, changes required action, escalates severity, or reopens a resolved incident sends an immediate update and restarts the applicable schedule, regardless of earlier acknowledgement.
- Authoritative resolution sends one immediate recovery notification to email/mobile and studio. It does not imply closure; required review remains visible in the studio.

### Warning schedule

- Initial email/studio delivery is queued immediately.
- If active and unacknowledged after 30 elapsed minutes, add a mobile notification.
- While active and unacknowledged, repeat at six-hour intervals after that escalation.
- After acknowledgement, send one reminder every 24 elapsed hours while active.
- If a declared trigger crosses into critical severity, the incident records escalation and the critical schedule starts immediately. Mere operator non-acknowledgement does not by itself change canonical risk severity, although it changes notification routing.
- Authoritative resolution sends one email/studio recovery update; mobile recovery is sent when mobile warning escalation was previously used.

### Provider retry and deduplication

- A failed individual provider attempt retries after 1, 5, and 15 elapsed minutes using the same logical delivery/idempotency identity with a distinct attempt identity.
- A confirmed provider acceptance/delivery stops transport retry for that destination but not the incident reminder schedule.
- Unknown provider outcome is queried/reconciled where the provider supports it; otherwise a same-idempotency retry is permitted because notification duplication has no trading effect and is preferable to silent loss.
- Exhausting required delivery attempts updates the alert-delivery failure incident and uses every remaining independent path. The external dead-man monitor maintains its own durable schedule when the trading process is unavailable.
- Reminder calculation persists next-due time and schedule version so restart neither loses nor multiplies reminders. Overdue reminders are coalesced into one immediate current-state update, not replayed as a burst of every missed message.

### Acknowledgement and control boundary

- Studio acknowledgement records incident/evidence digest, operator/action identity, time, optional note, and current next action. It takes effect only for notification scheduling.
- Acknowledgement cannot suppress immediate worsened/reopened updates, external dead-man detection, provider-failure reporting, required resolution/closure review, or any canonical risk/lifecycle action.
- Operator unavailability or failure to acknowledge never authorizes resume, new exposure, allocation/accounting repair, or extra liquidation beyond the accepted safety state machine. The current safety posture remains fail-closed under its own rules.
- Critical alerts and escalated warnings ignore informational digest/quiet-hour preferences. Informational notifications may be batched; safety notifications cannot be silently deferred for convenience.

### Worked example

A critical unknown-order incident notifies at minute 0, 5, and 15. The operator acknowledges at minute 18; the minute-30/hourly unacknowledged reminders stop. If the condition remains active, the next reminder is four hours after acknowledgement. A conflicting fill then appears at minute 40, causing an immediate update despite acknowledgement and restarting the appropriate critical schedule from the worsened evidence.

### Consequences

- Critical conditions remain hard to miss without producing five-minute noise indefinitely after the operator responds.
- Persistent warning conditions become mobile-visible after 30 minutes while short self-recovering warnings remain email/studio only.
- Durable next-due state and idempotency make restart/provider duplication testable.
- The schedule creates some mobile/email cost, bounded by incident deduplication and acknowledgement.

### Declined alternatives

- **Notify once:** permits filtering, delay, or operator distraction to hide a critical condition indefinitely.
- **Repeat every five minutes until resolution:** creates alert fatigue during acknowledged long-running recovery and encourages unsafe muting.
- **No default schedule:** makes new incident rules easy to ship without adequate escalation.
- **Treat non-acknowledgement as trading authority:** conflates human availability with economic state and could trigger unsafe actions.

## Continuous essential and targeted market-evidence capture

Selected by the operator on 2026-07-17: during an active paper/live run, retain every raw trade and best-bid/offer update for the active symbol, continuously prove stream/depth continuity, retain depth relevant to actual decisions/obligations, and keep only a bounded temporary raw diff-depth buffer unless a material incident seals it.

### Active-run continuous capture

For the exact active paper/live interval, capture with source identity/sequence, event/received/admitted times, raw-parent digest, normalizer version, gaps/duplicates/conflicts/repairs, and manifest segment:

- every Binance raw trade event for the selected symbol;
- every `bookTicker` best-bid/offer change;
- all diff-depth update identities/ranges needed to prove stream continuity and rebuild status;
- normalized depth changes at prices currently relevant to one or more managed paper/live orders, their nearest two observed price levels on each side, current top-20 executable levels, and the accepted terminal-disposal price band; and
- the exact REST book snapshots and buffered bridging diff updates used to initialize/rebuild local depth state.

The runtime may receive/process the full diff stream needed to maintain the one-symbol local book, but does not persist the complete full-depth feed outside the bounded incident buffer. Target membership changes are versioned evidence: when a paper/live order becomes resting, the runtime records the targeted price set and obtains/links a sufficiently authoritative current snapshot before using queue-ahead depth.

If the REST snapshot's accepted maximum depth does not include the order price, a stream gap breaks continuity, an update range does not bridge, or targeted evidence is otherwise missing/inconsistent, queue position becomes unavailable. Paper execution downgrades to the accepted no-depth strict-trade-through policy; it never assumes zero queue or reconstructs favorable missing depth.

### Snapshot/rebuild triggers

Obtain and journal/reference a rate-limit-safe book snapshot plus buffered-diff bridge at:

- initial active-run depth initialization;
- start of tracking for a newly resting managed order when current retained state cannot authoritatively cover its price;
- detected diff-depth gap, invalid bridge, rotation failure, or continuity rebuild;
- recovery/startup before depth-dependent decision readiness;
- start of a material depth/liquidity/terminal incident where the current snapshot is safely obtainable; and
- operator-requested bounded diagnostic capture when it cannot weaken command/control capacity.

Snapshot failure or rate-limit pressure never triggers an unsafe retry storm. Existing control-capacity and freshness rules decide posture; the no-depth paper fallback is permitted only where the accepted execution policy permits it and is fully visible in qualification evidence.

### Bounded raw incident buffer

- Maintain a rolling five elapsed minutes of raw diff-depth frames for the active symbol in a bounded local ring, with exact frame/update identities and checksums.
- A critical incident, a warning materially related to market/stream/order/fill/account/reconciliation/liquidity/terminal behavior, or an authenticated operator capture request seals the preceding five minutes and begins a fifteen-minute post-trigger capture.
- A matching/relevant new trigger extends the end to fifteen minutes after its latest occurrence. Overlapping windows merge and preserve all linked incident identities.
- Unfiltered incident capture stops after 60 continuous minutes for one merged incident window unless the operator explicitly records a bounded extension and storage/control health permits it. Continuous essential/targeted capture remains active afterward.
- Raw frames aging out without a qualifying trigger are deleted as temporary diagnostic data. They are never advertised as retained evidence.
- If the capture/persistence path failed during the incident, the manifest records exact missing intervals and cause. The system does not claim a complete pre/post window or promotion replay.

### Mode and storage boundaries

- No active paper/live run means no continuous high-rate online market capture, apart from separately requested bounded research/download work and minimum connectivity/health checks.
- Private user/order/account events, commands, fills, fees, reconciliations, and safety consequences remain journal evidence regardless of public market-window policy.
- Capture appends immutable segments locally, verifies sequence/checksum/schema, and compacts completed segments into compressed Parquet/raw archives without changing source identity/order.
- Capture throughput, ring bytes, compaction rate, disk headroom, gaps, target-level coverage, and manifest completeness are monitored and benchmarked on the minimum Azure profile.

### Worked example

A paper buy becomes resting at rung `90`. The runtime proves a snapshot/diff bridge and records depth at that price and nearby levels while retaining all trades/BBO. If an outcome-unknown order incident opens at 12:00, the sealed evidence includes raw diff-depth from 11:55 through at least 12:15. If the target price was outside authoritative snapshot coverage, the paper fill model uses no-depth strict trade-through instead of treating queue ahead as zero.

### Consequences

- Captured paper replay can reproduce conservative queue/liquidity decisions when evidence exists and explicitly shows when it does not.
- The system retains high-value pre-incident context without paying to archive full depth permanently.
- One-symbol local book processing and a five-minute ring require measured memory/disk/CPU capacity but remain bounded.
- Continuous full-depth archiving remains out of scope; future multi-symbol/IBKR capture must define separate capacity and source contracts.

### Declined alternatives

- **Trades/BBO only:** cannot reproduce evidenced queue-ahead or quantity-sensitive depth behavior when a price merely trades at the limit.
- **Permanent full-depth archive:** adds disproportionate ingestion, storage, backup, and Azure cost for one grid.
- **Begin detailed capture only after an incident:** loses the conditions that caused the failure and cannot reconstruct pre-trigger queue/continuity behavior.
- **Invent depth outside snapshot/stream coverage:** creates optimistic false precision and invalidates promotion evidence.

## Tiered evidence retention

Selected by the operator on 2026-07-17: retention follows evidential value and replay/promotion dependencies rather than one duration for every channel. Moving immutable evidence to a cheaper storage tier does not change its identity, retention class, checksum, authority, or restore requirements.

### Retention classes

| Class | Retained material | Duration and clock |
| --- | --- | --- |
| System-life authoritative | Complete trading journal for every run/mode; configurations/semantics/schemas/manifests/migrations; operator actions/approvals; accounting/reconciliation/risk/lifecycle; live venue order/fill/fee/account evidence; incident/alert lifecycle; evidence checksums/retention/deletion history | Until controlled retirement of the system and successful export/verification under an explicitly approved retirement procedure |
| System-life promotion | Historical datasets/source objects and captured paper/Testnet/first-live market/evidence bundles actually used by a promotion, activation, or live authority; successful qualifying paper/Testnet/first-live evidence; complete critical-incident bundles | Same system-life rule; stale promotion authority does not delete the evidence that justified or invalidated it |
| One-year diagnostic evidence | Failed/non-promoted paper/Testnet market captures and complete bundles; warning-incident raw capture windows/attachments; non-promoted full replay bundles | One year from the later of attempt/run closure, incident closure, final evidence use, or invalidation decision |
| 120-day metrics | Low-cardinality operational metric samples and objective/availability calculations | 120 days from sample/end of calculated interval; sealed qualifying summaries remain in system-life journal/promotion evidence |
| 30-day collected diagnostics | Centrally collected structured diagnostic logs and spans, including DEBUG | 30 days from `logged_at`; relevant subsets sealed into an incident/evidence bundle inherit that bundle's longer class |
| Local diagnostic buffer | Rotating JSONL files | Seven days or 500 MiB, whichever is reached first, under the accepted rotation policy |
| Temporary/rebuildable | Untriggered raw diff-depth ring; download/compaction/export temporary files; verified rebuildable caches/projections | Five-minute ring or bounded job lifetime; delete after non-use/verified replacement according to the owning job policy |

Derived research results not used by promotion follow their research-job policy, but any exact dataset/configuration/result later admitted into promotion moves into system-life promotion evidence before authority is granted. A source that can be downloaded again is not considered retained merely because its URL still exists; promotion retains the exact source checksum/object it used.

### Preservation and dependency rules

- Every retained artifact has a retention class, start/end calculation, owning evidence/run/incident references, storage tier/location, checksum, backup class, and current preservation status in its manifest/catalogue.
- No automatic expiry/deletion may proceed while the artifact supports an active/open run, live allocation, unexpired activation/promotion authority, unresolved/uncLOSED warning or critical incident, pending reconciliation/repair, evidence-impact review, ongoing export/restore/migration, or explicit authenticated preservation hold.
- A preservation hold records reason, actor, start, optional expiry/review time, and affected content identities. It extends retention; it cannot shorten the base class.
- Reference/dependency checks are content-identity based. An artifact is not deletable while any retained complete bundle, journal event, manifest, result, incident, or backup policy still requires it.
- Expiry is reported in advance through storage/retention health. A failed archive move, verification, or deletion never silently removes the catalogue entry or claims success.
- System-life does not mean active-disk: immutable closed artifacts may move to Azure cool/archive-equivalent storage after checksum verification and demonstrated restoration within their required recovery use.

### Privacy and legal boundary

- Retention classes apply after secret prohibition/redaction; retained trading/account/operator evidence remains sensitive and requires the later access/encryption/security controls.
- This is an engineering replay/safety policy, not tax, accounting-law, financial-regulatory, or litigation advice. Applicable legal/tax requirements may lengthen retention and create holds; they cannot be assumed satisfied by these durations.
- If later legal/privacy requirements demand deletion of data embedded in an append-only authority, the system requires a separately reviewed crypto-erasure/anonymization/evidence-impact design. It does not silently mutate journal history.

### Worked examples

**Promoted paper run:** its complete captured production market evidence and sealed promotion bundle remain system-life evidence even after the candidate later becomes stale, because they explain the activation decision and subsequent comparison.

**Failed attempt:** a non-promoted paper capture closes on 2026-08-01 and its final review occurs on 2026-08-08. With no hold/reference, its raw market bundle becomes eligible after 2027-08-08; its journal/incident/decision history remains system-life.

**Diagnostic clue:** a DEBUG span used in a critical incident would normally expire after 30 days, but the relevant subset is sealed into the critical incident bundle before expiry and inherits system-life retention.

### Consequences

- Long-term storage concentrates on exact decisions, live/private evidence, successful promotion evidence, and critical incidents rather than routine verbose diagnostics.
- A 120-day metric window covers the maximum 90-day qualifying paper observation plus review margin.
- Retention requires a dependency catalogue and expiry/hold tests, but avoids per-run ad hoc settings.
- Azure research can estimate hot/cool/archive capacity from explicit classes and measured capture volume.

### Declined alternatives

- **Retain everything indefinitely:** makes verbose diagnostics and failed captures grow without bounded value/cost/privacy review.
- **Thirty days except journal:** can delete market dependencies required to replay paper qualification or a later incident.
- **Configure each run independently:** makes evidence inconsistent and permits accidental deletion of required promotion/recovery inputs.
- **Delete when a candidate becomes stale:** confuses loss of activation authority with loss of historical decision evidence.

## Lossless immutable market-segment compaction

Selected by the operator on 2026-07-17: compact bulk captured market evidence into typed compressed Parquet segments without downsampling, reordering, or rewriting journal evidence. Raw temporary capture may be deleted only after exhaustive value/count/sequence/manifest/checksum verification of its published replacement.

### Segment policy

- Active capture appends to one bounded raw segment per declared stream/capture class and run.
- Close a segment after 15 elapsed minutes or 256 MiB of raw bytes, whichever occurs first; also close cleanly at run/lifecycle boundary, capture-schema change, stream generation change, incident-window boundary, shutdown, or storage-tier handoff.
- A crash leaves a recoverable incomplete segment marked unsealed. Recovery validates complete frames, truncates only an incomplete trailing frame under its format contract, and records exact findings before continuation into a new segment.
- Segment identity includes run/capture manifest, stream/source generation, exact source/event/processing range, schema/normalizer version, target-depth policy, closure reason, and raw checksum/byte/event counts.

### Streaming conversion

- Convert source-exact trade/BBO/depth fields, timestamp values/precision, update/trade IDs, raw-parent digests, continuity classifications, target membership, and canonical order into typed Parquet using Zstandard compression.
- Conversion streams bounded row groups of at most 64 MiB and has a 256 MiB total compaction working-memory ceiling. It cannot load a 256 MiB segment, the local book, or the incident ring as one in-memory object.
- Compaction runs at bounded low priority/concurrency and yields/pauses when persistence latency, event backlog, CPU/memory/disk pressure, control-path work, terminal activity, reconciliation, or safety deadlines require resources.
- Temporary output is written under a non-published identity. Publication uses an atomic catalogue/manifest transition only after verification; consumers never discover a half-written final object.

### Verification before raw deletion

For every source record, verify exact decoded canonical field equality and ordering between the raw segment and candidate Parquet. Also verify:

- expected/actual total and per-event-family counts;
- first/last source identity, source sequence/update ranges, event time, and processing reference;
- duplicate/gap/out-of-order/conflict/repair findings and target-depth classifications;
- exact decimals/integers/timestamp precision and null/enum/schema semantics;
- parent/raw and normalized content relationships;
- Parquet schema, row-group statistics, full-file byte length/SHA-256, and manifest checksum; and
- successful open/read by the supported replay reader plus deterministic representative/full-segment decode verification as specified by tests.

Only after the final object is durable, catalogue-visible, checksum-verified, and covered by its required backup/storage policy may the raw temporary segment become deletable. Failure retains/quarantines raw input, removes/unpublishes the candidate object, increments failure metrics, and creates a warning; inability to preserve active evidence escalates under storage/persistence failure rules.

### Non-market boundaries

- The append-only trading journal is never logically compacted, summarized, downsampled, or rewritten. SQLite physical maintenance is a separately verified database operation and cannot alter event meaning/order.
- Closed diagnostic log segments use their accepted compression/expiry policy, not the market-evidence Parquet contract.
- Metrics may follow their retention backend's storage compaction while preserving the accepted 120-day observations/summaries; they never replace journal evidence.
- Recovery snapshots are already bounded derived projections and are not combined into an authoritative “latest state” file.

### Consequences

- Exact market replay survives while bulk storage/backup/export becomes materially smaller and queryable.
- Streaming limits keep compaction compatible with a 4-GiB-class candidate node, subject to measured benchmark acceptance.
- Temporary space must accommodate raw plus candidate output and safety margin; capacity alerts must fire before conversion cannot complete.
- Converter equality, crash recovery, atomic publication, pause/yield, corrupt input/output, full disk, and version migration become acceptance cases.

### Declined alternatives

- **Keep all raw segments:** is operationally simple but expands hot storage, backup, and export unnecessarily.
- **Downsample old market evidence:** destroys exact event/queue/continuity replay and cannot support promotion evidence.
- **Rewrite the full journal/database:** mixes bulk maintenance with authoritative transactional evidence and raises corruption/recovery risk.
- **Load full segments into memory:** makes a storage optimization capable of starving the safety-critical runtime.

## Operator review status

Operator review completed on 2026-07-17. All event-journal, observability, retention, recovery-evidence, minimum-resource, failure-response, and mandatory verification decisions in this specification are accepted for MVP planning. Implementation evidence remains required before paper/live promotion; approval of this specification is not approval to trade.

### B1ms-first runtime sizing decision

The current Azure retail-price snapshot is documented in [`analysis/azure-mvp-monthly-cost-estimate.md`](azure-mvp-monthly-cost-estimate.md). It assumes one always-on PAYG Linux node in Germany West Central for 730 hours/month, a single Standard SSD, static public IPv4, first-month evidence storage, low-volume Azure Monitor use, and a conservative Azure VM Backup allowance. Prices exclude VAT, support plans, trading capital, Binance fees, SMS, high availability, and separate development/backtest compute.

Selected by the operator on 2026-07-17: start with a Linux `Standard_B1ms` (one vCPU and 2 GiB RAM) and prove or disprove its sufficiency through measurement. The selection minimizes starting cost; it does not waive any safety, replay, recovery, evidence, or qualification requirement.

The five-minute market ring remains disk-backed rather than retained wholly in RAM. Compaction is bounded, low-priority, and pausable. Backtests and other research workloads cannot run concurrently on the qualifying online node. Before the 30-day paper qualification run, a continuous 24-hour production-data benchmark plus restart/replay/reconciliation and compaction drills must measure peak/steady application and host memory, swap/page pressure, out-of-memory events, B-series CPU-credit balance, event latency, disk transaction count/headroom, evidence volume, compaction throughput, and recovery performance. Any out-of-memory event, sustained resource exhaustion, failure to preserve disk headroom, or violation of accepted latency/recovery objectives rejects B1ms for qualification and requires resize/retest.

The researched 4-GiB `Standard_B2als_v2` is the first resize target; the 8-GiB `Standard_B2as_v2` remains the next step. Their higher cost was declined as the starting assumption, not as permitted recovery options. The selected local/Blob split is documented below; application-backup cadence and recovery objectives remain open.

### Hybrid local SSD and Blob evidence storage

Selected by the operator on 2026-07-17: combine one 64-GiB Standard SSD E6 LRS managed disk with Azure Blob Storage. The local disk is the bounded active working store; Blob is the off-VM durable backup and evidence store.

The local SSD holds:

- the operating system, runtime, and deployment metadata;
- the active SQLite database and WAL;
- open raw capture segments and the disk-backed five-minute depth ring;
- raw and candidate files while one bounded compaction is being verified;
- current recovery snapshots and bounded local diagnostic logs; and
- bounded staging required for backup, upload, restore, and evidence-bundle creation.

Blob Storage holds:

- verified application/database backups and their manifests;
- closed, verified Parquet/Zstandard market-evidence segments;
- incident, promotion, activation, export, and portable evidence bundles; and
- retained closed diagnostics or other explicitly classified evidence.

Fresh durable objects use Hot ZRS by default so a single datacenter/zone failure is not also the loss of the off-VM copy. Objects become eligible for an automatic Cool-tier transition after 30 days when their recovery/retrieval requirements permit it. Archive-tier movement is not automatic in the MVP; it requires a declared restoration-time allowance and a tested restore path. Retention identity and holds remain independent of storage tier.

### Verified offload boundary

Blob cannot host the active SQLite database, WAL, open segment, or compaction workspace. For every closed object, the application:

1. seals and verifies the local source/candidate under its accepted format contract;
2. uploads under a non-published object identity using managed application credentials;
3. verifies exact byte length, SHA-256, metadata/schema identity, and successful supported-reader access;
4. atomically publishes the durable manifest/catalogue reference; and
5. deletes an eligible local closed copy only after remote durability, retention, reference, and backup requirements are satisfied.

Interrupted uploads remain unpublished and retry idempotently. A local-space warning can accelerate eligible uploads/cleanup but cannot delete unverified or required evidence. Active journal/WAL files, open segments, evidence on hold, and the only verified copy are never pressure-deletion candidates.

### Cost and capacity consequences

- The current normal planning range is approximately EUR 24-30/month before VAT for B1ms, E6, static IPv4, expected SSD transactions, first-month Blob evidence, and application-level Blob backup operation, provided collected logs remain in the free ingestion allowance.
- The 64-GiB E6 base meter costs only about USD 2.40/month more than 32-GiB E4 while doubling local space available for the operating system and raw-plus-candidate compaction coexistence.
- Blob capacity is inexpensive at the accepted one-symbol volume but grows cumulatively; the 24-hour benchmark must replace the 0.5-3-GiB/day planning assumption and set capacity/cost alerts.
- Full Azure VM Backup, 32-GiB local disk, and 128-GiB initial disk were not selected. Full VM Backup may be added later if tested application-level rebuild/restore cannot meet the selected recovery objectives.

### Declined alternatives

- **32-GiB local SSD plus Blob:** saves about USD 2.40/month but leaves materially less room for the OS, journal, open capture, compaction coexistence, logs, and restore staging.
- **128-GiB initial local SSD:** adds headroom but is unnecessary before measured evidence shows the 64-GiB working set is insufficient.
- **Blob-mounted active SQLite or WAL:** object storage does not provide the local transactional filesystem semantics required by the authoritative database.
- **Local SSD only:** a VM/disk loss could remove both active state and retained evidence and therefore cannot satisfy off-VM backup/restoration requirements.

## Application recovery objectives and recoverable points

Selected by the operator on 2026-07-17: a 15-minute recovery point objective (RPO) and a 60-minute recovery time objective (RTO) for complete loss of the online VM and its managed disk.

### Objective definitions

- **RPO:** the greatest permitted gap between the newest committed application history required for recovery and the newest verified off-VM recoverable point. During changed paper/live state, the protected journal position cannot lag the authoritative local journal by more than 15 elapsed minutes. A point older than 15 minutes may remain current only when no protected state has changed since that point, which is demonstrated by processing position rather than assumed from quiet market time.
- **RTO:** elapsed time from the first external detection of the total service/disk loss or formal disaster declaration, whichever occurs first, until a compatible runtime is provisioned, the selected point and required artifacts are restored and verified, the journal tail is replayed, invariants pass, Binance reconciliation completes, and the service is operator-accessible in a frozen non-trading posture. The objective is 60 minutes; trading resume is deliberately outside RTO.

These are operational objectives and promotion gates, not claims that Azure or Binance guarantees the outcome. An RPO breach invalidates affected qualifying evidence and triggers the separately specified observability-failure behavior; it cannot be hidden by later reconciliation.

### Recoverable-point contract

A recoverable point is a sealed manifest in Blob Storage referencing:

- one transactionally consistent SQLite application backup and its exact schema/migration state;
- first/last durable event and processing sequence covered by the backup;
- immutable configuration, build, normalizer, accounting, venue-rule, and strategy versions needed to interpret it;
- the compatible recovery snapshot identity, while keeping that snapshot explicitly derived and non-authoritative;
- all required content-addressed artifacts/evidence not already independently durable;
- creation/start/completion clocks, source VM/run identity, closure reason, byte lengths, SHA-256 values, and supported restore-reader version; and
- verification results and an explicit `VERIFIED`, `QUARANTINED`, or `EXPIRED` state.

Only a completely uploaded, checksum/reader-verified, catalogue-published point satisfies RPO. Started, partial, timed-out, incompatible, quarantined, or unverified backups do not. Multiple points remain available so restore can fall back from a corrupt or incompatible newest candidate without overwriting it.

### Restore sequence

1. Provision the declared compatible application/runtime infrastructure without trading authority.
2. Select the newest verified compatible point; if it fails, record the finding and try the next eligible older point.
3. Restore the database and artifacts into isolation, verify manifest/checksums/schema, and run database integrity checks.
4. Replay the complete available journal tail from the point's declared processing boundary and verify deterministic state hashes and accounting/risk invariants.
5. Reconnect market/user streams, fetch authoritative Binance account/open-order/trade facts, and perform the accepted reconciliation and late-fill handling.
6. Expose service readiness with canonical posture still frozen; require the accepted operator recovery/resume workflow before any new trading command.

A recoverable point never rolls Binance back and never proves that orders or fills after its boundary did not occur. Venue facts and reconciliation remain authoritative for external side effects. Missing local history within the accepted RPO is declared evidence loss, not silently invented from current balances.

### Local snapshot distinction

The already accepted five-minute/10,000-event local recovery snapshot accelerates ordinary restart and tail replay but is a derived cache and may be lost with the disk. The Blob recoverable point is the independently verified off-VM package that satisfies disaster RPO. A local snapshot alone never counts as a recoverable point.

### Acceptance evidence

The implementation must demonstrate measured point creation/verification lag, restore from newest and older fallback points, corrupt/partial/incompatible point rejection, total-VM/disk-loss provisioning, journal-tail replay, invariant verification, venue reconciliation including late fills, frozen completion, and end-to-end RTO on B1ms. The 30-day qualifying paper run cannot begin until these drills meet the selected objectives.

### Declined alternatives

- **One-hour RPO/two-hour RTO:** reduces backup activity but permits too much recent decision/evidence loss for the qualifying system.
- **Near-zero RPO/sub-15-minute RTO:** requires continuous replication and/or standby infrastructure whose cost and operational complexity are disproportionate for the single-operator MVP.
- **Resume automatically at restore completion:** confuses technical recovery with trading authorization and can act before operator review of reconciliation and evidence loss.
- **Treat Binance reconciliation as reconstruction of the journal:** current venue facts can explain external side effects but cannot recreate every internal input, decision, state transition, or causal link.

## Simple full-database recovery-point policy

Selected by the operator on 2026-07-17: create a complete transactionally consistent SQLite online backup at a nominal ten-minute cadence whenever protected durable state has advanced. The ten-minute cadence reserves five minutes within the accepted 15-minute RPO for backup completion, streaming compression, upload, retry, verification, and manifest publication. RPO is enforced by protected processing-position lag, not merely by whether a scheduler fired.

### Construction

- Use SQLite's supported online backup mechanism in bounded page batches; never copy an open database/WAL pair as ordinary files and call it consistent.
- Capture the exact durable event/processing boundary in the same backup transaction/protocol and include every dependency required by the recoverable-point contract.
- Stream compression and upload without loading the full database or compressed result into memory. On B1ms, backup working memory is capped at 64 MiB, only one recovery-point job may execute at a time, and its heavy I/O/compression phase cannot overlap market-segment compaction.
- Safety/control-path persistence, venue processing, reconciliation, and emergency behavior have priority. Backup work yields in bounded batches, but yielding cannot silently cause protected lag to exceed RPO.
- If no protected state advanced after the last verified point, the existing point still covers the current durable processing position; the scheduler records the no-change coverage check and does not upload duplicate bytes merely to refresh wall time.
- Deployment, schema migration, restore-format change, or incompatible configuration activation requires a verified pre-change recovery point before mutation and a new verified post-change point after successful validation.
- Each job uses a unique idempotency identity. A retry resumes or replaces only its unpublished candidate; it cannot overwrite a verified point.

### Retention and thinning

- Retain every verified routine point for at least 24 hours.
- Retain one verified point per UTC day for 30 days.
- Retain pre-change and post-change points for at least 30 days and until the change is verified successful with no open rollback, incident, investigation, or evidence hold.
- A recovery point referenced by an incident, promotion bundle, audit/export, or preservation hold remains until every reference/hold permits expiry.
- Expiry deletes only a manifest-selected unreferenced point after confirming a newer usable point and required daily/pre-change coverage. It never changes the system-life journal/evidence retention policy.
- Expired objects follow the separately specified secure-deletion process; a catalogue tombstone records identity, reason, authorizing policy, time, and provider outcome without retaining the deleted sensitive payload.

### Resource and failure consequences

- Complete online backups are the simpler MVP mechanism. Incremental journal-segment backup is deferred unless measured database growth, B1ms CPU credits, I/O, Blob transfer, or cost makes complete points unable to meet the accepted objectives.
- The benchmark includes the largest expected database, concurrent online processing, point creation, retry, verification, retention thinning, and restore. It measures protected-position lag and application/host pressure, not only backup duration.
- B1ms failure to produce verified points within the accepted RPO is not permission to increase cadence or skip verification. It requires the defined incident/freeze behavior and either optimization through the deferred incremental design or resize/retest.

### Declined alternatives

- **Daily full plus ten-minute incremental journal segments now:** is more storage-efficient at scale but adds a second restore chain and more version/continuity failure modes before measured need.
- **Hourly complete backup:** cannot satisfy the accepted 15-minute RPO.
- **Exactly 15-minute scheduling with no margin:** routine compression/upload/retry time could make the verified protected position older than the objective.
- **Duplicate backup on unchanged state:** consumes CPU, disk transactions, and Blob operations without improving recoverable state.

## Restore verification and disaster-drill cadence

Selected by the operator on 2026-07-17: run an automated isolated recovery-point restore every week and a complete fresh-VM disaster-recovery drill every month. A successful full drill is also required before the 30-day qualifying paper run and before first real-money activation if the most recent successful drill is older than 30 days or the recovery path materially changed.

### Per-point verification

Every recovery point continues to receive construction-time length, checksum, manifest/schema, supported-reader, and catalogue verification. This proves that a candidate is complete and readable but does not count as an executed restore test.

### Weekly isolated restore

- Provision an isolated disposable restore target, preferably outside the active VM so the test also exercises Blob access and does not consume B1ms trading resources.
- Do not provide trading-capable credentials. When reconciliation behavior is exercised, use a declared read-only Binance credential or a recorded/replay venue adapter that cannot submit, cancel, or amend orders.
- Restore the newest verified point by default; at least once per month select an older eligible fallback point so fallback logic is exercised rather than assumed.
- Verify the manifest, object checksums, database integrity, schema compatibility, journal boundary/tail replay, deterministic state hashes, accounting/risk invariants, configuration/artifact resolution, and frozen final posture.
- Record start/end clocks, selected point, build/restore-reader versions, each phase duration/result, resource use, findings, and clean disposal of the isolated target.

### Monthly full disaster drill

- Begin from a declared total VM/managed-disk-loss scenario and an externally recorded detection/start time.
- Provision a fresh B1ms deployment from the versioned infrastructure/deployment definition, retrieve the selected Blob point and dependencies, perform the full restore sequence, rebuild projections, replay the available tail, and complete read-only/recorded Binance reconciliation including late-fill cases.
- Demonstrate protected operator access and health surfaces with trading posture frozen. No drill may authorize automatic resume or emit a venue command.
- Measure the complete accepted RTO boundary. Success requires completion within 60 minutes with zero unexplained integrity, accounting, order, or evidence difference.
- Preserve the signed/checksummed drill report, manifests, exact versions, timings, and findings as qualification evidence under the applicable run/promotion/incident retention class.
- Tear down the disposable VM, disk, network identities, credentials/tokens, and temporary restore data after evidence publication under the secure-deletion contract.

### Failure behavior and change invalidation

- Any checksum, compatibility, restore, replay, invariant, reconciliation, credential-isolation, cleanup, or RTO failure creates one durable recovery-test incident and makes recovery qualification invalid until corrected and successfully retested.
- A schema/restore-reader, backup format, deployment/IaC, Blob layout/credential, encryption, reconciliation, or relevant venue-contract change invalidates prior drill evidence for that changed path and requires a new isolated restore; material recovery-path changes require a new full drill.
- A missed weekly/monthly test is observable and cannot be reported as successful recoverability. Exact trading freeze/escalation timing belongs to the remaining observability-failure decision.

### Consequences

- Corrupt backups, missing dependencies, incompatible deployments, credential leakage, and unrealistic RTO are found before a real disaster.
- Disposable testing adds a small bounded Azure cost and operational workload; both are measured and included in cost alerts rather than omitted from the budget.
- The weekly test validates restore correctness frequently, while the monthly drill proves provisioning and the complete recovery sequence without maintaining a paid standby VM.

### Declined alternatives

- **Monthly isolated restore plus pre-promotion full drill:** costs slightly less but permits ordinary restore defects to remain undetected for a month.
- **Release/promotion-only restore:** does not prove continuous recoverability during a long paper/live run.
- **Test restore on the active database/VM only:** can interfere with trading resources and fails to prove off-VM provisioning and Blob recovery.
- **Give the drill live trading credentials:** creates an unnecessary path for a test to place or cancel real orders.

## Retention-aware secure deletion

Selected by the operator on 2026-07-17: use policy-governed logical/provider deletion with durable non-sensitive audit tombstones. Do not claim that application file overwrite can physically erase SSD remaps, Blob replicas, backups, or provider-managed media. Azure encryption at rest and provider media-sanitization remain the physical-media boundary; customer-managed per-object cryptographic erasure is not an MVP requirement.

### Deletion eligibility

An object, database row/class, local file, Blob version/snapshot, recovery point, or disposable restore resource is eligible only when all applicable conditions are true:

- its declared retention period has elapsed and it is not a system-life record;
- no preservation hold, legal/incident review, promotion/activation evidence rule, audit/export, replay dependency, bundle reference, recovery chain, or active job requires it;
- deletion cannot remove the only verified copy of still-retained evidence or a required newer/older recovery fallback;
- the exact identity/version/snapshot set has been enumerated from the authoritative catalogue rather than inferred from a filename/prefix;
- any configured Azure immutability or provider minimum-retention period permits deletion; and
- the versioned retention policy authorizes deletion without an ad hoc shortening by the operator or cleanup process.

System-life journal, live accounting/order/reconciliation history, promoted evidence, and critical-incident evidence are not routine deletion candidates. A deliberate later system-decommission/legal-deletion decision requires a separately authorized plan and cannot be inferred from inactivity or cost pressure.

### Execution and provider states

1. Produce an immutable deletion plan containing identities, versions/snapshots, retention class, expiry calculation, dependency/hold checks, byte estimate, policy version, and idempotency key.
2. Recheck eligibility immediately before execution and mark the plan `DELETE_REQUESTED` without deleting the audit facts needed to explain it.
3. Delete eligible local closed/staging copies, Blob objects, versions/snapshots, recovery manifests/dependencies as a consistent set, and disposable restore infrastructure/temporary credentials.
4. Query provider state and record `PROVIDER_RECOVERABLE` while Azure soft delete/version retention can still restore bytes; record `CONFIRMED_EXPIRED` only after the provider no longer exposes a recoverable version under the configured policy.
5. Retain a non-sensitive tombstone containing identity digest, class, byte count, policy/authorization, requested/provider-expiry clocks, outcome, and incident/error reference. It cannot retain payload, secrets, sensitive paths, or enough data to reconstruct deleted content.

Deletion is idempotent. Partial/provider failures leave the plan open, retry safely, and create/escalate one operational incident. They cannot be reported as success, silently drop catalogue references, or cause progressively broader prefix deletion.

### Local and secret handling

- Local cleanup removes only catalogue-identified closed files and permissible derived rows. It never recursively deletes a computed directory/prefix or active database/WAL/open segment.
- SQLite free-page cleanup or `secure_delete` may reduce ordinary residual application bytes but is not described as guaranteed physical erasure on SSD media. Database maintenance remains separately backed up, integrity-checked, and bounded.
- Secrets should not be present in retained evidence under the accepted redaction rules. Any suspected credential/token exposure triggers immediate revocation/rotation and incident preservation; waiting for log/blob expiry is not remediation.
- VM/disk decommission deletes the Azure managed-disk resource and associated snapshots after evidence migration/verification. Provider encryption/sanitization is the media-disposition control.

### Debugging and analysis preservation

Secure deletion does not replace the selected tiered retention. Blob remains the long-term debugging/replay/analysis store: system-life live/promoted/critical evidence, one-year failed paper/Testnet and warning evidence, 120-day metrics, 30-day logs/spans, and the selected recovery-point schedule. Before ordinary diagnostic expiry, relevant records may be sealed into a referenced incident/evidence bundle and inherit that bundle's longer class. An authenticated time-bounded/reviewed preservation hold prevents deletion without altering the original class.

### Acceptance evidence

Test exact eligibility at expiry boundaries, nested dependencies, active/expired holds, Blob versions/snapshots/soft deletion, recovery-chain thinning, partial provider failure/retry, idempotency, catalogue races, path/prefix confusion, active-file protection, tombstone redaction, credential-exposure revocation, and full disposable-drill teardown. Restore must prove retained evidence still works after unrelated eligible deletion.

### Declined alternatives

- **Customer-managed per-object cryptographic erasure:** can provide stronger selective unreadability but adds Key Vault/key-isolation, rotation, loss, backup, and restore failure modes disproportionate to the personal MVP.
- **Overwrite before delete:** cannot guarantee physical overwrite across SSD remapping, Blob replication, soft-deleted versions, or provider media.
- **Keep every diagnostic forever for possible debugging:** conflicts with the accepted tiered value/cost/privacy policy; preservation holds and incident promotion retain evidence with an explicit reason.
- **Immediate deletion with no tombstone/provider tracking:** makes it impossible to prove what was authorized, whether versions remain recoverable, or why evidence disappeared.

## Graded observability and evidence-protection failure behavior

Selected by the operator on 2026-07-17: classify failures by whether they remove authoritative persistence, a required protection/recovery path, or only a replaceable diagnostic projection. The system does not freeze solely because one optional vendor view is unavailable, and it never continues creating exposure when it cannot preserve or externally supervise the evidence required to recover safely.

### Class A — authoritative or state-uncertainty failure

Examples include failed/uncertain journal admission or processing commit; SQLite corruption/integrity/constraint failure; inability to durably establish a command/outbox identity before dispatch; unexplained accounting/invariant difference; uncertain venue-order/fill state; failed required reconciliation; or incompatible event/schema/configuration evidence.

- No command whose durable prerequisite is uncertain may be dispatched.
- Enter the canonical safety freeze immediately, stop acquisition/new exposure, and initiate the accepted reconciliation/recovery path.
- Valid already-backed inventory-reducing sells may remain only when the canonical exposure-reducing-pause rules can still prove their validity. If order/state validity itself is uncertain, they are not assumed valid.
- Emergency cancellation/stop behavior may use its accepted last-resort venue path when ordinary persistence is unavailable; every attempted/late result is reconstructed through subsequent reconciliation and marked as emergency evidence loss/recovery, never represented as an ordinary committed command.
- A Class A failure is critical, invalidates affected qualifying evidence until explained/recovered, and cannot auto-resume.

### Class B — required protection or external-supervision failure

Examples include protected processing lag crossing the selected 15-minute RPO; no functioning off-VM backup publication path; no verified external critical-alert/dead-man path; inability to preserve required incident/evidence data; disk headroom/space-to-exhaustion insufficient for journal, reconciliation, emergency, and recovery writes; or failed mandatory restore qualification.

- Create/escalate one durable incident through every remaining path and freeze acquisition/new exposure at the breached objective/threshold.
- Stop nonessential DEBUG, export, research, compaction, and ordinary cleanup work first; attempt verified offload and safe catalogue-selected cleanup without deleting required/unverified data.
- Preserve valid exposure-reducing orders under the already accepted pause semantics when authoritative order/inventory state remains certain.
- A single notification destination may fail without freezing while another tested external critical path remains available; loss of every external critical path must produce the freeze no later than the accepted two-minute dead-man boundary.
- Restoring the protection removes the technical condition but does not authorize resume. Evidence impact, RPO/retention gaps, current venue facts, and incident state must be reviewed/reconciled.

### Class C — replaceable diagnostic projection failure

Examples include Azure Monitor/Log Analytics ingestion outage, dashboard/studio rendering failure, remote metric sink failure, optional diagnostic-span export failure, or one notification destination failing while another required external path remains verified.

- Continue paper/live decisions temporarily only while authoritative journal/archive persistence, internal risk/accounting/reconciliation monitors, local redacted JSONL spooling, bounded queues/storage, external dead-man/critical alerting, and protected health remain operational.
- Record destination failure, backlog/dropped-eligible-debug counters, retry outcomes, and one aggregated incident locally and through remaining destinations.
- Material events are never sampled or dropped to preserve optional DEBUG. Optional DEBUG is disabled first; bounded INFO aggregation follows its accepted rules.
- Escalate to Class B before local queue/disk capacity, diagnostic retention, operator visibility, or evidence completeness becomes unsafe. Vendor recovery drains idempotently and cannot duplicate incidents or change canonical trading state.

### Recovery and qualification

- Repairing a sink, backup, disk, or database is necessary but insufficient. Recovery verifies integrity, replays required state, reconciles Binance, classifies evidence gaps, resolves the root condition, and ends in the accepted frozen/paused posture.
- Operator acknowledgement changes notification scheduling only. The accepted authenticated recovery/resume control is required to resume trading.
- Every degraded interval is included in service-objective accounting. Class A, unexplained difference, missing required evidence, RPO breach, unsafe alerting gap, or untested recovery-path failure blocks promotion until its declared remediation/retest rule passes.
- Diagnostic-provider downtime alone does not falsify backtest/paper/live decision parity when complete authoritative and local diagnostic evidence proves identical decisions; any unprovable interval is excluded or fails qualification explicitly.

### Consequences

- A temporary Azure dashboard/log-ingestion outage does not unnecessarily cancel a safe, fully evidenced grid.
- The system cannot trade its way through loss of its journal, recovery protection, critical external supervision, or safe disk reserve.
- Exposure-reducing behavior remains available only when backing inventory and order state are still provably valid.
- Failure categories and transitions become deterministic fault-injection assertions rather than operator judgment during an incident.

### Declined alternatives

- **Freeze on every observability failure:** makes an optional dashboard or remote metric sink an availability-critical trading dependency and causes unnecessary churn/cancellation.
- **Continue whenever the strategy loop runs:** permits trading without durable causal evidence, recovery protection, external supervision, or bounded storage.
- **Drop material logs/events under pressure:** preserves process availability by destroying the evidence needed to prove safety and accounting.
- **Automatic resume when a provider recovers:** ignores possible evidence gaps, stale venue state, late fills, and the accepted operator-controlled recovery boundary.

## Mandatory risk-based fault-injection and acceptance matrix

Selected by the operator on 2026-07-17: implement a bounded deterministic fault matrix traced to accepted invariants, promotion gates, deadlines, and named failure scenarios. Exhaustive combinations are not required, but each material single fault and the small set of interaction faults below must have a repeatable injected case and explicit oracle.

### Universal oracle

Every applicable case asserts all of the following, not merely that the process stayed running:

- exact admitted/processed event, causation/correlation, command/outbox, order/fill, accounting, reconciliation, incident, and posture evidence in the expected order;
- no external command before its durable prerequisite, no duplicated logical command/order, and deterministic idempotent retry after ambiguous outcomes;
- the expected Class A/B/C classification, canonical safety posture, deadline, surviving/cancelled order set, notification schedule, acknowledgement semantics, and operator-resume requirement;
- zero unexplained balance, inventory, obligation, fee, order, fill, evidence, or state-hash difference;
- byte-identical deterministic replay results for the captured canonical input/configuration boundary;
- material logs unsampled, bounded metric labels, successful secret redaction, and an explainable incident/root-cause trail;
- restart/recovery/reconciliation behavior, including late facts, without retroactively rewriting processing history; and
- cleanup/offload/deletion behavior that cannot remove active, unverified, held, referenced, or sole retained evidence.

Any unexpected venue command, secret leakage, unexplained economic/evidence difference, missing material event, false healthy state, automatic unsafe resume, or nondeterministic replay is a hard failure. Retrying a flaky test until green is not acceptance; seeds, clocks, source payloads, injected boundaries, and scheduler order are captured and replayable.

### Required matrix

| Family | Minimum deterministic injections | Required outcome focus |
| --- | --- | --- |
| Admission/transaction/outbox | fail before/after admission commit; during processing transaction; after commit before dispatch; after dispatch before acknowledgement; database busy/locked; constraint failure | exact resume boundary, atomic batch, no command-before-commit, stable idempotency, no duplicate venue effect |
| SQLite/disk integrity | WAL/checkpoint failure; read-only/permission loss; full disk; corrupt page/index; failed integrity check; abrupt I/O error | immediate Class A/B posture, no unsafe cleanup, incident/evidence preservation, verified older-point recovery |
| Process/runtime crash | terminate at activation, bootstrap, order creation, partial fill, pair creation, cancellation, pause/stop, reconciliation repair, backup publication, compaction publication, and deletion publication boundaries | frozen restart, deterministic tail replay, exact command recovery, reconciliation before resume |
| Market streams | disconnect; stale data; duplicate/out-of-order trade; missing sequence; diff-depth gap; failed snapshot bridge; finite-stream rotation overlap/gap; clock offset/skew | source continuity evidence, no invented ordering/depth, no-depth/freeze policy, deterministic repair and decision parity |
| Binance command transport | timeout before/after send; connection reset; HTTP 429/backoff and 418-style protection; 5xx; invalid signature/time; duplicate client identity; unknown response | ambiguous-outcome recovery by query/reconciliation, bounded retry, no blind replacement, correct incident/posture |
| Venue order/fill states | `LIMIT_MAKER` rejection; filter/rounding rejection; partial/cumulative fills; multiple commissions/assets; fill during cancel; late fill after cancel/stop/restart; order missing from open set but terminal history delayed | exact net inventory/fees, cumulative pairing, valid reducing orders only, no orphan obligation, late-fill reconciliation |
| Accounting/allocation/reconciliation | manual/out-of-band account activity; allocation drift; unknown asset; fee-reserve exhaustion; unmatched order/trade; balance and history disagreement; duplicate/missing venue facts | fact-specific authority, zero unexplained difference, evidence-preserving adjustment/refusal, material operator control |
| Risk/operator control | stale input; breached economic limits; global stop-loss trigger; pause/resume; operator stop; emergency stop; duplicate/replayed operator request; expired authorization | correct posture overlay, acquisition block, permitted reducing orders, idempotent control, no acknowledgement-as-resume |
| Logs/metrics/health | remote log/metric/dashboard sink down; local queue saturation; rotation/compression failure; DEBUG session expiry; metric-cardinality attack; stale health; process hang/dead-man | Class C continuation only inside bounds, material evidence retained, escalation before local exhaustion, external alert within deadline |
| Alerts/incidents | one/all destinations unavailable; provider timeout/duplicate/late success; reminder restart; acknowledgement before/after escalation; recurrence after closure | one fingerprinted incident, idempotent delivery, accepted escalation/reminder schedule, no notification action as trading authority |
| Blob/archive/retention | upload interruption/throttle; truncated/corrupt object; checksum/reader mismatch; manifest race; tier/retrieval failure; expired/active hold; version/snapshot/soft-delete state; overbroad prefix attempt | unpublished partials, no premature local deletion, exact fallback, hold/reference safety, deletion tombstone/provider tracking |
| Backup/recovery | point duration/retry crosses lag threshold; newest corrupt/incompatible; older fallback; missing dependency; total VM/disk loss; read-only Binance unavailable; late fill during outage | 15-minute RPO/60-minute RTO evidence, Class B freeze, deterministic restore/replay, frozen reconciled completion |
| Resource pressure on B1ms | memory/page/swap pressure; allocation failure/OOM; depleted CPU credits; backup/compaction contention; high disk transactions; capture burst; local-space exhaustion forecast | bounded/yielding background work, no missed control deadline, resize/retest rejection when budgets fail |
| Redaction/security boundary | secret canaries in keys/values/headers/query strings/encoded/nested forms; authenticated-control failure/replay; credential exposure; restore target attempts venue write | no secret at any sink/bundle, fail-closed scrubber, immediate revocation incident, no trading credential in tests |

### Required interaction cases

Test only the combinations with a distinct accepted risk that a single-fault case cannot prove:

1. crash after venue dispatch with acknowledgement delayed or lost;
2. market-stream gap while an order is partially filled;
3. late fill during operator stop or restore/reconciliation;
4. disk pressure while backup and market-segment compaction are eligible;
5. remote diagnostics unavailable while one and then all external alert paths fail;
6. newest recovery point corrupt while Binance reconciliation returns delayed terminal history; and
7. retention/deletion becomes eligible while an incident concurrently establishes a preservation hold.

Additional combinations require a concrete invariant, promotion gate, incident, or architecture change; they are not added merely to increase a test count.

### Execution layers and gates

- Pure deterministic domain/property/serialization/redaction cases run on every relevant change with fixed and generated replay seeds retained on failure.
- Persistence, adapter, crash-boundary, local-resource, and injected-provider contract cases run in CI/release integration environments using simulators/proxies and disposable infrastructure without production trading credentials.
- Representative Binance protocol behavior runs on the accepted Testnet/integration path; Testnet fills never substitute for production-market simulation evidence.
- The continuous 24-hour B1ms production-data benchmark includes online backup, targeted capture, compaction, local logging, metrics, alert checks, resource pressure, restart/replay/reconciliation, and the accepted performance objectives.
- Weekly isolated restores and monthly full disaster drills remain scheduled operational gates.
- Before the 30-day qualifying paper run, every mandatory case applicable to that build/schema/deployment passes. Before first live, the same matrix plus current paper/Testnet/restore evidence passes under impact-based requalification.
- Each case publishes a machine-readable result linked to requirement/failure identifiers, exact build/config/schema/venue-rule versions, fixture/source digest, expected/actual posture/evidence, timing, and retained reproduction command. Coverage is measured by accepted requirement/failure mapping, not line percentage alone.

### MVP boundary and declined alternatives

- No uncontrolled chaos is injected into the real-money account or production write-capable venue path.
- No exhaustive Cartesian product of failures, arbitrary long-running fuzz campaign, multi-region failover, or application-HA chaos is required for MVP.
- **Exhaustive combinatorial chaos:** adds unbounded cost and ambiguous failures without requirement-based stopping criteria.
- **Happy paths plus restart smoke tests:** cannot prove ambiguous commands, partial/late fills, evidence loss, recovery, alerting, or safe storage pressure behavior.
- **Manual-only fault testing:** is not repeatable promotion evidence and cannot reliably guard later changes.
