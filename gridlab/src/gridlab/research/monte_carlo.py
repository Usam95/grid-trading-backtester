"""Monte Carlo robustness testing.

A single equity curve is one sample path. Monte Carlo resampling answers the
question that actually matters for sizing and survival: *across plausible
re-orderings/resamples of the same edge, how bad can the drawdown get and how
often do we end up unprofitable?* Two methods are provided:

* `trades`   — bootstrap (resample with replacement) the closed-trade PnLs.
* `returns`  — shuffle the per-bar returns to break path dependence.

Both report the distribution of final return and max drawdown plus the
probability of a losing outcome.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def _max_drawdown_from_equity(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, np.nan, peak)
    return float(np.nanmin(dd)) if dd.size else 0.0


def _percentiles(x: np.ndarray) -> dict[str, float]:
    if x.size == 0:
        return {}
    qs = [5, 25, 50, 75, 95]
    return {f"p{q}": float(np.percentile(x, q)) for q in qs}


def monte_carlo_trades(trade_pnls: list[float], initial_cash: float,
                       *, n_sims: int = 2000, seed: int = 0) -> dict:
    """Bootstrap closed-trade PnLs to build a distribution of outcomes."""
    pnls = np.asarray(trade_pnls, dtype=float)
    if pnls.size == 0 or initial_cash <= 0:
        return {"method": "trades", "n_sims": 0, "note": "no trades"}
    rng = np.random.default_rng(seed)
    final_returns = np.empty(n_sims)
    max_dds = np.empty(n_sims)
    m = pnls.size
    for i in range(n_sims):
        sample = rng.choice(pnls, size=m, replace=True)
        equity = initial_cash + np.cumsum(sample)
        equity = np.concatenate([[initial_cash], equity])
        final_returns[i] = equity[-1] / initial_cash - 1.0
        max_dds[i] = _max_drawdown_from_equity(equity)
    return {
        "method": "trades",
        "n_sims": n_sims,
        "prob_loss": float(np.mean(final_returns < 0)),
        "final_return": _percentiles(final_returns),
        "max_drawdown": _percentiles(max_dds),
        "mean_final_return": float(np.mean(final_returns)),
        "worst_max_drawdown": float(np.min(max_dds)),
    }


def monte_carlo_returns(equity_curve: list[float], *, n_sims: int = 2000,
                        seed: int = 0) -> dict:
    """Shuffle per-bar returns to break path dependence and re-simulate."""
    eq = np.asarray(equity_curve, dtype=float)
    if eq.size < 3:
        return {"method": "returns", "n_sims": 0, "note": "insufficient data"}
    rets = np.diff(eq) / np.where(eq[:-1] == 0, np.nan, eq[:-1])
    rets = np.nan_to_num(rets, nan=0.0)
    start = float(eq[0])
    rng = np.random.default_rng(seed)
    final_returns = np.empty(n_sims)
    max_dds = np.empty(n_sims)
    for i in range(n_sims):
        shuffled = rng.permutation(rets)
        equity = start * np.cumprod(1.0 + shuffled)
        equity = np.concatenate([[start], equity])
        final_returns[i] = equity[-1] / start - 1.0
        max_dds[i] = _max_drawdown_from_equity(equity)
    return {
        "method": "returns",
        "n_sims": n_sims,
        "prob_loss": float(np.mean(final_returns < 0)),
        "final_return": _percentiles(final_returns),
        "max_drawdown": _percentiles(max_dds),
        "mean_final_return": float(np.mean(final_returns)),
        "worst_max_drawdown": float(np.min(max_dds)),
    }


def monte_carlo(result_dict: dict, initial_cash: float, *, method: str = "trades",
                n_sims: int = 2000, seed: int = 0) -> dict:
    """Convenience dispatcher over a `run_backtest` result dict."""
    if method == "returns":
        return monte_carlo_returns(result_dict.get("equity_curve", []),
                                   n_sims=n_sims, seed=seed)
    pnls = [t["pnl"] for t in result_dict.get("trades", [])]
    return monte_carlo_trades(pnls, initial_cash, n_sims=n_sims, seed=seed)
