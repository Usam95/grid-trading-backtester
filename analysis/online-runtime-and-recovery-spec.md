# Online runtime and recovery specification

Status: operator approved  
Applies to: production-data paper trading, Binance venue-integration testing, first-live trading, unattended operation, operator control, shutdown, restart, recovery, and reconciliation

## Purpose

This specification defines the online components and ownership boundaries that turn the deterministic `gridlab` decision core into a safe long-running system. It covers process topology, canonical event admission, command dispatch and ambiguity recovery, public/private stream continuity, lifecycle orchestration, reconciliation, operator interventions, planned shutdown, crash restart, degraded operation, resource supervision, and mode-specific adapters.

The MVP remains one operator, one Binance Spot account allocation, one algorithm, one symbol, and one low-cost Azure VM. Its two concurrent online test types are the **Production-Data Paper Run** and the **Testnet Run**. Algorithm increments replace both runs sequentially after frozen closure and requalification; they do not overlap during the initial two-month learning period. It is a modular single-node system, not a distributed trading platform. Later venues, strategies, symbols, and deployment shapes use declared ports without importing Binance, Azure, SQLite, web, or filesystem concerns into the domain core.

## Current deployment boundary

The operator's laptop is the **research workstation**. It runs `gridlab` backtests and `gridlab-studio` analysis locally, including long-running historical searches when it is available. Its availability is useful for research throughput but is never a paper/live safety dependency: a sleep, power loss, update, or local failure may interrupt a backtest, but cannot stop, change, or authorize Azure trading.

The Azure B1ms-first node is the **online execution environment**. It runs only the bounded production-data paper runtime, Binance Testnet venue-integration mode when required, and later the first-live runtime. It does not run historical backtests, the full Studio UI, or broad parameter searches. This preserves its compute, memory, disk, and failure budget for decision-ready operation, evidence capture, reconciliation, recovery, and operator control.

Research crosses this boundary only through an explicit **paper candidate package**: a reviewed, immutable candidate configuration and its code, build, dataset, assumptions, gate-result, and evidence identities are copied or published as one sealed, digest-identified artifact. The online runtime cannot select, alter, or activate a backtest winner by itself, and it never accepts local workstation state as trading authority. The detailed artifact transport, local download/cache workflow, and exact Azure deployment mechanism remain deployment-spec decisions.

### Manual paper-candidate handoff

Selected by the operator on 2026-07-17: a positive backtest result never starts paper trading or becomes the Azure candidate automatically. The local research workflow may rank or recommend a candidate, but the operator must review the candidate and its gate evidence in Studio and explicitly select one exact paper-candidate-package digest for handoff to Azure.

The package is immutable after selection. Any change to strategy parameters, grid bounds, rung count, sizing, stop policy, execution assumptions, risk profile, code/build identity, source dataset, or decision-relevant configuration creates a new package identity and requires the applicable validation evidence. Upload, synchronization, or successful validation of a package grants no paper/live order authority by itself. The Azure runtime verifies the package and preserves its identity throughout paper decisions, evidence, replay, and any later promotion bundle.

Declined alternatives:

- automatically send the highest-return backtest to paper, because return alone does not satisfy the accepted robustness, accounting, parity, risk, and evidence gates;
- permit editable Azure-side candidate settings, because paper evidence would no longer correspond to the reviewed historical candidate; and
- use a dashboard screenshot or ordinary configuration file as the handoff, because neither proves the complete code/data/assumption/evidence identity.

## Selected process topology and authoritative ownership

Selected by the operator on 2026-07-17: qualification uses three independently supervised processes on the single Azure VM:

1. the **control gateway** exposes authenticated operator control and read projections to the local Studio;
2. the **Production-Data Paper Runtime** consumes Binance production public market evidence, owns local simulated execution, and is the sole writer of its journal, outbox, ledger, run state, and evidence; and
3. the **Testnet Runtime** consumes Binance Testnet evidence, owns its Testnet-only credentials and sessions, submits orders to Binance Testnet, and is the sole writer of its separate journal, outbox, ledger, run state, reconciliation state, and evidence.

The Production-Data Paper and Testnet processes are mode-isolated instances of one shared runtime application and deterministic decision core, not separately designed trading engines. For each increment they use the same decision-critical build and strategy candidate while retaining mode-specific adapters and evidence. They never share a writable database, outbox, ledger, order-identity sequence, command authority, balance, fee record, or run identity. Immutable build/package artifacts and explicitly read-only reference data may be shared.

The control gateway has no Binance production or Testnet trading credentials and cannot write either runtime's authoritative state directly. It may authenticate, validate, expire, and forward idempotent operator requests through the declared runtime control port, and may serve read-only projections and sealed exports. The receiving runtime alone decides whether a request is admissible and durably commits every resulting domain consequence. The exact transport and command-admission protocol remain review topics below.

Process supervision and resource boundaries must ensure that a gateway or Testnet failure cannot corrupt paper state, splice ledgers, reset the paper qualification clock, or cause paper evidence loss. The three-process qualification profile must pass the accepted B1ms sustained-load, recovery, compaction, and headroom benchmark. Failure requires resizing and repeating the benchmark; it does not permit merging the authoritative runtimes or weakening isolation.

Production-Data Paper and Testnet therefore have independent service users, unit files, configurations, stores, resource limits, restart scopes, and evidence identities, while activation binds both to the same qualified increment identity. The Gateway talks to each through a stable versioned compatibility contract. Replacing an increment requires both runs to freeze, reconcile and seal evidence before the new identities pass their applicable acceptance and receive separate explicit activation.

For first live operation, a new live-mode runtime instance is deployed with its own production credential scope, run identity, authoritative store, ledger, and activation authority. A running Testnet process is never switched in place to production and its database is never relabelled as live. The normal first-live profile is the control gateway plus the live runtime; concurrent shadow paper/live operation is not required by the first MVP.

This is a three-process modular single-node deployment during qualification, not a brokered microservice platform. No Redis, Kubernetes, distributed transaction, shared writable database, or managed message bus is introduced.

The process topology remains repeatable by run identity so later multiple-symbol or multiple-algorithm operation can add isolated runtimes without modifying the deterministic core or merging authoritative stores. That expansion is deferred for at least the initial two months and would require a new service-isolation, account-allocation, shared-rate-limit, reconciliation, recovery and capacity decision. Architectural extensibility does not itself authorize an additional runtime.

Declined alternatives:

- one process containing gateway, paper, and Testnet authority, because a gateway defect, Testnet fault, credential mistake, or shared-state defect would cross qualification boundaries;
- separate Azure VMs or managed services for every process, because that cost and operational surface are unnecessary for the single-operator MVP before measured isolation or capacity evidence requires it;
- a second vaguely named "live-simulation" process in addition to paper, because production-data paper is the live-market simulation while Testnet is the distinct venue-integration process; and
- converting a Testnet process or store into live mode, because environment identities, credentials, authoritative evidence, balances, and activation authority must remain unambiguous.

## Durable ingress sequencer and single-writer processing

Selected by the operator on 2026-07-17: every mode-isolated paper, Testnet, and live runtime owns exactly one **ingress sequencer**. Market-data receivers, account/order stream receivers, REST-query completions, domain timers, reconciliation workers, paper-execution adapters, and control-gateway handlers may perform transport work concurrently, but none may call the decision core or mutate authoritative run state from its callback, task, or thread.

Every decision-relevant input must pass through the ingress sequencer. It validates the declared source and schema, records the source event key and source ordering evidence, deduplicates exact redelivery, durably admits the canonical event, and assigns the runtime's monotonic processing sequence. Only after admission commits may the single journal processor consume the event. It consumes admitted events strictly in processing-sequence order and commits the complete decision batch, state transition, invariant results, accounting effects, and command-outbox entries atomically before the next event can mutate domain state.

The processing sequence is authoritative for exact replay. Source event time, source sequence, received time, and admitted time remain separate evidence; assigning a processing sequence never rewrites what the venue said happened or when it was observed. Duplicate source facts retain their duplicate-delivery evidence but cannot create a second domain consequence.

No bounded in-memory queue may silently discard, overwrite, or coalesce a decision-relevant event. Explicitly non-authoritative diagnostics may be sampled under their observability policy, but market, order, execution, balance, timer, reconciliation, risk, and operator-command facts cannot. If durable admission, continuity, freshness, disk headroom, or bounded processing backlog cannot be preserved, the affected runtime enters its accepted frozen/evidence-protection response and raises a durable incident. A Testnet overload or failure cannot reset or contaminate the independent paper runtime.

The sequencer is an internal component of each runtime, not a fourth Azure service, a shared cross-mode broker, or a replacement for source-specific continuity checks. Exact cross-source ordering, bounded staging/backpressure thresholds, and recovery of source gaps remain the next decisions within this review topic.

Declined alternatives:

- allow each adapter to update domain state directly, because callback races would make decisions, balances, and replay depend on thread scheduling;
- use a shared sequencer across paper and Testnet, because their event authority, run identities, ledgers, failure boundaries, and qualification claims are independent;
- acknowledge an operator request as admitted before durable commit, because a crash could lose an action the operator was told was accepted; and
- drop the oldest market event when memory is full, because the resulting continuity gap could silently change fills, decisions, and evidence.

## Observed-order admission and safety-command interlock

Selected by the operator on 2026-07-17 after reconciling the earlier data-architecture and observability contracts: online processing preserves what the runtime actually observed and admitted. Safety commands receive a fail-closed dispatch interlock and reserved admission capacity; they do not rewrite or jump ahead of already admitted venue facts.

The ordering contract is:

1. Explicit causation is preserved: a consequence cannot precede its cause.
2. Source-native sequence is preserved within each declared source scope. A gap, regression, overlap, or contradiction produces continuity evidence and the applicable safety response rather than invented reordering.
3. Otherwise independent online inputs retain durable observed admission order. The sequencer does not wait for a global event-time watermark or retrospectively sort already admitted facts.
4. When eligible inputs truly have no established causal, source, or observed order, use the accepted deterministic fallback: authoritative execution/account facts; operator commands ordered `EmergencyStop`, `OperatorStop`, `Pause`, then `Resume`/`Start`; venue-rule, gap, and reconciliation observations; market evidence; then domain timers. Within a class, source sequence or source event identity precedes canonical event identity as the final stable tie-break.
5. A late fact retains its source event time and sequence but receives the next processing sequence. It is accounted and reconciled without editing prior history.
6. Captured replay uses the original processing sequence exactly. Synthetic historical input without an original processing sequence uses the same causal/source/fallback rules declared in its manifest.

An authenticated, correctly scoped `EmergencyStop`, `OperatorStop`, or `Pause` request activates the runtime's **safety-command dispatch interlock** as the request enters durable admission. The interlock immediately prevents dispatch of any not-yet-transmitted placement or replacement that could increase or renew exposure. It still permits cancellation, authoritative queries, reconciliation, evidence capture, and other commands allowed by the stricter safety path.

The interlock is fail-closed but not a domain-state shortcut. It cannot acknowledge the operator request, change the canonical safety posture, erase an outbox entry, undo a transmitted command, or ignore a late fill. Only durable admission and normal sequenced processing create the operator-command event and its domain consequences. If admission fails after the interlock activates, the runtime remains blocked/frozen and raises an incident; process restart also begins frozen. Any already transmitted or outcome-unknown command is reconciled under the accepted rules.

`Resume` and `Start` never receive a permissive fast path. They remain ordinary durably admitted commands and cannot clear the interlock or authorize placement until sequenced domain processing, reconciliation, freshness, configuration, and risk preconditions all succeed.

Example: a Binance partial fill is admitted as sequence `812` immediately before an operator stop arrives. The fill remains `812`, changes inventory, fees, and obligations, and cannot be moved behind the stop. As the authenticated stop begins admission, the dispatch interlock blocks any unsent exposure-increasing command. The stop is then admitted as `813`; canonical processing applies its cancellation/disposition policy, while any later-reported fill is still posted and reconciled.

Declined alternatives:

- prioritize a stop by moving it ahead of an already admitted fill, because this falsifies what the runtime knew and breaks captured replay;
- globally sort online inputs by source event time, because late delivery would require rewriting decisions already made;
- let the gateway alone block dispatch, because the gateway does not own either runtime's command authority; and
- let `Resume` or `Start` clear the interlock before canonical processing, because an exposure-enabling request cannot bypass reconciliation or risk preconditions.

## Deadline-based backpressure and bounded staging

Selected by the operator on 2026-07-17: ingress capacity is bounded by explicit item, byte, oldest-age, persistence-latency, freshness, and disk-headroom limits derived from the mandatory 24-hour B1ms production-data benchmark. There is no unbounded memory queue and no universal arbitrary event-count limit presented as safe for every source or record size.

Each runtime uses two bounded layers:

1. small per-source in-memory staging sufficient to decouple transport callbacks from the durable admission transaction; and
2. the authoritative durable inbox of admitted events awaiting single-writer journal processing.

The benchmark fixes the versioned deployment-profile limits for each source and runtime from observed record sizes, normal and burst rates, persistence time, processing throughput, memory pressure, disk transaction/headroom behavior, and recovery performance. The limits must survive the accepted slow-persistence, market-burst, compaction-contention, restart, stream-gap, disk-pressure, and concurrent paper/Testnet fault cases. Any B1ms out-of-memory event, sustained resource exhaustion, evidence loss, missed safety deadline, or failure to preserve emergency disk headroom rejects B1ms and requires resize/retest rather than weaker queue policy.

Backpressure is applied in this order:

1. preserve reserved admission and dispatch capacity for authenticated stop/pause, cancellation, authoritative execution/account facts, reconciliation, and safety/control traffic;
2. yield or pause low-priority compaction, export, projection refresh, snapshot, backup-heavy phases, and diagnostic work within their separately accepted RPO/retention deadlines;
3. throttle or reject non-critical gateway reads, bulk downloads, report generation, and new diagnostic capture before they contend with runtime evidence;
4. continue durably spooling required decision evidence while all capacity, continuity, and freshness limits remain valid; and
5. freeze or reduce exposure under the already accepted source-specific safety deadline before the backlog can make a decision unsafe.

The accepted normal-load objective remains p99 no greater than one elapsed second from runtime receipt of an eligible market/account fact through completed processing. A continuous five-minute objective breach opens or updates the accepted warning incident, but safety posture is controlled by the stricter facts below:

- any failure to durably admit a decision-relevant event, private-stream disconnect or unproven gap, outcome-unknown safety command, or loss of required persistence/evidence capacity selects `FROZEN` immediately;
- executable BBO/depth/material valuation older than five seconds selects `FROZEN`;
- strategy-decision market input older than 15 seconds selects at least `REDUCE_ONLY` only while executable valuation and every account/control condition remain valid;
- an in-memory staging limit reached before durable preservation is proven is treated as a classified continuity/evidence failure, never as permission to drop the oldest item; and
- disk-space exhaustion forecast or headroom loss escalates before the reserved journal, cancellation, reconciliation, incident, and recovery writes can be consumed.

Public WebSocket data generally cannot be safely "paused" at the venue. If the runtime can no longer read and durably preserve it, the adapter records the discontinuity, stops making continuity-dependent decisions, reconnects/repairs from authoritative evidence where possible, and remains frozen or degraded until the accepted continuity rule succeeds. No missing trade, BBO, or depth update is invented during repair.

Paper and Testnet capacity, metrics, incidents, and safety responses remain isolated. Testnet saturation cannot consume the paper runtime's reserved queue/disk budget or reset paper qualification; the three-process benchmark must prove this on the shared VM. No Redis, external broker, or cross-mode spill queue is introduced for the MVP.

Declined alternatives:

- unbounded RAM queues, because a burst can turn market-data pressure into VM failure;
- a single hard-coded event count for every source, because event size, rate, safety deadline, and replay value differ and must be measured;
- silently dropping, overwriting, or coalescing decision evidence, because the resulting run cannot prove continuity or deterministic replay;
- continuing normal decisions until physical disk exhaustion, because cancellation, reconciliation, incident, and recovery evidence require protected reserve; and
- solving B1ms failure with a message broker, because resizing the single node is simpler until measured requirements justify a distributed boundary.

## Runtime lifecycle separated from trading permission

Selected by the operator on 2026-07-17: every authoritative runtime exposes exactly one **runtime lifecycle phase** independently from the grid run lifecycle, safety posture, reconciliation result, process liveness, service readiness, and decision readiness. A process can therefore be operating and observable while its run is paused and its safety posture is frozen; the word "running" alone never implies permission to place an order.

The runtime lifecycle is:

```text
STARTING
  -> RECOVERING
  -> RECONCILING
  -> FROZEN_READY
  -> OPERATING
  -> SHUTTING_DOWN
  -> STOPPED
```

### `STARTING`

- Acquire the single-instance ownership lock for the mode-specific store and verify the exact deployment, build, schema, environment, credential-scope, and immutable candidate identities.
- Activate the safety-command dispatch interlock before any venue adapter capable of placement can dispatch.
- Publish process liveness when the process can respond, but report service readiness and decision readiness as false.
- Any ambiguous prior termination or missing required dependency is retained as recovery evidence; it cannot be treated as a clean start.

### `RECOVERING`

- Open and integrity-check the authoritative store, reject incompatible or partially migrated state, restore only through the accepted recovery path when necessary, and acquire the last durable processing boundary.
- Load the latest verified recovery snapshot only as an accelerator, replay the complete journal tail, rebuild projections, reconstruct outbox/command ambiguity, incidents, timers, allocations, inventory, obligations, and safety state, and verify deterministic state hashes plus accounting/risk invariants.
- No placement or replacement is permitted. Failure remains fail-closed in `RECOVERING` with an incident and operator-visible evidence; the phase cannot be skipped because replay appears superficially successful.

### `RECONCILING`

- Establish required stream/control connectivity, clock evidence, venue rules, freshness, and source continuity.
- Testnet/live query authoritative orders, recent executions/trades, balances, permissions, allocations, and applicable account limits; classify every expected/observed difference and recover every outcome-unknown command.
- Under the accepted restart policy, cancel every surviving managed buy and sell, continue admitting late fills and command outcomes, and prove the resulting state. Paper performs the equivalent local simulator, market-capture continuity, candidate identity, ledger, timer, and invariant reconciliation without pretending that a production exchange paper account exists.
- Any unresolved decision-material difference keeps the runtime in `RECONCILING` and safety posture `FROZEN`.

### `FROZEN_READY`

- Recovery, required reconciliation, invariant checks, projections, protected operator access, and evidence paths are complete enough for safe inspection and an explicit operator decision.
- Service readiness may be true, while decision readiness for new exposure and trading permission remain false.
- The runtime waits for a valid mode-specific `Start`, `Resume`, operator-stop, or shutdown request. A `Start`/`Resume` performs the complete current preflight; rejection leaves the runtime frozen-ready and records every failed condition.
- Live activation still requires the separately accepted promotion approval, re-authenticated single-use confirmation, activation authorization, and fresh preflight. Infrastructure readiness cannot replace them.

### `OPERATING`

- The runtime continuously admits and processes events, supervises dependencies, executes reconciliation, publishes evidence and health, and accepts authenticated operator commands.
- `OPERATING` is not a safety posture. `NORMAL`, `REDUCE_ONLY`, `FROZEN`, `TERMINAL_LIQUIDATION`, or `CLOSED` may govern command permission while the process remains in this phase.
- Pause, stop, emergency, risk, evidence, continuity, or reconciliation events change canonical run/safety state through the sequencer; they do not require the process to pretend it has stopped operating.

### `SHUTTING_DOWN`

- Activate the dispatch interlock, set the effective posture to at least frozen, reject new exposure, and begin the accepted planned-shutdown workflow.
- Attempt cancellation of every managed buy and sell, continue admitting late fills/fees/outcomes, query and reconcile as capacity permits, durably record unresolved identities and shutdown progress, and preserve backup/evidence requirements.
- Reach `STOPPED` as clean only after the accepted cancellation, reconciliation, persistence, and evidence conditions succeed. At 60 elapsed seconds, record a critical incomplete-shutdown result and terminate according to the supervisor contract; timeout never fabricates a clean state.

### `STOPPED` and abnormal termination

- `STOPPED` means that process instance has ended and has no command authority. It does not close the economic grid run, dispose of inventory, prove a clean shutdown, or authorize another instance.
- A crash, kill, host restart, or incomplete shutdown from any phase is detected by the supervisor and prior durable evidence. A replacement process starts again at `STARTING`; it never resumes directly into `OPERATING`.
- Automatic infrastructure restart is permitted, but automatic trading resume is prohibited. The replacement must complete recovery/reconciliation, cancel surviving managed orders under the accepted policy, reach `FROZEN_READY`, and wait for the operator.

The control gateway has its own simple process liveness/readiness lifecycle but cannot advance an authoritative runtime phase or posture by reporting itself healthy. Studio displays lifecycle phase, grid lifecycle, safety posture, reconciliation status, service readiness, decision readiness, active incident, and last durable processing sequence as separate fields.

Example status:

```text
runtime_lifecycle = OPERATING
grid_lifecycle = PAUSED
safety_posture = FROZEN
reconciliation = COMPLETE
service_readiness = true
decision_readiness = false
```

Declined alternatives:

- one `RUNNING/STOPPED` flag, because it conflates process execution, grid lifecycle, safety permission, recovery, and readiness;
- enter `OPERATING` automatically after restart, because infrastructure recovery cannot restore trading authority;
- represent `REDUCE_ONLY` or `FROZEN` as runtime phases, because safety posture is an independent domain dimension used consistently across backtest, replay, paper, Testnet, and live modes; and
- treat `STOPPED` as an operator stop or closed grid, because process termination and economic run disposition are different operations.

## Durable command dispatch and unknown outcomes

Selected by the operator on 2026-07-17: every external venue command is durably identified and committed before transmission, and its command lifecycle is tracked separately from the resulting venue order status and execution events.

The canonical command lifecycle is:

```text
COMMITTED
  -> DEFERRED | DISPATCH_READY
  -> DISPATCHING
       -> CONFIRMED_ACCEPTED
       -> CONFIRMED_REJECTED
       -> OUTCOME_UNKNOWN
            -> RECONCILING
                 -> RESOLVED_ACCEPTED | PROVEN_NO_EFFECT | UNRESOLVED
```

- `COMMITTED` proves the command intent, command ID, managed-order ID, client-order ID, request digest, target environment, and causation were committed with the originating decision.
- `DEFERRED` means dispatch is not currently authorized because of posture, rate capacity, dependency, or timing; it does not mean rejection.
- `DISPATCHING` begins immediately before the sole owning runtime dispatcher attempts the request. No gateway or secondary worker may dispatch it.
- `CONFIRMED_ACCEPTED` and `CONFIRMED_REJECTED` require unambiguous venue evidence about that exact identity.
- A timeout, connection loss, process interruption, or server failure after transmission may have begun selects `OUTCOME_UNKNOWN`. The runtime freezes the affected obligation, queries by its original identity, and reconciles orders, trades, executions, commissions, and balances. It never creates a replacement while the predecessor could exist.
- `PROVEN_NO_EFFECT` requires authoritative evidence that the command did not create or change venue state. Absence from one non-atomic response is insufficient.
- `UNRESOLVED` is a durable incident and blocks decision readiness until evidence or operator-controlled recovery resolves the uncertainty.

Automatic transport retry is permitted only when the runtime can prove that no request bytes were transmitted. A confirmed `LIMIT_MAKER` would-take rejection may enter the separately accepted post-only placement sequence: no more than three uniquely identified attempts within ten elapsed seconds, followed by pause/freeze if no compliant maker order is accepted. The MVP does not use a taker fallback or a general cancel-replace loop.

The dispatcher obeys `Retry-After`, venue request-weight and order-count limits, and a versioned local limiter. It reserves independent capacity for cancellation, order/account queries, reconciliation, listen-key or session maintenance, and emergency evidence. `429` defers ordinary work; repeated pressure or `418` opens an incident, blocks ordinary dispatch, and follows the venue's recovery boundary. Rate pressure can never consume the reserved safety path.

This contract provides deterministic intent and idempotent recovery, not a false claim of exactly-once network delivery.

Declined alternatives:

- retry every timeout with a new order identity, because the original may already exist or have filled;
- infer rejection from a missing open order, because terminal or filled orders may be absent from that view;
- let both gateway and runtime submit commands, because command ownership and rate reservation would be ambiguous; and
- implement general automatic order chasing or cancel-replace in the MVP, because it expands ambiguity and execution-risk paths without being required by the static grid contract.

## Public and private stream continuity

Selected by the operator on 2026-07-17: every WebSocket connection is one explicit **stream generation** with connection-open time, endpoint, subscription set, first and last source identities, continuity result, closure reason, and link to the preceding generation.

Public production streams rotate before Binance's finite connection lifetime: start replacement no later than 23 hours after connection establishment, overlap old and new generations, deduplicate source-native identities, and promote the replacement only after its required subscriptions and continuity are proven. A failed overlap remains a classified gap rather than being hidden by reconnect success.

- Diff-depth consumption buffers updates, obtains the authoritative snapshot, bridges the snapshot update ID to the buffered sequence, and applies only contiguous updates. Any unbridgeable or later gap discards the derived book and rebuilds it; missing depth is never invented.
- Trades and BBO use exact source identities where provided. Duplicate delivery is harmless; a missing, regressing, or contradictory identity creates explicit continuity evidence.
- Executable BBO/depth/material valuation older than five seconds freezes trading. Strategy-decision input older than 15 seconds selects at least the accepted degraded posture even if the socket remains connected.

Production-data paper has no production private account stream and no production trading credentials. Testnet and live each own separate private-stream generations, endpoints, credentials, stores, and run identities. Private streams rotate before expiry, overlap and deduplicate where the venue permits, and classify continuity explicitly. Execution reports and account/balance updates are deduplicated using venue identities and cumulative quantities, not arrival time.

A private-stream disconnect, unproven rotation, gap, or contradictory cumulative state freezes the affected Testnet/live runtime and triggers REST reconciliation. Reconnect alone never proves that no fill, cancellation, commission, or balance change was missed. Connection/message limits and ping/pong deadlines are monitored and budgeted as part of the adapter contract.

Declined alternatives:

- reconnect at the advertised maximum lifetime, because clock skew and network delay can create an avoidable gap;
- treat a newly connected socket as continuous, because connection health is not event completeness;
- fill missing order-book updates from interpolation, because invented liquidity can create false fills and decisions; and
- share private streams or credentials between Testnet and live, because their authorities and evidence cannot be mixed.

## Reconciliation orchestration

Selected by the operator on 2026-07-17: reconciliation is a recurring authoritative comparison and evidence-preserving repair workflow, not only a startup query or an open-order refresh.

It is triggered:

- at startup/restart and before activation or resume;
- at least every 60 elapsed seconds while trading;
- after a public/private stream disconnect, classified gap, or unproven rotation;
- for any outcome-unknown submit or cancel command;
- after partial, duplicated, conflicting, or late fill evidence;
- after any balance, allocation, fee, or accounting difference;
- when foreign/manual account activity is observed;
- after restore or recovery and before claiming a clean shutdown;
- before live activation confirmation; and
- after filter, permission, timestamp, identity, or authoritative-rule failure where executable authority may have changed.

Each pass covers all effective and outcome-unknown managed orders; relevant recent and terminal order history; trades, executions, and native-asset commissions; exact balances for every actual asset; grid allocation, reservations, fee reserve, inventory lots, paired-rung provenance, and outstanding obligations; whole-account allocation coverage and foreign activity; current venue rules, permissions, and order limits; and every linked command identity.

Binance sources are not assumed to form one atomic snapshot. Every request/response boundary, server or observation time, pagination boundary, and source identity is recorded. The pass repeats affected reads until the evidence converges at a defensible common boundary or the applicable safety deadline expires. Trigger admission and exposure blocking are immediate; an inconclusive pass remains `PENDING_EVIDENCE` or another explicit non-reconciled state and cannot be converted to success by timeout.

Every reconciliation item ends as `RECONCILED`, `PENDING_EVIDENCE`, `VENUE_AHEAD`, `LOCAL_AHEAD`, `CONFLICTING_EVIDENCE`, or `UNEXPLAINED_DIFFERENCE`. Repair appends authoritative missing facts and rebuilds projections. It never edits a prior posting, invents a balance, or silently forces local state to match one response. Late fills post their actual quantity, quote, and fee asset. Material compensating postings or allocation changes require operator approval. Activation/resume requires zero unresolved decision-material differences.

Declined alternatives:

- reconcile only current open orders, because fills, terminal orders, fees, balances, and foreign activity would remain unproved;
- overwrite the local projection with the latest REST response, because it destroys causation and cannot repair the journal or ledger;
- accept a numeric tolerance for unexplained differences, because a small asset difference can still change an obligation or risk boundary; and
- auto-resume when one reconciliation request returns successfully, because transport success is not evidence convergence.

## Paper, Testnet, and live adapter separation

Selected by the operator on 2026-07-17: all modes use the same deterministic domain core, accounting rules, risk rules, canonical events, command intents, identity contracts, and reconciliation vocabulary. Environment-specific behavior is confined to explicit adapters.

- **Paper adapter:** consumes production public market evidence, applies the accepted conservative local execution simulator, and writes an isolated virtual allocation ledger. It has no production trading authority.
- **Testnet adapter:** consumes Testnet evidence, uses the actual Binance Testnet API and virtual Testnet account balances, and writes an isolated Testnet ledger. It qualifies venue integration only; its economics are diagnostic.
- **Live adapter:** consumes production public and authenticated private evidence, sends real production commands under restricted credentials, and accounts against the isolated real-money allocation subledger.

Paper and Testnet may run concurrently on the Azure VM only with separate stores, ingress, ledgers, run identities, credentials, command dispatchers, incidents, and resource budgets. Live starts as a fresh process and store; Testnet is never switched or relabelled into live. Domain code contains no `if paper/testnet/live` behavior: an adapter turns environment evidence into canonical facts and canonical command intents into environment outcomes.

Given identical ordered canonical inputs and immutable decision context, the core must produce identical decisions across modes. Adapter outcomes—simulated fills, Testnet reports, or live venue evidence—remain explicit canonical facts and may legitimately cause later state to diverge.

Declined alternatives:

- use Testnet as production paper evidence, because its market and virtual balances do not establish production behavior or profitability;
- place zero-value or immediately cancelled production orders for paper, because paper must have no production order authority;
- fork separate strategy engines per mode, because parity could not be demonstrated; and
- convert a qualified Testnet process in place to live, because credentials, authority, balances, and evidence identity would become ambiguous.

## Operator-command admission and concurrency

Selected by the operator on 2026-07-17: the control gateway is the only operator-facing network service, but the targeted runtime is the sole authority that durably admits, authorizes, sequences, and executes a command. The gateway has no Binance credentials and no direct authoritative database write path.

Every request includes the accepted SSH-rooted operator identity, command name, idempotency key, canonical request digest, target environment/runtime/run, expected configuration and state version, issued and expiry times, action parameters, and exact operator-confirmation evidence when required. The same idempotency key and digest returns the original admission/result; reuse with different content is a conflict. An admitted command remains durable after the SSH/Studio request ends or expires.

- A request not yet admitted expires after 60 seconds unless a stricter workflow applies.
- Live activation authorization is single-use and accepted for no more than 15 minutes.
- `EmergencyStop` requires authentication but no second confirmation. `Pause`, `OperatorStop`, and emergency commands receive reserved admission and the dispatch interlock.
- `Start`, `Resume`, first-live activation, terminal inventory disposal, and material reconciliation adjustments require fresh authentication and the relevant explicit confirmation/preconditions.
- Read and control permissions are distinct even for the single operator.

Concurrent commands enter the same durable ingress sequence as other decision facts. An admitted stop/pause dominates later start/resume intent; start/resume can neither overtake the stop nor clear a frozen posture until reconciliation, freshness, risk, configuration, and authorization preconditions pass. Conflicting or stale expected versions are rejected explicitly. The exact private-network, TLS, identity-provider, credential-storage, and session mechanism is delegated to the security specification without weakening this semantic contract.

Declined alternatives:

- allow Studio to write the runtime database, because it would bypass durable admission, authorization, and replay;
- use a browser retry as a new command, because a lost response could duplicate an irreversible action;
- make emergency stop depend on a confirmation dialog, because it delays the fail-closed path; and
- let a valid login session authorize indefinitely queued live activation, because authority must remain fresh and scope-specific.

## Planned shutdown, crash, and supervisor restart

Selected by the operator on 2026-07-17: planned shutdown and abnormal replacement share the same frozen recovery guarantees but retain distinct evidence.

A planned shutdown activates the dispatch interlock, enters `SHUTTING_DOWN`, rejects placement/replacement, attempts cancellation of every managed buy and sell, continues admitting late executions/fees/outcomes, queries and reconciles, seals durable progress, and preserves recovery evidence. A warning is raised if clean proof is not complete at 30 elapsed seconds. At 60 seconds the result is durably classified clean or incomplete; an incomplete result is critical and cannot be represented as a normal stop.

The supervisor may restart a crashed or killed runtime with bounded exponential backoff and jitter. The replacement must acquire the exclusive mode/store lock before opening authority; two authoritative writers are never permitted. It begins at `STARTING`, detects the incomplete termination, verifies the store, loads a verified snapshot, replays the journal tail, reconstructs command/outbox ambiguity, and reconciles. It cancels any surviving managed orders, reaches `FROZEN_READY`, and waits for explicit operator authority. It never auto-resumes trading.

The external dead-man path alerts if the expected authoritative runtime heartbeat is absent for two minutes, including when the VM or process cannot report its own failure. Supervisor restart does not suppress the original incident or reset qualification evidence.

Declined alternatives:

- wait indefinitely for a clean shutdown, because the supervisor and operator need a bounded, truthful result;
- treat process exit as proof that orders are cancelled, because venue orders can survive local termination;
- auto-resume after successful replay, because restored state is not renewed trading authority; and
- permit a second process to take over before proving exclusive ownership, because split authority can create duplicate orders and journals.

## B1ms capture, backup, and compaction schedule

Selected by the operator on 2026-07-17: online work is prioritized and resource-bounded rather than scheduled as competing unbounded background jobs.

Priority is: (1) admission, journal, and safety control; (2) cancellation, reconciliation, and unknown-outcome recovery; (3) required market capture, health, and incidents; (4) recovery snapshots and backup; (5) compaction and Blob offload; then (6) exports, downloads, and optional diagnostics.

- Required trade, BBO, and targeted-depth capture is continuous; the disk-backed incident ring retains at least the accepted five-minute context.
- Capture segments seal at 15 minutes or 256 MiB, whichever comes first, and use bounded streaming Parquet/Zstandard conversion rather than loading a segment into memory.
- A recovery snapshot is attempted every five minutes or 10,000 processed events, whichever comes first.
- When authoritative state changed, a complete online SQLite recovery candidate is produced on a nominal ten-minute cadence using SQLite's supported online-backup mechanism; the active database/WAL files are never copied directly.
- Sealed segments and verified recovery artifacts are published and checksum-verified in Blob within the accepted 15-minute RPO.
- Only one heavy compression, backup, compaction, or offload phase runs at a time. Backup working memory is capped at 64 MiB; every other phase has benchmarked item, byte, elapsed-time, disk, and CPU limits.
- Background work yields to admission backlog, freshness risk, reconciliation, safety commands, disk reserve, or resource pressure. Studio downloads use sealed Blob artifacts, never the live database or active segment.
- Paper and Testnet retain separate quotas and evidence identities even when the supervisor schedules their background work cooperatively.

The complete three-process profile must pass the mandatory 24-hour B1ms benchmark, including bursts, rotation, reconciliation, backup, compaction, restart, and fault injection. Failure requires resizing and rerunning qualification; it does not justify weakening evidence or isolation.

Declined alternatives:

- run compaction and backup whenever a fixed clock fires regardless of load, because background work must not steal safety capacity;
- copy live SQLite and WAL files to Blob, because the pair may not form a recoverable transaction boundary;
- let Studio query or download the authoritative live store, because analysis load and partial files would cross the runtime boundary; and
- keep B1ms by dropping required evidence, because VM size is subordinate to correctness and recovery.

## Dependency failures and degraded operation

Selected by the operator on 2026-07-17: dependencies are classified by the uncertainty their failure creates, and each class has a fail-closed response.

- **Class A—authoritative state or command uncertainty:** journal/SQLite failure, unknown command/order outcome, invariant violation, private-stream gap, or failed authoritative reconciliation. Freeze immediately, prohibit unsafe dispatch, preserve only proven inventory-reducing actions where the risk contract permits, open a critical incident, and require evidence-gated manual resume.
- **Class B—required protection loss:** projected/actual Blob RPO beyond 15 minutes, unavailable recovery publication, loss of all alert paths, disk-reserve threat, or failed restore qualification. Stop new exposure, shed optional work, preserve and offload evidence, permit only proven risk-reducing commands, and require manual recovery confirmation.
- **Class C—replaceable diagnostic loss:** Azure Monitor/dashboard/optional export failure or loss of one redundant alert destination. Continue only inside the accepted evidence and resource bounds, spool locally, reduce diagnostic verbosity where necessary, and escalate before the failure becomes Class B.

Retries use bounded exponential backoff with jitter, honor `Retry-After`, and operate behind a per-dependency circuit breaker. Safety queries, cancellation, reconciliation, and journal capacity have reserved budgets. Recovery requires fresh, representative proof—such as continuity, reconciliation convergence, durable write/read, or verified upload—not one successful request. Testnet dependency failure remains isolated from paper unless the shared VM, disk, network, alerting, or evidence boundary itself is unsafe.

Declined alternatives:

- retry every dependency indefinitely at full rate, because retry storms consume the safety path and can extend venue bans;
- report healthy after one successful probe, because intermittent failure may not have restored continuity or authority;
- stop the independent paper runtime for every Testnet defect, because mode isolation is a qualification requirement; and
- continue new exposure through Class A or B uncertainty, because the runtime cannot prove safe decisions or recoverability.

## Runtime acceptance and implementation handoff

Selected by the operator on 2026-07-17: implementation begins from an explicit handoff package, and runtime qualification proceeds in dependency order with traceable evidence.

The implementation handoff must contain:

- the runtime, command, reconciliation, grid, and safety state machines with transition guards;
- domain ports and paper/Testnet/live adapter contracts;
- canonical event, command, identity, journal/outbox, snapshot, and reconciliation schemas;
- reconciliation source/authority/repair matrix and failure/deadline table;
- B1ms resource, queue, disk, rate, backup, and retention budgets;
- security/trust boundaries and credential ownership;
- distinct lifecycle, posture, reconciliation, liveness, readiness, and incident statuses;
- requirement-to-test-to-evidence traceability;
- schema/config migration and rollback constraints; and
- operator incident, shutdown, restore, reconciliation, and activation runbooks.

The verification sequence is:

1. deterministic domain, exact accounting, serialization, snapshot, and replay tests;
2. SQLite/journal/outbox crash-boundary and corruption/recovery tests;
3. paper simulator and all mode-adapter contract tests;
4. Testnet integration scenarios and the accepted seven-day soak;
5. public/private stream rotation, overlap, gap, repair, and staleness tests;
6. timeout, disconnect, `429`, `418`, `5xx`, duplicate, and unknown-command tests;
7. late/partial fills, cancellation races, fee assets, and foreign-account activity tests;
8. interaction fault tests across persistence, streams, venue, gateway, backup, and alerts;
9. the 24-hour three-process B1ms resource and recovery benchmark;
10. weekly restore evidence and monthly disaster-recovery exercise during qualification;
11. at least 30 continuous qualifying paper days with the accepted 99.5% decision-ready availability and no unresolved material incident; and
12. final replay, accounting, reconciliation, security, promotion, and activation review.

Any unexpected venue command, duplicated managed order or fill consequence, unexplained balance difference, command dispatched before durable commitment, required evidence loss, secret disclosure, false healthy/readiness claim, automatic trading resume, or nondeterministic replay is a hard qualification failure.

The tracer-bullet implementation path is journal/outbox first, then deterministic paper, replay/reconciliation, Testnet integration, control gateway, and finally Azure qualification. The MVP does not add Kubernetes, Redis, a distributed message broker, multiple live symbols, or adaptive/dynamic grid behavior.

Declined alternatives:

- build the web control surface before the authoritative journal/recovery path, because it would exercise commands without proven durability;
- qualify components only in isolation, because the dangerous failures occur across persistence, streams, commands, and recovery;
- count Testnet profitability as promotion evidence, because Testnet is an integration environment; and
- expand to distributed infrastructure or adaptive strategies during runtime implementation, because neither is required to validate the first static single-symbol system.

## Inherited accepted contracts

- `gridlab` and `gridlab-studio` are canonical; legacy live code is requirements and failure-scenario material only.
- Paper trading consumes production public market evidence and simulates orders locally. Testnet is a separate venue-integration mode. Live fills come only from authoritative Binance execution/account evidence.
- One deterministic canonical event core and immutable decision context serve replay, paper, Testnet comparison, and live operation.
- Event admission is durable and ordered. Processing one event commits all decisions, state hashes, invariant outcomes, accounting consequences, and command-outbox entries atomically before dispatch.
- Unknown command outcomes prohibit blind replacement. Managed order identities are generation-specific and stable across transmission, venue evidence, reconciliation, and replay.
- Exact multi-asset accounting, allocation isolation, risk posture, reconciliation, evidence-preserving repair, and zero unexplained difference remain mandatory.
- Every process start is `FROZEN`. It rebuilds from journal/snapshot, queries and reconciles Binance, cancels surviving managed orders under the accepted policy, and waits for an authenticated operator resume/stop choice.
- Planned process shutdown immediately freezes, attempts cancellation of every managed buy and sell, continues admitting late facts, and has 60 seconds to reach a verified clean shutdown; otherwise it records a critical incomplete shutdown.
- Decision readiness is distinct from process liveness, service readiness, and safety posture. Infrastructure restart never grants trading authority.
- The observability contract requires decision-complete evidence, graded Class A/B/C failure behavior, external dead-man alerting, B1ms resource proof, 15-minute RPO, 60-minute RTO, and the accepted fault matrix.
- No application-level high availability, multiple simultaneous live grids, borrowing/shorting, or automatic real-money activation is in the MVP.

## Codebase audit

### Canonical foundation

`gridlab` contains an I/O-free candle backtest engine, action vocabulary, fill-derived ledger, conservative execution policies, exchange-rule simulation, and research tools. It has no production REST adapter, public/private stream consumers, durable journal/outbox, online lifecycle, command recovery, account reconciliation, or unattended supervisor.

`gridlab-studio` is a small synchronous research application shell around the engine. It has no authentication, live control plane, durable trading state, exchange credentials, stream management, health/dead-man logic, or restart recovery. It remains the UI foundation but cannot own online trading authority in its current form.

### Legacy requirement sources

`backtester_old` contains useful runtime scenarios:

- a main-loop pump that serializes queued execution reports/fills before and after each closed candle;
- Binance public and user-data WebSocket connection, ping, reconnect, and listen-key keepalive mechanics;
- deterministic/parseable client-order identity concepts;
- startup and periodic open-order queries, managed-order cancellation, query by client identity, and execution-report updates;
- paper/live entry points, account/equity/PnL observations, append-style run files, and kill-switch behavior; and
- deployment/runtime sequence diagrams and configuration examples.

These behaviors cannot be reused as the runtime implementation because:

- legacy `PAPER` submits executable orders to Spot Testnet instead of running production-data local simulation;
- public input is closed klines rather than the accepted trade/BBO/targeted-depth evidence;
- a full public queue silently drops its oldest candle and reconnect does not classify or recover gaps;
- user-stream keepalive, handler, persistence, and reconciliation failures are often logged and operation continues;
- startup/periodic reconciliation replaces in-memory knowledge from current open orders only, without complete order/trade history, balances, allocation coverage, fees, or a common authoritative boundary;
- local order state is in memory, identifiers can repeat across later cycles, values use binary floats, and command intent may be persisted only after REST success;
- broad exception suppression hides state uncertainty, shutdown is best-effort without the accepted 60-second proof, and no focused online failure-injection suite exists; and
- strategy, orchestration, venue SDK, persistence, accounting, and reporting responsibilities are tightly coupled.

The canonical runtime therefore reimplements the useful scenarios behind typed ports and the accepted journal, outbox, exact-accounting, reconciliation, safety, and observability contracts. Direct imports from legacy online modules are prohibited.

## Operator-review resolution

The operator approved the complete runtime package on 2026-07-17:

1. **resolved:** runtime/studio process topology and authoritative ownership;
2. **resolved:** canonical event ingress, concurrency serialization, queueing, and backpressure;
3. **resolved:** lifecycle phases from process boot through frozen startup, readiness, activation/resume, and operation;
4. **resolved:** durable command dispatcher states, retries, rate-limit reservation, and unknown-outcome recovery;
5. **resolved:** public market and private account/order stream generations, rotation, gap classification, and repair;
6. **resolved:** reconciliation triggers, common evidence boundaries, scope, deadlines, and repair orchestration;
7. **resolved:** paper, Testnet, and live adapter separation while preserving decision parity;
8. **resolved:** authenticated operator-command admission, idempotency, authorization expiry, and concurrency;
9. **resolved:** planned shutdown, abnormal termination, supervisor restart, and incomplete-shutdown recovery;
10. **resolved:** background backup/capture/compaction/retention scheduling under B1ms resource limits;
11. **resolved:** dependency supervision, degraded-mode transitions, retry/backoff, and unattended escalation; and
12. **resolved:** runtime-specific acceptance scenarios and implementation handoff boundaries not already fixed upstream.

No runtime-design question remains open in this ticket. Security mechanism selection, detailed operator UI workflows, current Azure service wiring, and whole-system verification/release planning remain in their dedicated Wayfinder tickets.
