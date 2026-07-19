# grid-backtest-core — Deep Technical Findings

**Target:** `C:\Users\W4TV5V8\PROJECTS\backtester\grid-backtest-core`
**Package:** `grid_backtest` v0.1.0 · Python ≥3.11 · deps: numpy, pandas, numba
**Author tag:** Usam95 · License: MIT
**Scope:** code analysis, grid-trading research comparison, code judgment, monetization.

> Companion files: `backtest-core-grid-trading-analysis.html` (executive report),
> `grid-trading-research-sources.md` (citations), `roadmap.md`, `capability-matrix.json`.

---

## 1. What the code currently does

`grid_backtest` is a **pure-computation grid-trading backtest library** (no file/network I/O in the
engine; data is passed in as a pandas OHLCV `DataFrame`). It ships **two execution engines**, **two
grid strategies**, a **policy toolkit** for adaptive grids, a **metrics/reporting layer**, and a
**parameter-sweep research layer**.

Reference entry points (`src/grid_backtest/__init__.py`):

- `BacktestEngine` (`engine.py`) — event-driven, per-candle Python loop. The accurate/reference engine.
- `FastBacktestEngine` (`engine_fast.py`) + `_numba_engine.py` — Numba-JIT kernel, ~200–400× faster,
  but only supports `SimpleGridStrategy` / `DynamicGridStrategy` and a **reduced feature set**.
- `SimpleGridStrategy` (`strategy/grid_simple.py`) — static spot grid (Binance-style).
- `DynamicGridStrategy` (`strategy/grid_dynamic.py`) — ATR/percent-adaptive range & spacing, SL/TP,
  RSI/EMA/ADX filters, floating-grid recentering — composed from policy objects.
- `GridResearchRunner` (`research/grid_search.py`) — multi-process parameter sweep over a param grid
  and multiple timeframes; `grid_search_fast.py` — Numba single-core sweep.
- Results: `results/metrics.py`, `results/trade_builder.py`, `results/repository.py`,
  `results/benchmarks.py`, `results/models.py`.

A minimal run (from `README.md`): build a `BacktestConfig`, instantiate a strategy + `BacktestEngine`,
call `.run()`, read `result.metrics`.

### Execution model (data flow)

```
DataFrame(OHLCV)
  -> _prepare_data(): validate cols, optional indicator enrichment (ATR/EMA/RSI/ADX), warmup drop
  -> _to_candles(): vectorised conversion to Candle objects (object.__new__ fast path)
  -> _apply_bootstrap(candle0): long_only | neutral_split | neutral_topup
  for each candle:
     _expire_open_orders()
     actions = strategy.on_candle(candle, account)   # PLACE_ORDER / CANCEL_OPEN_ORDERS / GRID_EXIT
     apply actions (constraints + reservations on PLACE_ORDER)
     filled = _simulate_fills_for_candle(candle)      # SAME-bar fill
     for fill: release reservation, charge fee, _apply_fill (FIFO), trade_builder.on_fill
     strategy.on_orders_filled(filled)                # places neighbour rungs
     _update_equity(candle)                           # mark-to-market on close
  -> BacktestResult(metrics, trades, equity_curve, extra{benchmark, positions, bootstrap, ...})
```

Strategy ↔ engine communicate through a **command object** `EngineAction`
(`engine_actions.py`) with strict `__post_init__` validation — a clean, testable boundary.

---

## 2. Architecture & abstractions

| Layer | Module(s) | Abstraction quality |
|---|---|---|
| Domain models | `models.py` | Plain dataclasses (`Candle` is `slots=True`); frozen events. Clean. |
| Config | `config.py` | Frozen dataclasses, layered sub-configs, no Pydantic. Clean. |
| Engine | `engine.py`, `engine_fast.py`, `_numba_engine.py` | Two engines behind similar shapes; **no shared core** → divergence risk. |
| Strategy | `strategy/base.py` (`IStrategy`), `grid_simple.py`, `grid_dynamic.py` | Interface + composition. `DynamicGrid` wraps `SimpleGrid` + policies. Strong. |
| Policies | `strategy/policies/{range,space,sltp,filter,recenter}.py` | Each adaptive behaviour isolated, structurally-typed cfg. Strong. |
| Execution | `execution/{bootstrap,constraints,reservations}.py` | Spot-style fund locking + feasibility. Good separation. |
| Results | `results/{metrics,trade_builder,benchmarks,repository,models}.py` | Pluggable `MetricRegistry`; I/O isolated in repository. Good. |
| Research | `research/{grid_search,grid_search_fast}.py` | Process-pool sweep with Windows fallback paths. Pragmatic. |
| Data | `data/protocols.py` | `DataSource` `Protocol` — clean inversion of I/O. |

**Notable strengths**
- True separation of concerns; the engine has zero I/O and zero exchange knowledge (design principles
  in `README.md` are actually honoured).
- Policy composition makes the dynamic grid genuinely extensible and unit-testable.
- `MetricRegistry` (`metrics.py:12-35`) is a clean open/closed extension point.
- Performance engineering is real: Numba kernel, `object.__new__` candle path (`engine.py:333-347`),
  insertion-ordered-dict FIFO, multi-process sweeps with pickled shared buffers.

---

## 3. Order simulation & correctness risks (the important part)

### 3.1 Fill rules (`engine._simulate_fills_for_candle`, engine.py:502-570)
- LIMIT BUY fills if `candle.low <= price`; LIMIT SELL fills if `candle.high >= price`; fill price is
  **exactly** the order price (no slippage). MARKET fills at `close ± slippage_pct`.

### 3.2 Same-bar fill / intrabar lookahead — **CRITICAL, documented**
Orders placed in `on_candle()` for bar *N* are matched against **bar *N*'s** OHLC range in the same
iteration (engine.py:516-520). For a static grid whose rungs straddle the current price this is
defensible, but it is an **optimistic assumption**: a level already inside the current bar fills
instantly at the level price. There is **no intrabar sequencing** — if a buy rung (at the low) and a
sell rung (at the high) are both inside one bar, **both fill in the same bar** regardless of the true
tick order. This is the classic OHLC ambiguity and it biases results favourably. No "fill from bar
N+1" / conservative mode exists. (Industry treatment: see research sources on intrabar fill optimism.)

### 3.3 No partial fills / no liquidity
Each order is all-or-nothing; `candle.volume` is never consulted for fill sizing. Grid strategies that
would in reality only partially fill at a rung are over-filled here.

### 3.4 Fees / slippage / spread
- A single `trading_fee_pct` is charged on **both** sides (engine.py:179, 456) — **no maker/taker
  split**, no fee tiers, no rebates. Grids are maker-heavy in reality, so this typically **overstates
  cost** for limit-maker grids and understates it for market exits.
- Slippage applies to MARKET only; **LIMIT and forced-exit fills get zero slippage**; **spread is not
  modelled at all**.

### 3.5 Forced-exit price is the bar close, not the trigger — **bug-class**
`SLTPPolicy.check` (sltp.py:66-83) triggers on `candle.low <= SL` / `candle.high >= TP` (intrabar), but
`_force_flatten_and_cancel` (engine.py:439-460) liquidates at **`candle.close`**, not at the SL/TP
price. On a bar that spikes through the stop and recovers, PnL is computed at the close — materially
wrong for stop accounting, and it hides gap risk entirely.

### 3.6 Two independent FIFO implementations can diverge — **verified**
The engine matches SELLs against `_open_positions` for **cash** accounting (engine.py:599-668); the
`TradeBuilder` (`trade_builder.py`) keeps a *separate* FIFO of `_OpenLot`s for the **trades list**.
Crucially, **bootstrap inventory** (`initial_base_qty`, `neutral_split`, `neutral_topup`) is injected
straight into engine positions (`execution/bootstrap.py`) but **never fed to `TradeBuilder`**. When
that base is later sold, `TradeBuilder` has no opening lot and the engine's cash reflects a sale the
trades list cannot.

**Empirical confirmation** (throwaway script against the real engine, oscillating price, neutral_split
bootstrap 50%): `sum(trade.net_pnl) = 4.6010` but `final_equity − initial = 4.5000` — the trade ledger
does **not** reconcile to equity. Any report that sums trade PnL will disagree with the equity curve
whenever bootstrap inventory is used.

### 3.7 Default static grid is **not two-sided at seeding** — **verified, non-obvious**
`SimpleGridStrategy._seed_initial_orders` (grid_simple.py:213-231) seeds BUY rungs below price and
SELL rungs above. But with the **default** `BootstrapMode.LONG_ONLY` there is no base inventory, so the
engine's `OrderConstraintPolicy` (constraints.py:57-63) rejects every initial SELL with
`insufficient_base_skip`. Verified: a 5-level grid around 100 accepted only `['BUY','BUY']` — **both
SELL seeds were silently dropped**. The grid only becomes two-sided after a BUY fills and a sell
neighbour is armed. Users expecting a symmetric "neutral" grid out of the box will be surprised; this
interaction is undocumented.

### 3.8 Vestigial / unused state
`AccountState.base_free/base_locked/quote_free/quote_locked` (models.py:109-112) are not used by the
engine (which tracks `_base_inventory_cache` + `ReservationBook` separately) — dead surface that
invites confusion.

---

## 4. Portfolio / accounting / risk

- **PnL**: FIFO realized PnL net of proportional buy+sell fees (engine.py:630-635). Reasonable and
  mirrored in `TradeBuilder` — but see §3.6 divergence.
- **Equity**: `cash + base_inventory * close` per bar (engine.py:683-687). Mark-to-market on **close
  only** ⇒ intrabar excursions invisible ⇒ **max-drawdown is understated** (metrics.py:52-78 walks
  close-equity points).
- **Risk controls present**: global SL/TP, order expiry, insufficient-funds skip/resize, min order qty,
  spot reservations. **Absent**: max inventory / max notional exposure, leverage/margin, liquidation,
  per-rung budget, short legs (`PositionSide.SHORT` exists but is never opened — engine.py:576-590).
- **Futures grids are not representable** (no margin, funding, or liquidation), despite the dynamic
  config language implying advanced use.

---

## 5. Reporting & metrics

- Metrics (metrics.py): `net_pnl`, `total_return_pct`, `max_drawdown(_pct)`, `n_trades`,
  `win_rate_pct`, `avg_trade_pnl`, `profit_factor`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`.
- `repository.py` writes `summary.json`, `trades.csv`, `equity_curve.csv`, `extra.json`;
  `print_result_summary` renders a console summary with Buy&Hold alpha.
- **Issues**
  - **Annualisation**: Sharpe/Sortino annualise from the *median candle interval*
    (`_periods_per_year`, metrics.py:132-150). On 1-minute data that is ~525,600 periods/yr, and grid
    per-bar returns are ~0 on most bars, so the reported Sharpe is statistically fragile and hard to
    compare across timeframes.
  - **`avg_trade_pnl`** (metrics.py:93-97) is `equity_delta / n_trades`, mixing realized + unrealized +
    bootstrap — **not** the mean of `trade.net_pnl`. Inconsistent with the trades table.
  - **`profit_factor`** returns `inf` when there are no losing trades (metrics.py:108-109) — common for
    a grid that never closes a loser, which pollutes ranking/sorting in sweeps.
  - **Drawdown** ignores intrabar lows (§4).

---

## 6. Configuration & extensibility

- Config is clean, frozen, layered (`BacktestConfig` → `Constraint/Reservation/OrderExpiry/Warmup/
  Bootstrap/IndicatorSpec`). Good.
- Extension points: `IStrategy`, policy classes, `MetricRegistry`, `DataSource` protocol.
- **Extensibility ceiling**: `FastBacktestEngine` hard-codes `isinstance` checks for the two built-in
  strategies (engine_fast.py:107-115); **custom strategies cannot use the fast path**, and the fast
  dynamic kernel honours only `band_pct` + `interval` (engine_fast.py:190-227), **ignoring** ATR range,
  spacing mode, SL/TP, and filters. So "screen fast, validate full" can promote the wrong candidates.

---

## 7. Tests, performance, maintainability

- **Tests**: 103 test functions across 7 files (`test_engine`, `test_execution`, `test_indicators`,
  `test_metrics`, `test_research`, `test_strategies`, `test_trade_builder`). Solid unit coverage of the
  Python engine, execution policies, metrics, and trade builder.
- **Test gaps** (evidence: grep): **no test references `FastBacktestEngine` / `simulate_grid_full`** ⇒
  the fast/Numba path and fast/full **parity are untested**; `hypothesis` is a declared dev dependency
  but **never imported** ⇒ no property-based invariants (e.g., cash conservation, FIFO equivalence).
  No tests for the §3.6 trade-vs-equity reconciliation or §3.7 seeding asymmetry.
- **Performance**: genuinely good for the Python tier; the Numba tier is fast but feature-thin. One
  caveat: the SELL path scans `_position_fifo` each fill (engine.py:613) — typically O(1) but the
  comment overstates the guarantee; degrades with many tiny lots. Equity curve stores one Python object
  per candle (memory on long 1-minute series).
- **Maintainability**: readable, well-commented, consistent naming. Main debts: duplicated FIFO logic
  (engine vs trade_builder), two engines without a shared kernel, and undocumented config interactions.

---

## 8. Suitability for serious grid-trading backtesting

**Verdict: good prototyping/research tool for single-symbol spot *long* grids; NOT yet suitable for
"serious" grid research, especially anything leveraged/futures or anything sold as decision-grade.**

Adequate today: static & adaptive (ATR/percent) grids, recentering, SL/TP/filters, fee-aware FIFO
accounting, multi-timeframe parameter sweeps, Buy&Hold benchmark, core metrics.

Blocking for "serious":
1. Intrabar/same-bar fill optimism with no conservative mode (§3.2) — inflates results.
2. No futures/short/leverage/liquidation (§4) — half the grid universe is unrepresentable.
3. No walk-forward / Monte Carlo / deflated-Sharpe (overfitting controls) — the single biggest risk in
   grid research per the literature.
4. Forced-exit-at-close stop accounting (§3.5) and close-only drawdown (§4) — understate tail risk.
5. Fast/full engine divergence with no parity tests (§6, §7) — silently wrong sweep rankings.
6. Trade-ledger vs equity reconciliation gap with bootstrap (§3.6).

---

## 9. Frank senior-engineer judgment

**Where the design is clean:** the I/O-free engine boundary, the `EngineAction` command pattern, policy
composition for the dynamic grid, the metric registry, and the `DataSource` protocol. This is a
better-than-average hobby/SaaS core — clearly written by someone who knows how to structure Python.

**Where it will bite future grid work:**
- The fill model is the foundation and it is the weakest part. Every downstream metric inherits the
  same-bar/no-partial/no-spread optimism. Fixing this *after* a SaaS is selling reports is expensive
  and reputationally risky.
- Two engines and two FIFO ledgers mean every new feature must be implemented (and tested) twice or it
  silently diverges. There is currently **no parity test** keeping them honest.
- Stop/exit accounting at the bar close is a correctness bug, not a modelling choice — it should fill at
  the trigger.
- Several "advanced" config knobs (futures-sounding language, fast dynamic grid) imply capabilities the
  engine does not actually deliver. That is a trust hazard for a paid product.

**Likely-bug / fragile hotspots to fix first:** `_force_flatten_and_cancel` exit price (engine.py:450);
bootstrap base not registered with `TradeBuilder`; `avg_trade_pnl` definition; `profit_factor` inf;
fast dynamic kernel ignoring most config; Sharpe annualisation on sub-hour data.

---

## 10. Quick reference — file map

| File | Role |
|---|---|
| `engine.py` | Reference event loop, fills, FIFO cash accounting, bootstrap orchestration |
| `engine_fast.py` | Numba front-end; isinstance dispatch; trade reconstruction |
| `_numba_engine.py` | JIT kernels `simulate_grid_full` / `simulate_dynamic_grid` |
| `models.py` | `Candle`, `Order`, `Position`, `AccountState`, events |
| `config.py` | `BacktestConfig` + sub-configs |
| `engine_actions.py` | `EngineAction` command + validation |
| `indicators.py` | ATR / EMA / RSI / ADX (pure pandas) |
| `strategy/grid_simple.py` | Static grid ladder + neighbour replacement |
| `strategy/grid_dynamic.py` | Adaptive grid composed of policies |
| `strategy/policies/*` | range / space / sltp / filter / recenter |
| `execution/*` | bootstrap / constraints / reservations |
| `results/*` | metrics / trade_builder / benchmarks / repository / models |
| `research/*` | grid_search (multiproc) / grid_search_fast (numba) |
| `data/protocols.py` | `DataSource` protocol |
