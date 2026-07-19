"""Service layer — the only place that talks to the gridlab engine.

It drives the engine directly (rather than only the thin facade) so it can emit
a richer, perfectly-aligned payload for the UI: down-sampled equity / price /
benchmark curves on a shared index, a drawdown series, the grid rung ladder for
the price overlay, trade markers mapped onto the down-sampled axis, and a set of
plain-English insights + an overall verdict. Everything returned is JSON-safe.
"""
from __future__ import annotations

import bisect
import math
from typing import Any, Optional

import numpy as np
import pandas as pd

from gridlab.api.facade import (
    BacktestSpec, _build_config, _build_strategy, _build_data,
    _enrich_indicators, _config_summary,
)
from gridlab.config.models import GridConfig
from gridlab.engine.engine import BacktestEngine, EngineResult
from gridlab.indicators.indicators import atr as atr_ind, ema as ema_ind
from gridlab.research.grid_search import ParamSpace, grid_search
from gridlab.research.walk_forward import walk_forward
from gridlab.research.monte_carlo import monte_carlo
from gridlab.research.robustness import robustness_report
from gridlab.results.benchmarks import buy_and_hold, dca_benchmark
from gridlab.results.metrics import compute_metrics
from gridlab.results.report import render_html_report

from backend.presets import HEADLINE_METRICS, METRIC_META

MAX_POINTS = 600
MAX_TRADES = 2000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(x: Any) -> Optional[float]:
    """Coerce to a JSON-safe float (NaN/inf -> None)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _json_safe(obj: Any) -> Any:
    """Recursively replace NaN/inf floats with None so the payload is strict-JSON."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def _ds_indices(n: int, max_points: int = MAX_POINTS) -> np.ndarray:
    if n <= max_points:
        return np.arange(n)
    return np.unique(np.linspace(0, n - 1, max_points).astype(int))


def _pick(arr, idx) -> list[float]:
    a = np.asarray(arr, dtype=float)
    return [(_f(v) if math.isfinite(v) else None) for v in a[idx]]


def _drawdown_series(equity: np.ndarray) -> list[float]:
    if equity.size == 0:
        return []
    peak = np.maximum.accumulate(equity)
    dd = np.where(peak > 0, (equity - peak) / peak, 0.0)
    return [float(v) for v in dd]


# ---------------------------------------------------------------------------
# Grid geometry (preview + price-chart overlay)
# ---------------------------------------------------------------------------

def compute_grid_levels(spec_dict: dict) -> dict:
    """Resolve the rung ladder for a spec — works for static and adaptive grids."""
    grid = dict(spec_dict.get("grid") or {})
    levels_n = int(grid.get("levels", 10) or 10)
    spacing = grid.get("spacing", "arithmetic")
    direction = grid.get("direction", "neutral")
    adaptive = bool(grid.get("adaptive", False))
    lower = grid.get("lower")
    upper = grid.get("upper")
    lookback = int(grid.get("lookback", 100) or 100)
    atr_period = int(grid.get("atr_period", 14) or 14)
    atr_mult = float(grid.get("atr_mult", 2.0) or 2.0)

    source = "static"
    need_derive = adaptive or lower is None or upper is None

    if need_derive:
        spec = BacktestSpec.from_dict(spec_dict)
        candles = list(_build_data(spec).candles())
        closes = np.array([c.close for c in candles], dtype=float)
        highs = np.array([c.high for c in candles], dtype=float)
        lows = np.array([c.low for c in candles], dtype=float)
        if closes.size == 0:
            return {"error": "no data to derive grid bounds"}
        win = closes[-lookback:] if closes.size > lookback else closes
        if adaptive and spacing == "atr":
            center = float(ema_ind(pd.Series(closes), max(2, lookback)).iloc[-1])
            atr_val = float(atr_ind(pd.Series(highs), pd.Series(lows),
                                    pd.Series(closes), atr_period).iloc[-1])
            lower = center - atr_mult * atr_val
            upper = center + atr_mult * atr_val
            source = "adaptive_atr"
        elif adaptive:
            lower = float(np.min(win))
            upper = float(np.max(win))
            source = "adaptive_rolling"
        else:
            lower = float(np.min(win))
            upper = float(np.max(win))
            source = "derived"

    lower = float(lower)
    upper = float(upper)
    if lower >= upper or lower <= 0:
        return {"error": "invalid grid bounds (lower must be > 0 and < upper)"}

    if spacing == "geometric":
        rungs = np.geomspace(lower, upper, levels_n)
    else:  # arithmetic / atr (atr approximated linearly for preview)
        rungs = np.linspace(lower, upper, levels_n)

    return {
        "lower": lower,
        "upper": upper,
        "center": (lower + upper) / 2.0,
        "spacing": spacing,
        "direction": direction,
        "adaptive": adaptive,
        "source": source,
        "levels": [float(x) for x in rungs],
        "spacing_pct": float((upper - lower) / lower / max(1, levels_n - 1)),
    }


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def _serialize_trades(trades, full_ts: list, ds_idx: np.ndarray) -> list[dict]:
    """Map each closed trade onto the down-sampled axis for chart markers."""
    out: list[dict] = []
    ds_list = ds_idx.tolist()
    n_full = len(full_ts)
    for t in trades[:MAX_TRADES]:
        # bar index of the exit, via timestamp bisect on the full axis
        exit_bar = bisect.bisect_left(full_ts, t.closed_at) if full_ts else 0
        exit_bar = min(max(exit_bar, 0), n_full - 1) if n_full else 0
        entry_bar = bisect.bisect_left(full_ts, t.opened_at) if full_ts else 0
        entry_bar = min(max(entry_bar, 0), n_full - 1) if n_full else 0
        out.append({
            "side": t.side.value,
            "qty": _f(t.qty),
            "entry_price": _f(t.entry_price),
            "exit_price": _f(t.exit_price),
            "pnl": _f(t.pnl),
            "return_pct": _f(t.return_pct),
            "bars_held": int(t.bars_held),
            "opened_at": t.opened_at.isoformat(),
            "closed_at": t.closed_at.isoformat(),
            "exit_reason": t.exit_reason,
            "entry_x": bisect.bisect_left(ds_list, entry_bar),
            "exit_x": bisect.bisect_left(ds_list, exit_bar),
        })
    return out


def run_backtest(spec_dict: dict, *, with_report: bool = False,
                 include_trades: bool = True) -> dict:
    spec = BacktestSpec.from_dict(spec_dict)
    config = _build_config(spec)
    gc = GridConfig(**spec.grid)
    data = _build_data(spec)
    if gc.adaptive or (spec.filter or {}).get("kind") in ("trend", "regime", "rsi"):
        data = _enrich_indicators(data, gc)

    strategy = _build_strategy(spec)
    engine = BacktestEngine(config)
    result: EngineResult = engine.run(data, strategy)

    metrics = compute_metrics(result, n_trials=spec.n_trials)
    bh = buy_and_hold(result.close, config.initial_cash, config.fees.taker)
    dca = dca_benchmark(result.close, config.initial_cash, fee=config.fees.taker)

    n = len(result.equity)
    idx = _ds_indices(n)
    equity = np.asarray(result.equity, dtype=float)
    dd_full = np.asarray(_drawdown_series(equity), dtype=float)
    full_ts = result.timestamps

    payload = {
        "symbol": result.symbol,
        "bars": result.bars,
        "start": full_ts[0].isoformat() if full_ts else None,
        "end": full_ts[-1].isoformat() if full_ts else None,
        "initial_cash": _f(result.initial_cash),
        "final_equity": _f(result.final_equity),
        "fees_paid": _f(result.fees_paid),
        "realized_pnl": _f(result.realized_pnl),
        "liquidated": bool(result.liquidated),
        "rejections": dict(result.rejections),
        "metrics": {k: _f(v) for k, v in metrics.items()},
        "benchmarks": {
            "buy_and_hold": {"total_return": _f(bh["total_return"]),
                             "final_equity": _f(bh["final_equity"]),
                             "max_drawdown": _f(bh["max_drawdown"])},
            "dca": {"total_return": _f(dca["total_return"]),
                    "final_equity": _f(dca["final_equity"]),
                    "max_drawdown": _f(dca["max_drawdown"])},
        },
        "series": {
            "x": [int(i) for i in idx],
            "timestamps": [full_ts[i].isoformat() for i in idx] if full_ts else [],
            "equity": _pick(result.equity, idx),
            "price": _pick(result.close, idx),
            "buy_and_hold": _pick(bh["equity_curve"], idx) if bh["equity_curve"] else [],
            "dca": _pick(dca["equity_curve"], idx) if dca["equity_curve"] else [],
            "drawdown": _pick(dd_full, idx) if dd_full.size else [],
        },
        "trades": _serialize_trades(result.closed_trades, full_ts, idx) if include_trades else [],
        "n_closed_trades": len(result.closed_trades),
        "config_summary": _config_summary(spec, config),
    }

    # Grid overlay for the price chart (mapped onto the down-sampled axis).
    try:
        payload["grid"] = compute_grid_levels(spec_dict)
    except Exception as exc:  # noqa: BLE001 - overlay is best-effort
        payload["grid"] = {"error": str(exc)}

    payload["insights"] = _build_insights(payload, spec_dict)
    payload["verdict"] = _build_verdict(payload)
    payload["data_source"] = _data_source_summary(spec_dict, result)

    if with_report:
        payload["html_report"] = render_html_report(
            result, metrics,
            benchmarks={"buy_and_hold": bh, "dca": dca},
            config_summary=_config_summary(spec, config))
    return payload


# ---------------------------------------------------------------------------
# Insights + verdict (the "informative" layer)
# ---------------------------------------------------------------------------

def _build_insights(payload: dict, spec_dict: dict) -> list[dict]:
    m = payload["metrics"]
    out: list[dict] = []

    ret = m.get("total_return")
    bh = payload["benchmarks"]["buy_and_hold"]["total_return"]
    if ret is not None and bh is not None:
        diff = ret - bh
        if diff > 0.005:
            out.append({"tone": "good", "text": (
                f"Beats buy & hold by {diff*100:.1f} pts "
                f"({ret*100:.1f}% vs {bh*100:.1f}%) — the grid is adding value here.")})
        elif diff < -0.005:
            out.append({"tone": "bad", "text": (
                f"Underperforms buy & hold by {abs(diff)*100:.1f} pts "
                f"({ret*100:.1f}% vs {bh*100:.1f}%). Simply holding would have done better.")})
        else:
            out.append({"tone": "info", "text": (
                f"Roughly matches buy & hold ({ret*100:.1f}% vs {bh*100:.1f}%).")})

    dd = m.get("max_drawdown")
    if dd is not None:
        if dd > -0.05:
            out.append({"tone": "good", "text": f"Shallow max drawdown of {dd*100:.1f}% — a smooth ride."})
        elif dd > -0.20:
            out.append({"tone": "warn", "text": f"Moderate max drawdown of {dd*100:.1f}% — survivable but watch sizing."})
        else:
            out.append({"tone": "bad", "text": f"Deep max drawdown of {dd*100:.1f}% — likely an inventory build-up in a trend."})

    fee = m.get("fee_drag")
    if fee is not None and fee > 0.02:
        out.append({"tone": "warn", "text": (
            f"Fee drag is {fee*100:.1f}% of capital. Grids trade a lot — widen spacing or "
            f"use maker-only fills to keep more of the edge.")})

    fpr = m.get("fee_to_profit_ratio")
    if fpr is not None:
        if fpr >= 1.0:
            out.append({"tone": "bad", "text": (
                f"Fees ate the edge: you paid {fpr:.2f}× as much in fees as you kept in net profit. "
                f"This config churns for the exchange, not for you — widen spacing or trade less.")})
        elif fpr >= 0.5:
            out.append({"tone": "warn", "text": (
                f"Fee-to-profit ratio is {fpr:.2f} — fees consume a large share of the gross edge. "
                f"Thin margin; sensitive to slippage.")})
        elif fpr > 0:
            out.append({"tone": "good", "text": (
                f"Fee-to-profit ratio is a healthy {fpr:.2f} — most of the gross edge survives costs.")})

    util = m.get("avg_capital_utilization")
    if util is not None:
        if util < 0.15:
            out.append({"tone": "info", "text": (
                f"Average capital utilisation is only {util*100:.0f}% — most of your cash sat idle. "
                f"Returns are small relative to capital tied up; consider tighter bounds or fewer rungs.")})
        elif util > 0.85:
            out.append({"tone": "warn", "text": (
                f"Capital utilisation runs hot at {util*100:.0f}% — little dry powder left for deeper dips.")})

    tpd = m.get("trades_per_day")
    if tpd is not None and tpd > 0:
        out.append({"tone": "info", "text": (
            f"Roughly {tpd:.1f} round-trips per day. On a live venue every one pays the spread + fee, "
            f"so realised results will trail the backtest if your cost assumptions are optimistic.")})

    if (spec_dict.get("data") or {}).get("kind", "synthetic") not in ("binance", "csv", "dataframe"):
        out.append({"tone": "warn", "text": (
            "This run used SYNTHETIC data. Treat the numbers as a stress test, not a forecast — "
            "switch the data source to real Binance klines before trusting profitability.")})

    pf = m.get("profit_factor")
    wr = m.get("win_rate")
    if pf is not None and wr is not None:
        if pf >= 1.5:
            out.append({"tone": "good", "text": f"Profit factor {pf:.2f} with a {wr*100:.0f}% win rate — a healthy edge."})
        elif pf >= 1.0:
            out.append({"tone": "info", "text": f"Profit factor {pf:.2f} (win rate {wr*100:.0f}%) — marginally profitable; fragile to costs."})
        else:
            out.append({"tone": "bad", "text": f"Profit factor {pf:.2f} < 1 — losing strategy as configured."})

    dsr = m.get("deflated_sharpe")
    n_trials = spec_dict.get("n_trials", 1)
    if dsr is not None and n_trials and n_trials > 1:
        if dsr < 0.6:
            out.append({"tone": "bad", "text": (
                f"Deflated Sharpe is only {dsr*100:.0f}% after {n_trials} trials — high over-fitting risk. "
                f"Validate with walk-forward before trusting it.")})
        else:
            out.append({"tone": "good", "text": f"Deflated Sharpe holds at {dsr*100:.0f}% after {n_trials} trials — robust to selection bias."})

    if payload["liquidated"]:
        out.append({"tone": "bad", "text": "Position was LIQUIDATED during the run — leverage/risk caps are too loose."})

    rej = payload["rejections"]
    if rej:
        total = sum(rej.values())
        out.append({"tone": "warn", "text": (
            f"{total} orders were rejected ({', '.join(f'{k}:{v}' for k, v in rej.items())}). "
            f"Constraints or capital limited the grid.")})

    regime = (spec_dict.get("data") or {}).get("regime")
    if regime == "trend":
        out.append({"tone": "info", "text": "Tested on a trending regime — the hardest case for grids. Survival here is a strong signal."})
    elif regime == "range":
        out.append({"tone": "info", "text": "Tested on a ranging regime — grid's natural habitat. Confirm it also survives a trend before going live."})
    return out


def _build_verdict(payload: dict) -> dict:
    m = payload["metrics"]
    score = 0
    ret = m.get("total_return") or 0.0
    bh = payload["benchmarks"]["buy_and_hold"]["total_return"] or 0.0
    dd = m.get("max_drawdown") or 0.0
    pf = m.get("profit_factor") or 0.0
    sharpe = m.get("sharpe") or 0.0

    if ret > bh:
        score += 2
    if ret > 0:
        score += 1
    if dd > -0.10:
        score += 1
    if pf >= 1.5:
        score += 2
    elif pf >= 1.0:
        score += 1
    if sharpe >= 1.0:
        score += 1
    if payload["liquidated"]:
        score -= 4

    if score >= 6:
        label, tone = "Strong", "good"
    elif score >= 4:
        label, tone = "Promising", "good"
    elif score >= 2:
        label, tone = "Marginal", "warn"
    else:
        label, tone = "Weak", "bad"
    return {"label": label, "tone": tone, "score": score, "max_score": 7}


def _data_source_summary(spec_dict: dict, result) -> dict:
    """Describe where the price data + cost model came from (real vs synthetic)."""
    d = spec_dict.get("data") or {}
    kind = d.get("kind", "synthetic")
    venue = spec_dict.get("venue")
    real = kind in ("binance", "csv")
    if kind == "binance":
        label = f"Binance {d.get('symbol', spec_dict.get('symbol', ''))} · {d.get('interval', '1h')}"
        desc = "Live Binance klines (real market history)."
    elif kind == "csv":
        label = "CSV file"
        desc = "Imported CSV price history."
    elif kind == "dataframe":
        label = "Custom data"
        desc = "Records supplied directly."
        real = True
    else:
        label = f"Synthetic · {d.get('regime', 'range')}"
        desc = "Generated price path — good for stress-testing, not for live expectations."
    return {
        "kind": kind,
        "is_real": bool(real),
        "label": label,
        "description": desc,
        "venue": venue,
        "exchange_rules_on": bool((spec_dict.get("exchange_rules") or {}).get("enabled") or venue),
    }


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

def run_grid_search(base: dict, space: dict, *, objective: str = "deflated_sharpe",
                    maximize: bool = True, top_k: Optional[int] = None) -> dict:
    ps = ParamSpace({k: list(v) for k, v in space.items()})
    results = grid_search(base, ps, objective=objective, maximize=maximize, top_k=top_k)
    rows = []
    for r in results:
        rows.append({
            "params": r["params"],
            "score": _f(r["score"]),
            "total_return": _f(r["metrics"].get("total_return")),
            "max_drawdown": _f(r["metrics"].get("max_drawdown")),
            "sharpe": _f(r["metrics"].get("sharpe")),
            "deflated_sharpe": _f(r["metrics"].get("deflated_sharpe")),
            "win_rate": _f(r["metrics"].get("win_rate")),
            "profit_factor": _f(r["metrics"].get("profit_factor")),
            "n_trades": r["metrics"].get("n_trades"),
        })
    keys = list(space.keys())
    heatmap = _build_heatmap(rows, keys) if len(keys) == 2 else None
    return {"objective": objective, "n_results": len(rows), "axes": keys,
            "results": rows, "heatmap": heatmap}


def _build_heatmap(rows: list[dict], keys: list[str]) -> dict:
    kx, ky = keys[0], keys[1]
    xs, ys = [], []
    for r in rows:
        if r["params"].get(kx) not in xs:
            xs.append(r["params"].get(kx))
        if r["params"].get(ky) not in ys:
            ys.append(r["params"].get(ky))
    xs = sorted(xs, key=lambda v: (isinstance(v, str), v))
    ys = sorted(ys, key=lambda v: (isinstance(v, str), v))
    lookup = {(r["params"].get(kx), r["params"].get(ky)): r["score"] for r in rows}
    z = [[lookup.get((x, y)) for x in xs] for y in ys]
    return {"x_label": kx, "y_label": ky, "x": xs, "y": ys, "z": z}


def run_walk_forward(base: dict, space: dict, *, n_splits: int = 4,
                     objective: str = "deflated_sharpe") -> dict:
    ps = ParamSpace({k: list(v) for k, v in space.items()})
    res = walk_forward(base, ps, n_splits=n_splits, objective=objective)
    for f in res.get("folds", []):
        for k in ("is_score", "oos_score", "oos_total_return", "oos_max_drawdown"):
            f[k] = _f(f.get(k))
    s = res.get("summary", {})
    for k in ("mean_oos_score", "mean_oos_return"):
        if k in s:
            s[k] = _f(s[k])
    return res


def _mc_histogram(samples: np.ndarray, bins: int = 40) -> dict:
    if samples.size == 0:
        return {"counts": [], "edges": []}
    counts, edges = np.histogram(samples, bins=bins)
    return {"counts": [int(c) for c in counts],
            "edges": [float(e) for e in edges],
            "centers": [float((edges[i] + edges[i + 1]) / 2) for i in range(len(edges) - 1)]}


def run_monte_carlo(base: dict, *, method: str = "trades", n_sims: int = 2000,
                    seed: int = 0) -> dict:
    result = run_backtest(base, include_trades=True)
    initial = float(base.get("initial_cash", 10_000.0))
    equity = np.array([p for p in result["series"]["equity"] if p is not None], dtype=float)
    pnls = np.array([t["pnl"] for t in result["trades"] if t.get("pnl") is not None], dtype=float)

    mc = monte_carlo({"equity_curve": equity.tolist(), "trades": result["trades"]},
                     initial, method=method, n_sims=n_sims, seed=seed)

    # Reproduce the bootstrap locally (same seed) to expose the full distribution
    # of final returns for the histogram chart.
    rng = np.random.default_rng(seed)
    final_returns = np.array([], dtype=float)
    if method == "returns" and equity.size >= 3:
        rets = np.diff(equity) / np.where(equity[:-1] == 0, np.nan, equity[:-1])
        rets = np.nan_to_num(rets, nan=0.0)
        start = float(equity[0])
        fr = np.empty(n_sims)
        for i in range(n_sims):
            fr[i] = (start * np.prod(1.0 + rng.permutation(rets))) / start - 1.0
        final_returns = fr
    elif method == "trades" and pnls.size > 0 and initial > 0:
        m = pnls.size
        fr = np.empty(n_sims)
        for i in range(n_sims):
            fr[i] = np.sum(rng.choice(pnls, size=m, replace=True)) / initial
        final_returns = fr

    out = {k: (_f(v) if isinstance(v, (int, float)) else v) for k, v in mc.items()}
    out["histogram"] = _mc_histogram(final_returns)
    out["base_total_return"] = result["metrics"].get("total_return")
    out["base_max_drawdown"] = result["metrics"].get("max_drawdown")
    out["n_trades_used"] = int(pnls.size)
    return out


def run_robustness(base: dict, space: Optional[dict] = None, *,
                   n_splits: int = 3, mc_sims: int = 800) -> dict:
    """Deployment trust scorecard: walk-forward OOS + deflated Sharpe + Monte-Carlo.

    Returns a 0-100 trust score with a transparent component breakdown. ``space``
    is the parameter grid to walk-forward optimise over; empty/None scores the
    single fixed configuration (walk-forward component is skipped).
    """
    space = {k: list(v) for k, v in (space or {}).items() if v}
    rep = robustness_report(base, space or None, n_splits=n_splits, mc_sims=mc_sims)
    return _json_safe(rep)
