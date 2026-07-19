# gridlab

A correct, fast, and extensible **grid-trading backtesting engine** for spot and
futures markets. `gridlab` is a ground-up rewrite of an earlier grid backtester,
fixing its correctness bugs and filling its capability gaps, with a clean,
JSON-serializable API designed so a web frontend or REST service can sit on top.

> Backtest results are research artifacts, not investment advice. Past
> performance does not guarantee future results.

---

## Why this exists

Grid bots look easy and backtest beautifully — which is exactly why most grid
backtests lie. `gridlab` is built around the failure modes that make grid
backtests over-optimistic:

| Old-engine flaw | gridlab fix |
|---|---|
| Trade ledger and equity curve kept in **two** FIFO ledgers that could disagree | **One `Ledger`** is the single source of truth; equity *and* trades derive from the same fills |
| Bootstrap inventory never registered with the trade builder | Bootstrap inventory flows through `apply_fill` like any other fill |
| Same-bar fills (lookahead bias) baked in | Pluggable **fill model**: `conservative` (next-bar eligibility) vs `optimistic` (documented bias) |
| Flat fee model | **Maker/taker fees** — limit fills pay maker, market/stop pay taker |
| No slippage/spread | **Slippage model** on aggressive fills (market + triggered stops) |
| Stops filled at bar **close** | Stops fill at the **trigger price** (+ slippage) |
| Long-only; no shorting/leverage | **Futures**: shorts, leverage, isolated-margin **liquidation** |
| Close-only drawdown (understated) | **Intrabar** max drawdown + drawdown duration |
| `profit_factor` = +inf with no losers; `avg_trade_pnl` = equityΔ/n | Correct trade stats; `profit_factor` is `None` when undefined |
| Fragile annualisation | Explicit / inferred `periods_per_year`; **deflated Sharpe** for overfitting |
| No walk-forward / Monte Carlo | `grid_search`, `walk_forward` (OOS), `monte_carlo` |
| No report output | Self-contained **HTML report** (no build step) |

---

## Install

```bash
cd gridlab
pip install -e .          # core (numpy, pandas)
pip install -e ".[dev]"   # + pytest, hypothesis (to run the test suite)
pip install -e ".[fast]"  # + numba (optional acceleration hooks)
```

Requires Python ≥ 3.11.

## 60-second example

```python
from gridlab import run_backtest

out = run_backtest({
    "symbol": "BTCUSDT",
    "market_type": "spot",
    "initial_cash": 10_000.0,
    "grid": {"levels": 14, "lower": 80, "upper": 120,
             "spacing": "geometric", "direction": "long"},
    "sizing": {"mode": "fixed_quote", "value": 100.0},
    "fees": {"maker": 0.0002, "taker": 0.0005},
    "fill": {"mode": "conservative"},
    "data": {"kind": "synthetic", "n": 2000, "regime": "range", "seed": 7},
})

print(out["metrics"]["total_return"], out["benchmarks"]["buy_and_hold"]["total_return"])
```

`run_backtest` returns a **plain JSON-serializable dict** (`json.dumps(out)` just
works), so it is ready to hand to a frontend or an HTTP response.

Generate a standalone HTML report:

```python
out = run_backtest(spec, with_report=True)
open("report.html", "w", encoding="utf-8").write(out["html_report"])  # open in a browser
```

See `examples/` for `quickstart.py`, `generate_report.py`, and
`research_example.py`.

---

## Spot Trading Edition (v1.1)

v1.1 makes spot backtests **trustworthy and money-relevant** for live venues —
Binance crypto now, Interactive Brokers stocks later. Every feature is **opt-in
and additive**: existing specs behave identically.

### 1. Exchange realism — real venue filters

Live exchanges quantise price to a **tick size**, quantise quantity to a **lot
step**, and reject orders below **min-qty / min-notional**. A backtest that
ignores these overstates fills. Turn them on with a one-word `venue` preset:

```python
out = run_backtest({
    "symbol": "BTCUSDT",
    "venue": "binance",          # applies real Binance spot filters
    "grid": {"levels": 20, "lower": 60000, "upper": 90000,
             "spacing": "geometric", "direction": "long"},
    "sizing": {"mode": "fixed_quote", "value": 50.0},
    "fees": {"maker": 0.001, "taker": 0.001},   # Binance spot default 0.10%
    "data": {"kind": "binance", "interval": "1h", "limit": 2000},
})
```

Or specify filters explicitly via `exchange_rules`:

```python
"exchange_rules": {"enabled": True, "tick_size": 0.01,
                   "step_size": 0.00001, "min_qty": 0.00001,
                   "min_notional": 5.0},
```

Presets available: `gridlab.available_presets()` → `["binance", "ibkr"]`.
Orders below the mins are **rejected** (and counted in `rejections`), exactly as
the exchange would; reduce-only exits keep their full size so inventory is never
stranded.

### 2. Real market data — Binance klines & CSV

No more synthetic-only research. `data.kind` now accepts `binance` and `csv`:

```python
"data": {"kind": "binance", "symbol": "ETHUSDT",
         "interval": "1h", "limit": 5000}      # paginated, cached to ~/.gridlab
"data": {"kind": "csv", "path": "data/BTCUSDT-1h.csv"}
```

Binance fetches use stdlib `urllib` (no new deps), paginate automatically, fall
back across hosts, and **cache to disk** so repeat runs are instant. Direct
helpers are public too:

```python
from gridlab import fetch_binance_klines_df, load_binance_klines, load_csv
df = fetch_binance_klines_df("BTCUSDT", "1h", max_candles=5000)
```

### 3. Grid economics metrics

Seven metrics aimed at *grid* profitability, not generic returns:
`trades_per_day`, `return_over_buy_hold`, `fee_to_profit_ratio`,
`avg_capital_utilization`, `time_in_market_frac`, `realized_grid_pnl`,
`avg_round_trip_bps`. The engine now records a per-bar **invested fraction** so
capital-efficiency is measured, not guessed. (`fee_to_profit_ratio` is the
single most honest "is this real?" number for a grid — high churn that pays the
exchange more than you keep shows up immediately.)

### 4. Parallel parameter search

`grid_search(..., workers=N)` spreads a sweep across processes:

```python
from gridlab.research import grid_search
results = grid_search(base_spec, space, workers=8)   # serial default = 1
```

Ranking is **identical** to serial; `workers=1` (default) keeps studio behaviour
unchanged. (Process-spawn overhead means the win shows on large sweeps over long
real-data runs.)

### 5. RSI mean-reversion filter

Gate grid entries on RSI so you stop buying into momentum blow-offs (only buy
when not overbought, only sell when not oversold). The RSI period follows the
grid's `atr_period` (default 14, the standard RSI lookback):

```python
"filter": {"kind": "rsi", "oversold": 35, "overbought": 65}
# `lower`/`upper` are accepted as aliases for oversold/overbought.
```

Tighter bands (e.g. 40/60) trade less but more selectively; wider bands (e.g.
20/80) behave closer to an unfiltered grid.

### 6. Robustness scorecard — a deployment trust score

The headline number for "should I run this live?". `robustness_report` fuses
**walk-forward out-of-sample** consistency, **deflated Sharpe** (overfitting
penalty across all trials), and **Monte-Carlo** path risk into a single
**0–100 trust score** with a letter grade:

```python
from gridlab import robustness_report
rep = robustness_report(base_spec, space)
print(rep["trust_score"], rep["grade"])     # e.g. 57.3 "Fragile"
print(rep["components"])                     # out_of_sample / overfitting / path_risk
```

It is deliberately **pessimistic**: a config can show a great in-sample profit
factor and still score "Fragile" once trial count and path risk are accounted
for — which is the point.

---

## Architecture

The package is layered so each concern is independently testable and the engine
boundary stays I/O-free.

```
data ─► engine ─► strategy (returns EngineActions)
          │            ▲
          ▼            │ StrategyContext (read-only snapshot)
    execution      accounting
 (fees, slippage,   (Ledger:
  fills, margin,     cash + FIFO
  constraints)       positions)
          │
          ▼
       results (metrics, benchmarks, HTML report)
          │
          ▼
      research (grid search, walk-forward, Monte Carlo)
          │
          ▼
        api  (run_backtest facade — JSON in, JSON out)
```

- **`core/`** — vocabulary: `enums`, `models` (Candle/Order/Fill/Position/AccountState),
  `events`, `actions` (`EngineAction` command pattern with `__post_init__` validation).
- **`config/`** — immutable (frozen) config objects; `BacktestConfig` aggregates
  fee/slippage/fill/margin/bootstrap/constraint/sizing sub-configs.
- **`data/`** — `DataSource` protocol, DataFrame loader, synthetic generator, and
  **real-data loaders** (`load_binance_klines`, `load_csv`) with on-disk caching.
- **`indicators/`** — pure-pandas ATR/EMA/RSI/ADX/Bollinger for adaptive grids.
- **`execution/`** — `FeeModel`, `SlippageModel`, `resolve_fill`, `ConstraintChecker`,
  `MarginModel`, and the **`ExchangeQuantizer`** (tick/step/min-notional venue filters).
- **`accounting/`** — the **`Ledger`**: the single source of truth.
- **`engine/`** — one correct event loop; one order book; pluggable fill mode.
- **`strategy/`** — `Strategy` base + the unified **`GridStrategy`**, composed from
  swappable policies (`range`, `spacing`, `sizing`, `filters` incl. **RSI**, `sltp`, `recenter`).
- **`results/`** — metrics (with the fixes above + **grid-economics metrics**),
  benchmarks (B&H, DCA), HTML report.
- **`research/`** — `grid_search` (now **parallel**), `walk_forward`, `monte_carlo`,
  and the **`robustness_report`** deployment trust scorecard.
- **`api/`** — the `run_backtest` facade.

### The grid mechanic

The grid is **fill-driven**: when a BUY rung fills, a take-profit SELL is ensured
one rung higher; when a SELL rung fills, a re-buy BUY is ensured one rung lower.
This works for **long-only** grids (no seed inventory needed) and **neutral**
grids (seed both sides from bootstrap inventory). All order placement goes
through `EngineAction`s, so the engine remains the single authority over cash.

### Grid variants supported

Arithmetic / geometric / ATR spacing · long-only / neutral / short direction ·
static or adaptive (rolling / ATR) range · drift **recenter** · stop-loss /
take-profit overlay · trend & regime (ADX) **filters** · fixed-base / fixed-quote /
%-equity / **martingale (with ruin guard)** sizing · inventory & exposure **caps** ·
spot **and** futures (leverage, shorts, liquidation).

---

## Testing

```bash
pip install -e ".[dev]"
pytest                       # ~80 tests (incl. the v1.1 spot-edition suite)
pytest --cov=gridlab         # coverage
```

The suite includes **property-based tests** (hypothesis) for the invariants the
single-ledger design guarantees: cash conservation, equity = cash + inventory,
"when flat, equity change == sum of trade PnLs", and FIFO integrity vs an
independent replay.

---

## Building a frontend on top

`run_backtest(spec)` is the contract. `spec` is a nested dict; the result is a
dict of `metrics`, `benchmarks`, a downsampled `equity_curve`/`price_curve`,
`trades`, and `rejections`. Nothing in the result is a custom object, so it maps
cleanly to an HTTP/JSON API. The engine internals can evolve without breaking
this surface.

## License

MIT.
