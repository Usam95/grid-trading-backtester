# grid-backtest-core — Enhancement Roadmap

Prioritised by **(impact on correctness/trust) × (unlock for grid research & monetization) ÷ effort**.
Each item lists the concrete code touch-points. Effort: S (≤1d), M (2–5d), L (1–3wk).

---

## P0 — Correctness & trust (do before any paid report ships)

| # | Item | Why | Touch-points | Effort |
|---|---|---|---|---|
| 0.1 | **Conservative intrabar fill mode** (fill from bar N+1; resolve buy/sell same-bar by worst case) | Removes the biggest source of optimistic bias | `engine._simulate_fills_for_candle`, new `FillModel` + `BacktestConfig` flag | M |
| 0.2 | **Forced-exit fills at the trigger price** (not bar close), with slippage; handle gaps | SL/TP accounting is currently wrong | `engine._force_flatten_and_cancel`, `SLTPPolicy.check` returns trigger price | S |
| 0.3 | **Reconcile trade ledger with equity** (register bootstrap lots with `TradeBuilder`; or derive trades from engine FIFO) | `sum(trade.net_pnl) ≠ equity Δ` today (verified) | `TradeBuilder`, `engine._apply_bootstrap`, `engine._apply_fill` | M |
| 0.4 | **Fast/full engine parity tests** + restrict fast engine to the subset it truly models | Sweeps can rank the wrong candidate silently | new `tests/test_engine_parity.py`; doc + guard in `engine_fast.py` | M |
| 0.5 | **Maker/taker fees** | Grids are maker-heavy; single fee misprices everything | `BacktestConfig`, `engine` fee calc, reservations/constraints | S |
| 0.6 | **Intrabar drawdown + fix Sharpe annualisation + metric definitions** (`avg_trade_pnl`, `profit_factor` inf) | Headline numbers are currently misleading | `results/metrics.py` | S |
| 0.7 | **Document the long-only seeding asymmetry** (upper SELL seeds dropped without base) and add a "true neutral" option | Surprising, undocumented behaviour (verified) | `grid_simple.py`, `bootstrap.py`, README | S |

## P1 — Grid-research completeness

| # | Item | Why | Touch-points | Effort |
|---|---|---|---|---|
| 1.1 | **Walk-forward runner** (rolling/anchored train→OOS) | #1 defence against overfitting (literature) | new `research/walk_forward.py` wrapping `GridResearchRunner` | M |
| 1.2 | **Deflated Sharpe / PBO in sweep ranking** | Stop promoting noise | `research/grid_search.py` ranking, `results/metrics.py` | M |
| 1.3 | **Monte Carlo robustness** (trade/return bootstrap, start-date sensitivity, parameter jitter) | Confidence intervals on results | new `research/monte_carlo.py` | M |
| 1.4 | **Inventory & exposure risk caps** (max base qty / max notional) as first-class constraints | Real grids cap inventory | `execution/constraints.py`, `config.py` | S |
| 1.5 | **Spread + volume-aware partial fills** | Realistic execution | `FillModel` (from 0.1), uses `candle.volume` | M |
| 1.6 | **Inventory-aware recentering** (reconcile open lots when the grid moves) | Dynamic grid currently leaves inventory unmanaged on recenter | `grid_dynamic._build_inner`, engine | M |

## P2 — New grid universes (unlocks futures/short markets)

| # | Item | Why | Touch-points | Effort |
|---|---|---|---|---|
| 2.1 | **Short position lifecycle + neutral/short grid** | `PositionSide.SHORT` exists but is never opened | `engine._apply_fill`, strategies, bootstrap | L |
| 2.2 | **Margin model + funding + liquidation** | Required for honest futures-grid backtests | new `execution/margin.py`, engine per-bar liquidation check | L |
| 2.3 | **Multi-symbol portfolio layer** (N engines, one cash account) | Cross-asset grids, correlation | new `portfolio/` orchestrator | L |
| 2.4 | **DCA + martingale sizing policies** (with hard ruin guards) | Common bot variants (Pionex/3Commas) | new `strategy/policies/sizing.py` | M |

## P3 — Product surface (the monetizable layer)

| # | Item | Why | Touch-points | Effort |
|---|---|---|---|---|
| 3.1 | **HTML/PDF report renderer** from `BacktestResult` (equity, drawdown, per-rung, fee drag, benchmark, robustness) | This is the artifact users pay for | new `results/report.py`; reuse `grid-backtest-saas` | M |
| 3.2 | **Regime tagging + adaptive-parameter recommendation** | The real differentiator vs free native bots | research + `indicators`, optional ML add-on | L |
| 3.3 | **Benchmark suite** (DCA, 50/50 rebalanced, B&H + alpha/beta) | Credible comparison | `results/benchmarks.py` | S |
| 3.4 | **Property-based tests** (cash conservation, FIFO invariants) using the already-declared `hypothesis` | Lock correctness as features grow | `tests/` | S |

---

## Suggested sequence (tracer-bullet)

1. **Trust pass:** 0.2 → 0.3 → 0.6 → 0.7 (fast, removes the embarrassing/wrong bits).
2. **Fill realism:** 0.1 → 0.5 → 1.5 (the fill model is the foundation; do it once, well).
3. **Honest research:** 1.1 → 1.2 → 1.3 (overfitting controls — the literature's core message).
4. **Parity + tests:** 0.4 → 3.4 (keep the two engines honest as you add features).
5. **Universe + product:** P2 (futures/short) and P3 (reports/regime) in parallel once the core is trustworthy.

## Definition of "sellable"
- Conservative fill mode + maker/taker fees + walk-forward/Monte Carlo + deflated Sharpe (so results are
  *defensible*), and a polished report renderer (so results are *presentable*). Until then the engine is
  a strong internal research tool, not a decision-grade product.
