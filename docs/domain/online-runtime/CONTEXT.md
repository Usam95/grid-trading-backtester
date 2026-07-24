# Online Runtime Glossary

## Control gateway

The non-trading Azure boundary that authenticates operator access, exposes read projections, and forwards requests without owning venue credentials or authoritative trading mutation.
_Avoid_: Operator Studio, trading runtime, shared database writer

## Operator command

An authenticated, idempotent, time-scoped request for one runtime action whose durable admission is distinct from its later execution and outcome.
_Avoid_: UI action, direct database update, venue command

## Mode-isolated runtime

An independently supervised online runtime with exactly one environment-specific command authority, run identity, authoritative state, and ledger.
_Avoid_: Multi-mode runtime, shared trading process

## Mode adapter

The environment boundary that maps canonical runtime facts and command intents to paper, Testnet, or live authority without changing domain policy.
_Avoid_: Mode-specific strategy, separate trading engine

## Paper trading

The online mode that consumes live production exchange data but uses paper orders, fills, balances, and risk transitions without sending executable orders.

## Production-Data Paper Run

An online grid run driven by Binance production public market data whose orders, fills, fees, and balances are simulated locally; it sends no orders to Binance.
_Avoid_: Production-market simulation run, live simulation, production-data test

## Testnet Run

An online grid run driven by Binance Testnet data whose API orders and virtual-account outcomes are authoritatively handled by Binance Testnet.
_Avoid_: Testnet experimentation slot, Testnet paper trading, Testnet venue run

## Testnet credential

A Binance Testnet-only API identity that authorizes declared virtual-asset account queries and Spot order operations without authority over production funds.
_Avoid_: Paper credential, production trading credential

## Production trading credential

A dedicated Binance production API identity permitted to query the allocated account and perform only approved Spot order operations after live preparation is authorized.
_Avoid_: Binance login, withdrawal key, live activation

## Credential generation

The uninterrupted evidence scope of one exact venue credential identity and Key Vault version; replacement begins a new generation without rewriting earlier evidence.
_Avoid_: Runtime generation, secret value, routine restart

## Emergency credential replacement

The frozen incident-recovery transition from an unsafe or unusable venue credential generation to a newly validated one.
_Avoid_: Scheduled rotation, hot reload, ordinary restart

## MVP increment

A deliberately versioned capability step, such as regime-aware adaptive-grid MVP1 or a later filter increment, that receives its own candidate, release and validation identities.
_Avoid_: In-place strategy mutation, release rebuild, active run edit

## Shakedown period

The pre-qualification online observation period in which first-launch defects and improvements are expected; its evidence is retained but does not count toward a changed candidate's qualifying clock.
_Avoid_: Qualification month, disposable test, retroactive qualification

## Paper order

A non-executable hypothetical order whose lifecycle is derived from observed production market evidence under the frozen paper execution policy.
_Avoid_: Testnet order, live order, synthetic market order

## Natural paper fill

A paper-order fill caused solely by qualifying observed Binance production market evidence rather than an injected event or deterministic test fixture.
_Avoid_: Injected fill, test fill, Testnet fill

## Live trading

The online mode authorized to submit real Binance Spot orders after mandatory validation gates and explicit manual activation.

## Paper candidate package

The sealed, digest-identified candidate and decision context explicitly selected by the operator for admission to Azure paper qualification after historical validation.
_Avoid_: Backtest winner, promotion bundle, editable paper configuration

## Promotion bundle

The sealed, digest-identified collection of evidence and exact decision context presented for approval of one candidate's advance to live activation.
_Avoid_: Backtest report, dashboard, deployment package

## Promotion approval

The operator's explicit acceptance of one exact promotion-bundle digest; it creates only a time-bounded pending activation authorization and does not start trading.
_Avoid_: Activation, gate pass

## Activation confirmation

The re-authenticated, single-use operator action that authorizes one live start after fresh fail-closed preflight against the approved promotion bundle.
_Avoid_: Promotion approval, automatic activation, resume

## Activation authorization

The expiring authority bound to one promotion bundle and activation context that may be consumed by exactly one live activation attempt.
_Avoid_: API credential, deployment permission, trading-enabled account

## First-live probation

The consecutive initial real-money observation period in which one exactly approved live run remains capped and immutable while producing evidence for a separate future promotion decision.
_Avoid_: Paper qualification, automatic scaling period, fully validated live operation

## Probation abort

The irreversible failure of one first-live probation attempt after a declared terminal, evidence-integrity, correctness, authorization, or safety boundary is crossed.
_Avoid_: Temporary frozen posture, process restart, software rollback

## Promotion rollback

The withdrawal of a candidate's authority to advance or remain in a promotion stage, requiring declared requalification before new activation authority can be granted.
_Avoid_: Deployment rollback, inventory disposal, database rollback

## Evidence-impact assessment

The durable classification of which existing promotion evidence a change can invalidate and which exact stages must be rerun before authority may be granted again.
_Avoid_: Regression guess, changed-files list, developer sign-off

## Non-impact attestation

Machine-verifiable evidence that a specific change cannot alter the identified reused artifact's inputs, decisions, states, outputs, invariants, metrics, or interpretation.
_Avoid_: No functional change, low-risk change, code-review opinion

## Live fill-active day

A UTC date containing at least one Binance-authoritative partial or full execution of an ordinary managed rung order for the identified live run.
_Avoid_: Order-active day, paper fill day, Testnet activity day

## Real completed paired cycle

A live grid cycle whose cumulative initial rung order and canonical paired obligation both completed through Binance executions with actual fees authoritatively posted or bounded and reconciled.
_Avoid_: Partial fill, bootstrap, paper cycle, Testnet cycle

## Continuous freshness chain

The unbroken sequence of valid historical, paper, Testnet, approval, and current preflight evidence that keeps one immutable candidate eligible for live activation.
_Avoid_: Fixed evidence expiry, report creation date, process uptime

## Stale promotion evidence

Retained promotion evidence whose required freshness or continuity relationship no longer permits it to grant activation authority.
_Avoid_: Deleted evidence, failed strategy, corrupted evidence

## Adverse execution sensitivity

A deterministic rerun of one frozen candidate in which exactly one declared execution-cost or fill assumption is made worse to test result robustness.
_Avoid_: Parameter optimization, alternative candidate, production configuration

## Combined adverse execution scenario

The bounded sensitivity rerun that applies all accepted adverse fee, price-cost, liquidity, and latency assumptions simultaneously to the frozen candidate.
_Avoid_: Worst possible market, Monte Carlo simulation, baseline result

## Basis point

One hundredth of one percentage point: one basis point is `0.01%`, and five basis points are `0.05%`.
_Avoid_: Five percent, percentage point

## Safety posture

The single effective command-permission classification overlaid on a run's grid lifecycle; trigger evidence determines it but cannot independently authorize commands.
_Avoid_: Lifecycle state, safety flags

## Normal posture

The safety posture in which ordinary grid commands are permitted subject to every applicable limit and invariant.
_Avoid_: Healthy, running

## Reduce-only posture

The safety posture that prohibits new base-asset exposure while permitting valid fully backed inventory-reducing sells, cancellation, and reconciliation.
_Avoid_: Exposure-reducing pause, sell-only mode

## Frozen posture

The safety posture that prohibits order placement and replacement while permitting managed-order cancellation and evidence gathering needed to establish authoritative state.
_Avoid_: Paused, stopped

## Terminal-liquidation posture

The irreversible safety posture that permits only reconciliation, cancellation, and approved terminal-disposal orders on the path to run closure.
_Avoid_: Reduce-only posture, emergency stop

## Closed posture

The safety posture of a permanently closed run in which no trading command is permitted.
_Avoid_: Flat, inactive

## Explained bounded anomaly

An unexpected or refused operation whose durable evidence proves exact exposure remains known and whose retry or evidence bounds are not exhausted.
_Avoid_: Warning, ignored error

## Known economic restriction

A reconciled condition that removes permission to increase exposure without making current orders, assets, or accounting uncertain.
_Avoid_: State-uncertain incident

## State-uncertain incident

An anomaly in which exact material orders, exposure, assets, or accounting cannot be proven and the effective safety posture must therefore be frozen.
_Avoid_: Known economic restriction, warning

## Trading event journal

The durable append-only record of market inputs, decisions, commands, acknowledgments, fills, balance changes, reconciliations, and risk-state transitions. It supports audit and replay; it is distinct from diagnostic logging.

## Decision-complete journal

A trading event journal that retains every material input, output, no-action/refusal reason, and causal reference required to reconstruct what the system knew, decided, intended, and observed.
_Avoid_: Activity log, state-change log

## Content-addressed evidence reference

An immutable reference that identifies archived evidence by its cryptographic content digest, schema, manifest, and exact record or byte range rather than by a mutable location alone.
_Avoid_: File path, latest object, log link

## Evidence checksum

A versioned cryptographic digest and byte length used to verify that an archived market, backup, bundle, or export artifact remains exactly the retained artifact.
_Avoid_: Replay equality, file timestamp

## Complete evidence bundle

A sealed manifest-based export containing every dependency required for checksum verification and offline replay of its declared evidence scope.
_Avoid_: Report export, referential evidence bundle

## Referential evidence bundle

A sealed manifest-based export that leaves declared large dependencies in immutable retained storage and therefore is not independently replayable.
_Avoid_: Complete evidence bundle, broken export

## Market archive

The immutable, provenance-preserving collection of historical and recorded market evidence available to research, validation, and replay.

## Targeted depth capture

Retention of source-continuous order-book evidence only for current executable liquidity, managed-order price neighborhoods, and approved terminal bands rather than permanent full-depth history.
_Avoid_: Full-depth archive, partial-depth assumption

## Incident capture window

A bounded sealed interval of raw market evidence before and after a material incident trigger, linked to its normal continuous evidence and exact completeness findings.
_Avoid_: Permanent full-depth capture, diagnostic log window

## Dataset manifest

The immutable identity and provenance record for a specific market dataset, including its scope, source lineage, validation findings, and relationships to derived datasets.

## Source-data gap

An interval whose expected market evidence is absent because of acquisition, transfer, archive, parsing, or unresolved provenance rather than a proven venue interruption.
_Avoid_: Market outage, empty market

## Venue market interruption

An authoritatively established interval in which venue trading or required market-data publication was interrupted and whose absence is represented explicitly in canonical time.
_Avoid_: Source-data gap, missing candle

## Canonical event

A normalized, uniquely identified fact presented in the same domain language regardless of whether it originated from historical data, a simulator, paper trading, or a live venue.

## Causation identity

The durable identity of the immediate fact or command that directly produced a journaled consequence.
_Avoid_: Correlation identity, run identity

## Correlation identity

The durable identity grouping the complete lifecycle of one business operation, such as a managed order from decision through final reconciliation.
_Avoid_: Causation identity, run identity, trace identity

## Source event key

The authoritative source-native identity or deterministic composite used to recognize duplicate or conflicting delivery of one source fact.
_Avoid_: Processing sequence, arrival timestamp

## Event time

The authoritative time at which the represented fact occurred at its source. Domain decisions use event time rather than the runtime machine's wall clock.

## Received time

The time at which the runtime observed an event. It is operational evidence for delay and gap diagnosis, not the event's domain time.

## Admitted time

The UTC time at which durable event admission committed, used to distinguish source/transport delay from journal-admission delay.
_Avoid_: Event time, received time

## Processed time

The UTC time at which an admitted event's journal processing transaction committed, used for operational latency diagnosis rather than domain ordering.
_Avoid_: Event time, processing sequence

## Source sequence

The ordering identity supplied by a declared source within its stated scope, used to prove continuity without replacing the run's processing sequence.
_Avoid_: Processing sequence, arrival order

## Processing sequence

The deterministic order assigned to canonical events for a run, including events that share the same event time.

## Event admission

The durable acceptance of a validated, deduplicated canonical event into a run's processing order. It does not mean that a trading venue accepted an order.

## Ingress sequencer

The single per-runtime admission boundary that durably places concurrent decision-relevant inputs into one authoritative processing sequence before domain state may change.
_Avoid_: Message broker, market-data queue, cross-mode sequencer

## Safety-command dispatch interlock

The fail-closed runtime gate that blocks not-yet-transmitted placement and replacement while an authenticated stop or pause request enters canonical processing, without reordering facts or changing domain state itself.
_Avoid_: Safety posture, event priority, gateway stop

## Journal processing transaction

The indivisible durable commit of every deterministic consequence of one admitted canonical event, including decisions, state hashes, invariant outcomes, accounting effects, and command outbox entries.
_Avoid_: Log write, event admission

## Command outbox entry

A durable external-command record created inside a journal processing transaction and eligible for dispatch only after that transaction commits; it is intent evidence, not proof of transmission or acceptance.
_Avoid_: Sent order, pending log

## Command lifecycle

The durable evidence state of one external command from committed intent through dispatch, venue confirmation or uncertainty, and reconciliation resolution, independent from the resulting order lifecycle.
_Avoid_: Venue order status, execution type

## Decision batch

The complete, ordered outcome of processing one canonical event from a given prior state, containing zero or more trading or risk intents.

## Order intent

A deterministic request describing the order state or change required by a trading decision. It is not evidence that an order was transmitted, accepted, or executed.

## Managed order identity

A generation-specific client identity that connects one grid order intent to every transmission, venue order, execution, cancellation, reconciliation, and replay fact throughout its lifetime.

## Effective managed order

A grid order obligation that the venue could still accept or execute, including outcome-unknown and cancellation-pending states, and which therefore still consumes rung and order capacity.
_Avoid_: Open order

## Venue order headroom

The remaining authenticated venue capacity after effective account orders and the configured safety reserve are subtracted from every applicable order limit.
_Avoid_: Grid order limit

## Operational order ceiling

The independent maximum number of concurrent effective managed grid orders authorized for a run or deployment regardless of a strategy's preferred rung count.
_Avoid_: Rung count, venue order limit

## Submission unknown

An order-command state in which transmission may have reached the venue but acceptance or execution is not yet proven; replacement remains prohibited until reconciliation.

## Post-only placement sequence

The bounded set of uniquely identified maker-only submission attempts allowed for one rung obligation after confirmed would-take rejections.
_Avoid_: Order chase, taker fallback

## Venue rule observation

A time-versioned exact record of the symbol, exchange, asset, permission, and limit rules used to validate an executable order.

## Venue order status

The venue's current lifecycle classification of an identified order, distinct from the type of event that most recently changed it.

## Venue execution type

The venue's classification of the event that changed or reported an order, distinct from the order's resulting lifecycle status.

## Stream continuity

Evidence that the required ordered venue events have no unclassified gap across normal reception, rotation, disconnect, and recovery.

## Stream generation

One identified connection lifetime whose subscription scope, source boundaries, continuity result, and closure evidence can be linked to adjacent lifetimes.
_Avoid_: Reconnect, socket status

## Decision-input freshness

Evidence that a market or account input is recent enough under its configured source-specific deadline to participate in a new domain decision.
_Avoid_: Connected, latest value

## Decision-ready availability

The share of a qualifying paper interval during which required evidence, recovered state, persistence, and control paths permit the runtime to process a new canonical event safely within its deadlines.
_Avoid_: Process uptime, websocket connectivity

## Decision readiness

The current evidence-backed ability to admit and safely process the next possible canonical event under all applicable freshness, continuity, persistence, reconciliation, risk, and control-path rules.
_Avoid_: Process liveness, service readiness, normal posture

## Control-path availability

Evidence that authenticated venue commands and authoritative queries required for cancellation, reconciliation, and safety can currently be performed within reserved capacity.
_Avoid_: Internet connectivity, public API availability

## Process shutdown

An operational stop of the single runtime that freezes trading and attempts to cancel and reconcile managed orders without permanently closing the grid run or disposing of inventory.
_Avoid_: Operator stop, emergency stop

## Runtime lifecycle phase

The operational progress state of one authoritative runtime process from startup through recovery, frozen readiness, operation, shutdown, and termination, independent from grid lifecycle and safety posture.
_Avoid_: Trading state, safety posture, process liveness

## Incomplete shutdown

A process shutdown whose bounded cancellation, reconciliation, and durable-state requirements did not all complete before termination.
_Avoid_: Clean shutdown, operator stop

## Frozen startup

The mandatory process-start condition in which recovered state may be rebuilt, queried, cancelled, and reconciled but no order placement or replacement is authorized.
_Avoid_: Automatic resume, inactive run

## Recovery snapshot

A checksum-verified, versioned copy of derived run state at one committed processing boundary, used only to accelerate recovery and never to replace journal authority.
_Avoid_: Backup, journal checkpoint

## Journal-tail replay

Deterministic processing of every journal event after a recovery snapshot's boundary before rebuilt state can be reconciled or considered for resume.
_Avoid_: Incremental restore, automatic resume

## Risk-control acceptance case

An executable specification of one safety rule's trigger boundary, effective posture, command permissions, evidence, alert, restart behavior, recovery, and replay expectation.
_Avoid_: Unit test, log assertion

## External dead-man alert

A notification generated outside the trading process when its expected health signal disappears, including when the process cannot report its own failure.
_Avoid_: Application error log, heartbeat metric

## Price touch

Market evidence that reaches an order's limit price without moving beyond it.

## Trade-through

Market evidence that moves beyond an order's limit price in the direction required for its execution.

## Volume participation

The share of observed eligible market volume that a simulated order is permitted to consume.

## Queue ahead

The eligible quantity assumed to have execution priority over a simulated resting order at the same price.

## Promotion fill policy

The mandatory conservative fill assumptions whose results may be used as evidence when deciding whether a strategy can advance toward live trading.

## Full holdout event replay

Event-sequenced evaluation of one frozen candidate across the complete locked promotion holdout using its declared quality-approved one-second and trade evidence.
_Avoid_: Selected stress replay, minute backtest

## Captured paper replay

Deterministic reprocessing of the complete retained market, timer, decision, simulated execution, accounting, reconciliation, and risk evidence from a paper-trading interval.
_Avoid_: Paper rerun, historical backtest

## Sensitivity scenario

A labelled alternative-assumption run used to measure how strongly a result depends on uncertain inputs. It does not replace the mandatory promotion result.

## Deterministic replay equality

The requirement that identical ordered inputs and immutable decision context reproduce exactly the same decisions, domain states, domain outputs, and derived trading records. Operational measurements that cannot influence decisions are excluded.

## Domain timer

A configured passage-of-time condition whose expiry can change a trading, lifecycle, reconciliation, or risk decision and is therefore represented as a canonical event.

## Operational clock

A source or schedule used for monitoring, transport, maintenance, or measurement that cannot directly change trading state.

## Venue-integration test

A mode that exercises real venue interfaces against a separate non-production market and virtual venue account. It validates connectivity, protocol, order lifecycle, account evidence, and reconciliation but is neither paper trading nor evidence of production fill realism.
_Avoid_: Testnet paper trading, production simulation

## Testnet result

The orders, balances, accounting, lifecycle evidence, and economics produced by a venue-integration test; its P&L is diagnostic and cannot represent production-market performance.
_Avoid_: Paper result, production result

## Testnet soak

An uninterrupted observation interval for one scenario-qualified build and one Testnet account generation, used to establish sustained venue-integration behavior rather than production economics.
_Avoid_: Paper clock, profitability test

## Testnet integration scenario

A predeclared acceptance case that exercises one venue-contract or recovery behavior through real Testnet evidence where controllable and a tagged injected boundary condition where it is not.
_Avoid_: Manual Testnet experiment, production-paper scenario

## Reconciliation

Comparison and repair planning between the runtime's expected orders, fills, inventory, and balances and the exchange-authoritative state.

## Reconciliation case

The durable trigger-to-convergence investigation that groups one reconciliation scope, evidence boundaries, comparison items, repair actions, safety effects, and final outcome.
_Avoid_: Reconciliation item, balance refresh

## Reconciliation item

A durable comparison of one material expected fact with the authoritative evidence capable of confirming or contradicting it.

## Reconciled

A reconciliation state in which authoritative evidence supports the expected and observed material facts.

## Pending evidence

A reconciliation state in which an identified in-flight command or evidence request may explain a difference before an explicit deadline.

## Decision-material difference

A source-exact reconciliation difference that can change command authorization, exposure, assets, accounting validity, or a risk boundary, or whose consequences cannot be authoritatively bounded.
_Avoid_: Large difference, tolerance breach

## Venue ahead

A reconciliation state in which authenticated venue evidence has not yet been admitted into the canonical local history.

## Local ahead

A reconciliation state in which canonical local state expects a venue fact that current authoritative venue evidence does not establish.

## Conflicting evidence

A reconciliation state in which sources that should agree describe the same identified fact incompatibly.

## Unexplained difference

A reconciliation state in which no accepted evidence-backed explanation accounts for the difference between expected and observed facts.

## Evidence-preserving repair

A reconciliation action that appends authoritative evidence or a linked correction while retaining the complete prior history.

## Compensating posting

An evidence-backed asset posting that corrects a proven prior or external effect without editing the original posting.

## Allocation coverage

The condition in which authenticated whole-account quantities are sufficient to back every known internal allocation and its supported obligations for each native asset.
