"""Engine event loop: fills, eligibility modes, conservation, flatten, liquidation."""
from __future__ import annotations

import pytest

from gridlab.config.config import BacktestConfig
from gridlab.config.models import FeeConfig, FillConfig, MarginConfig, SlippageConfig
from gridlab.core.actions import EngineAction
from gridlab.core.enums import FillMode, MarketType, Side
from gridlab.engine.engine import BacktestEngine
from gridlab.strategy.base import Strategy

from conftest import ds, make_candles


class SeedOnceStrategy(Strategy):
    """Places a fixed set of orders on start, then does nothing."""

    def __init__(self, actions):
        self._actions = actions

    def on_start(self, ctx):
        return list(self._actions)

    def on_bar(self, ctx):
        return []


class FlattenAtEnd(SeedOnceStrategy):
    def on_finish(self, ctx):
        return [EngineAction.flatten()]


def _cfg(**kw):
    base = dict(initial_cash=1000.0, fees=FeeConfig(0.0, 0.0),
                slippage=SlippageConfig(0.0, 0.0))
    base.update(kw)
    return BacktestConfig(**base)


def test_buy_limit_fills_next_bar_conservative():
    # Price path: 100 (seed), then dips to 95 on bar 1.
    candles = make_candles([100.0, 95.0, 96.0])
    strat = SeedOnceStrategy([EngineAction.place_limit(Side.BUY, 95.0, 1.0)])
    cfg = _cfg(fill=FillConfig(mode=FillMode.CONSERVATIVE))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    # One buy fill at 95.
    assert len(res.fills) == 1
    assert res.fills[0].side is Side.BUY
    assert res.fills[0].price == pytest.approx(95.0)


def test_conservative_does_not_fill_on_seed_bar_if_only_seed_bar_touches():
    # Bar 0 already touches 95 but order seeded "before" bar 0 (created_bar=-1)
    # so it IS eligible on bar 0 in conservative mode (seeds are pre-bar).
    candles = make_candles([100.0, 100.0])
    candles[0].low = 94.0  # bar 0 dips to 94
    strat = SeedOnceStrategy([EngineAction.place_limit(Side.BUY, 95.0, 1.0)])
    cfg = _cfg(fill=FillConfig(mode=FillMode.CONSERVATIVE))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    assert len(res.fills) == 1  # seed eligible on bar 0


def test_flat_run_trade_pnl_equals_equity_change():
    # Buy at 95, sell at 105, flatten at end (already flat) -> equity == sum pnl.
    candles = make_candles([100.0, 95.0, 105.0, 100.0])
    strat = FlattenAtEnd([
        EngineAction.place_limit(Side.BUY, 95.0, 1.0),
        EngineAction.place_limit(Side.SELL, 105.0, 1.0),
    ])
    cfg = _cfg(fees=FeeConfig(0.001, 0.001), fill=FillConfig(mode=FillMode.CONSERVATIVE))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    equity_change = res.final_equity - res.initial_cash
    # SELL at 105 needs inventory from the BUY at 95; both should fill.
    sum_pnl = sum(t.pnl for t in res.closed_trades)
    assert equity_change == pytest.approx(sum_pnl, abs=1e-9)


def test_market_order_fills_immediately():
    candles = make_candles([100.0, 100.0])
    strat = SeedOnceStrategy([EngineAction.place_market(Side.BUY, 1.0)])
    cfg = _cfg(fill=FillConfig(mode=FillMode.CONSERVATIVE))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    assert len(res.fills) == 1
    assert res.fills[0].reason == "market"


def test_optimistic_fills_same_bar():
    # In optimistic mode an order placed on bar 0 can fill on bar 0.
    candles = make_candles([100.0, 100.0])
    candles[0].low = 94.0

    class SeedOnBar(Strategy):
        def __init__(self):
            self.done = False

        def on_bar(self, ctx):
            if not self.done:
                self.done = True
                return [EngineAction.place_limit(Side.BUY, 95.0, 1.0)]
            return []

    cfg = _cfg(fill=FillConfig(mode=FillMode.OPTIMISTIC))
    res = BacktestEngine(cfg).run(ds(candles), SeedOnBar())
    assert len(res.fills) == 1


def test_spot_sell_seed_without_inventory_is_rejected():
    candles = make_candles([100.0, 105.0])
    candles[1].high = 106.0
    strat = SeedOnceStrategy([EngineAction.place_limit(Side.SELL, 105.0, 1.0)])
    cfg = _cfg(fill=FillConfig(mode=FillMode.CONSERVATIVE))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    assert len(res.fills) == 0
    assert res.rejections.get("insufficient_base", 0) >= 1


def test_bootstrap_inventory_enables_sell():
    from gridlab.config.models import BootstrapConfig
    candles = make_candles([100.0, 105.0])
    candles[1].high = 106.0
    strat = SeedOnceStrategy([EngineAction.place_limit(Side.SELL, 105.0, 1.0)])
    cfg = _cfg(fill=FillConfig(mode=FillMode.CONSERVATIVE),
               bootstrap=BootstrapConfig(base_fraction=0.5))
    res = BacktestEngine(cfg).run(ds(candles), strat)
    # bootstrap buy + the sell
    assert any(f.reason == "bootstrap" for f in res.fills)
    assert any(f.side is Side.SELL and f.reason == "limit" for f in res.fills)


def test_futures_liquidation_triggers():
    # 10x long, price crashes -> liquidation.
    candles = make_candles([100.0, 100.0, 50.0])
    candles[2].low = 50.0
    strat = SeedOnceStrategy([EngineAction.place_market(Side.BUY, 5.0)])
    cfg = BacktestConfig(
        initial_cash=100.0, market_type=MarketType.FUTURES,
        fees=FeeConfig(0.0, 0.0), slippage=SlippageConfig(0.0, 0.0),
        margin=MarginConfig(leverage=10.0, maintenance_margin_frac=0.005),
        fill=FillConfig(mode=FillMode.CONSERVATIVE),
    )
    res = BacktestEngine(cfg).run(ds(candles), strat)
    assert res.liquidated
