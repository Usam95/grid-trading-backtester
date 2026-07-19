"""Research tooling: grid search, walk-forward, Monte Carlo, and the facade."""
from __future__ import annotations

import json

import pytest

from gridlab.api.facade import BacktestSpec, run_backtest
from gridlab.research.grid_search import ParamSpace, grid_search
from gridlab.research.monte_carlo import monte_carlo, monte_carlo_trades
from gridlab.research.walk_forward import walk_forward


BASE_SPEC = {
    "symbol": "T", "initial_cash": 10_000.0,
    "grid": {"levels": 10, "lower": 85.0, "upper": 115.0, "direction": "long"},
    "sizing": {"mode": "fixed_quote", "value": 80.0},
    "data": {"kind": "synthetic", "n": 600, "regime": "range", "seed": 3},
}


def test_run_backtest_is_json_serializable():
    out = run_backtest(BASE_SPEC)
    # Must serialize cleanly for a frontend/API.
    s = json.dumps(out)
    assert isinstance(s, str)
    assert "metrics" in out and "benchmarks" in out and "equity_curve" in out


def test_run_backtest_with_report_embeds_html():
    out = run_backtest(BASE_SPEC, with_report=True)
    assert out["html_report"].startswith("<!DOCTYPE html>")
    assert "Equity Curve" in out["html_report"]


def test_grid_search_ranks_and_sets_n_trials():
    space = ParamSpace({"grid.levels": [6, 10], "sizing.value": [50.0, 100.0]})
    ranked = grid_search(BASE_SPEC, space, objective="total_return")
    assert len(ranked) == 4
    # Sorted best-first by objective.
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    # n_trials propagated -> deflated sharpe present in metrics.
    assert "deflated_sharpe" in ranked[0]["metrics"]


def test_monte_carlo_trades_distribution():
    out = run_backtest(BASE_SPEC)
    pnls = [t["pnl"] for t in out["trades"]]
    if not pnls:
        pytest.skip("no trades to resample")
    mc = monte_carlo_trades(pnls, 10_000.0, n_sims=500, seed=0)
    assert mc["n_sims"] == 500
    assert "p5" in mc["final_return"] and "p95" in mc["final_return"]
    assert 0.0 <= mc["prob_loss"] <= 1.0


def test_monte_carlo_dispatcher_returns_method():
    out = run_backtest(BASE_SPEC)
    mc = monte_carlo(out, 10_000.0, method="returns", n_sims=300)
    assert mc["method"] == "returns"


def test_walk_forward_reports_oos():
    space = ParamSpace({"grid.levels": [8, 12]})
    wf = walk_forward(BASE_SPEC, space, n_splits=3, objective="total_return")
    assert wf["summary"]["n_folds"] >= 1
    for fold in wf["folds"]:
        assert "is_score" in fold and "oos_score" in fold
