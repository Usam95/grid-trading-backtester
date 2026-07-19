# Operator workflows and UI specification

Status: accepted operator workflow and UI contract  
Applies to: the secured single-operator workstation for local research, candidate comparison and promotion, production-data paper qualification, Testnet venue integration, first-live activation and operation, reconciliation, incidents, evidence, and audit history

## Purpose

This specification defines what the operator must be able to understand and do, which evidence must be visible before each consequential action, and how the local Studio communicates with the local research service and the Azure control gateway without becoming trading authority itself.

It is a workflow and information-architecture contract, not the production frontend implementation. The throwaway multi-variant UI prototype resolved the final information-hierarchy decision and must not be migrated into production code.

## Inherited boundaries

- `gridlab-studio` is the canonical application shell and must remain a consumer of canonical engine/runtime contracts rather than reimplementing strategy, accounting, risk, reconciliation, or authorization policy.
- The laptop runs research and analysis. Azure runs production-data paper, Testnet, and later live runtimes. Laptop availability cannot be an online safety dependency.
- The local workstation reaches online runtimes only through the authenticated control gateway. It has no Binance keys and cannot directly mutate an authoritative runtime database.
- Studio is the normal surface for trading-system monitoring, evidence download, configuration selection, and allowlisted operator commands through the Gateway. It never provides an arbitrary shell, root access, unrestricted VM file editing, or generic service/package administration; exceptional VM administration remains direct SSH-terminal work.
- Production-data paper, Testnet, and live are distinct environments with distinct evidence, ledgers, stores, commands, and authority. Testnet economics are diagnostic only.
- Candidate promotion is explicit and immutable. Passing gates, uploading a package, or opening a screen never starts paper or live trading automatically.
- Runtime lifecycle, grid lifecycle, safety posture, reconciliation status, service readiness, decision readiness, incidents, and command outcome remain visibly distinct.
- The personal MVP has one operator, one active live symbol/grid, no tenancy/billing, no mobile trading, no automatic activation, and no generic dashboard builder.

## Existing-frontend audit

### `gridlab-studio`: retain and deepen

The canonical Studio already provides:

- a compact local FastAPI plus no-build JavaScript application shell;
- schema-driven configuration that delegates defaults and validation to `gridlab`;
- a guided four-step strategy form, presets, live grid preview, and pre-run cost-edge context;
- backtest history, configuration reload, rich charts, benchmarks, plain-English verdicts, economics, trades, all metrics, and an on-demand robustness view;
- grid search, walk-forward, Monte Carlo, a bounded research wizard, and a Learn area; and
- reusable UI primitives, dark/light design tokens, toasts, sortable tables, accordions, tabs, metric help, and API tests.

Its important gaps are local-browser history rather than durable provenance; synchronous/ephemeral research state; no immutable promotion workflow; no authenticated online control plane; and no paper/Testnet/live, reconciliation, incident, command, recovery, or audit views. Its current static-client organization is appropriate for the research-only scope but needs explicit component/state/port boundaries before online workflows are added.

### `grid-backtest-saas`: migrate selected workflow patterns

The legacy SaaS provides useful patterns that are more mature than the canonical Studio:

- persisted backtest and research-job lists;
- a seven-step research wizard with search-space summaries and compute-budget review;
- explicit job phases, completion counters, progress bars, estimates, leave-and-return behavior, safe cancel, resume, and restart;
- persisted candidate trials with stable fingerprints, stage/progression fields, rankings, sensitivity views, scatter/parallel comparison, trial drill-down, and detailed analysis;
- a professional sidebar/dashboard structure, loading/empty/error states, result drill-down, interactive charts, and configuration summaries; and
- backend examples of job, run, trial, migration, and result-reference persistence.

These are interaction and evidence-schema sources only. The legacy UI uses obsolete engine semantics, offers dynamic strategy controls outside the MVP, ranks heavily by return without the complete accepted promotion gates, and contains multi-user/JWT/Celery/Redis assumptions that are neither necessary nor safe to copy. Its aggregate "portfolio" P&L across unrelated backtests is analytically misleading and must not become the canonical research home.

### Neither frontend currently provides

- a reviewable immutable candidate/package identity and complete gate evidence chain;
- qualifying paper-clock continuity, Testnet integration qualification, or first-live probation views;
- authoritative runtime lifecycle/readiness/posture/freshness and allocation-isolated inventory/accounting views;
- idempotent operator-command admission and outcome tracking;
- reconciliation item comparison, authoritative-source boundaries, late-fill repair, or material-adjustment approval;
- durable incident acknowledgement/resolution and external-alert context;
- safe pause, operator stop, emergency stop, resume, activation, or terminal-disposal workflows; or
- decision-complete audit navigation and sealed evidence export/download.

Those workflows must be derived from the accepted specifications, not improvised from current dashboards.

## Capability disposition

| Existing pattern | Decision direction |
| --- | --- |
| Studio engine-schema configuration and live grid preview | Retain and deepen |
| Studio result tabs, benchmarks, economics, trades, help, and Learn | Retain and align with accepted terminology/evidence |
| SaaS persisted jobs, phases, progress, cancel/resume, and drill-down | Reimplement against canonical job and provenance contracts |
| SaaS research wizard, compute-budget review, comparison, and sensitivity views | Selectively migrate, removing unsupported strategy choices and return-only promotion implications |
| SaaS authentication, tenancy, PostgreSQL, Celery, Redis, and billing assumptions | Reject as UI architecture defaults; use only requirements that survive the security/Azure decisions |
| Combined P&L across unrelated historical experiments | Reject; show research evidence, not a fictional portfolio |
| Current localStorage research history as authoritative evidence | Reject; it may remain a disposable convenience cache only |
| Legacy online screens or live modules | Requirements/scenario source only; no direct import |

## Decision overview

The review will resolve these topics one at a time. Each decision will include the recommendation, realistic alternatives, consequences, examples, and declined choices.

1. **Workstation composition and trust boundary** — one shell with separated research/operations workspaces versus separate applications or a blended mode switch.
2. **Top-level information architecture** — primary navigation, stable object hierarchy, environment context, breadcrumbs, and where global status lives.
3. **Global status and authority header** — environment, runtime identity, connection generation, freshness, lifecycle, safety posture, reconciliation, readiness, active candidate, capital authority, and incidents.
4. **Research creation workflow** — guided versus expert configuration, data selection/provenance, presets, validation, preview, cost assumptions, and unsupported-feature handling.
5. **Research-job lifecycle** — queue/run/progress/cancel/resume/retry semantics, laptop interruption, deterministic identity, resource estimates, and durable history.
6. **Results and experiment comparison** — single-run interpretation, benchmarks, accounting, trades, robustness, parameter plateaus, cross-symbol/regime evidence, side-by-side comparison, and misleading aggregate avoidance.
7. **Candidate selection and evidence sufficiency** — how hard failures, gate states, warnings, return-primary ranking, DSR credibility, fidelity parity, activity, and manual selection are presented.
8. **Immutable paper-candidate handoff** — package review, digest/config/build/data identity, validation, upload, Azure admission, supersession, and proof that admission grants no trading authority.
9. **Paper and Testnet qualification workspace** — clearly separated purposes, clocks, scenarios, incidents, decision-ready availability, economic evidence, protocol evidence, and qualification reset/continuity.
10. **Live-readiness and two-step activation** — promotion evidence, capital/loss limits, permissions, freshness, reconciliation, fresh authentication, single-use confirmation, preflight, rejection, and expiry.
11. **Live operating view** — current grid, market and rung state, managed/effective orders, partial fills, inventory and obligations, exact assets/fees, allocation, equity, P&L, limits, evidence freshness, and command outcomes.
12. **Safety-control workflow** — pause, operator stop, emergency stop, resume, terminal disposal, permitted reducing sells, confirmations, dominance/concurrency, and visible late-fill handling.
13. **Reconciliation workspace** — trigger/reason, evidence boundary, expected versus venue facts, item classifications, convergence, repair proposals, compensating postings, operator approval, and resume blocking.
14. **Incident workflow** — severity, root-condition aggregation, occurrences, evidence, current safety effect, alert delivery, acknowledgement, escalation, resolution proof, closure review, and recurrence.
15. **Audit, evidence, and downloads** — causal timeline, commands and outcomes, configuration versions, approvals, journal-linked explanations, bundles, sealed Blob downloads, retention/holds, and redaction.
16. **Disconnected, stale, degraded, and recovery UX** — truthful last-known data, no false healthy state, read-only behavior, command uncertainty, frozen startup, restore/replay progress, and manual recovery authority.
17. **Learning, glossary, accessibility, and device scope** — contextual explanations without hiding evidence, consistent canonical terms, keyboard/accessibility requirements, desktop-first responsive behavior, and non-actionable mobile notifications.
18. **Frontend boundaries and verification** — typed API/view contracts, authoritative versus projected state, safe command components, local versus Azure data ownership, browser/E2E and accessibility tests, and architecture rules preventing policy duplication.
19. **Throwaway UI prototype and visual selection** — three structurally different variants on the canonical Studio shell, switchable by `?variant=`, followed by an explicit winning composition and cleanup.

## Explicit non-goals

- Reproduce the legacy SaaS product or its multi-user navigation.
- Put Binance credentials, direct runtime database access, or trading policy in the browser.
- Treat Testnet as a profitability simulator or merge its balances with paper/live.
- Make risk or accounting status understandable only through color.
- Add mobile order controls, social sharing, dashboard customization, or multiple simultaneous live-grid views.
- Implement adaptive/dynamic strategy controls merely because a legacy screen contains them.

## Decision 1: one shell with trust-separated workspaces

Selected by the operator on 2026-07-18: use one consistent Operator Studio shell with two visibly and technically separated workspaces:

1. the **Research workspace** communicates with the laptop's local research service, configures and runs historical research, analyses evidence, and prepares an immutable candidate handoff; and
2. the **Operations workspace** communicates only with the authenticated Azure control gateway and presents paper, Testnet, and later live status and controls.

This is one operator-facing application, not one backend, state store, trust zone, or command authority. Research cannot send venue commands or mutate Azure runtime state. Operations cannot edit an admitted candidate or call the local engine as a substitute for authoritative online evidence. The only transition between them is an explicit, digest-identified candidate-package handoff and its resulting evidence links.

The shell must preserve independent failure behavior. If the local research service or a laptop backtest fails, the Operations workspace can still inspect and control the Azure runtime. If Azure or the gateway is unreachable, Research remains usable while Operations displays truthful last-known time, connection loss, and unavailable command authority; it never presents cached state as current.

Workspace identity is persistent and cannot be communicated only by color. Navigation, page titles, command components, API clients, cached state, and URLs remain workspace-scoped. Opening a link or switching workspace cannot start, resume, promote, or activate anything.

Consequences:

- one design system and causal navigation can connect research evidence to qualification without duplicating applications;
- local research and Azure operation retain distinct API ports, state models, authentication/authorization, failure handling, and tests;
- online command components cannot be mounted in Research routes, and research configuration editors cannot be mounted in authoritative Operations routes;
- later Interactive Brokers or additional strategies can extend the declared workspace contracts without creating a second workstation; and
- the global shell must clearly show workspace, environment, freshness, authority, and connection context before the operator acts.

Example: a long local parameter search exhausts laptop memory. The Research workspace marks that job interrupted, but the independently connected Operations workspace continues to show the Azure paper runtime. Conversely, an Azure outage makes Operations stale/read-only while the local Research workspace continues normally.

Declined alternatives:

- two completely separate applications, because their additional visual isolation does not outweigh duplicated authentication, navigation, design, evidence linking, and maintenance for one operator;
- one blended dashboard with a paper/Testnet/live mode switch, because simulated and real state or commands could be confused and a UI mode change could appear to grant authority; and
- a shared frontend data store or generic API client across both workspaces, because cached research and authoritative online state require different identity, freshness, trust, and failure semantics.

## Decision 2: two-level workspace and object navigation

Selected by the operator on 2026-07-18: navigation first selects the trust-separated workspace and then exposes a small stable object/workflow hierarchy. Status changes move an object through its lifecycle without moving its canonical location or rewriting its URL identity.

The primary navigation is:

```text
Research
  Overview
  Experiments
  Candidates
  Data
  Learn

Operations
  Command Center
  Qualification
  Reconciliation
  Incidents
  Evidence & Audit
```

`Experiments` contains creation, queued/running jobs, progress, completed results, and comparisons rather than separate top-level entries for backtests, jobs, and results. `Candidates` owns validation evidence, manual selection, immutable package preparation, and handoff history. `Data` owns dataset availability, quality, provenance, and manifests; it does not expose runtime market capture as editable research data.

`Command Center` is the entry point for the explicitly selected online runtime and its current grid, orders, inventory, accounting, risk, readiness, and controls. `Qualification` connects admitted candidates to paper evidence, Testnet integration evidence, live readiness, activation history, and probation. Reconciliation, incidents, and evidence remain stable cross-runtime work areas because they can span lifecycle stages and must not disappear when a run pauses or closes.

Authentication/session, settings, notifications, sealed downloads, help/glossary access, and operator profile are global utilities, not primary navigation destinations. Exact environment selection and the persistent authority/status header are resolved separately.

The canonical evidence chain is navigable in both directions without copying authority between workspaces:

```text
Research experiment
  -> result and comparison evidence
  -> symbol-specific candidate
  -> immutable paper candidate package
  -> paper qualification
  -> Testnet integration evidence
  -> live activation decision
  -> first-live probation
  -> operational and audit evidence
```

Every link retains the source object's identity and opens the destination in its owning workspace. A cross-workspace link can navigate and select context, but it cannot issue a command, promote, activate, or mutate evidence.

Consequences:

- the primary navigation stays compact while details live under stable objects;
- research history is treated as experiment evidence rather than a fictional portfolio of unrelated returns;
- qualification and live history remain inspectable after lifecycle changes;
- later strategies or venues add filters/types beneath stable destinations rather than new top-level products; and
- URLs, breadcrumbs, recent objects, notifications, and audit links can share the same canonical object identities.

Example: selecting a candidate opens its complete historical gate evidence under `Research > Candidates`. Following its handoff opens the corresponding immutable package under `Operations > Qualification`; returning through the provenance link restores the original candidate rather than creating an editable copy.

Declined alternatives:

- stage-based `Discover -> Backtest -> Validate -> Paper -> Testnet -> Live` navigation, because concurrent qualification and cross-stage reconciliation/incidents/evidence do not have one stable stage;
- one flat feature list of dashboards, jobs, results, modes, orders, logs, and settings, because it mixes trust boundaries and grows into an unscannable sidebar; and
- dynamically hiding completed or currently inapplicable destinations, because historical evidence and recovery workflows must remain locatable even when no action is available.

## Decision 3: persistent two-layer authority context header

Selected by the operator on 2026-07-18: every workstation page has a compact sticky **authority context header** with separate identity/context and condition/permission layers. It reports evidence and navigation context; it never grants authority or substitutes for a page-level preflight.

The first layer answers **what is being viewed**. In Operations it contains workspace, explicit `PAPER`/`TESTNET`/`LIVE` environment, symbol, runtime/run identity, active immutable candidate/package identity, connection generation or state, source `as of` time, and current operator session scope. In Research it contains workspace, `LOCAL` authority, local research-service state, selected dataset/manifest, experiment/candidate identity where applicable, and the explicit statement `NO ONLINE TRADING AUTHORITY`.

The second layer answers **whether the selected target is current and actionable**. For an online runtime it keeps runtime lifecycle, grid lifecycle, safety posture, reconciliation state, decision readiness, decision-input freshness, outcome-unknown command count, highest active incident severity/count, and applicable live capital authority visible as distinct values. It never collapses them into one green/red health indicator or one generic `running` state.

Example Operations header:

```text
OPERATIONS | LIVE | BTCUSDT | runtime live-001 | candidate a83f… | as of 14:32:08 UTC
OPERATING | GRID ACTIVE | NORMAL | RECONCILED | DECISION READY | 0 UNKNOWN | 0 CRITICAL
```

Example Research header:

```text
RESEARCH | LOCAL | dataset btcusdt-1m-2021-2026@91ce… | experiment exp-142
LOCAL SERVICE READY | NO ONLINE TRADING AUTHORITY
```

Rules:

- workspace and environment use text plus shape/icon/pattern and accessible labels; color is supplementary only;
- `LIVE` receives the strongest persistent environment treatment, but no ordinary healthy state is represented as an alarm;
- last-authoritative update and freshness remain visible, and stale/disconnected state cannot be styled as current;
- clicking a status opens its owning evidence or workflow without performing a mutation;
- critical incidents and outcome-unknown commands cannot be dismissed from the header merely by acknowledgement;
- on narrower displays, secondary identity details may collapse into an accessible context drawer, but workspace, environment, freshness, safety posture, decision readiness, and critical/unknown state remain visible; and
- balances, charts, complete risk limits, order tables, and action buttons remain in the Command Center rather than expanding the header into a command console.

Consequences:

- the operator can distinguish simulated, integration, and real-money state before interpreting any page or action;
- every route must bind displayed state to one explicit environment/runtime identity and authoritative observation time;
- components require compact, stable labels and drill-through evidence rather than vague status prose;
- screenshot/export context includes the same identity and `as of` boundary; and
- automated UI tests must prove that stale, disconnected, frozen, unreconciled, unknown-command, and critical-incident states remain visible across routes and viewport sizes.

Declined alternatives:

- a minimal header with page-specific status only, because critical runtime/reconciliation context would disappear during navigation;
- a permanent full command/status console, because it would duplicate the Command Center, overwhelm the one-symbol MVP, and reduce scanability; and
- one composite health light, because liveness, readiness, posture, reconciliation, freshness, and command certainty have different meanings and recovery rules.

## Decision 4: four guided sections with progressive disclosure

Selected by the operator on 2026-07-18: research creation uses four guided sections on one coherent page, advanced fields collapsed by default, a persistent consequences preview, and a final canonical review before creating the experiment. Beginner and advanced presentation share one specification and engine contract; there is no second simplified strategy model.

### 1. Market & Data

The operator selects symbol, historical period, granularity, exact dataset/manifest identity, source, available coverage, quality state, and evidence role. Gaps, unsupported derivations, consumed holdout restrictions, and promotion eligibility are shown before configuration proceeds.

### 2. Grid & Capital

The operator configures bounds, arithmetic or geometric spacing, exact rung-count semantics, fixed quote sizing, activation/bootstrap assumptions, range-exhaustion policy, and applicable retained-holding policy. The UI derives the ladder, planned quote/base needs, maximum planned inventory/exposure, allocation requirement, reservations, and fee reserve from canonical engine services rather than duplicating formulas in JavaScript.

### 3. Costs & Execution

The operator reviews declared Binance fee assumptions and fee assets, spread, slippage, post-only placement behavior, venue rounding/filter observations, simulation fidelity, and the resulting minimum expected net cycle edge. Assumptions are versioned evidence, not unlabelled UI defaults.

### 4. Risk & Evaluation

The operator selects the accepted global stop-loss/range behavior, applicable static-grid filters, experiment type, bounded search domains/budget when relevant, walk-forward/holdout/sensitivity plan, and whether the experiment is exploratory or intended to produce promotion evidence. Unsupported MVP behaviors—futures, shorting, borrowing, leverage, adaptive/dynamic grids, compounding, and multiple live symbols—are not presented as executable choices.

The persistent preview displays the grid ladder and activation reference; planned quote/base inventory, fee reserve, maximum exposure, and venue-filter fit; expected gross and net cycle edge; dataset/evidence qualification; generated trial count and approximate compute requirement; and blocking errors versus non-blocking warnings. Every derived value identifies the canonical service/configuration version that produced it.

The final review shows the complete canonical configuration, code/build identity, dataset/manifest and evidence-role identity, cost/fill assumptions, search/evaluation plan, derived capital obligations, experiment classification, and resulting digest before submission. Presets populate an editable canonical configuration. JSON import/export may be provided as a power-user convenience, but import passes through the same schema, derivation, preview, and final review.

Invalid or unsupported configurations cannot run. A permitted exploratory experiment using evidence or assumptions that cannot qualify receives a permanent `NOT PROMOTION ELIGIBLE` classification with exact machine-readable reasons on its creation review, job, results, comparisons, and exports. It cannot later become eligible by relabelling; changed evidence creates a new experiment identity.

Consequences:

- the four sections retain Studio's compactness while adopting the SaaS workflow's review and compute-budget clarity;
- relationships between rung count, sizing, inventory, fees, fill fidelity, risk, and compute remain visible together;
- defaults and derived values come from canonical backend contracts, preventing UI/engine semantic drift;
- exploratory analysis remains useful without contaminating promotion evidence; and
- automated tests must cover conditional fields, unsupported-feature absence, exact preview/service agreement, canonical serialization, and eligibility-reason persistence.

Declined alternatives:

- a seven-step full-screen wizard, because it increases iteration friction and hides economic relationships across pages for the personal MVP;
- one dense expert form, because promotion eligibility, data quality, and capital consequences can be lost among many controls;
- separate beginner and expert configuration models, because they would create two semantic paths and undermine replay/parity; and
- raw JSON as the primary editor, because schema validity alone does not make consequences, provenance, or evidence role understandable.

## Decision 5: lightweight durable and resumable local jobs

Selected by the operator on 2026-07-18: use a lightweight local research-job runner backed by the durable research store. The browser creates and observes jobs but never owns their execution. The MVP does not require Redis, Celery, a network broker, or a distributed scheduler.

The visible lifecycle is:

```text
QUEUED -> RUNNING -> COMPLETED
             |-> CANCEL_REQUESTED -> CANCELLED
             |-> INTERRUPTED
             `-> FAILED
```

Before entering `QUEUED`, the system persists the experiment identity and digest, canonical configuration, dataset/manifest and evidence role, build/code and schema versions, cost/fill assumptions, declared work plan, resource profile, and attempt identity. A queue position is not evidence that execution started.

Progress commits at deterministic safe work boundaries such as a completed trial, walk-forward fold, sensitivity scenario, or replay segment. The UI shows current phase, phase and total completed/remaining units, elapsed time, approximate remaining time with its uncertainty, latest durable checkpoint, resource usage against the local budget, warnings, and the last worker heartbeat. Progress percentages are derived from declared work units rather than invented from elapsed time.

Cancellation is cooperative. `CANCEL_REQUESTED` stops admission of new work units, completes or safely abandons the current unit according to its contract, persists the boundary, and ends as `CANCELLED`. Closing the page neither cancels nor detaches evidence from the job.

An unclean service exit, laptop sleep/restart, lost worker heartbeat, or process replacement changes a previously running attempt to `INTERRUPTED`; it cannot remain falsely `RUNNING` or be classified as a strategy failure. Resume is an explicit operator action after store integrity and exact experiment, dataset, build, schema, and checkpoint compatibility are verified. It reuses only completed deterministic units with stable fingerprints and continues the same experiment/attempt history. A changed input, assumption, build, or evidence role uses `Clone as new experiment`.

`Retry from zero` creates a new attempt identity under the same immutable experiment while retaining the prior failed/cancelled attempt and its evidence. Deterministic invalid-input failures are not offered as resumable. Repeated infrastructure failure is visible and never silently loops.

The default local resource policy runs at most one heavy research job concurrently; other heavy jobs remain queued. Small explicitly classified work may share capacity only after measured resource policy allows it. This preserves laptop responsiveness and avoids a distributed scheduler while leaving a future worker-port seam.

Example: a 100,000-trial search has 37,420 durably completed trial fingerprints when Windows restarts. On service restart the attempt becomes `INTERRUPTED — 37.4% preserved`; after verification, explicit Resume schedules the next incomplete trial. Editing the range or upgrading the engine instead creates a new experiment.

Consequences:

- long searches survive browser closure and laptop interruption without overstating completion;
- progress, resume, and comparison evidence are deterministic and provenance-bound;
- one local store/runner is sufficient for the personal MVP and remains simpler to operate and test;
- the runner needs crash-boundary, cancellation, checkpoint, deduplication, compatibility, and resource-budget tests; and
- job status is research evidence but never online runtime or promotion status.

Declined alternatives:

- synchronous browser-request execution as the only model, because long work would be coupled to page, HTTP, service, and laptop continuity;
- Celery/Redis distributed jobs, because their services and failure modes are not justified for one laptop/operator before measurements require them;
- restart an interrupted search automatically with changed code or data, because prior trial fingerprints would no longer describe identical work; and
- overwrite a failed attempt during retry, because the lost evidence would hide reliability defects and search exposure.

## Decision 6: return-led evidence results with bounded comparison and trade visualization

Selected by the operator on 2026-07-18: use a return-led, evidence-first result workspace. Net return is the headline performance measure, but it cannot compensate for a mandatory correctness, accounting, parity, risk, robustness, activity, data, or evidence failure. There is no composite deployment/trust score.

A single result uses six stable views:

1. **Overview** — net return, Buy-and-Hold/DCA comparison, promotion eligibility, hard-gate summary, maximum drawdown, completed-cycle activity, and concise plain-language interpretation;
2. **Performance** — equity/benchmark/drawdown curves, period and regime returns, capital utilization, inventory exposure, and terminal result;
3. **Economics & Accounting** — realized grid profit, actual fees and fee assets, spread/slippage cost, quote/base flows and ending equity, gross/net cycle edge, rejections, and reconciliation/invariant outcome;
4. **Trades & Execution** — the interactive trade visual analysis defined below, exact trade/fill/cycle tables, holding durations, post-only rejections, partial-fill behavior, and execution quality;
5. **Robustness** — walk-forward/holdout, cross-symbol/regime breadth, parameter plateau, Deflated Sharpe credibility, fidelity parity, and execution sensitivities; and
6. **Evidence** — exact configuration/dataset/build/assumption/experiment identities, job attempts, warnings, logs, reports, and sealed evidence downloads.

### Interactive trade visual analysis

The result dashboard includes an interactive price-and-grid chart sourced from canonical market, order, fill, fee, and paired-cycle records rather than reconstructing trades in the browser. It shows:

- price/candle or event evidence with the configured lower/upper bounds, activation reference, and arithmetic/geometric rung prices;
- distinct accessible shapes for buy fills, sell fills, bootstrap acquisition, stop/terminal disposal, and rejected/cancelled order context where useful;
- partial fills at their actual quantity and time, visually grouped under the managed order but expandable to each fill and fee asset;
- a selectable paired cycle connecting the accumulated buy obligation to its cumulative paired sell completion, including realized gross spread, fees, slippage, net result, and holding duration;
- synchronized inventory/base, quote balance, grid equity, realized P&L, drawdown, and safety/lifecycle annotations over the selected interval; and
- zoom, pan, time brush, rung/side/cycle/outcome filters, show/hide layers, reset, and evidence-aware tooltip/detail drawer.

Clicking a marker highlights its managed order, rung, complete fill sequence, paired obligation, accounting postings, and canonical event/journal references. Selecting a table row focuses the chart on the same evidence. Visual aggregation may reduce marker density at wide zoom levels, but it must display the aggregation count and expand to exact underlying records; it cannot discard or alter evidence.

Color is never the only side/outcome encoding. Tooltips show exact source/event time, price, base/quote quantity, fee quantity/asset, order/fill identity, rung, cycle identity, and simulation/venue provenance. The default chart avoids clutter by showing completed cycles and material lifecycle/safety annotations, with optional incomplete orders and detailed fills.

For candidate comparison, up to four compatible experiments appear in aligned columns with synchronized time ranges or small-multiple charts. The UI does not place every trade from several experiments on one price chart. Larger sets use a sortable/filterable results table and drill into the selected experiments.

Comparison first exposes hard failures and promotion ineligibility, then applies the accepted lexicographic ranking among survivors: return is primary outside the practical-equivalence band; accepted risk/stability criteria decide inside the band. Differences in datasets, periods, symbols, fees, fidelity, build, and evaluation role are explicit. Incompatible experiments may be inspected diagnostically but receive no declared winner. Unrelated P&L paths are never added into a fictional research portfolio.

Example: Candidate B has the highest net return but fails fidelity parity; it remains visibly highest-return but non-promotable and cannot outrank passing candidates. Candidates A and C have materially equivalent returns, so their accepted drawdown/stability criteria decide the order. Opening Candidate C's weaker period selects the exact cycles, inventory path, and market evidence responsible for the difference.

Consequences:

- return remains prominent while non-compensating gates retain authority;
- visual analysis connects apparent performance to actual rung cycles, inventory, costs, and market paths;
- the backend must expose canonical chart-ready references/series without making downsampled pixels authoritative evidence;
- charts and tables require synchronized selection, accessible encodings, density controls, and exact drill-through tests; and
- comparison compatibility and ranking explanations become explicit data contracts rather than frontend heuristics.

Declined alternatives:

- one composite trust score, because weighting could hide mandatory failures and imply false precision;
- a raw metric/chart explorer without a fixed hierarchy, because the operator would have to remember every gate and compatibility rule;
- combined P&L across unrelated experiments, because it represents no executable portfolio or promotion claim;
- browser-reconstructed trades from equity changes, because partial fills, fee assets, paired provenance, and rejections would be lost; and
- plotting all compared candidates' trades on one chart, because marker density would obscure rather than support analysis.

## Decision 7: ranked candidate shortlist with evidence gate matrix

Selected by the operator on 2026-07-18: the Candidates area combines a ranked shortlist with an evidence gate matrix for the selected candidate. Automatic selection, mandatory-gate override, and a composite readiness score remain prohibited.

The shortlist shows candidate identity, symbol/search family, eligibility, net return and benchmark difference, maximum drawdown, Deflated Sharpe credibility, out-of-sample result, regime/panel breadth, fidelity parity, completed-cycle activity, evidence freshness, and ranking explanation. Hard-failed candidates remain visible for learning and debugging but are excluded from the promotable ranking.

Among candidates with complete current mandatory evidence, the UI applies the accepted lexicographic order. Return is primary outside the practical-equivalence band. When candidates are materially equivalent on return, the next accepted risk/stability criterion decides. Every change in rank includes a machine-generated explanation linked to the exact values and frozen ranking-policy version; the UI never invents a weighted score.

The selected candidate's gate matrix groups correctness/accounting, data quality, parity/fidelity, economic return/activity, cross-symbol/regime/robustness, execution sensitivity, evidence freshness, and applicable safety requirements. Every gate row contains:

- stable requirement/gate identity and policy version;
- state: `PASS`, `FAIL`, `NOT_RUN`, `INVALIDATED`, `EXPIRED`, or `NOT_APPLICABLE`;
- required threshold/condition and exact observed value;
- evaluation time and the dataset, build, configuration, assumption, and result identities;
- concise reason, invalidation/expiry cause where applicable, and evidence link; and
- whether it blocks selection, package preparation, later activation, or is diagnostic only.

Warnings are separate from gate states. Acknowledging a warning records that it was read but cannot turn a failed, missing, invalidated, or expired mandatory gate into a pass. Filtering can focus on blocking or changed items without hiding their count/status from the summary.

Up to four compatible candidates can be compared using the accepted Decision 6 metrics, small multiples, and trade analysis. Incompatible evidence can be inspected side by side but is clearly non-ranking. Selecting a shortlist row updates the matrix and evidence drawer without losing comparison context.

The only selection action is `Select candidate for paper-package preparation`. Before confirmation, Studio shows the exact candidate digest, current gate completeness/freshness, ranking reason, alternatives considered, and the fact that selection neither creates/admit a package nor starts paper or live operation. Confirmation creates an append-only candidate selection record containing operator, time, selected digest, ranking-policy/evidence snapshot, compared candidate identities, and optional operator rationale. A later different selection creates a new record; it never edits the prior decision.

Example: Candidate B has `16.8%` return but `FAIL` fidelity parity and stays visible as highest raw return but non-promotable. Candidates A (`14.2%`, larger drawdown) and C (`13.9%`, smaller drawdown) both pass and fall inside the accepted practical-equivalence band; the matrix shows the exact next criterion that ranks C or A rather than presenting a mysterious score.

Consequences:

- the operator can see both performance and why a candidate may or may not advance;
- failure diagnosis starts from the exact threshold, value, and evidence instead of a generic banner;
- selection remains manual, immutable, reviewable, and separate from package handoff/online authority;
- the backend owns gate/ranking states and explanations, while the frontend presents and navigates them; and
- UI tests must prove no failed/incomplete/expired candidate can expose a successful selection action and no acknowledgement changes gate authority.

Declined alternatives:

- a sequential checklist as the primary view, because it makes cross-candidate comparison and revisiting related gates slow;
- a compact table plus one pass/fail banner, because it hides thresholds, invalidation, provenance, and debugging evidence;
- one composite trust/deployment score, because weighted compensation can conceal mandatory failures; and
- an override or automatic highest-return selection, because both contradict the accepted evidence-bound manual promotion contract.

## Decision 8: guided four-stage sealed candidate handoff

Selected by the operator on 2026-07-18: the cross-workspace handoff is a guided, evidence-bound pipeline with four explicit states of responsibility—prepare, seal, transfer, and verify/admit. Package admission and starting paper qualification are separate actions.

### Stage 1 — Prepare in Research

Studio displays the exact symbol-specific candidate and selection record; complete gate matrix and evidence identities; canonical configuration; code/build and schema versions; dataset/market-evidence manifests; fee, spread, slippage, fill, rounding, and venue-rule assumptions; risk/evaluation policy; required reports/artifact references; retention dependencies; and every missing, expired, or invalidated item.

Preparation is blocked unless all required historical-promotion gates are current and passing and all package dependencies can be resolved. The operator reviews the complete manifest preview and the consequences of the candidate's capital, inventory, fee-reserve, stop, and evidence configuration.

### Stage 2 — Seal in Research

Sealing produces one immutable paper candidate package with package identity, candidate digest, manifest version, per-file/reference checksums and lengths, package checksum, creation time, and causal link to the selection record. The package contains no credentials or secrets.

After `SEALED`, contents cannot be edited, silently supplemented, or relabelled. Any configuration, build, dataset, assumption, gate evidence, or required dependency change creates a new candidate/package identity. A sealed package may be inspected, exported, and transferred, but it has no Azure/runtime authority.

### Stage 3 — Transfer across the trust boundary

```text
SEALED -> TRANSFERRING -> RECEIVED
```

Transfer uses the authenticated handoff port selected later by the security/Azure specifications and is idempotent by exact package identity/digest. Progress, retries, timeout/unknown receipt, destination, and checksums are visible. A retry queries/reuses the original identity and cannot create a semantically duplicate package. Manual sealed export/import remains a supported recovery path, not the primary workflow.

### Stage 4 — Verify and admit in Operations

```text
RECEIVED -> VERIFYING -> ADMITTED | REJECTED
```

Azure independently verifies manifest/checksum/length, package completeness and resolvability, schema/build/runtime compatibility, exact candidate/evidence identities, current required gates and freshness, supported static-Spot configuration, retention availability, and absence of unexpected or prohibited secret content. Rejection preserves the exact failed checks and received artifact evidence; it never edits the package.

`ADMITTED` means only that Azure accepted and preserved that exact package for the applicable qualification workflow. It does not start a runtime, start the qualifying paper clock, submit an order, grant activation authority, or prove the strategy safe/profitable. Starting paper is a separate authenticated command after runtime recovery/readiness and a fresh package-specific preflight.

A later package may explicitly supersede the admitted choice, but prior selections, packages, transfers, admission decisions, qualification effects, and reasons remain immutable. If supersession affects an active qualifying run, the accepted requalification/reset rules apply visibly; the UI cannot swap a package beneath a running clock.

Consequences:

- the operator can prove exactly what moved from historical research into online qualification;
- transfer failure, package rejection, admission, and runtime start have distinct truthful states;
- Git remains appropriate for source/deployment definitions but is not used as candidate admission authority;
- the backend owns package construction/verification while the frontend renders manifest/evidence and requests explicit transitions; and
- tests must cover checksum mismatch, missing references, stale gates, duplicate/retried transfer, incompatible build/schema, prohibited content, supersession, and the absence of automatic runtime start.

Declined alternatives:

- manual download/upload as the primary flow, because file copies and destination ambiguity add avoidable operator error, though sealed manual transfer remains a fallback;
- Git-based candidate handoff, because it couples research selection to code deployment and cannot carry/authorize the complete evidence package cleanly;
- a direct `Send/Promote to paper` button, because it collapses selection, sealing, transfer, admission, preflight, and runtime authority; and
- editable Azure-side candidate settings, because resulting paper evidence would no longer correspond to the reviewed historical candidate.

## Decision 9: purpose-separated Paper and Testnet qualification workspace

Selected by the operator on 2026-07-18: `Operations > Qualification` presents production-data paper and Binance Testnet evidence together at summary level but in separate purpose-labelled workspaces, stores, clocks, ledgers, controls, incidents, and economics. Their requirements combine with logical `AND`; their data never merges.

The overview is bound to one exact admitted paper candidate package and decision-critical build and states each purpose explicitly:

| Environment | Market and orders | Qualification claim |
| --- | --- | --- |
| Production-data paper | Binance production public market evidence with locally simulated orders and virtual allocation ledger | Production-market strategy behavior, economics, decision parity, accounting, and unattended operation |
| Binance Testnet | Testnet market/account evidence and actual Testnet API commands against virtual venue balances | Venue protocol, order/account lifecycle, streams, rate limits, command ambiguity, reconciliation, restart, and recovery integration |

### Paper workspace

It shows the consecutive 30-day qualifying clock and exact start/boundary; package/build/data/fill/risk identities; production-market freshness/capture; simulated order/fill/cycle and interactive trade evidence; return/drawdown/fees/execution-assumption divergence; identical-input decision parity; accounting/reconciliation/invariants; decision-ready availability; completed-cycle activity; incidents, deliberate faults, unavailable/frozen intervals; and the effect of every interruption/change on clock continuity and qualification.

Paper profit is visible and compared with historical expectations, but one month's positive profit is not the sole gate and a safe loss cannot be hidden. No production private-account data, Binance production order, or real account balance appears as paper state.

### Testnet workspace

It shows the seven-day soak; Testnet endpoint/account generation and virtual balances; versioned venue-contract scenario matrix; submissions, acceptances, rejections, cancellations, partial/late fills and native commissions; unknown outcomes and reconciliation; public/private stream rotation/gaps/repair; filters, permissions, timestamps and rate limits; planned/crash restart recovery; incidents and unresolved scenarios; and protocol evidence links.

Every economic field is labelled `DIAGNOSTIC — NOT PRODUCTION PERFORMANCE EVIDENCE`. Testnet balances, fills, prices, returns, clocks, and incidents never contribute to paper P&L or replace a paper requirement.

### Combined qualification readiness

The overview exposes historical/package state, Paper state, Testnet state, blocking item count, and overall next-stage readiness without a weighted score. Each environment can be `NOT_STARTED`, `IN_PROGRESS`, `RESTRICTED`, `INTERRUPTED`, `FAILED`, `QUALIFIED`, `INVALIDATED`, or `EXPIRED` as applicable under its governing evidence contract. The overall result is not ready unless every mandatory current component passes.

Paper and Testnet may run concurrently on their isolated runtimes. Controls and links always bind an explicit environment/runtime identity. A Testnet defect does not pause/reset paper unless the shared VM/network/disk/evidence/control boundary becomes unsafe; such a shared cause links two separate effects rather than merging the incidents.

Every pause, restriction, interruption, build/package change, evidence gap, invalidation, or reset shows what happened; affected environment and interval; whether its clock continued, was preserved with visible degraded time, ended, or must restart; invalidated evidence; governing rule; and exact conditions to continue or begin a new attempt.

Consequences:

- the operator can see both requirements and their combined readiness without confusing their claims;
- paper remains the production-market performance/behavior simulator and Testnet remains the protocol integration environment;
- concurrent qualification shortens elapsed time without weakening isolation;
- shared infrastructure incidents remain causally linked but environment-specific; and
- UI/API tests must prohibit cross-environment balances, orders, P&L, clocks, controls, or authority and must preserve the Testnet diagnostic label.

Declined alternatives:

- a forced paper-then-Testnet sequence, because independent qualification can run concurrently and the sequence adds delay without evidence benefit;
- one merged `paper trading` dashboard, because it falsely equates production simulation with Testnet integration and risks mixing balances/P&L;
- one combined qualification score, because paper and protocol failures are non-compensating; and
- Testnet profitability as a live-readiness claim, because its market and virtual account do not represent production economics.

## Decision 10: separate promotion approval and live-confirmation screens

Selected by the operator on 2026-07-18: first-live activation is presented as two separate evidence-bound workflows and durable actions, never consecutive pages of one disposable modal. Passing gates, opening either screen, deployment, or time passage cannot synthesize an action.

### Step 1 — promotion-bundle approval

The read-only approval screen identifies the exact promotion-bundle digest; decision-critical build/source/dependency/schema/replay identities; immutable strategy, symbol, quantized ladder, activation/bootstrap and terminal behavior; production Binance account/allocation and permission profile; deployment and risk-profile identities; `250 USDT` maximum allocation; exact proposed quote/base/fee-asset quantities and dynamic fee reserve; daily/run/terminal loss limits; every historical, Paper, Testnet, accounting, reconciliation, recovery, fault, availability, activity, security, and incident gate; evidence/report/archive digests; zero-unresolved-gate statement; and non-blocking diagnostic warnings.

Missing, failed, invalidated, expired, superseded, or unresolved mandatory evidence blocks approval. Warning acknowledgement cannot override it. The operator accepts the exact digest with an action labelled for its effect, for example `Approve bundle a83f… for one BTCUSDT live-activation attempt`.

Approval creates an activation authorization bound to the exact bundle and activation context. It sends no Binance command, starts no grid, and begins a visible 15-domain-minute expiry. The approval page and durable record remain navigable after expiry or use.

### Step 2 — re-authenticated live confirmation

A separate screen has the persistent `LIVE` authority context and shows the remaining authorization time, exact approved account/allocation/deployment/build/candidate/risk identities, current price and configured bounds, quantized bootstrap acquisition and initial order plan, maximum planned inventory/exposure, exact required assets and fee reserve, current venue filters/fees/permissions/order headroom, and stream/clock/persistence/alert/control-path/reconciliation/incident/command-certainty state.

A fresh fail-closed preflight runs immediately before confirmation and again immediately before executable bootstrap authorization. Each requirement displays `PASS`, blocking state, current exact value, source time/freshness, and evidence. Confirmation remains unavailable unless all required identities match; price is strictly within bounds; the plan is fully funded and venue-valid within `250 USDT`; and every continuity, persistence, control, invariant, reconciliation, incident, and unknown-command rule passes.

The operator re-authenticates using the security specification's selected mechanism and invokes an explicit action such as `Confirm one LIVE BTCUSDT activation — maximum 250 USDT`. It cannot be a generic `OK`, keyboard-default action, or hidden continuation from approval.

After confirmation the UI shows `ACTIVATION ATTEMPT PENDING`, not `RUNNING`, until authoritative outcome evidence arrives. Confirmed success consumes the authorization and opens first-live probation. Confirmed rejection consumes it and shows the exact reason. An uncertain bootstrap outcome consumes it, selects the accepted frozen/reconciliation path, and never exposes a blind retry. Operator cancellation, expiry, failed preflight, or any material identity/context change invalidates or consumes the authorization under the accepted contract and requires a new bundle/approval where applicable.

The resulting 30-day first-live probation view starts only at the accepted durable activation boundary and displays its immutable identities, capital ceiling, review schedule, activity requirement, incidents/restrictions, and completion/abort evidence. Successful activation is never labelled fully validated live operation.

Consequences:

- careful evidence review and immediate capital authorization remain temporally and visually distinct;
- the operator always sees the exact real account, amount, grid, risk limits, current market eligibility, and command scope before confirmation;
- pending, rejected, expired, invalidated, and uncertain outcomes retain truthful durable states and audit links;
- authentication technology can be selected later without changing the two-action semantic contract; and
- end-to-end tests must prove no auto/cross-environment/default action, stale approval, failed preflight, double attempt, or false running state is possible.

Declined alternatives:

- one modal containing both actions, because rapid click-through and ephemeral evidence weaken deliberate review and later audit navigation;
- Studio approval followed by command-line activation, because the target identity, preflight, and audit trail would be fragmented;
- one confirmation that both approves and activates, automatic gate-driven activation, a 24-hour cooling period, or two-person approval, as already declined by the promotion contract; and
- presenting REST submission success as a running grid, because bootstrap acceptance/execution may still be uncertain.

## Decision 11: task-prioritized Command Center with large trade chart

Selected by the operator on 2026-07-18: the current-runtime Command Center prioritizes safety/capital context, visual trade analysis, current rung/order obligations, exact allocation/accounting, and recent causal operations in that order. It is neither a chart-only discretionary terminal nor an all-metrics operations wall.

The persistent authority context header remains above the page. The first in-page strip shows conservative grid equity and net return; exact allocated, reserved, committed, available, and fee-reserve assets; applicable `250 USDT` authority; daily-loss, run-drawdown, and terminal-loss threshold usage/distance; price position within bounds and range-exhaustion state; unknown-command and unresolved-reconciliation counts; and highest active incident. Each value has an authoritative `as of` boundary and evidence link.

The main workspace gives the interactive price/grid/trade overlay the largest region. In live it uses actual venue order, execution, commission, account, and market evidence and includes current price/bounds/rungs; bootstrap/disposal; resting, partial, filled, cancelled, rejected, cancellation-pending, and outcome-unknown orders; exact buy/sell fills and fee assets; paired-cycle connections/results; synchronized inventory, balances, equity/P&L/drawdown; and pause/stop/recovery/reconciliation/incident annotations. The Decision 6 accessibility, zoom/filter, density, table synchronization, and exact drill-through rules apply unchanged.

Beside the chart, the current rung ladder shows for every rung: price, side/obligation, managed-order identity/generation, effective state, filled/remaining quantity, reserved assets, paired provenance, configured versus submitted price, post-only attempt state, and expected net edge. Empty, valid resting, partial, cancellation-pending, and outcome-unknown states are unmistakable. Duplicate/one-order-per-rung violations are critical, not visually collapsed.

The accounting area presents exact quote/base/fee-asset quantities by free/reserved/committed classification; planned versus current and maximum inventory; realized grid profit versus unrealized inventory movement; actual fees by native asset; conservative liquidation equity; allocation coverage; and foreign/manual order or balance activity affecting allocation/headroom. Whole-account observations are shown only as coverage/foreign-context evidence and never added to grid performance.

Stable lower tabs show managed orders, individual fills, paired cycles, command lifecycle/outcomes, accounting postings, and the causal event timeline. Selecting any record focuses the related chart interval/rung/cycle and opens linked reconciliation, incident, journal, and evidence views. Filters change presentation only and cannot change runtime state.

Paper and Testnet may reuse this view contract only with their explicit environment labels, isolated evidence and purpose. Testnet P&L retains its diagnostic warning. Live data always comes through the authenticated control gateway's read projections; the browser never queries Binance or an authoritative store directly.

Safety actions are spatially and semantically separated from chart filters and ordinary navigation. Their exact admission, confirmation, dominance, and disposition workflow is Decision 12.

Consequences:

- visual market/rung/cycle analysis remains central without hiding capital, inventory, fees, risk, reconciliation, or uncertainty;
- the same canonical identity links charts, tables, accounting, commands, incidents, reconciliation, and audit evidence;
- page projections must retain exact source times and distinguish delayed visualization from authoritative state;
- the one-symbol MVP avoids customizable dashboards while preserving later typed panels; and
- UI tests must cover partial/late fills, native fees, range exhaustion, unknown commands, duplicate rung state, foreign activity, stale projection, and chart/table/evidence synchronization.

Declined alternatives:

- a chart-centric TradingView-style terminal, because operational/accounting uncertainty and risk limits could become secondary;
- a table-centric operations console, because it weakens the visual trade analysis explicitly required by the operator;
- a configurable drag-and-drop dashboard, because it adds complexity and can hide mandatory safety context; and
- displaying whole-account equity as grid performance, because the allocated grid is economically isolated from manual/other-algorithm activity.

## Decision 12: persistent graduated safety controls with command-specific workflows

Selected by the operator on 2026-07-18: a compact, environment-bound safety rail remains available throughout Operations and presents `Pause`, `Operator Stop`, and `Emergency Stop` as distinct commands. Resume and inventory disposition appear only when applicable. Controls never appear in Research, never use generic labels, and never share one generic confirmation policy.

### Exposure-reducing Pause

Before request submission, a concise consequence panel states that Pause cancels/blocks exposure-increasing buys, retains only proven valid inventory-reducing sells, retains inventory, and blocks bootstrap/configuration change; it does not close the run or liquidate. It requires an authenticated explicit action but not fresh re-authentication.

The visible command path is `REQUESTED -> DURABLY_ADMITTED -> CANCELLING_BUYS -> RECONCILING -> PAUSED`, with explicit rejected or outcome-unknown states. The UI changes canonical status only after corresponding runtime evidence; late/racing fills remain visible and update inventory, obligations, fees, and accounting.

### Operator Stop

Operator Stop permanently ends the grid run, cancels every managed buy and sell, reconciles cancellations/racing/late fills, prevents future resume under that run, and determines final grid inventory. Its review shows the exact environment/run, current orders/inventory, consequences, and default `retain` disposition. It requires fresh authentication and explicit permanent-action confirmation.

After authoritative cancellation/reconciliation, retaining inventory creates the accepted retained holding linked to the closed run. `Liquidate inventory` is a separate freshly confirmed workflow with current exact quantity, executable-price evidence, estimated fees/slippage/proceeds, bounded terminal order plan, and possible venue-invalid residual. Operator Stop never silently liquidates.

### Emergency Stop

Emergency Stop is visually separated and immediately available across Operations. One authenticated action activates the reserved fail-closed path without a confirmation dialog: block new trading commands; cancel every managed buy and sell; retain inventory; reconcile late fills and uncertain outcomes; and leave the runtime/run in the accepted frozen emergency condition for deliberate follow-up. It never automatically liquidates or represents cancellation as complete before evidence.

### Reconciled Resume

Resume is not the inverse of Pause and never a direct toggle. It requires fresh authentication and a complete preview/preflight proving selected runtime/state/config versions, reconciliation with zero unresolved decision-material differences, no unknown command, passing accounting/risk invariants, current venue rules/fees/permissions/order headroom, exact balances/allocation/fee coverage, fresh market/account/control paths, and current price/range state. It lists only the currently missing valid orders that would be recreated. If price is outside bounds, accepted range-exhausted behavior applies rather than new exposure beyond the grid.

### Command interaction and evidence

Every request carries idempotency key/digest, exact environment/runtime/run, expected state/config version, issued/expiry time, and authenticated operator. Repeated identical requests return the original result; changed content under one key conflicts. Stale/wrong-target requests fail before admission. The UI shows request, durable admission, interlock, dispatch/cancellation, reconciliation, and completion separately and never updates optimistically.

An admitted Emergency Stop, Operator Stop, or Pause dominates a later Resume/Start. Concurrent commands remain in canonical ingress order; the UI cannot resolve a conflict by button order. Any outcome-unknown command becomes persistent header/reconciliation/incident state. Safety views retain cancellations, late fills, disposition, authentication, confirmation, and evidence links.

Consequences:

- urgent restriction remains accessible without making destructive and reversible commands look equivalent;
- the operator sees exactly which orders survive Pause and that both Stop types cancel buys and sells;
- retain-by-default prevents an ordinary or emergency stop from accidentally selling inventory;
- resume cannot bypass recovery merely because a button becomes visible; and
- UI/E2E tests must exercise stale context, double clicks, concurrent Pause/Resume, late fills, unknown cancellation, auth expiry, stop retain/liquidate, emergency no-confirmation, and truthful status progression.

Declined alternatives:

- one generic Actions menu/confirmation, because it hides the urgent path and misrepresents distinct semantics;
- a dedicated Safety page only, because navigation delay and loss of current context weaken emergency response;
- optimistic status change on click, because durable admission and venue cancellation may fail or remain unknown;
- confirmation before Emergency Stop, because it delays the accepted immediate fail-closed action; and
- automatic liquidation on Pause/Stop/Emergency, because disposition is a separate economic decision and retain is the safe default.

## Decision 13: case-based reconciliation with item-level evidence

Selected by the operator on 2026-07-18: every reconciliation trigger creates or causally updates an identifiable reconciliation case. The workspace exposes the complete trigger-to-convergence workflow; it does not reduce reconciliation to a green/red badge or raw database diff.

The case header identifies environment/runtime/run/candidate/configuration; trigger and linked command/incident/recovery; start/latest times; each REST/stream evidence boundary and convergence iteration; scope and deadline; current reconciliation classification; effective safety posture; material unresolved count; and explicit `Resume BLOCKED/ELIGIBLE` result.

The scope summary covers all effective/outcome-unknown managed orders, relevant recent/terminal order history, trades/executions/native commissions, exact balances for every actual asset, grid allocation/reservations/fee reserve, inventory lots and paired obligations, whole-account allocation coverage/foreign activity, current venue rules/permissions/order limits, and related local expectations. It states which sources/pages/time boundaries have and have not been observed; one successful request is never presented as a complete snapshot.

The item matrix shows one reconciliation item per identified expected/observed material fact with stable identity/type; exact local expectation; exact authoritative evidence and source/request/page time; native-unit difference without arbitrary tolerance; `RECONCILED`, `PENDING_EVIDENCE`, `VENUE_AHEAD`, `LOCAL_AHEAD`, `CONFLICTING_EVIDENCE`, or `UNEXPLAINED_DIFFERENCE`; decision-material reason/safety effect; related command/order/fill/fee/allocation/posting identities; and next query/evidence/repair.

Selecting an item opens a causal timeline and side-by-side evidence detail, including original canonical events, command lifecycle, WebSocket generations/gaps, REST queries and pagination, orders/trades/fees/balances, accounting postings, market/trade chart interval, and every prior repair attempt. Raw payload display follows redaction and retention rules and is never required to understand the normalized difference.

The repair panel distinguishes:

- **authoritative fact admission/rebuild:** append a proven missing order, fill, commission, balance or venue fact and rebuild projections/inventory/obligations/accounting; this records authority and does not require operator discretion;
- **continued evidence collection:** query/repeat non-atomic sources until the case converges or remains explicitly pending/conflicting; and
- **material adjustment:** a compensating posting, allocation change, adoption/disposition of foreign activity, or another decision requiring exact before/after native assets, accounting/risk effect, evidence/rationale, fresh authentication, and explicit operator approval.

No action edits/deletes a prior event/posting, invents a balance, silently forces local state to match one response, or uses acknowledgement as repair. Late fills and actual fee assets post with original identities/times and update the trade overlay and obligations.

A case becomes `RECONCILED` only after the applicable reads converge, all items have authoritative evidence/accepted repair, invariants and allocation coverage pass, and zero decision-material differences remain. Failed deadlines preserve the non-reconciled state and safety restriction. Resume remains blocked until the separate Resume preflight consumes the successful current case; case success alone never auto-resumes.

Example: a cancel response is lost, local projection expects cancelled, and Binance later proves a `0.003 BTC` fill plus `0.0004 BNB` fee. The case marks order/fill/fee and BTC/BNB balance items `VENUE_AHEAD`, appends the authoritative facts, rebuilds inventory/paired obligations/postings, repeats account/order reads, and closes only when the exact balances converge. No compensating operator posting is needed unless evidence reveals an additional unexplained external effect.

Consequences:

- the operator can understand why the runtime is frozen and what exact evidence would unblock it;
- safe authoritative repair remains automated/evidence-driven while discretionary material changes remain explicit;
- reconciliation, trade chart, accounting, commands, incidents, and audit share canonical identities;
- the UI must support large-but-bounded item sets through grouping/filtering without hiding blocking counts; and
- contract/E2E tests must cover non-atomic reads, pagination, cancel/fill races, native fees, foreign activity, conflicting sources, material approval, convergence, deadlines, and no auto-resume.

Declined alternatives:

- automatic reconciliation with summary-only reporting, because material differences/adjustments and evidence boundaries would be opaque;
- a raw local-versus-Binance diff explorer, because manual identity/source/pagination correlation is error-prone;
- tolerance-based green status, because a numerically small unexplained asset difference can change obligations or authority; and
- manual `Mark reconciled`, because acknowledgement cannot replace authoritative convergence.

## Decision 14: root-condition incident inbox and evidence case pages

Selected by the operator on 2026-07-18: Incidents uses a triage inbox of durable root-condition cases, not a per-log/per-alert event feed. Matching occurrences update one open incident by deterministic fingerprint and scope, retaining count, first/latest time, maximum severity, and every occurrence.

The inbox shows severity; `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, or `CLOSED`; environment/runtime/run; concise root condition; occurrence count and latest time; current safety/qualification/availability effect; acknowledgement/reminder state; and blocking linked reconciliation/command where applicable. Filters never hide the total critical/unacknowledged count from the authority context header.

The incident case page contains stable identity/fingerprint and detection-rule version; affected identities; first/latest occurrence and maximum severity; exact observed values/thresholds and source times; current posture/readiness/qualification impact; related commands/orders/fills/assets/reconciliation; journal, diagnostic log, span, metric, market-capture and backup/restore evidence; alert destinations, deliveries, retries and reminder schedule; authoritative recovery conditions and applicable runbook; and the complete occurrence/operator/system transition timeline.

The lifecycle remains:

```text
OPEN -> ACKNOWLEDGED -> RESOLVED -> CLOSED
```

Acknowledgement records authenticated operator/time and optional note and changes reminder scheduling only. It cannot lower severity, change safety posture, resolve evidence, stop escalation, or authorize resume.

`RESOLVED` requires the incident-specific authoritative recovery rule—for example proven stream continuity plus converged reconciliation, a verified durable write/read, or restored external supervision. The operator cannot manually mark a condition resolved merely because it appears quiet. Severity may escalate automatically as duration/impact grows; maximum severity remains in the record.

Warning and critical incidents require an incident closure review after resolution. The operator inspects the recovery evidence, records conclusion/follow-up and any corrective ticket or preservation hold, then closes. A matching condition recurring while the case is not closed adds an occurrence and may reopen/escalate according to policy; recurrence after closure creates a new linked incident so the prior review is never rewritten.

Alert-delivery states for Studio, email, mobile/SMS/push, and external dead-man path are visible. Notification content remains secret-minimized and non-actionable; its authenticated link opens the incident but cannot acknowledge or control trading. Critical incidents remain in the authority context after acknowledgement until authoritative resolution.

Consequences:

- repeated technical noise becomes one understandable operational problem without losing occurrences;
- acknowledgement, recovery proof, and closure remain distinct and auditable;
- incident navigation unifies safety state, reconciliation, commands, runtime evidence, alerts, and runbooks;
- external notification failure itself remains visible/escalatable; and
- tests must cover fingerprint aggregation, escalation, acknowledgement limits, authoritative resolution, closure review, recurrence, delivery failures, dead-man incidents, and persistent critical header context.

Declined alternatives:

- a chronological alert-event feed, because repetition creates noise and obscures root recovery state;
- dashboard counters with email/mobile as the primary workflow, because evidence, acknowledgement, and closure become fragmented;
- manual resolve/close as one action, because silence or acknowledgement is not recovery proof; and
- actionable notification links, because external message channels are not authenticated trading-control surfaces.

## Decision 15: local causal analysis with sealed evidence bundles

Selected by the operator on 2026-07-18: Evidence & Audit provides a causal explorer, operator/configuration history, evidence-bundle builder, and verified download/cache workflow. Analysis and visualization occur in the local Operator Studio; evidence authority and storage remain source-specific.

### Data and authority boundary

- Historical backtest/research input, jobs, results, comparisons, and locally created candidate evidence are collected in the laptop research store and analyzed locally.
- Paper, Testnet, and later live runtime evidence is generated and durably admitted on Azure, with required closed evidence/recovery artifacts verified and retained in Blob. Azure remains authoritative for those online histories.
- Studio may read current non-authoritative online projections through the authenticated control gateway for operational inspection. Deep/offline analysis uses checksum-verified sealed bundles or referenced sealed Blob artifacts downloaded to a local evidence cache.
- A complete bundle materializes every dependency required for its declared offline inspection/replay. A referential bundle retains explicit Blob dependencies and is not presented as portable/offline-complete.
- Local online-evidence copies are immutable verified analysis inputs and a disposable/rebuildable cache. Local annotations or visual filters never rewrite Azure journals, accounting, commands, incidents, reconciliation, retention, or qualification evidence.
- Laptop outage, deletion, or corruption of the local cache cannot affect Paper/Testnet/live safety. The cache can be rebuilt from retained authorized Blob evidence. Conversely, local research remains usable when Azure is unavailable.

The system need not download every retained raw byte pre-emptively. A complete requested scope downloads all required dependencies; ordinary exploration may fetch only manifests/summaries and retrieve sealed artifacts on demand. Before offline use, Studio shows completeness, checksums, size, source, retention/hold state, and last verification.

### Causal explorer

The operator can begin from a candidate/package, runtime/run, decision, managed order/command, fill/cycle, accounting posting, reconciliation case/item, incident, operator action, activation, or recovery. The explorer relates:

```text
source fact -> canonical event -> prior state/rule -> decision/reason
            -> command -> paper/venue outcome -> fills/fees
            -> accounting/risk -> reconciliation/incident/operator effect
```

Authoritative journal/venue/accounting/approval evidence and non-authoritative logs/spans/metrics/reports use distinct labels. Plain-language explanations render stable reason codes and exact inputs rather than generated guesses. Every item links to the corresponding trade-chart interval and canonical identities.

### Operator and configuration history

Filters cover candidate selections/package admissions; starts/pauses/stops/resumes/emergencies; reconciliation adjustments; promotion/activation; configuration/build/schema/dependency change; restore/recovery/migration; authentication; and command outcome. Later records supersede but never edit history.

### Evidence bundles

The builder accepts a bounded research experiment/candidate, Paper/Testnet/live run, promotion/activation, reconciliation case, incident, or recovery exercise. It computes all dependencies and displays missing/expired/held/referential content before generation.

Every complete or referential bundle has exact scope, canonical manifest, completeness classification, per-file/reference byte length and SHA-256, identities/versions, required journal/market evidence, selected reports/diagnostics, redaction result, and retention/hold dependencies. Generation is a durable job; success requires sealed, checksum/reader-verified publication in Blob or the appropriate local research artifact store.

### Downloads, retention, and holds

Studio downloads only sealed artifacts, never active SQLite/WAL/open capture files. Access authorization/link expiry follows the security specification. Studio verifies manifest/checksums after download and records local cache status without claiming a new authoritative copy. Retention class, expiry, references, and preservation holds are visible; a hold request records reason/review boundary. Ordinary audit actions cannot delete or rewrite evidence.

Consequences:

- the laptop provides the rich offline visual/debug experience requested without becoming an online dependency;
- Azure online evidence retains one authoritative history while sealed copies remain reproducible and independently verifiable;
- bandwidth/storage remain bounded through manifest-first, on-demand, complete-versus-referential behavior;
- research and online evidence can share analysis components while preserving source/authority labels; and
- tests must cover checksum mismatch, incomplete/referential/offline state, interrupted/resumed downloads, cache corruption/rebuild, redaction, holds, causal links, and prohibition of active-file/direct-authority access.

Declined alternatives:

- a file catalogue/log search as the primary analysis surface, because causality and bundle completeness would remain manual;
- fixed reports only, because novel fill/command/accounting/recovery questions require interactive drill-through;
- direct Studio queries against the authoritative runtime database, because analysis load and trust would cross the online boundary;
- treating downloaded online evidence as a writable new authority, because local analysis must not fork runtime history; and
- downloading all retained raw evidence automatically, because manifest-first on-demand retrieval is sufficient and cheaper for the personal MVP.

## Decision 16: explicit last-known state, freshness, and recovery progress

Selected by the operator on 2026-07-18: Studio preserves useful last-known operational context during staleness/disconnection while making observation time and command-path authority unmistakable. It never blanks evidence unnecessarily, presents cached state as current, or queues capital-affecting browser commands for later transmission.

The Studio view freshness state is distinct from runtime lifecycle, service/decision readiness, stream continuity, and safety posture. At minimum it represents:

```text
CURRENT
STALE — last authoritative update <time/age>
DISCONNECTED — last authoritative update <time/age>
RECOVERING — current runtime phase/progress
FROZEN_READY — recovery/reconciliation complete; no trading authority
```

Every displayed online value retains its source/observation time and selected environment/runtime identity. Stale/disconnected pages use persistent text, icon/pattern, and watermark treatment and state exactly which feeds/projections are stale. Color is supplementary. Last-known orders, inventory, incidents, reconciliation, command identities, and evidence remain inspectable with their times; local sealed cached evidence remains available offline.

Projection freshness and command-path availability are separate. A stale market projection does not prove cancellation/query control is unavailable, and a fresh public stream does not prove private/order control. The gateway/runtime authoritatively reports each command's admissibility. If the gateway itself is unreachable, Studio cannot send a command and shows the external alert/runbook route; it does not store a future Pause/Stop/Emergency/Resume/activation command in browser storage.

If a request was durably admitted before its response was lost, Studio represents the original idempotency identity as pending/outcome unknown and queries/reconnects to that identity. It never creates a second request merely because a browser timeout, refresh, or reconnect occurred. If durable admission was never proven, the UI states that fact and requires a new deliberate action after current context is restored.

Reconnection is only transport restoration. The stale/disconnected banner remains until Studio receives an identified fresh snapshot/projection boundary, catches up every applicable sequence or gap repair, admits late facts, and obtains the runtime's authoritative lifecycle/reconciliation/readiness status. Before/after changes—including fills, fees, cancellations, balances, incidents, and command outcomes—are highlighted.

Recovery displays `STARTING`, store/snapshot verification, journal-tail replay with boundary/progress, invariant/accounting checks, stream/control restoration, authoritative queries, surviving-order cancellation, reconciliation/convergence, and `FROZEN_READY`. Progress is evidence-based rather than an invented timer. Failure remains visible at its phase with linked incident/evidence. Completion never auto-resumes; the accepted Resume workflow remains separate.

Class A/B/C degraded states show lost dependency, protected capabilities, disabled/retained commands, evidence/RPO/control consequence, retry/backoff/circuit state, incident/escalation, and recovery proof needed. Optional projections may be disabled without hiding authoritative safety impact.

Consequences:

- the operator retains valuable last-known context during outages without being misled about currency;
- local audit/research remains useful while Azure is unavailable and cannot affect online authority;
- safe cancellation/reconciliation paths can remain available independently from market-display freshness;
- browser/network retries cannot duplicate commands; and
- tests must cover per-source staleness, gateway loss, response loss before/after admission, refresh/reconnect, late fills, snapshot catch-up, recovery failure/progress, narrow viewports, and no offline command queue/auto-resume.

Declined alternatives:

- a blank connection lock screen, because it removes last-known orders/inventory/incidents/evidence when most useful;
- optimistic offline commands, because stale queued intent has ambiguous ordering and authority;
- clearing warnings on socket reconnect, because transport restoration does not prove continuity, reconciliation, or readiness; and
- one generic offline flag, because data, control, evidence, alert, Blob, and runtime dependencies can fail independently.

## Decision 17: contextual learning plus dedicated Learn and Glossary

Selected by the operator on 2026-07-18 with learning declared a primary product requirement: unfamiliar concepts must be explainable where they affect a decision, supported by a searchable canonical glossary and deeper lessons. The workstation does not assume prior knowledge of grid trading, exchange mechanics, accounting, risk, statistics, or runtime operations and does not hide material facts in a separate expert mode.

Every important term, field, metric, state, gate, warning, blocked action, and consequential control supports a layered contextual explanation:

1. one-sentence plain-language definition;
2. why it matters in this system;
3. the current exact value/state and how to interpret it;
4. a concrete grid-trading example or visual scenario;
5. related canonical terms and common confusions;
6. the governing requirement/evidence and “Learn more” lesson; and
7. for blocked/restricted actions, the exact reason and what evidence—not a workaround—can change it.

Example:

```text
Decision readiness: NO

The runtime cannot safely process a new trading decision.
Why here: one BTC reconciliation difference remains and strategy input is 18 seconds old.
Required: zero decision-material differences and input age <= 15 seconds.
Learn: Decision readiness · Reconciliation · Input freshness
```

Context help uses stable reason/term identities returned by canonical services, not frontend guesses. Short definitions never replace exact thresholds, asset quantities, source times, or evidence. Consequential reviews—candidate selection, handoff, activation, pause/stop/resume, reconciliation adjustment, incident closure—include “what this will do / will not do” explanations.

`Research > Learn` provides an end-to-end curriculum for Spot/grid foundations; bootstrap/inventory/paired cycles; fees/spread/slippage/rounding/post-only behavior; backtest and trade visualization; walk-forward/holdout/robustness/statistical credibility; accounting/allocation/reconciliation; Paper versus Testnet versus live; risk/loss limits; commands/unknown outcomes; streams/recovery; incidents/evidence; and safe operator workflows. Lessons reuse real/sandboxed evidence visualizations and scenarios but cannot issue online commands.

The searchable Glossary renders the domain context documents as the single source of truth, supports aliases and “avoid” terms, links definitions bidirectionally, and shows which context owns a term. Adding or correcting a canonical term remains a small reviewable documentation change rather than hard-coded copies across screens. Broken glossary/lesson links and definitions that drift from service reason codes fail documentation/UI verification.

Learning history, bookmarks, and completed examples may be stored as local convenience state but never change gate, permission, risk, readiness, or command authority. There is no mandatory quiz, certification, or separate beginner engine in the personal MVP.

The accessibility baseline is WCAG 2.2 Level AA, the current W3C Recommendation; WCAG 3.0 remains a monitored Working Draft rather than the release target. Requirements include full keyboard operation and visible focus; semantic structure/labels/tables and screen-reader status; contrast and no color-only meaning; reduced motion; accessible validation/error summaries; text/table equivalents for charts; labelled shapes for sides/states; browser zoom/reflow; and accessible time/number/asset/fee presentation.

Full Research and Operations control is supported on desktop/laptop browsers. Narrow/mobile presentation is read-only for runtime status, incidents, and evidence summaries. Email/mobile alerts remain non-actionable deep links. Mobile activation, Resume, Pause/Stop/Emergency Stop, liquidation, or material reconciliation approval is out of the MVP.

Consequences:

- learning is integrated into real decisions and failure states rather than requiring prior study of a manual;
- one canonical vocabulary serves specs, UI, lessons, reason codes, audit, and support;
- accessible alternatives also make dense financial/operational evidence easier for every operator to inspect;
- mobile remains useful for awareness without becoming a second high-risk control product; and
- tests must cover keyboard/focus, semantics, contrast, non-color states, chart alternatives, help/reason links, glossary consistency, responsive read-only enforcement, and absence of authority effects from learning state.

Declined alternatives:

- a Learn page plus ordinary tooltips only, because explanation would be disconnected from current blocked/risky decisions;
- separate beginner/expert modes, because hiding evidence or changing terminology creates two semantic products;
- mandatory lessons/quizzes before operation, because completion state is not safety evidence and can create false confidence;
- mobile trading controls, because they expand high-risk authentication/confirmation/testing surface beyond the personal desktop MVP; and
- WCAG 3.0 as the current conformance target, because it remains a Working Draft rather than a stable Recommendation.

Official accessibility references: <https://www.w3.org/TR/WCAG22/> and <https://www.w3.org/WAI/standards-guidelines/wcag/wcag3-intro/>.

## Decision 18: controlled React, TypeScript, and Vite modernization

Selected by the operator on 2026-07-18: preserve `gridlab-studio` as the canonical product/application foundation and retain its FastAPI research/backend boundary, visual language, engine facade, and accepted workflows while incrementally replacing the growing vanilla-JavaScript UI with a typed React/TypeScript single-page application built by Vite. The MVP does not adopt the legacy SaaS's Next.js/server-rendering, tenancy, Redis, or Celery topology.

Node tooling is required for frontend development, build, type checking, linting, and tests, but not as an additional production service. Vite emits versioned static assets served by the appropriate Studio host/FastAPI deployment boundary. No SSR, public SEO, React Server Components, or Node application server is required for the secured personal workstation.

The frontend architecture follows the selected two-workspace hierarchy:

```text
application shell
  authority context / routing / authenticated session / notifications
  research workspace
    overview / experiments / candidates / data / learn
  operations workspace
    command center / qualification / reconciliation / incidents / evidence
  shared presentation
    accessible charts / tables / forms / help / formatting / status display
```

Research and Operations use separate typed ports/API clients, query caches, route namespaces, error/freshness handling, and feature state. They may share presentation components and canonical identity/value types but cannot import one another's mutating services or blur trust. Cross-workspace navigation passes immutable identities, never mutable state or authority.

FastAPI/OpenAPI and versioned event/view schemas generate or verify TypeScript transport contracts. Explicit adapters map transport DTOs into immutable UI view models. Server/authenticated projections, local view/filter state, local research drafts, and cached sealed evidence are distinct stores with distinct lifetimes. No global mutable object may combine local research state with Paper/Testnet/live authority.

Canonical backends own strategy defaults/derivations, gate/ranking decisions, accounting, risk, reconciliation, command admission/outcome, authorization, reason codes, and evidence. The UI renders them, validates transport/form shape for usability, and requests actions; it never reimplements authority or uses its calculation to permit a command. Command UI is non-optimistic and obtains durable state by idempotency identity.

Browser code cannot access Binance, Azure/Blob credentials, secrets, SQLite/WAL, active capture files, or runtime databases. Environment endpoints and feature flags are allowlisted/build-configured and secret-free. The production build has an immutable identity linked to deployment/evidence and excludes source maps or diagnostics according to the security/release decision.

The minimum verification layers are:

- unit/component tests for accessible rendering, conditional fields, state tables, charts, filters, reason/help links, and command consequence components;
- generated-schema/contract fixtures and compatibility tests for current, additive, rejected, and unknown enum/schema versions;
- integration tests using deterministic research/gateway adapters and canonical fixtures, not ad-hoc component mocks for decision-critical flows;
- Playwright-style browser end-to-end journeys for research, candidate handoff, Paper/Testnet, activation, Command Center, controls, reconciliation, incidents, evidence, disconnection, and recovery;
- WCAG 2.2 AA automated checks plus manual keyboard, focus, screen-reader, zoom/reflow, non-color, chart-alternative, and reduced-motion review;
- visual regression across Research/Paper/Testnet/LIVE, light/dark/high-contrast where supported, normal/frozen/stale/unknown/critical states, and target viewports;
- failure fixtures for latency, disconnection, late fills, duplicates, unknown commands, stale state/config, auth expiry, schema mismatch, and evidence/cache corruption;
- architecture-conformance rules prohibiting cross-workspace service imports, backend/domain-policy duplication, direct infrastructure access, untyped decision-critical payloads, and production prototype code; and
- production-build dependency, secret/canary, CSP/security-header, asset-integrity, size/performance, provenance, and reproducibility checks fixed by later security/release work.

Migration is incremental rather than a big-bang rewrite: introduce the typed shell/design tokens/contracts; port and prove one end-to-end Research vertical slice; prove result/trade-chart parity; port remaining Research; build Operations against typed deterministic gateway fixtures before Azure; run old/new read-only comparison where useful; and delete the old frontend only after workflow, evidence, accessibility, and visual parity are accepted. New online mutations are implemented only in the typed path.

Consequences:

- a build step is accepted in exchange for compile-time contracts, component/state boundaries, scalable testing, and safer evolution;
- FastAPI and Python domain/runtime services remain authoritative and deployable without a Node server;
- the current Studio and SaaS UI are design/workflow sources, not code to concatenate into another large script;
- later strategies/venues extend typed adapters and feature contracts without a generic plugin framework; and
- migration must budget deliberate parity and deletion work rather than leaving two permanent frontends.

Declined alternatives:

- continue with vanilla JavaScript modules as the long-term workstation architecture, because the accepted live, reconciliation, incident, evidence, accessibility, and state requirements exceed the current large-script structure's safe maintainability;
- adopt the complete Next.js/SaaS frontend architecture, because SSR/public-web/multi-user server concerns duplicate FastAPI and add an unnecessary production boundary;
- rewrite every screen before proving one vertical slice, because semantic/visual regressions would be difficult to isolate; and
- put canonical policy in TypeScript for responsiveness, because duplicated gate/risk/accounting/command logic would break parity and authority.

Current official implementation references: <https://react.dev/learn/build-a-react-app-from-scratch>, <https://vite.dev/guide/>, and <https://vite.dev/guide/build>.

## Decision 19: Command Canvas foundation with focused evidence and learning patterns

Selected by the operator on 2026-07-18: use Option 1, Command Canvas, as the default Command Center foundation. Preserve its permanent navigation, persistent authority/safety header, large trade/grid visualization, adjacent rung ladder, and evidence immediately below. Incorporate Option 2's selected-evidence inspector for drill-through and Option 3's plain-language current-focus explanation, but do not introduce Option 3's aggregate confidence percentage because canonical readiness and health facts must remain explicit.

A self-contained throwaway prototype now exists at `gridlab-studio/frontend/prototype-operator-command-center.html`. When Studio is running, use `/prototype-operator-command-center.html?variant=A`, `B`, or `C`; the bottom switcher and left/right arrow keys change variants. The page contains mock state only, makes no network requests, has no API client, and labels itself as a throwaway prototype. Safety-control clicks only display an eight-second local notice that no command was sent. This file is an information-hierarchy experiment and must not be migrated into production code.

All three variants deliberately show the same accepted operational facts: authority context, freshness, runtime/readiness/reconciliation state, 250 USDT capital bound, daily loss and fee reserve, Pause/Operator Stop/Emergency Stop, an evidence-linked trade/grid overlay, partial and paired fills, exact identities/assets/fees, rung state, causal history, and contextual learning. The decision is therefore about hierarchy rather than missing features.

### Option 1 — Command Canvas (recommended)

Permanent product navigation on the left, authority and safety across the top, a large trade/grid chart with the rung ladder beside it, and exact orders/accounting/reconciliation/causal evidence immediately below. It gives the strongest balanced daily-operation overview and the clearest route back to Qualification, Reconciliation, Incidents, Evidence, and Learn. Its likely implementation direction is the main shell for normal operation, with deeper inspectors opened from selected evidence.

### Option 2 — Evidence Workbench

Causal timeline on the left, the largest central execution chart, and an exact selected-evidence inspector on the right. It is best for debugging a fill, order, or accounting transition and keeps causes beside the visual event. Its weakness as the default is reduced persistent product navigation and less calm top-level scanning. The valuable inspector/timeline pattern can still be used for chart drill-through and reconciliation details if another option is selected.

### Option 3 — Focus Stack

Capital, inventory, operating health, and safety controls form a permanent left rail; the main canvas prioritizes the current focus and only then expands into accounting, recent evidence, and readiness explanations. It is calm and approachable, particularly for learning what presently requires attention. Its weakness is that the invented aggregate confidence percentage can imply more certainty than the canonical facts support; production should replace that dial with explicit readiness/health facts if this hierarchy is selected.

Accepted composition: Option 1 is the default Command Center foundation, Option 2's selected-evidence inspector is reused for drill-through, and Option 3's plain-language current-focus explanation is reused without its aggregate confidence score. This gives one balanced daily surface while preserving stronger investigation and learning patterns where they belong.

Prototype verification on 2026-07-18 covered all three URLs at a 1280 by 720 desktop viewport, absence of horizontal overflow, visible authority/safety/trade/rung evidence, the variant identity, and a real click on the mock Emergency Stop control. The click retained the prototype URL and produced only the local “not sent; no API client” notice.
