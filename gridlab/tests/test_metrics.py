"""Metrics: correctness of the fixes over the old engine."""
from __future__ import annotations

import math

import numpy as np
import pytest

from gridlab.accounting.ledger import ClosedTrade
from gridlab.core.enums import PositionSide
from gridlab.results.metrics import (
    MetricContext, REGISTRY, _norm_cdf, _norm_ppf, compute_metrics,
)
from datetime import datetime, timezone

TS = datetime(2021, 1, 1, tzinfo=timezone.utc)


def mk_trade(pnl, entry=100.0, qty=1.0, bars=1):
    exit_price = entry + pnl / qty
    return ClosedTrade(
        symbol="X", side=PositionSide.LONG, qty=qty, entry_price=entry,
        exit_price=exit_price, entry_fee=0.0, exit_fee=0.0, gross_pnl=pnl,
        pnl=pnl, opened_at=TS, closed_at=TS, bars_held=bars,
        entry_reason="lot", exit_reason="limit")


def _ctx(equity, highs=None, lows=None, trades=None, ppy=365.0, n_trials=1):
    equity = np.asarray(equity, float)
    highs = np.asarray(highs if highs is not None else equity, float)
    lows = np.asarray(lows if lows is not None else equity, float)
    rets = np.diff(equity) / equity[:-1] if equity.size > 1 else np.array([])
    return MetricContext(equity=equity, equity_high=highs, equity_low=lows,
                         close=equity, returns=rets, trades=trades or [],
                         periods_per_year=ppy, initial_cash=float(equity[0]),
                         fees_paid=0.0, n_trials=n_trials)


def test_norm_helpers_roundtrip():
    assert _norm_cdf(0.0) == pytest.approx(0.5, abs=1e-9)
    assert _norm_ppf(0.5) == pytest.approx(0.0, abs=1e-6)
    assert _norm_cdf(_norm_ppf(0.84)) == pytest.approx(0.84, abs=1e-3)


def test_profit_factor_none_when_no_losers():
    ctx = _ctx([1000, 1010, 1020], trades=[mk_trade(5), mk_trade(5)])
    pf = REGISTRY._fns["profit_factor"](ctx)
    assert pf is None  # not +inf


def test_avg_trade_pnl_is_mean_of_actual_trades():
    trades = [mk_trade(10), mk_trade(-4), mk_trade(6)]
    ctx = _ctx([1000, 1005, 1010, 1012], trades=trades)
    avg = REGISTRY._fns["avg_trade_pnl"](ctx)
    assert avg == pytest.approx((10 - 4 + 6) / 3)


def test_intrabar_drawdown_uses_lows():
    # Close-only would miss the intrabar dip; intrabar must catch it.
    equity = [1000, 1000, 1000]
    highs = [1000, 1000, 1000]
    lows = [1000, 800, 1000]   # 20% intrabar dip
    ctx = _ctx(equity, highs=highs, lows=lows)
    mdd = REGISTRY._fns["max_drawdown"](ctx)
    assert mdd == pytest.approx(-0.20, abs=1e-9)


def test_max_dd_duration_counts_bars_underwater():
    equity = [1000, 900, 950, 1100]  # underwater bars 1 and 2
    ctx = _ctx(equity)
    dur = REGISTRY._fns["max_drawdown_duration"](ctx)
    assert dur == 2.0


def test_sharpe_scales_with_periods_per_year():
    rng = np.random.default_rng(0)
    eq = 1000 * np.cumprod(1 + rng.normal(0.0005, 0.01, 500))
    eq = np.concatenate([[1000.0], eq])
    s_hourly = REGISTRY._fns["sharpe"](_ctx(eq, ppy=24 * 365))
    s_daily = REGISTRY._fns["sharpe"](_ctx(eq, ppy=365))
    assert s_hourly > s_daily  # higher frequency -> larger annualisation factor


def test_deflated_sharpe_decreases_with_more_trials():
    rng = np.random.default_rng(1)
    eq = 1000 * np.cumprod(1 + rng.normal(0.001, 0.01, 400))
    eq = np.concatenate([[1000.0], eq])
    ds1 = REGISTRY._fns["deflated_sharpe"](_ctx(eq, n_trials=1))
    ds100 = REGISTRY._fns["deflated_sharpe"](_ctx(eq, n_trials=100))
    assert ds100 <= ds1  # more configs tried -> more deflation


def test_compute_metrics_smoke():
    class FakeResult:
        equity = [1000, 1010, 1005, 1020]
        equity_high = [1000, 1012, 1010, 1022]
        equity_low = [1000, 1000, 1000, 1015]
        close = [100, 101, 100.5, 102]
        closed_trades = [mk_trade(10), mk_trade(-3)]
        periods_per_year = 365.0
        initial_cash = 1000.0
        fees_paid = 1.5
        realized_pnl = 7.0
        final_equity = 1020.0
        bars = 4
        liquidated = False
    m = compute_metrics(FakeResult())
    assert m["total_return"] == pytest.approx(0.02)
    assert m["n_trades"] == 2
    assert m["win_rate"] == pytest.approx(0.5)
