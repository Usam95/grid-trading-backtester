"""Execution microstructure: fees, slippage, fill resolution, constraints, margin."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from gridlab.config.models import (
    ConstraintConfig, FeeConfig, FillConfig, MarginConfig, SlippageConfig,
)
from gridlab.core.enums import (
    Liquidity, MarketType, OrderType, PositionSide, Side,
)
from gridlab.core.models import Candle, Order
from gridlab.execution.constraints import ConstraintChecker, RejectReason
from gridlab.execution.fees import FeeModel
from gridlab.execution.fills import resolve_fill
from gridlab.execution.margin import MarginModel
from gridlab.execution.slippage import SlippageModel

TS = datetime(2021, 1, 1, tzinfo=timezone.utc)


def candle(o, h, l, c, v=1000.0):
    return Candle(timestamp=TS, open=o, high=h, low=l, close=c, volume=v, index=0)


# ---- fees -----------------------------------------------------------------

def test_maker_taker_fees():
    fm = FeeModel(FeeConfig(maker=0.001, taker=0.002))
    assert fm.fee(1000.0, Liquidity.MAKER) == pytest.approx(1.0)
    assert fm.fee(1000.0, Liquidity.TAKER) == pytest.approx(2.0)


# ---- slippage -------------------------------------------------------------

def test_slippage_is_adverse():
    sm = SlippageModel(SlippageConfig(spread_frac=0.0, impact_frac=0.01))
    assert sm.apply(100.0, Side.BUY) == pytest.approx(101.0)   # buy pays up
    assert sm.apply(100.0, Side.SELL) == pytest.approx(99.0)   # sell receives less


def test_zero_slippage_noop():
    sm = SlippageModel(SlippageConfig(0.0, 0.0))
    assert sm.apply(100.0, Side.BUY) == 100.0


# ---- fills ----------------------------------------------------------------

def test_buy_limit_fills_when_low_touches():
    cfg = FillConfig()
    slip = SlippageModel(SlippageConfig(0.0, 0.0))
    o = Order(symbol="X", side=Side.BUY, type=OrderType.LIMIT, qty=1.0, price=95.0)
    res = resolve_fill(o, candle(100, 101, 94, 99), cfg, slip, market_ref_price=100)
    assert res.filled and res.price == pytest.approx(95.0)
    assert res.liquidity is Liquidity.MAKER


def test_buy_limit_no_fill_when_above_low():
    cfg = FillConfig()
    slip = SlippageModel(SlippageConfig(0.0, 0.0))
    o = Order(symbol="X", side=Side.BUY, type=OrderType.LIMIT, qty=1.0, price=90.0)
    res = resolve_fill(o, candle(100, 101, 95, 99), cfg, slip, market_ref_price=100)
    assert not res.filled


def test_buy_limit_gap_fills_at_open():
    cfg = FillConfig(fill_gaps_at_open=True)
    slip = SlippageModel(SlippageConfig(0.0, 0.0))
    o = Order(symbol="X", side=Side.BUY, type=OrderType.LIMIT, qty=1.0, price=95.0)
    # Opens at 90 (gapped below the 95 limit) -> fills at the better 90.
    res = resolve_fill(o, candle(90, 92, 88, 91), cfg, slip, market_ref_price=90)
    assert res.filled and res.price == pytest.approx(90.0)


def test_stop_fills_at_trigger_not_close():
    cfg = FillConfig()
    slip = SlippageModel(SlippageConfig(0.0, 0.0))
    # Sell stop at 95: triggers when low <= 95; fills at 95, NOT at close 90.
    o = Order(symbol="X", side=Side.SELL, type=OrderType.STOP, qty=1.0, stop_price=95.0)
    res = resolve_fill(o, candle(100, 101, 90, 90), cfg, slip, market_ref_price=100)
    assert res.filled and res.price == pytest.approx(95.0)
    assert res.liquidity is Liquidity.TAKER


def test_stop_fill_includes_slippage():
    cfg = FillConfig()
    slip = SlippageModel(SlippageConfig(0.0, 0.01))
    o = Order(symbol="X", side=Side.SELL, type=OrderType.STOP, qty=1.0, stop_price=95.0)
    res = resolve_fill(o, candle(100, 101, 90, 90), cfg, slip, market_ref_price=100)
    assert res.price == pytest.approx(95.0 * 0.99)  # adverse for a sell


# ---- constraints ----------------------------------------------------------

def test_spot_sell_without_inventory_rejected():
    cc = ConstraintChecker(ConstraintConfig(), MarketType.SPOT, allow_short=False)
    r = cc.check(side=Side.SELL, qty=1.0, price=100.0, base_inventory=0.0,
                 equity=1000.0, last_price=100.0, open_orders=0,
                 available_cash=1000.0, available_base=0.0)
    assert r is RejectReason.INSUFFICIENT_BASE


def test_buy_insufficient_cash_rejected():
    cc = ConstraintChecker(ConstraintConfig(), MarketType.SPOT, allow_short=False)
    r = cc.check(side=Side.BUY, qty=1.0, price=100.0, base_inventory=0.0,
                 equity=50.0, last_price=100.0, open_orders=0,
                 available_cash=50.0, available_base=0.0)
    assert r is RejectReason.INSUFFICIENT_CASH


def test_inventory_cap_enforced():
    cc = ConstraintChecker(ConstraintConfig(max_base_inventory=1.0),
                           MarketType.SPOT, allow_short=False)
    r = cc.check(side=Side.BUY, qty=2.0, price=100.0, base_inventory=0.0,
                 equity=10_000.0, last_price=100.0, open_orders=0,
                 available_cash=10_000.0, available_base=0.0)
    assert r is RejectReason.MAX_INVENTORY


def test_ok_path():
    cc = ConstraintChecker(ConstraintConfig(), MarketType.SPOT, allow_short=False)
    r = cc.check(side=Side.BUY, qty=1.0, price=100.0, base_inventory=0.0,
                 equity=10_000.0, last_price=100.0, open_orders=0,
                 available_cash=10_000.0, available_base=0.0)
    assert r is RejectReason.OK


# ---- margin ---------------------------------------------------------------

def test_long_liquidation_price_below_entry():
    mm = MarginModel(MarginConfig(leverage=10.0, maintenance_margin_frac=0.005))
    # wallet = initial margin = notional/leverage = 100*1/10 = 10
    liq = mm.liquidation_price(PositionSide.LONG, 100.0, 1.0, wallet_balance=10.0)
    assert liq is not None and liq < 100.0


def test_spot_long_has_no_liquidation():
    mm = MarginModel(MarginConfig(leverage=1.0))
    assert mm.liquidation_price(PositionSide.LONG, 100.0, 1.0, 100.0) is None


def test_short_liquidation_price_above_entry():
    mm = MarginModel(MarginConfig(leverage=5.0, maintenance_margin_frac=0.005,
                                  allow_short=True))
    liq = mm.liquidation_price(PositionSide.SHORT, 100.0, 1.0, wallet_balance=20.0)
    assert liq is not None and liq > 100.0
