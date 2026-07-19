# Canonical capability audit

Date: 2026-07-13  
Scope: `gridlab`, `gridlab-studio`, `grid-backtest-core`, `grid-backtest-saas`, and `backtester_old`  
Method: primary local source, tests, package/configuration files, and project documentation. This is an inventory and migration decision aid, not a certification of trading correctness.

## Executive conclusion

`gridlab` is the best canonical engine. It is the only generation explicitly organized around one fill stream, one ledger, an I/O-free event loop, conservative fill eligibility, venue constraints, realistic fees/slippage, and research validation. `gridlab-studio` is the best canonical application shell because it already consumes the engine's JSON facade and is comparatively small. Neither is an online trading system.

`grid-backtest-core` and `grid-backtest-saas` must remain readable reference sources during consolidation. The core contains useful policy, constraint, result, repository, and accelerated-search ideas, but represents the older semantics that `gridlab` says it rewrote to correct. The SaaS contains the most mature workflow/UI and operational web architecture: persisted jobs, research pipelines/tournaments, progress, authentication, database migrations, Celery, and Docker composition. These are migration sources, not canonical domain implementations.

`backtester_old` is the only source with substantial Binance Spot online machinery: REST adapter, kline/user streams, account state, deterministic client order IDs, startup reconciliation, order management, safety checks, live repositories, and kill-switch behavior. It is valuable as a requirements mine. Its broad exception suppression, weak test coverage around online behavior, mixed concerns, and divergent strategy/accounting semantics make direct reuse unsafe.

The recommended boundary is therefore: retain `gridlab` semantics; extend `gridlab-studio`; migrate concepts and UI workflows through explicit specifications and new tests; do not copy old engines or live code wholesale.

## Evidence and test health

### Test inventory

Static discovery (`def test_`) found 82 tests in `gridlab`, 12 in `gridlab-studio`, 2 directly declared test functions in `grid-backtest-core`, 15 in `grid-backtest-saas`, and 17 in `backtester_old`. Static function counting materially understates parametrized/unittest-style collection and must not be interpreted as the executed test count.

On this Windows managed environment, the suites were also run independently. `gridlab` completed 81/82 tests successfully; the sole failure was `test_parallel_grid_search_matches_serial` because the sandbox denied creation of a Windows multiprocessing named pipe (`PermissionError: WinError 5`), not because serial/parallel results disagreed. Parallel search therefore remains unverified here, rather than disproven. `gridlab-studio` passed 12 tests with one Starlette deprecation warning. `grid-backtest-core` passed 103 tests with 92 warnings, primarily deprecated naive UTC timestamps. `grid-backtest-saas` did not complete within more than two minutes and was terminated, so its health is unknown. `backtester_old` failed collection because two tests import the removed `infra.config_models` module; it also emitted Pydantic v2 deprecation warnings. Each suite still needs a clean, reproducible CI environment before migration evidence becomes an acceptance claim.

The suite distribution itself is material: `gridlab/tests/test_ledger.py`, `test_properties.py`, `test_execution.py`, `test_engine.py`, `test_metrics.py`, `test_research.py`, and `test_spot_edition.py` target correctness layers and properties. Online code under `backtester_old/app/trading`, `core/live`, and `infra/marketdata` has no comparably focused integration/failure-injection suite.

## Capability inventory

### `gridlab` — canonical engine

Capabilities:

- A JSON-serializable `run_backtest` facade intended for HTTP/UI boundaries (`gridlab/README.md:50-75`).
- Spot and futures vocabulary, although the selected MVP should expose only long-only spot (`gridlab/README.md:27`, `gridlab/src/gridlab/accounting/ledger.py:11-12`).
- Arithmetic/geometric grids, policy modules for range, spacing, sizing, filters, recentering, and SL/TP (`gridlab/src/gridlab/strategy/policies/`).
- Synthetic, CSV, and paginated/cached Binance kline inputs (`gridlab/README.md:119-136`).
- Venue rule quantization and rejection for tick, lot, minimum quantity, and minimum notional (`gridlab/README.md:88-117`; `gridlab/src/gridlab/execution/exchange_rules.py`).
- Maker/taker fees, slippage, constraints, fill models, margin/liquidation support (`gridlab/src/gridlab/execution/`).
- Metrics, benchmarks, standalone HTML reporting, grid-specific economics (`gridlab/README.md:138-146`, `195-216`).
- Grid search, walk-forward analysis, Monte Carlo, robustness scoring, and multiprocessing search (`gridlab/README.md:148-190`; `gridlab/src/gridlab/research/`).

Correctness guarantees present in design and tests:

- One `Ledger` derives cash, positions, equity, and FIFO closed trades from every fill, including bootstrap and forced flattening (`gridlab/src/gridlab/accounting/ledger.py:1-12`, `53-69`, `129-196`).
- Spot equity is cash plus marked base inventory; buy and sell cash movement includes fill fees (`gridlab/src/gridlab/accounting/ledger.py:120-125`, `186-195`).
- One I/O-free engine, one order book, configurable optimistic versus conservative eligibility, stop trigger pricing, and intrabar liquidation checks (`gridlab/src/gridlab/engine/engine.py:1-17`).
- Undefined statistics and overfitting-sensitive metrics are intentionally represented rather than cosmetically inflated (`gridlab/README.md:28-31`).

Risks/gaps:

- It is candle-event simulation, not an online event processor or tick/order-book replay engine.
- README assertions are stronger than a formal invariant specification; exact conservation equations, rounding tolerances, event ordering, partial fills, duplicate events, and replay determinism need explicit contracts.
- Binance presets cannot substitute for time-versioned exchange metadata. Filters and fees can change.
- Futures functionality expands the state space and should be disabled at the product boundary for the long-only MVP.
- The robustness score is a heuristic aggregate, not a sufficient promotion gate (`gridlab/README.md:175-190`).
- Parallel grid-search health was not established in the managed Windows environment.
- Direct floating-point cash/quantity arithmetic (`ledger.py:61-69`, `129-195`) needs a precision policy before live reconciliation.

Documentation: strongest engine README and examples of the five projects, plus layered package structure. Still missing are authoritative event schemas, accounting equations, failure semantics, data-quality contracts, and versioned strategy specifications.

### `gridlab-studio` — canonical operator application shell

Capabilities:

- FastAPI backend, typed schemas/presets/service layer, static HTML/CSS/JavaScript client, run history, schema-driven configuration, charts, and API tests (`gridlab-studio/backend/`, `frontend/js/`, `tests/test_api.py`).
- It is deliberately aligned to the `gridlab` facade rather than duplicating engine internals.
- Existing UI covers backtest configuration/results and gives a low-complexity base for a personal workstation.

Guarantees and health:

- API-level tests exist for request validation and workflows and all 12 passed in this environment. The UI has no automated browser/E2E suite in the repository.
- Backend exception mapping exists (`gridlab-studio/backend/app.py:49`), and an overlay path is explicitly best-effort (`backend/service.py:244`); error classifications and persistence guarantees are not yet operational contracts.

Risks/gaps:

- No authentication, live command approval, secrets handling, durable event journal, metrics/alerts, exchange reconciliation, restart recovery, or deployment control plane.
- Browser-held history/configuration is not an audit record.
- Static client architecture is manageable for the current scope but needs component/state discipline as live workflows grow.
- No explicit separation yet between research actions and capital-affecting commands.

### `grid-backtest-core` — legacy domain/reference source

Capabilities:

- Backtest engine and a separate fast/Numba engine, simple/dynamic grid strategies, policy modules, execution constraints/bootstrap/reservations, indicators, result metrics/benchmarks/repositories/trade building, and serial/fast research grid search (`grid-backtest-core/src/grid_backtest/`).
- Its protocols and repositories contain useful interface vocabulary.

Risks/gaps:

- `gridlab` explicitly identifies this generation's class of defects: dual FIFO representations, missing bootstrap trades, implicit same-bar fills, flat fees, absent spread/slippage, stop-at-close behavior, understated drawdown, and fragile metrics (`gridlab/README.md:13-32`). Every reused concept must be checked against those corrections.
- Separate regular and fast engines create semantic-drift risk; `gridlab` intentionally replaced this with one engine (`gridlab/src/gridlab/engine/engine.py:3-6`).
- Exception swallowing in the old engine/repository (`grid-backtest-core/src/grid_backtest/engine.py:219-236`, `results/repository.py:46`) can hide corrupted outputs.
- The current suite passed 103 collected tests in this environment, but emitted 92 deprecation warnings. Coverage breadth and semantic equivalence to `gridlab` were not established.

Disposition: preserve as read-only reference until every useful policy, metric, repository behavior, and acceleration technique is either migrated with parity tests or explicitly rejected.

### `grid-backtest-saas` — UI/workflow and service architecture source

Capabilities:

- FastAPI API with auth/security, database sessions/models, Alembic migrations, backtest and research schemas/services, Celery workers, and Docker Compose (`grid-backtest-saas/backend/app/`, `backend/alembic/`, `docker-compose.yml`).
- Persisted research jobs, progress, trials, multi-phase research pipeline, and tournament concepts (`backend/app/services/research_*`, migrations `0002`-`0005`).
- A more mature single-page UI for research/backtest workflows (`frontend/static/index.html`, `frontend/static/app.js`) and a dedicated architecture document.

Risks/gaps:

- It is coupled to the legacy `grid-backtest-core` semantics and must not become the source of trading truth.
- SaaS tenancy/auth concerns exceed a single-operator MVP; copying them wholesale increases cost and attack surface.
- Celery/database topology is heavier than the minimal single-instance Azure target.
- Broad exception translation in workers/services/APIs can obscure domain error classes (`backend/app/workers/backtest_task.py:20`, `services/research_pipeline_service.py:600,672`, `api/v1/research.py:405`).
- No live execution/control workflows or durable trading audit journal.

Disposition: migrate UX information architecture, job lifecycle, progress presentation, comparison/tournament workflows, and selected persistence schemas. Redesign them around `gridlab` and single-operator security; reject premature tenancy and distributed-worker complexity.

### `backtester_old` — online requirements/reference source

Capabilities:

- Binance Spot REST adapter and exchange base (`backtester_old/infra/exchange/binance_spot.py`, `base.py`).
- Binance kline and user-data streams with reconnect/keepalive mechanisms (`infra/marketdata/binance_kline_stream.py`, `binance_user_stream.py`).
- Paper/live entry points and a runtime that pumps execution reports into fill events (`app/research/trade_paper.py`, `trade_live.py`; `app/trading/runtime.py:183-220`).
- Order manager with deterministic/parseable client IDs, locally tracked state, startup reconciliation, managed-order cancellation, and execution-report updates (`core/live/order_manager.py:23-72`, `102-176`, `178-207`).
- Safety checks for order notional, open-order count, and spot inventory, plus durable submitted-intent/event writes after REST success (`app/trading/execution.py:40-86`, `126-208`).
- Account state, PnL ledger, equity tracker, live result repository/reporting, YAML configs, secret loader, logging setup, Dockerfile, and deployment/runtime UML.

Important weaknesses:

- Durable intent is written *after* REST success (`app/trading/execution.py:53-55`, `189-208`), leaving an ambiguity window if the process dies after exchange acceptance but before persistence. A production design needs a command/outbox/idempotency protocol and reconciliation rule.
- The runtime intentionally suppresses persistence exceptions (`app/trading/runtime.py:178-180`), which violates the proposed auditability gate: losing evidence must trigger degraded/blocked trading, not silent continuation.
- Many broad `except Exception` paths exist across runtime, streams, exchange, repositories, and order manager; recovery policy is implicit and failures may be hidden.
- Client ID hashing uses SHA-1 only as a compact identifier, not security; collision/idempotency lifecycle and Binance length rules require an explicit schema (`core/live/order_manager.py:19-45`, `159-166`).
- Local order tracking and startup reconciliation are useful, but no evidence establishes exact handling of REST timeout-after-accept, duplicated/out-of-order events, listen-key gaps, partial-fill/cancel races, clock skew, filter changes, or foreign/manual orders.
- Safety limits are local checks and can race stale balances/open orders (`app/trading/execution.py:153-185`). Portfolio-level, daily-loss, stale-data, connectivity, and emergency-stop state machines are incomplete.
- Live code is not backed by an exchange simulator/failure-injection test suite. The 17 discovered old-project tests focus primarily on backtest/data/result models.
- Strategy, execution, persistence, and orchestration are tightly connected to old domain types, so direct imports would contaminate canonical semantics.

Disposition: extract scenarios, state transitions, adapter requirements, and test cases; redesign implementation behind canonical ports. Do not reuse runtime code unchanged.

## Retain / migrate / redesign / reject matrix

| Capability | Source | Decision | Destination condition |
|---|---|---|---|
| Single fill-derived FIFO ledger | `gridlab` | Retain | Formalize conservation/precision/replay invariants and property tests |
| I/O-free engine and action vocabulary | `gridlab` | Retain/deepen | One deterministic decision core across backtest, replay, paper, live |
| Conservative candle fill model | `gridlab` | Retain | Clearly label fidelity; add trade/order-book replay tier |
| Fees, slippage, stops, venue constraints | `gridlab` | Retain/deepen | Time-versioned venue rules; rejection and partial-fill models |
| Futures/margin/shorting | `gridlab` | Reject from MVP surface | Keep isolated internally only if it cannot affect spot invariants |
| Walk-forward, Monte Carlo, deflated Sharpe, robustness | `gridlab` | Retain/deepen | Replace single trust score as gate with explicit evidence bundle |
| Static studio API/client | `gridlab-studio` | Retain | Add durable backend state, auth, command boundaries, E2E tests |
| SaaS research workflow and visual design | `grid-backtest-saas` | Migrate | Reimplement against canonical schemas; conduct screen-by-screen audit |
| Persisted jobs/progress/trials/tournaments | `grid-backtest-saas` | Migrate selectively | Single-node database/worker initially; deterministic job provenance |
| Multi-user tenancy/billing | `grid-backtest-saas` | Reject | Out of scope for personal system |
| Celery/Redis distributed topology | `grid-backtest-saas` | Defer/reject initially | Only adopt if measured workload exceeds simple worker model |
| Old/fast dual engines | `grid-backtest-core` | Reject | One semantic engine; optimize behind parity-tested boundaries |
| Old policies/metrics/repositories | `grid-backtest-core` | Audit and migrate selectively | Re-derive tests under canonical accounting, never copy assumptions |
| Binance REST/stream adapter scenarios | `backtester_old` | Redesign | Ports/adapters, typed errors, sequence IDs, health/degraded modes |
| Deterministic client order identity | `backtester_old` | Migrate concept | Versioned collision-safe identity and idempotency lifecycle |
| Startup reconciliation/order ownership | `backtester_old` | Redesign | Explicit authoritative-source and foreign-order policy |
| Safety checks and kill switch | `backtester_old` | Redesign/deepen | Atomic risk state machine, stale-state guards, tested stop semantics |
| Live repository/event traces | `backtester_old` | Migrate concept | Append-only journal + structured logs + metrics; persistence failure blocks risk |
| Broad exception swallowing | legacy projects | Reject | Typed failures, explicit retry/degrade/halt policy, observable incidents |

## Required specifications exposed by the audit

1. Canonical long-only static-grid semantics: level lifecycle, bootstrap inventory, sizing, reservations, sell-only-owned inventory, grid completion, bounds and shutdown.
2. Accounting invariant catalogue: quote/base conservation, fee asset handling, precision/rounding, FIFO realization, locked/free balances, equity, deposits/withdrawals, and reconciliation tolerances.
3. Canonical event and command schemas shared across modes, including ordering, timestamps, deduplication, replay versioning, and deterministic decisions.
4. Binance adapter contract: REST ambiguity, websocket gaps, sequence recovery, partial fills, cancellations, rejected/expired orders, filter refresh, clock skew/rate limits, and foreign/manual orders.
5. Runtime state machine: start approval, bootstrap, healthy, degraded, reconcile, paused, emergency stop, shutdown, restart, and terminal incident states.
6. Promotion evidence: data quality, walk-forward/OOS, regime robustness, sensitivity/stability, realistic costs/rejections, high-fidelity replay, paper duration, operational fault drills, and manual capital activation.
7. Observability contract: append-only event journal, correlation/causation IDs, structured redacted logs, metrics/alerts, retention, export, and behavior replay.
8. Operator workflow specification informed by the SaaS UI: research provenance, comparisons, promotion bundle, paper/live status, approvals, reconciliation, incidents, pause/stop, and audit history.
9. Minimal Azure deployment and security threat model: durable database/storage, backups/restore drills, secrets and key permissions, private administration, patching, monitoring, and cost envelope.

## Final recommendation

Freeze the three legacy projects as reference inputs, not dependencies. Before archiving any of them, create a traceable inventory mapping each capability and workflow to one of: migrated with tests, superseded by canonical behavior, intentionally deferred, or rejected with reason. Build the online system as ports around `gridlab`'s deterministic core and evolve `gridlab-studio` using the SaaS UI as a UX reference. The first implementation tranche should establish canonical schemas, invariants, event journal, replay parity, and failure semantics before connecting capital-affecting Binance commands.
