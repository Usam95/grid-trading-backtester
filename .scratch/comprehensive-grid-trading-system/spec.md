# Comprehensive Grid-Trading System Specification

Status: ready-for-agent — adaptive-grid MVP1 revision approved 2026-07-24
Audience: the sole operator, implementers, reviewers, and future maintainers  
Normative language: `MUST`, `MUST NOT`, `SHOULD`, and `MAY` use RFC 2119 meanings

## Problem Statement

The project needs one trustworthy system for researching, backtesting, replaying, paper-running, Testnet-running, and eventually operating a tightly capped Binance Spot grid. The existing repositories contain useful strategy, visualization, and workflow code, but they do not yet form one authoritative path from market evidence to a deterministic decision, durable command, venue outcome, exact accounting, risk response, operator explanation, and promotion decision.

The system is primarily for one operator who is still learning exchange, accounting, risk, and validation concepts. It must therefore be understandable and educational without weakening safety. It must make returns useful as the primary strategy-selection outcome while treating accounting correctness, reproducibility, parity, risk, evidence completeness, and operational recovery as non-negotiable gates.

The first implementation must remain affordable on a work laptop for research and a minimal Azure VM for continuous Paper and Testnet operation. It must not become a disposable prototype: later strategies, venues, symbols, sizing policies, persistence adapters, and deployment shapes need explicit seams, but those future capabilities must not be prematurely implemented.

The project succeeds only when:

1. accounting and replay invariants pass with no unexplained balance, fee, order, fill, or inventory differences;
2. candle simulation, event replay, Production-Data Paper, Testnet decision harnesses, and future live operation share the same canonical decision semantics;
3. out-of-sample results remain positive after realistic fees, spread, slippage, rejected orders, latency, participation limits, and adverse sensitivity;
4. results survive several symbols, market regimes, validation folds, and execution fidelities rather than depending on one period or symbol;
5. continuous Paper and Testnet qualification proves order lifecycle, reconciliation, restart, recovery, logging, alerts, and evidence retention;
6. live authority can be granted only by an explicit evidence-bound operator workflow; and
7. the first real allocation cannot exceed the accepted capital and loss limits.

## Solution

Evolve `gridlab` and `gridlab-studio` as the canonical foundation. Selectively reimplement useful behavior, tests, documentation, and user-experience patterns from `grid-backtest-core` and `grid-backtest-saas`; do not run two competing engines or copy unsafe legacy live behavior.

Build one deterministic, typed trading core that consumes canonical events and emits decisions without depending on Binance, Azure, a database, a UI framework, wall-clock calls, or network callbacks. Surround that core with explicit ports for market data, execution, time, persistence, risk authority, and operator commands. All modes use the same grid, accounting, risk, identity, and reconciliation contracts; mode adapters translate external facts and execute or simulate command intents.

Use the local workstation for historical data acquisition, experiment configuration, backtests, high-fidelity replay, visualization, learning, comparison, release qualification, and verified evidence downloads. Use Azure only for the control gateway, one Production-Data Paper runtime, and one Binance Testnet runtime during MVP1. A future live runtime replaces or extends the credentialed operational topology only after every promotion gate passes and the operator separately authorizes it.

Use an append-only decision-complete event journal and atomic command outbox as authoritative operational evidence. Derive SQLite projections, dashboards, metrics, reports, and local analysis caches from that evidence. Retain large historical and captured market data as content-identified Parquet objects, with active online state on the managed disk and verified off-VM recovery/evidence in Azure Blob Storage.

The selected strategy is one regime-aware adaptive neutral Spot grid using only allocated owned inventory. One immutable strategy configuration classifies admitted past-only evidence, derives an initial immutable grid plan epoch, and may replace it with another immutable epoch only through a guarded cancellation, late-fill reconciliation, capital, inventory, fee, venue-rule, and economic-validation transition. It uses fixed quote sizing, geometric spacing by default, post-only ordinary rung orders, cumulative fill-driven pairing, no compounding, and no automatic downward price chasing. A confirmed downtrend selects recovery/reduce-only behavior until deterministic re-entry requirements pass. A configurable global stop-loss is part of the MVP; a global take-profit is not.

## Architecture Contexts and Boundaries

### Trading engine

The Trading engine owns canonical events, strategy decisions, immutable grid configuration, rung plans, allocation-scoped accounting, paired-cycle provenance, equity views, risk evaluation, safety posture, grid lifecycle, command intents, and deterministic replay fingerprints.

It MUST NOT import a web framework, database driver, filesystem API, Binance SDK, Azure SDK, UI package, or process supervisor. It MUST operate with injected domain time and source-exact decimal values. Strategy configuration and derived venue-quantized plans are immutable and separately identified.

### Online runtime

The Online runtime owns source adapters, stream generations, the ingress sequencer, durable processing transactions, command dispatch, command-outcome ambiguity, periodic and triggered reconciliation, startup recovery, degraded modes, runtime lifecycle, and mode isolation.

Each mode runtime is a single authoritative writer. Transport work may be concurrent, but callbacks and workers MUST NOT call the domain core or mutate authoritative run state directly. They submit observations to the bounded ingress sequencer, which orders and admits them durably.

The control gateway is the only operator-facing service. It authenticates and validates requests but has no Binance credential, no venue-command path, and no direct authoritative-database write access. The targeted runtime alone admits, sequences, authorizes, and executes an operator command.

### Operator Studio

The Operator Studio is one local shell with visibly separated Research and Operations workspaces. It owns guided configuration, experiment and candidate views, evidence comparison, trade visualization, learning content, glossary access, typed command workflows, reconciliation and incident cases, promotion review, verified evidence download, and local causal analysis.

The Studio is never an authority for balances, fills, permission, or trading state. It displays source identity, observation time, freshness, runtime, mode, account/allocation, configuration, evidence bundle, and current command authority. Cached information stays visibly cached and cannot queue a later capital-affecting action.

### Infrastructure

Infrastructure owns the local research workstation and the Azure online execution environment. Azure is one B1ms-first, single-node failure domain with native Linux services, durable local state, off-VM Blob recovery, Key Vault, monitored resource budgets, and frozen application recovery. It does not provide application-level high availability.

Infrastructure and deployment code implement outside adapters. They MUST NOT contain or override strategy, accounting, reconciliation, or risk decisions.

### Dependency direction

Dependencies point inward toward typed domain contracts. Venue, persistence, UI, and cloud implementations depend on those contracts. Circular dependencies, process-global mutable trading state, unvalidated dictionaries at safety boundaries, duplicate domain rules, and controllers that make business decisions are prohibited.

## User Stories

### Research and learning

1. As the operator, I want to configure one regime-aware adaptive grid through four guided sections—Market & Data, Grid & Capital, Costs & Execution, and Risk & Evaluation—so I can understand both its initial plan and bounded adaptation rules before running it.
2. As the operator, I want geometric and arithmetic spacing with geometric selected by default, so I can compare the accepted rung variants explicitly.
3. As the operator, I want rung count to mean total configured prices including both bounds, so configurations never hide an interval/rung off-by-one.
4. As the operator, I want the activation price excluded from the configured geometry unless it already equals a rung, so activation never silently mutates the grid.
5. As the operator, I want terms explained contextually and in a searchable glossary, so unfamiliar exchange, accounting, validation, and runtime language does not force me to guess.
6. As the operator, I want every experiment to bind exact code, configuration, datasets, schemas, costs, venue rules, and seeds, so I can reproduce it later.
7. As the operator, I want local research jobs to survive a browser close or laptop UI restart, so the browser does not own execution.
8. As the operator, I want net return to lead the result view while mandatory correctness gates remain separate, so a profitable but unsafe result cannot appear deployable.
9. As the operator, I want equity, drawdown, inventory, grid adaptation state, grid plan epochs, transition gates, rungs, orders, fills, paired cycles, fees, and safety events overlaid on price, so I can visually analyze strategy behavior.
10. As the operator, I want bounded candidate comparison and a gate matrix rather than an opaque score, so I can see why one candidate is recommended or rejected.

### Data and simulation

11. As the operator, I want broad five-year research over quality-approved one-minute Binance history, so initial exploration remains computationally practical.
12. As the operator, I want promotion finalists replayed against trades, best bid/offer, and targeted depth evidence, so fill conclusions are not based only on candle extremes.
13. As the operator, I want all source objects checksummed and manifested, so missing or corrected market evidence is explicit.
14. As the operator, I want gaps quarantined rather than interpolated, forward-filled, silently dropped, or invented, so data repair cannot manufacture profit.
15. As an implementer, I want the same canonical event fixtures to produce exact decision and state fingerprints in every mode harness, so parity is executable.
16. As an implementer, I want deadlines, timers, retries, freshness changes, observation completion, confirmation, residence, cooldown, and transition expiry represented as canonical events, so replay can reproduce decisions affected by time.
17. As the operator, I want conservative Paper fills based on observed production-market evidence and bounded queue/participation assumptions, so Paper tests the algorithm without real orders.
18. As the operator, I want Binance Testnet orders and virtual-account feedback kept distinct from Paper economics, so protocol validation is not mistaken for profitability evidence.
19. As the operator, I want captured cloud evidence downloadable and verifiable for local analysis, so Azure does not need to host the full Studio or research platform.

### Grid activation and cycling

20. As the operator, I want adaptive initialization rejected unless enough quality-approved past evidence exists and current validated price is strictly inside the derived bounds, so no under-informed or out-of-range bootstrap occurs.
21. As the operator, I want a fresh explicit activation after an eligibility rejection, so the system never remains armed to acquire later automatically.
22. As the operator, I want bootstrap quantity derived from all initial sell obligations, venue rounding, and fee coverage, so every initial sell is backed by owned inventory.
23. As the operator, I want incomplete bootstrap inventory to block ladder placement, so the strategy cannot silently scale or expose an unbacked sell.
24. As the operator, I want ordinary rungs submitted post-only while bootstrap and terminal disposal may be aggressive, so normal cycle economics preserve maker intent and safety exits prioritize completion.
25. As the operator, I want one managed order per rung and one side at a time, so exposure and reconciliation stay unambiguous.
26. As the operator, I want partial fills accumulated into one paired obligation, so several execution fragments do not create duplicate cycles or orders.
27. As the operator, I want paired sells to use actual net base received after native-asset fees and venue effects, so inventory remains conserved.
28. As the operator, I want replacement buys to retain the approved fixed quote principal, so MVP results do not compound or drift during a run.
29. As the operator, I want every adjacent cycle to have positive net margin after fees, rounding, execution allowance, and safety margin, so knowingly loss-making grids cannot activate.
30. As the operator, I want an open-ended run lifecycle, so the grid does not stop after an arbitrary cycle count.
31. As the operator, I want adaptation to occur only after past-only confirmation, hysteresis, minimum residence, cooldown, freshness, reconciliation, and plan-admission gates pass, and I want every replacement ladder to have an immutable epoch identity with no ambiguous old/new overlap, so noise cannot churn orders or erase provenance.
32. As the operator, I want normal ranges to cycle symmetrically, high-volatility ranges to widen without increasing fixed quote sizing, confirmed uptrends to permit only bounded upward adaptation, confirmed downtrends to prohibit downward shifting and new buys, and uncertain evidence to freeze new placement, so every grid adaptation state has a deterministic safe consequence.

### Accounting and reconciliation

33. As the operator, I want a grid allocation separated from total account balances and foreign activity, so unrelated account use cannot be mistaken for grid assets.
34. As the operator, I want every fill posted in actual base, quote, and fee assets, so conservation does not assume all fees are quote-denominated.
35. As the operator, I want source-exact decimal arithmetic and quantization only at explicit venue or display boundaries, so binary floating-point error cannot create unexplained balances.
36. As the operator, I want current grid equity and conservative liquidation equity shown separately, so mark-to-market value is not confused with bounded exit value.
37. As the operator, I want ordinary cycle results attributed through paired-lot provenance and terminal disposal through deterministic FIFO, so profit and remaining inventory are explainable.
38. As an implementer, I want the invariant suite evaluated after every atomic posting batch and reconciliation, so corrupted accounting cannot increase exposure.
39. As the operator, I want reconciliation to compare expected and observed facts with source, time, and explicit state, so no latest-value-wins repair hides disagreement.
40. As the operator, I want safe automatic repair limited to deterministic, idempotent, evidence-backed, non-exposure-increasing actions, so material ownership or loss changes require my approval.
41. As the operator, I want late fills admitted with their original venue identity and time, so cancellation races can converge without rewriting history.
42. As the operator, I want foreign orders and balance changes to trigger isolation review when they affect allocation or headroom, so one account can remain usable for other future algorithms without ambiguous ownership.

### Risk and lifecycle

43. As the operator, I want grid lifecycle and safety posture displayed separately, so a responsive process or active grid never implies permission to buy.
44. As the operator, I want Pause to cancel and block buys while preserving valid inventory-reducing sells, so exposure can reduce without discarding recovery.
45. As the operator, I want Resume to require fresh authoritative reconciliation and all invariants, so paused authority cannot return from stale local state.
46. As the operator, I want Operator Stop to cancel managed orders, reconcile late fills, and let me choose retained holding or disposal within accepted rules, so a deliberate end is distinct from an emergency.
47. As the operator, I want Emergency Stop and terminal global stop-loss behavior to latch irreversibly and dispose only after authoritative exposure is known, so urgency cannot create duplicate or oversized orders.
48. As the operator, I want daily, run-drawdown, terminal-loss, capital, inventory, order-count, and per-buy limits, so loss and commitment are bounded independently.
49. As the operator, I want unknown command, order, fill, balance, fee, or decision state to fail closed, so uncertainty cannot trigger replacement exposure.
50. As the operator, I want every restart to begin frozen and reconcile before any order authority, so supervisor recovery never resumes blindly.

### Operations, evidence, and promotion

51. As the operator, I want Production-Data Paper and Testnet to run concurrently but with separate sources, ledgers, clocks, credentials, controls, and economic interpretation, so both purposes are proven without mixing evidence.
52. As the operator, I want a decision-complete event journal, structured logs, metrics, incidents, alerts, and causal spans, so I can debug what happened without exposing secrets.
53. As the operator, I want one reconciliation case to show trigger, expected facts, observed facts, evidence, repairs, deadlines, and convergence, so a green badge cannot hide unresolved details.
54. As the operator, I want one root-condition incident updated across repeated occurrences and notification attempts, so alert noise does not fragment the underlying problem.
55. As the operator, I want critical incidents delivered through Studio, email, and a mobile channel with repeat/escalation rules, so a lone unattended VM is externally supervised.
56. As the operator, I want manual candidate sealing and Azure admission, so a promising backtest cannot start Paper automatically.
57. As the operator, I want promotion approval separate from a re-authenticated, single-use 15-minute live confirmation, so reviewing evidence is not the same action as risking capital.
58. As the operator, I want the exact account, allocation, credential permission, configuration, build, risk profile, evidence, and fresh venue state checked immediately before bootstrap, so stale approval cannot override current safety.
59. As the operator, I want first-live operation explicitly labelled probationary and reviewed daily for seven days then weekly, so a successful start is not mistaken for mature operation.
60. As the operator, I want evidence downloaded and verified locally without deleting its cloud authority, so I can inspect and visualize it offline.

## Implementation Decisions

### 1. Canonical foundation and migration

- `gridlab` remains the canonical Python engine/research foundation.
- `gridlab-studio` remains the canonical product and FastAPI boundary.
- The Studio frontend evolves incrementally to React, TypeScript, and Vite while retaining its accepted visual language and workflows.
- Legacy repositories are requirement, characterization-test, and UX sources. Useful behavior is reimplemented through canonical contracts; legacy engines do not receive live authority.
- Delivery uses tested vertical slices. Each slice first characterizes retained behavior, establishes the target contract, migrates one consumer, proves parity, then removes the duplicate path.

### 2. Regime-aware adaptive grid contract

- Scope is Binance Spot inventory trading using only explicitly allocated owned assets. Borrowing, short exposure, margin, leverage, futures, and options are forbidden.
- One immutable strategy configuration governs the complete run. It includes symbol, adaptation-policy identity, source-exact observation windows and thresholds, confirmation and hysteresis rules, minimum epoch residence, transition cooldown and expiry, maximum transition frequency, permitted width and upward-shift bounds, total rung count, spacing type, fixed quote principal, execution policy, fee assumptions, stop price, capital envelope, and risk-profile identities.
- Adaptation inputs use only complete, quality-approved observations whose event time is no later than the decision boundary. Wall-clock arrival order, incomplete candles, future samples, and mutable “latest” data MUST NOT affect classification.
- The deterministic grid adaptation states are `RANGE_NORMAL`, `RANGE_HIGH_VOLATILITY`, `TREND_UP`, `TREND_DOWN`, and `UNCERTAIN`. They are trading decisions and are distinct from the nine analytical market-regime cells used to evaluate research breadth.
- State precedence is fail-closed: insufficient, stale, gapped, contradictory, or unreconciled decision evidence selects `UNCERTAIN`; a confirmed downtrend selects `TREND_DOWN`; a confirmed uptrend selects `TREND_UP`; a sideways high-volatility observation selects `RANGE_HIGH_VOLATILITY`; otherwise a qualified sideways observation selects `RANGE_NORMAL`.
- `RANGE_NORMAL` derives a symmetric bounded ladder. `RANGE_HIGH_VOLATILITY` may widen the ladder within the immutable policy limits but cannot increase fixed quote principal. `TREND_UP` may request a bounded upward epoch. `TREND_DOWN` MUST NOT shift bounds downward or place exposure-increasing buys and instead selects downtrend recovery with at least `REDUCE_ONLY`. `UNCERTAIN` selects `FROZEN` for placement and replacement.
- Arithmetic and geometric spacing are supported; geometric is default. Rung count includes both bounds. The activation/reference price is not inserted into geometry. A rung equal to it begins inactive; buys are strictly below and sells strictly above when the effective posture permits both sides.
- Every derived ladder is an immutable, content-identified grid plan epoch. Its identity covers source observations, adaptation decision, derivation semantics, exact unquantized values, venue-rule observation, quantized rungs, roles, obligations, allocation assumptions, and predecessor/transition causality.
- Initial activation requires enough warm-up evidence, a confirmed non-`UNCERTAIN` state, price strictly inside the derived bounds, complete venue-valid quantization, sufficient allocation and fee reserve, positive adjacent net-cycle economics, fresh authoritative data, and zero unresolved safety or reconciliation item.
- Bootstrap is a real aggressive acquisition sized from initial sell obligations. No ladder is placed until backing inventory is complete. A later epoch may bootstrap only the exact additional backing inventory admitted inside the original capital envelope and fee coverage; inability to do so refuses or expires the transition without silently scaling or adding capital.
- An epoch transition proceeds only as `ACTIVE → CHANGE_CONFIRMED → TRANSITION_REQUESTED → OLD_EXPOSURE_BLOCKED → CANCELLING → RECONCILING → DERIVING → VALIDATING → optional BOOTSTRAPPING → ACTIVATING → ACTIVE`. Every state change is canonical and journaled.
- After transition request, old-epoch exposure-increasing placement and replacement are prohibited. All effective old-epoch obligations are cancelled or proven terminal, late fills are admitted and posted, allocation and inventory are reconciled, and only then may a replacement epoch be validated or activated. Old and new epochs MUST NOT have simultaneously ambiguous exposure.
- Confirmation, hysteresis, minimum residence, cooldown, maximum transition frequency, and transition expiry are immutable policy controls evaluated in domain time. A failed gate records an explanatory no-action. A failed, expired, or uncertain transition leaves the reconciled current epoch in its permitted safe posture or selects the more restrictive posture; it never remains silently armed.
- Ordinary orders are Binance post-only `LIMIT_MAKER` intents. They never fall back to taker-capable normal orders.
- A rejected post-only order is reconciled, re-priced only in the economically favorable direction, and retried at most three total attempts within ten domain seconds, waiting 250 ms then one second. Displacement cannot exceed the lesser of 0.25% of rung price and 25% of the adjacent gap. Exhaustion selects at least `REDUCE_ONLY`.
- Each epoch rung has at most one effective managed order and one side. Partial fills aggregate under one cycle/rung obligation; the paired order tracks cumulative net quantity. Orders, fills, lots, postings, cycles, and retained inventory keep their originating epoch identity across transitions.
- Quote principal is fixed for the run. Profit remains uncommitted quote; no compounding or adaptation-driven sizing occurs.
- A configurable global stop-loss is mandatory. There is no global take-profit in MVP1.

### 3. Capital and risk profile

- The first-live grid capital envelope is at most `250 USDT` equivalent, including principal, base inventory, and every native fee reserve. It is immutable for a run.
- Fee reserve is the greater of `5 USDT` equivalent and twice projected fees for approved obligations plus bounded terminal disposal. Consequently principal cannot exceed `245 USDT` when the minimum reserve applies.
- Each exposure-increasing buy is at most `20 USDT` quantized principal.
- At most 20 effective managed grid orders may be concurrent, one per rung. Venue capacity retains headroom equal to the greater of ten slots or 20% of the authenticated venue limit; foreign orders count.
- Daily loss selects `REDUCE_ONLY` at the lesser of 2% and `5 USDT`.
- Run drawdown selects `REDUCE_ONLY` at the lesser of 8% and `20 USDT`.
- Terminal equity loss latches global stop at the lesser of 12% and `30 USDT`.
- Warnings occur at 80% of each accepted loss threshold.
- Commitment is evaluated using worst-case managed orders, cancellation-pending and outcome-unknown obligations, transition bootstrap, and the maximum planned inventory of the proposed epoch, not only current fills.
- Missing/stale valuation is not zero. Executable BBO/depth or liquidation valuation older than five seconds selects `FROZEN`; strategy input older than 15 seconds selects at least `REDUCE_ONLY` when other critical evidence is healthy.
- A private stream disconnect/gap, unknown command outcome, clock offset beyond 500 ms or timestamp rejection, or unavailable authenticated control path for ten seconds selects `FROZEN`.

### 4. Accounting and reconciliation

- One exact multi-asset grid subledger is derived from canonical event postings. Cost lots, cycle results, equity, and reconciliation are projections, not competing ledgers.
- Every posting carries run, allocation, asset, amount, cause, order/fill/cycle identities, source identity, event time, admission position, and schema version.
- Native quantities are authoritative. Quote valuations never mutate them and each fee is counted once.
- Paired-lot and grid-plan-epoch provenance define ordinary cycle results. Terminal disposal consumes residual lots FIFO; retained holdings preserve their acquisition and epoch provenance.
- Deterministic residual assignment preserves venue-rounded dust as pending or retained inventory; it is never silently discarded.
- Invariants cover asset conservation, allocation ownership, reservation coverage, backing inventory, order/fill monotonicity, fee completeness, lot/cycle provenance, posting balance, capital limits, and reconciliation convergence.
- Authority is fact-specific: configuration proves approved intent; the journal proves admitted local decisions; Binance proves venue orders, trades, fees, and account observations; the subledger proves allocation attribution; market sources prove observations; versioned venue rules prove validation.
- Reconciliation states retain expected, observed, source, time, difference, materiality, deadline, and resolution. Automatic repair appends evidence; it cannot edit, fabricate, silently reassign facts, or transfer an old-epoch obligation into a new epoch.
- Full authenticated reconciliation runs during startup and at least every 60 seconds, and is also triggered by epoch transitions, gaps, ambiguous commands, late fills, balance changes, rule changes, shutdown, resume, stop, backup recovery, and operator request.

### 5. Data architecture and mode parity

- Broad research uses source-identified one-minute historical data across the full candidate panel and five-year window.
- High-fidelity development and both holdout passes use exact trades, BBO, targeted decision-relevant depth, venue rules, fees, and canonical time events where required.
- Historical/captured bulk data is immutable, content-identified, typed compressed Parquet. SQLite in WAL mode stores local job metadata and online authoritative/projection state as appropriate.
- The event model separates source event time, local observation time, admission sequence, durable commit time, decision time, and command time.
- One deterministic ordering policy handles equal timestamps, concurrent sources, duplicates, late arrivals, gaps, closed-observation boundaries, adaptation decisions, transition timers, and other domain timers.
- Candle simulation is permitted for broad search but cannot independently qualify promotion. Event replay is the fidelity authority for the locked holdout.
- Production-Data Paper consumes Binance production public market evidence and simulates acknowledgements, fills, orders, and balances locally. Its conservative policy models queue ahead and permits use of no more than 5% of observed reusable volume.
- Testnet consumes Testnet market/account evidence and submits real API commands against virtual assets. Testnet P&L is diagnostic only.
- Candle, event replay, fake-runtime, Paper, Testnet, and future live harnesses implement the same adaptation decision, grid-plan-epoch, transition, event, intent, managed identity, order state, accounting, risk, and reconciliation contracts.

### 6. Durable runtime and recovery

- MVP1 runs three independently supervised Azure processes: control gateway, Production-Data Paper runtime, and Testnet runtime. The two runtimes have distinct stores, ledgers, identities, credentials, clocks, and authority.
- Each runtime owns one bounded ingress sequencer and one authoritative writer. Backpressure is measured by count, bytes, oldest age, commit latency, freshness, and disk headroom; no queue is unbounded.
- A journal processing transaction atomically records the admitted observation, adaptation classification, epoch/transition consequence or explanatory no-action, projection changes needed for recovery, and command outbox intents before acknowledging progress.
- Every venue command has a durable managed identity and independent command lifecycle. Timeout or transport ambiguity is `UNKNOWN`, never a confirmed rejection and never permission to resend under a new identity.
- Public and private WebSockets use explicit stream generations, rotate with overlap before 23 hours, detect sequence/time gaps, and repair from authoritative REST or retained evidence before decision readiness returns.
- Runtime lifecycle is separate from trading permission: `STARTING`, `RECOVERING`, `RECONCILING`, `FROZEN_READY`, `OPERATING`, `SHUTTING_DOWN`, and `STOPPED` do not imply a grid lifecycle or safety posture.
- Planned shutdown blocks new exposure, safely handles managed orders, seals state/evidence, and stops. Crash/supervisor replacement always restores the latest compatible point, replays the journal tail, checks invariants, reconciles Binance, and ends frozen.
- Recovery never rolls Binance back. Late external facts are reconciled into the restored local history with their authoritative identity.
- Safety/control persistence, ingress, venue evidence, reconciliation, and emergency commands outrank capture, backup, compaction, metrics, exports, and diagnostics under resource pressure.

### 7. Journal, logs, metrics, and incidents

- The canonical journal is append-only, schema-versioned, decision-complete, causally linked, and secret-safe. It records refusals and non-actions when they explain state.
- Diagnostic logs are structured JSON with stable run, mode, process, event, command, order, cycle, reconciliation, incident, configuration, and release identities. Secrets, tokens, signatures, sensitive headers, and raw credentials are prohibited and tested through redaction/canary checks.
- Local JSONL diagnostics rotate at seven days or 500 MiB, whichever comes first. Collected logs and spans remain 30 days; low-cardinality metrics remain 120 days.
- Multi-step technical workflows use structured start/progress/end span records within the logging system; no separate tracing platform is required.
- Health exposes liveness, service readiness, decision readiness, evidence freshness, safety posture, reconciliation status, backup protection, storage headroom, and external alert path separately.
- Qualification requires at least 99.5% decision-ready availability over the Paper interval, permits no more than 3 hours 36 minutes of unavailable time in 30 days, and permits no unplanned continuous unavailable interval over 30 minutes.
- Critical incidents notify Studio, email, and mobile; warnings notify Studio/email and escalate according to persistence. Notification delivery never changes canonical safety state.
- The system retains one durable incident per deterministic root-condition fingerprint and scope, with every occurrence, acknowledgement, recovery, resolution, and review.

### 8. Market capture, retention, and recovery evidence

- During an active online run, capture every observed raw trade and BBO update for the active symbol, prove stream/depth continuity, and retain depth that affected actual decisions or obligations.
- Keep raw diff-depth in a five-minute bounded ring unless a material incident seals it. Compact closed market evidence to Parquet losslessly; verify types, values, count, order, sequence, manifest, reader, and checksum before deleting replacement input.
- System-life authoritative evidence includes complete journals, configurations, schemas, migrations, operator actions, accounting, reconciliation, risk, lifecycle, live venue facts, and incident history.
- System-life promotion evidence includes exact datasets and captures used for promotion, qualifying Paper/Testnet/first-live bundles, and critical incidents.
- Failed non-promoted Paper/Testnet captures, warning incident bundles, and non-promoted full replays remain one year. Preservation holds extend but never shorten retention.
- The online database produces a complete, transactionally consistent backup nominally every ten minutes when protected state advances. Only a completely uploaded, checksum/reader-verified, catalogued Blob object is a recoverable point.
- Disaster objectives are 15-minute RPO and 60-minute frozen RTO. Trading resume is outside RTO.
- Retain one verified point per UTC day for 30 days plus required pre/post-change points. Perform an isolated restore weekly and a full fresh-VM disaster drill monthly, before qualifying Paper, and before live activation when the path changed or the latest successful drill is older than 30 days.
- Authoritative persistence failure selects `FROZEN`. Loss of the required off-VM protection or external dead-man path selects at least evidence-protection freeze before the accepted RPO/headroom boundary. Replaceable diagnostic projections degrade visibly and escalate before they threaten evidence.

### 9. Operator workflows

- Research and Operations are trust-separated workspaces in one Studio shell. The persistent authority header always exposes context and permission independently.
- Research creation uses progressive disclosure and a final canonical review. The same configuration contract serves beginner and advanced views.
- Results lead with net return and show the full evidence gate matrix. There is no composite trust score and no mandatory-gate override.
- Candidate handoff is Prepare, Seal, Transfer, Verify/Admit. Admission and starting qualification are distinct durable actions.
- Qualification presents Paper and Testnet together only at summary level. Their clocks, evidence, economics, incidents, and controls remain separate and both must pass.
- The Command Canvas prioritizes safety/capital, the grid adaptation view, a large price/grid/trade chart, epoch-qualified rung/order obligations, allocation/accounting, and causal operations.
- Pause is immediate; Operator Stop and Resume require command-specific preview and confirmation; Emergency Stop remains immediately accessible. Every consequential command is environment-bound, idempotent, expiring, concurrency-checked, durably admitted, and auditable.
- Reconciliation and incidents are case-based. Evidence & Audit provides local causal exploration, exact history, verified bundles, downloads, retention status, and holds.
- Contextual explanations state what a term means, why it matters now, the evidence used, and what changes if the operator acts. Learning does not hide numeric or technical truth.

### 10. Azure and security profile

- The online node is Linux `Standard_B1ms` in Germany West Central, initially one vCPU and 2 GiB RAM, with no swap and at least 384 MiB host-available memory at the worst representative 24-hour workload point.
- Use a 64-GiB Standard SSD E6 LRS disk for bounded active state and one GPv2 account with private-purpose containers and newly published Hot ZRS objects. Eligible closed evidence may move to Cool ZRS after 30 days; no automatic Archive tiering is used.
- Attach one Standard static public IPv4. The NSG admits SSH only from the declared operator source IP. Application, database, metrics, and health ports are never public; Studio reaches the loopback-bound gateway through SSH port forwarding.
- Use SSH public-key authentication with a dedicated project key. Password-based SSH is not the accepted production baseline.
- Run native `systemd` services under separate least-privilege OS users with explicit CPU, memory, file, process, restart, shutdown, credential, writable-directory, and network boundaries.
- Paper has no Binance private credential. The gateway has no venue credential. Testnet and future live use distinct least-privilege, trade-only credentials with withdrawals disabled and the static source IP allowlisted.
- Store venue secrets only in one Standard Key Vault with exact identity/version RBAC and subnet-restricted access. The credentialed runtime resolves `latest` once during frozen startup, records only the non-secret exact version/fingerprint, pins it in memory, and never hot-reloads it.
- Blob and Key Vault use subnet service endpoints and default-deny firewalls. ZRS is off-VM storage resilience, not runtime failover.
- Infrastructure is Bicep, validated and applied manually by the sole operator from the trusted laptop after `what-if` review. GitHub stores source and non-secret definitions but has no Azure authority; CI is optional.
- Qualified immutable release bundles are built and tested locally, uploaded through SSH, and installed side-by-side. The VM does not clone Git, resolve public dependencies, build source, or run historical backtests.
- No automatic update system, periodic drift scanner, application HA, VM Backup product, or maintenance automation is required for MVP1. The accepted deferred-maintenance exception remains visible and must be reviewed before live activation.
- Warn at EUR 35 projected/actual monthly Azure cost and open an operator-review incident at EUR 50. Cost controls never delete evidence or change trading authority.

### 11. Release, migration, and compatibility

- Verification has three levels: Level A local change feedback, Level B immutable release-candidate qualification, and Level C operational/promotion evidence.
- Python uses one locked `uv` workspace and the frontend one committed npm lock. A release identity covers source revision, dependency locks, toolchain, schemas, migrations, configuration contracts, tests, and build contents.
- Critical domain/runtime paths have no quality exemption. Minimum coverage is 90% branch coverage for critical paths and 80% overall, but semantic state, property, invariant, replay, and fault coverage outrank line counts.
- Durable evolution is forward-only expand–migrate–contract. Events and evidence are immutable; new readers support declared old schema ranges, and migrations append identity and verification evidence.
- Deployment is offline, side-by-side, and initially frozen. Acceptance proves configuration, identity, schema, persistence, replay, invariants, reconciliation, network, permissions, alerts, backups, and resource limits before any operating posture.
- Rollback is compatibility-driven and never means blindly replaying old commands or giving an old build authority over unresolved state. Repository, deployment, database, promotion, and economic inventory rollback are distinct.
- Each known extension seam has an executable contract/test double or reference proof. A change that crosses unrelated modules triggers an architecture review.

## Acceptance Criteria

### Historical research and holdout

1. Use 60 consecutive quality-approved months: 48 development months followed by one locked 12-month holdout.
2. Primary development evaluation uses eight chronological rolling folds of 24 training months plus three test months across the final 24 development months. An expanding-window sensitivity uses the same eight test boundaries.
3. No random cross-validation or state carry crosses a fold. The holdout is exposed once; a source correction after exposure requires a newly eligible future holdout.
4. The frozen robustness panel contains five eligible USDT Spot symbols selected deterministically from development-period liquidity. The proposed live symbol and at least four of five panel symbols must satisfy the accepted positive rolling and expanding breadth rules.
5. The nine-regime analytical matrix is trend down/sideways/up crossed with low/normal/high volatility using past-only labels. It evaluates evidence breadth and MUST NOT substitute for, relabel, or leak future information into the trading engine's five grid adaptation states. Each trend and volatility class has at least 60 proposed-symbol days; each cell has at least 20 days. At least five cells and the aggregate sideways regime are positive, and no one positive cell supplies over 70% of positive-cell profit.
6. Search is deterministic and strategy-only: seeded Sobol exploration uses 512 points per spacing stratum, followed by at most four plateau seeds per stratum and 51-point local neighborhoods. Declared adaptation-policy parameters are part of the strategy family and full trial accounting; fees, execution, risk, accounting, data-quality, capital ceilings, transition safety gates, and promotion thresholds are not optimized.
7. Candidate ranking first applies all hard gates, then uses constrained lexicographic return-led criteria. Deflated Sharpe Ratio confidence is at least 0.95 across the full nonduplicated trial family.
8. On the common flow-adjusted `250 USDT` basis, rolling development has at least six of eight positive quarters, median quarterly return at least 0.75%, and linked annualized return at least 5.0%. Expanding sensitivity has at least five of eight positive quarters and annualized return at least 3.0%.
9. The one-minute holdout and high-fidelity event holdout are each at least 4.0% net return. Absolute return difference and maximum-drawdown difference between them are each no more than one percentage point.
10. Rolling and expanding paths each complete at least 24 cumulative paired cycles, with at least two in six of eight folds and positive aggregate realized cycle result. Each holdout pass completes at least 12 cycles, has a fill/cycle in at least eight UTC months, and positive realized cycle result. Development fixtures cover all five grid adaptation states, every transition gate and refusal class, downtrend recovery without downward chasing, and late-fill reconciliation before a replacement epoch; the frozen holdout reports every state and epoch actually observed without imposing a favorable transition count.
11. The combined adverse execution scenario remains positive with no terminal stop and all invariants. The five scenarios cover higher/non-discounted fees, wider aggressive spread/slippage, participation reduced from 5% to 2.5% with doubled queue ahead, higher latency, and their combination.

### Paper and Testnet qualification

12. The qualifying Production-Data Paper Run uses one immutable candidate, build, risk profile, execution model, schemas, and virtual allocation for at least 30 consecutive UTC days under the evidence-continuity rules.
13. Paper must complete at least two natural paired cycles and have ordinary natural paper fills on at least three distinct UTC dates. If incomplete at day 30, the unchanged run may continue to day 90; failure by day 90 is insufficient natural activity evidence. No standalone Paper profit threshold applies.
14. Paper availability is at least 99.5%, no unplanned unavailable interval exceeds 30 minutes, and every accepted restart/recovery preserves exact evidence. Named reset conditions restart the full qualification clock.
15. Paper includes at least three planned restarts, one with a resting order; one forced termination with obligations; public and simulated-order stream gap repair; ambiguous submit/cancel; partial-fill/cancel/late-fill race during an epoch transition; deterministic replay of adaptation state and epoch identity; rate-limit/backoff; and external dead-man drills.
16. Testnet completes the 14 accepted scenario families covering authentication/time, venue rules, maker/aggressive orders, identity/idempotency, partial/cumulative fills, cancel races, ambiguity, stream recovery, frozen restart, reconciliation, rate limits, guarded epoch transition including a tagged downtrend recovery boundary, and terminal cleanup.
17. Testnet then runs seven consecutive reset-free days on one account generation. A reset closes that generation and restarts the soak without resetting an otherwise valid Paper clock.
18. Paper and Testnet use the same candidate/build but never share balances, orders, ledgers, credentials, clocks, source evidence, or profit conclusions.

### Promotion and first live

19. Paper begins no later than 30 elapsed days after the locked holdout endpoint. After qualification, Paper and Testnet observation continue without an invalidating break until approval.
20. At promotion approval, the latest complete Paper and Testnet/reconciliation endpoints are each no more than 24 hours old and have no unresolved decision-material item.
21. The operator approves one sealed promotion-bundle digest. Within 15 domain minutes the operator re-authenticates and confirms one single-use activation after two fresh fail-closed preflights. Passing gates never activate automatically.
22. Live preflight proves exact build, configuration, current grid adaptation state and observation evidence, proposed grid plan epoch, account/allocation, credential permission, venue rules, fees, balances, reservations, headroom, connectivity, clock, persistence, alerts, reconciliation, activation price, bootstrap plan, inventory, and `250 USDT` ceiling.
23. First-live probation runs unchanged for at least 30 elapsed days. Reviews are acknowledged daily for the first seven UTC observation days and at least once in every later seven-day interval.
24. Probation requires at least one real completed cumulative paired cycle and ordinary live fills on at least two UTC dates. If activity is incomplete at day 30, the unchanged probation may continue to day 90; failure then selects at least `REDUCE_ONLY` and requires a new promotion for another attempt. No standalone live-return threshold applies.
25. Any terminal condition, unsafe/non-replayable recovery, unexplained difference, unauthorized/duplicate command, lost critical evidence, invalidating change, or probation-critical defect aborts the attempt under the tiered fail-closed policy. Re-entry requires authoritative closure, an incident report, affected requalification, a new bundle, two-step activation, and a new probation.

### Runtime, recovery, security, and capacity

26. Every admitted event has exactly one deterministic, invariant-checked consequence and exact replay fingerprint, including adaptation classifications, gate refusals, epoch transitions, and no-actions; every command is durably identified before transmission.
27. Startup, replacement, and restore always end in a frozen, operator-accessible, invariant-checked, authoritatively reconciled state. No command is blindly reissued.
28. Protected off-VM state lag is no more than 15 minutes. A total VM/disk-loss drill reaches frozen recovery within 60 minutes using the newest point and also proves fallback from an older compatible point.
29. The representative B1ms qualification runs gateway, Paper, Testnet, monitoring, capture, backup, compaction, and required fault activity for 24 hours with no swap and at least 384 MiB available memory.
30. During the 24-hour run, p99 journal commit latency is no more than 250 ms; event-receipt-to-commit and dispatch-ready-to-attempt are each no more than one second; health age is no more than 30 seconds; protected health p95 is no more than 500 ms; RPO/RTO and every safety deadline still pass.
31. The capacity result is `B1MS_ACCEPTED`, `RESIZE_REQUIRED`, or `INCONCLUSIVE_RERUN`. Failure to meet correctness or resource thresholds requires optimization/retest or resize first to B2als_v2 (two vCPU/four GiB), then B2as_v2 (two vCPU/eight GiB); it never weakens evidence or safety.
32. Negative security tests prove service-user, gateway, Paper, Testnet, future live, Key Vault, Blob, SSH, inbound network, credential environment, secret logging, and withdrawal boundaries.
33. A full local Azure acceptance runner seals one report covering Bicep/release identities, isolation, permissions, Storage, Key Vault, monitoring/dead-man, failures, restart, recovery, reconciliation, Testnet bounded commands, and the 24-hour workload. Material changes rerun affected phases; uncertain cross-cutting changes rerun all.

## Testing Decisions

### Public adaptive-grid seams

- **Canonical decision/replay seam:** identical ordered canonical evidence and immutable decision context MUST reproduce the exact grid adaptation state, explanatory no-action or transition request, grid plan epoch, safety posture, intents, and fingerprint.
- **Journal/recovery seam:** every observation, gate result, cancellation, unknown outcome, late fill, reconciliation result, derivation, validation, bootstrap effect, and epoch activation commits through decision-complete transactions and rebuilds exactly after a crash.
- **Mode-conformance seam:** candle simulation, event replay, fake runtime, Production-Data Paper, and Testnet consume shared transition fixtures and MUST agree on canonical classifications, transition decisions, postures, postings, and fingerprints when their admitted facts are equivalent.
- **Typed Studio/FastAPI seam:** the API contract exposes observation identity, current adaptation state, active and proposed epoch identity, transition progress, gate/refusal evidence, and safety posture; browser tests prove the operator workflow while business decisions remain outside the UI.

### Test ownership

- Tests live with the module that owns the rule. Shared conformance scenario packs define mode/adapter parity without centralizing every test in one integration suite.
- Unit tests cover value objects and pure transitions. Property tests cover conservation, monotonic quantities, bounded exposure, quantization, pairing, and idempotency. State-machine tests cover grid, order, command, reconciliation, runtime, and safety transitions.
- Golden replay tests compare canonical decisions, postings, command intents, lifecycle, risk posture, and fingerprints—not merely summary P&L.
- Contract tests qualify market-data, execution, clock, persistence, alert, Key Vault, Blob, and operator-command adapters.
- Acceptance tests exercise processes and real persistence. Binance Testnet tests protocol behavior only; exact retained production evidence and Paper/replay test economic behavior.

### Mandatory fault themes

- duplicates, late and out-of-order events;
- partial and cumulative fills, cancel/fill races, native-asset fees, rounding dust;
- noisy threshold crossings, incomplete warm-up, hysteresis, minimum residence, cooldown and transition expiry;
- epoch cancellation with late fills, unknown outcomes, reconciliation differences, bootstrap refusal, and crash at each transition boundary;
- confirmed downtrend recovery proving no downward bound shift or exposure-increasing order;
- post-only rejection, rate limiting, timestamp rejection, ambiguous submit/query/cancel;
- public/private stream rotation, disconnect, gap, stale data, and failed repair;
- database interruption, disk pressure, corrupted snapshot, incomplete outbox, crash at each transaction boundary;
- foreign orders, balance transfers, venue-rule change, reconciliation mismatch, and operator-approved adjustment;
- alert-provider outage, dead-man failure, lost Blob path, RPO breach, corrupt/incompatible backup, and late fill during disaster recovery;
- command expiry, duplication, concurrency, authentication loss, stale Studio cache, and emergency interlock;
- retention expiry concurrent with a preservation hold and compaction interrupted before publication.

### Quality gates

- Formatting, linting, type checking, dependency-cycle checks, architecture import rules, schema compatibility, secret scanning, dependency scanning, and license policy run at the verification level defined for the change.
- Every commit created anywhere under this workspace uses `usam.sersultanov@gmail.com` as both author and committer email. A path-scoped Git configuration and identity hook reject any other email; verification must not be bypassed.
- Critical paths include canonical events/decisions, accounting, risk, safety, managed identity, command dispatch, reconciliation, persistence/replay, migrations, authentication/authorization, and promotion. They cannot use legacy exemptions.
- Legacy code follows a ratchet: no changed module may worsen its baseline, and migrated critical behavior must satisfy the strict target before receiving authority.
- Test evidence is content-identified and linked to the candidate. A passing test from a different build, dependency lock, schema, configuration, or venue contract cannot qualify the candidate.

## Staged Delivery

### Stage 0 — Baseline and characterization

Inventory canonical and legacy behavior, preserve useful tests and UX references, freeze glossary/context contracts, establish dependency rules, and create characterization fixtures for behavior that will be retained. No live authority exists.

### Stage 1 — Canonical engine and evidence spine

Implement canonical events, time, immutable strategy configuration, past-only adaptation classification, immutable grid plan epochs, guarded epoch transitions, exact accounting postings, invariants, risk/safety posture, managed identities, event journal, projections, and deterministic replay. Prove candle/replay parity on shared scenarios.

### Stage 2 — Local data and research workflow

Implement manifested Binance acquisition/import, quality quarantine, Parquet datasets, local durable experiment jobs, tiered fidelity, visualization, parameter search, folds/panel/regimes, candidate ranking, and sealed holdout. Backtests remain local.

### Stage 3 — Paper/Testnet runtime and adapters

Implement ingress sequencing, production public market adapter, conservative Paper execution, Testnet REST/WebSocket/account adapter, durable outbox, ambiguity resolution, reconciliation, startup recovery, logs/metrics/incidents/alerts, and mode-isolated stores. Qualify with local integration and Testnet fixtures before Azure.

### Stage 4 — Operator Studio modernization

Incrementally introduce the typed React/TypeScript/Vite shell, guided Research, results/trade analysis, candidate handoff, Qualification, Command Canvas, reconciliation/incident cases, evidence downloads, contextual learning, and glossary. Keep the FastAPI boundary and migrate one vertical workflow at a time.

### Stage 5 — Minimal Azure operation

Provision B1ms/E6/static-IP/Blob/Key-Vault/monitoring through Bicep. Install qualified bundles side-by-side, start frozen, run the full acceptance runner, disaster drills, and 24-hour capacity qualification. Do not run historical research or the full Studio on Azure.

### Stage 6 — MVP1 field qualification

Run exactly one regime-aware adaptive algorithm and one symbol concurrently as one Production-Data Paper Run and one Testnet Run. Use an initial flexible shakedown period to correct defects; decision-critical changes invalidate evidence according to the change-impact matrix. Begin the formal 30–90-day Paper clock only after the candidate and environment are stable, while completing the Testnet scenario campaign and seven-day soak.

### Stage 7 — Optional first-live probation

Only after every historical, replay, Paper, Testnet, recovery, security, and operational gate passes, construct the sealed promotion bundle. Real-money activation remains optional and requires the separate two-step operator authorization. Start at no more than `250 USDT`, do not compound, and apply the 30–90-day probation and abort rules.

### Stage 8 — Sequential increments

After MVP1 has collected useful long-run evidence, implement one independently classified increment at a time. Additional filters, continuously moving grids, downward-chasing behavior, opaque learned classifiers, additional symbols, concurrent strategies, Interactive Brokers, compounding, and scaling each require their own contract, evidence-impact analysis, tests, promotion evidence, and authorization. The first months deliberately avoid simultaneous new algorithms or symbols.

## Migration Guidance

1. Preserve the current working behavior with source-linked characterization tests before moving it.
2. Introduce canonical contracts beside legacy interfaces; do not force a big-bang rewrite.
3. Translate one end-to-end slice—input, decision, result, API, and Studio view—then prove exact or explicitly approved semantic differences.
4. Route new development only through the canonical slice. Keep legacy data read-only while it remains a comparison source.
5. Convert legacy float/quote-only fills, futures-oriented positions, inferred balances, and independent P&L ledgers into source-exact postings and explicit Spot allocation semantics. Do not fabricate precision or provenance that old records lack; quarantine ambiguity.
6. Migrate durable schemas through expand–migrate–contract with checkpoints, checksums, reader verification, replay comparison, and recoverable points. Never edit historical journal evidence in place.
7. Install releases side-by-side and restore/replay/reconcile under the candidate before switching the active pointer. Keep the immediate compatible rollback bundle, but never grant rollback code authority over unresolved venue state.
8. Remove a legacy path only after every consumer has moved, shared conformance passes, evidence remains readable, and the rollback/retention plan no longer depends on it.
9. Record every material migration as an impact manifest identifying changed contexts, contracts, schemas, evidence reuse, required reruns, and operator approval.

## Out of Scope

- shorting, borrowing, leverage, margin, futures, options, funding, and exchange margin-liquidation mechanics;
- allocating pre-existing base holdings as the initial bootstrap source;
- compounding or any adaptive sizing policy in MVP1;
- continuously moving/per-tick grids, unguarded cancel-and-rebuild behavior, or mutation of an active grid plan epoch;
- downward bound chasing or exposure-increasing buys selected by `TREND_DOWN`;
- opaque machine-learned regime classifiers, future-informed features, or automatic switching among independent strategy algorithms;
- multiple simultaneous live grids, multiple live symbols, or shared portfolio allocation in the first milestone;
- Interactive Brokers or another venue implementation, although the port is preserved;
- global take-profit, automated treasury transfer, tax-lot reporting, or tax/legal compliance claims;
- automatic Paper selection, automatic promotion, or automatic real-money activation;
- using Testnet profitability as production-strategy evidence;
- distributed research scheduling, Redis, Celery, Kubernetes, microservices, multi-region operation, or application-level high availability;
- hosting the full Studio or historical backtests on Azure;
- multi-user SaaS, tenancy, billing, public registration, customer administration, or organizational two-person approval;
- continuous full-depth order-book retention for every symbol;
- automatic OS/application maintenance, periodic drift repair, or CI-controlled Azure deployment in MVP1.

## Further Notes

### Normative decision records

This specification consolidates accepted behavior. The detailed records remain normative for examples, rationale, declined alternatives, edge cases, exact matrices, and acceptance procedures:

- [Architecture and quality requirements](../../analysis/architecture-quality-requirements.md)
- [Canonical grid semantics](../../analysis/domain-grid-semantics.md)
- [Data architecture and code reuse](../../analysis/data-architecture-and-code-reuse.md)
- [Accounting and reconciliation](../../analysis/accounting-and-reconciliation-spec.md)
- [Binance Spot contract](../../analysis/binance-spot-contract.md)
- [Risk and safety](../../analysis/risk-and-safety-spec.md)
- [Validation and promotion](../../analysis/validation-and-promotion-spec.md)
- [Event journal, observability, and retention](../../analysis/event-journal-observability-spec.md)
- [Online runtime and recovery](../../analysis/online-runtime-and-recovery-spec.md)
- [Operator workflows and UI](../../analysis/operator-workflows-and-ui-spec.md)
- [Minimal Azure deployment](../../analysis/azure-minimal-deployment-spec.md)
- [Security and secret management](../../analysis/security-and-secret-management-spec.md)
- [Verification, release, and migration](../../analysis/verification-release-and-migration-spec.md)

This comprehensive specification is authoritative when a detailed accepted record conflicts with it. In particular, the approved 2026-07-24 revision supersedes earlier references to a static-grid MVP1, a deferred dynamic-grid MVP2, immutable run-long price bounds, or automatic downtrend recentering. Detailed records remain normative only where consistent with this specification and continue to supply examples, rationale, edge cases, matrices, and procedures. A later implementation discovery may refine mechanism, but it may not silently change the selected product semantics, safety boundary, quantitative gate, evidence meaning, or declined option.

### Change-impact classes

Every change is classified by behavior and consumers, not filenames:

- **A — strategy/selection semantics:** rerun affected research, search, folds, panel, regimes, holdout, Paper, Testnet contracts, and promotion.
- **B — canonical decision/accounting/risk/evidence semantics:** rerun every affected upstream and downstream correctness, replay, historical, Paper, Testnet, and live gate.
- **C — Paper/high-fidelity execution or market-data behavior:** rerun affected event replay, holdout fidelity, Paper qualification, parity, and downstream promotion evidence.
- **D — Binance adapter, security, persistence, deployment, recovery, or operational boundary:** reuse economic evidence only with proven unchanged contracts; rerun affected Testnet, soak, recovery, security, deployment, and activation evidence.
- **E — proven read-only presentation/reporting:** rerun affected UI/report tests; any command, warning, gate, calculation, approval, or write impact raises the class.

The required reruns are the union across all affected classes. Evidence is superseded, never rewritten to appear as though it came from the changed build.

### Minimality rule

An MVP capability is justified only when it traces to an accepted invariant, promotion gate, parity need, named failure scenario, evidence requirement, operator learning need, or declared extension seam. The design preserves future compatibility through contracts and tests; it does not implement speculative platforms. This is how the project remains simple enough for one operator while still being maintainable, extensible, understandable, and safe.
