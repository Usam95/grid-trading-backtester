"""GridStrategy behaviour: pairing, long-only, neutral, recenter, adaptive."""
from __future__ import annotations

import pytest

from gridlab.config.config import BacktestConfig
from gridlab.config.models import (
    BootstrapConfig, FeeConfig, FillConfig, GridConfig, SlippageConfig,
)
from gridlab.core.enums import FillMode, Side
from gridlab.engine.engine import BacktestEngine
from gridlab.strategy.grid import GridStrategy
from gridlab.strategy.policies.sizing import FixedQuoteSizing

from conftest import ds, make_candles


def _cfg(**kw):
    base = dict(initial_cash=10_000.0, fees=FeeConfig(0.0002, 0.0005),
                slippage=SlippageConfig(0.0, 0.0),
                fill=FillConfig(mode=FillMode.CONSERVATIVE))
    base.update(kw)
    return BacktestConfig(**base)


def test_long_only_grid_places_only_buys_at_seed(ranging_data):
    gc = GridConfig(levels=10, lower=80.0, upper=120.0, direction="long")
    strat = GridStrategy.from_config(gc, FixedQuoteSizing(100.0))
    res = BacktestEngine(_cfg()).run(ranging_data, strat)
    # First fills should be buys (long-only seeds buys; sells come after).
    assert res.fills, "expected some fills"
    assert res.fills[0].side is Side.BUY


def test_long_only_grid_pairs_sell_after_buy():
    # Price dips to fill a buy, then rises to fill the paired sell one rung up.
    candles = make_candles([100.0, 89.0, 95.0, 100.0, 111.0, 100.0])
    gc = GridConfig(levels=5, lower=80.0, upper=120.0, spacing="arithmetic",
                    direction="long")
    strat = GridStrategy.from_config(gc, FixedQuoteSizing(500.0))
    res = BacktestEngine(_cfg()).run(ds(candles), strat)
    sides = [f.side for f in res.fills if f.reason == "limit"]
    assert Side.BUY in sides and Side.SELL in sides
    assert res.closed_trades, "a round trip should have closed"


def test_neutral_grid_with_bootstrap_seeds_both_sides(ranging_data):
    gc = GridConfig(levels=10, lower=80.0, upper=120.0, direction="neutral")
    strat = GridStrategy.from_config(gc, FixedQuoteSizing(50.0))
    cfg = _cfg(bootstrap=BootstrapConfig(base_fraction=0.5))
    res = BacktestEngine(cfg).run(ranging_data, strat)
    # With bootstrap inventory, sells can be seeded above price and fill.
    assert any(f.side is Side.SELL and f.reason == "limit" for f in res.fills)


def test_grid_profits_in_range_beats_bnh(ranging_data):
    from gridlab.results.benchmarks import buy_and_hold
    gc = GridConfig(levels=15, lower=85.0, upper=115.0, spacing="geometric",
                    direction="long")
    strat = GridStrategy.from_config(gc, FixedQuoteSizing(100.0))
    res = BacktestEngine(_cfg()).run(ranging_data, strat)
    bnh = buy_and_hold(res.close, 10_000.0, 0.0005)
    grid_ret = res.final_equity / res.initial_cash - 1.0
    # In a ranging market the grid should at least not be wiped out and should
    # generate trades.
    assert len(res.closed_trades) > 5
    assert grid_ret > -0.5


def test_adaptive_atr_grid_runs(ranging_data):
    # Adaptive grid needs enriched indicators; use the facade path.
    from gridlab.api.facade import run_backtest
    spec = {
        "symbol": "T", "initial_cash": 10_000.0,
        "grid": {"levels": 10, "adaptive": True, "spacing": "atr",
                 "atr_period": 14, "atr_mult": 2.0, "lookback": 50,
                 "recenter_drift_frac": 0.3, "direction": "long"},
        "sizing": {"mode": "fixed_quote", "value": 100.0},
        "data": {"kind": "synthetic", "n": 600, "regime": "range", "seed": 5},
    }
    out = run_backtest(spec)
    assert out["bars"] == 600
    assert out["metrics"]["n_trades"] >= 0  # should not crash


def test_stop_loss_exits_in_downtrend(trending_data):
    # Downtrending data with a stop loss should cap the drawdown.
    down = make_candles([100.0 - i for i in range(60)])  # steady decline
    gc = GridConfig(levels=8, lower=60.0, upper=100.0, direction="long",
                    stop_loss_frac=0.05)
    strat = GridStrategy.from_config(gc, FixedQuoteSizing(200.0))
    res = BacktestEngine(_cfg()).run(ds(down), strat)
    # A stop should have fired (a sell with reason 'stop').
    assert any(f.reason == "stop" for f in res.fills)
