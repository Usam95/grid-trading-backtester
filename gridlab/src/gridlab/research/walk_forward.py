"""Walk-forward (out-of-sample) evaluation.

In-sample optimisation that is never tested out-of-sample is how backtests lie.
`walk_forward` splits the timeline into expanding in-sample windows, optimises
the parameters on each in-sample window, then records performance on the *next*
unseen out-of-sample window. The spread between in-sample and out-of-sample
scores is the honest signal of robustness.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any

from gridlab.api.facade import BacktestSpec, _build_data, run_backtest
from gridlab.core.models import Candle
from gridlab.research.grid_search import ParamSpace, grid_search


def _candles_to_records(candles: list[Candle]) -> list[dict]:
    return [{
        "timestamp": c.timestamp.isoformat(), "open": c.open, "high": c.high,
        "low": c.low, "close": c.close, "volume": c.volume,
    } for c in candles]


def _spec_dict(spec: BacktestSpec | dict) -> dict:
    if isinstance(spec, BacktestSpec):
        return asdict(spec)
    return copy.deepcopy(spec)


def walk_forward(base_spec: BacktestSpec | dict, space: ParamSpace | dict,
                 *, n_splits: int = 4, objective: str = "deflated_sharpe",
                 maximize: bool = True) -> dict:
    """Expanding-window walk-forward optimisation.

    Returns {"folds": [...], "summary": {...}} where each fold reports the best
    in-sample params, the in-sample score, and the realised out-of-sample score.
    """
    if isinstance(space, dict):
        space = ParamSpace(space)
    base = _spec_dict(base_spec)
    spec_obj = BacktestSpec.from_dict(base)

    full = _build_data(spec_obj)
    candles = list(full.candles())
    n = len(candles)
    if n < (n_splits + 1) * 10:
        raise ValueError("not enough data for the requested number of splits")

    chunk = n // (n_splits + 1)
    folds: list[dict] = []

    for i in range(n_splits):
        is_end = chunk * (i + 1)
        oos_end = chunk * (i + 2) if i < n_splits - 1 else n
        is_candles = candles[:is_end]
        oos_candles = candles[is_end:oos_end]
        if len(oos_candles) < 5:
            continue

        is_spec = copy.deepcopy(base)
        is_spec["data"] = {"kind": "dataframe", "records": _candles_to_records(is_candles)}
        ranked = grid_search(is_spec, space, objective=objective, maximize=maximize)
        best = ranked[0]

        oos_spec = copy.deepcopy(base)
        oos_spec["data"] = {"kind": "dataframe", "records": _candles_to_records(oos_candles)}
        for key, val in best["params"].items():
            _set_path(oos_spec, key, val)
        oos_spec["n_trials"] = max(1, space.size())
        oos_out = run_backtest(oos_spec, include_trades=False)

        folds.append({
            "fold": i,
            "is_bars": len(is_candles),
            "oos_bars": len(oos_candles),
            "best_params": best["params"],
            "is_score": best["score"],
            "oos_score": oos_out["metrics"].get(objective),
            "oos_total_return": oos_out["metrics"].get("total_return"),
            "oos_max_drawdown": oos_out["metrics"].get("max_drawdown"),
        })

    valid_oos = [f["oos_score"] for f in folds if f["oos_score"] is not None]
    valid_ret = [f["oos_total_return"] for f in folds if f["oos_total_return"] is not None]
    summary = {
        "n_folds": len(folds),
        "mean_oos_score": (sum(valid_oos) / len(valid_oos)) if valid_oos else None,
        "mean_oos_return": (sum(valid_ret) / len(valid_ret)) if valid_ret else None,
        "positive_oos_folds": sum(1 for r in valid_ret if r > 0),
        "objective": objective,
    }
    return {"folds": folds, "summary": summary}


def _set_path(d: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = d
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value
