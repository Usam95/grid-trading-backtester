"""Ledger: FIFO accounting, cash conservation, trade==equity consistency."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from gridlab.accounting.ledger import Ledger
from gridlab.core.enums import Liquidity, MarketType, PositionSide, Side
from gridlab.core.models import Fill

TS = datetime(2021, 1, 1, tzinfo=timezone.utc)


def mk_fill(side, price, qty, fee=0.0, reason="limit"):
    return Fill(order_id="o", symbol="X", side=side, price=price, qty=qty,
                fee=fee, liquidity=Liquidity.MAKER, timestamp=TS, bar_index=0,
                reason=reason)


def test_spot_buy_then_sell_realizes_pnl():
    led = Ledger(1000.0, MarketType.SPOT, "X")
    led.apply_fill(mk_fill(Side.BUY, 100.0, 1.0, fee=0.1), bar_index=0)
    assert led.long_qty == pytest.approx(1.0)
    assert led.cash == pytest.approx(1000.0 - 100.0 - 0.1)
    trades = led.apply_fill(mk_fill(Side.SELL, 110.0, 1.0, fee=0.11), bar_index=1)
    assert led.long_qty == pytest.approx(0.0)
    assert len(trades) == 1
    t = trades[0]
    # gross 10, minus both fees
    assert t.gross_pnl == pytest.approx(10.0)
    assert t.pnl == pytest.approx(10.0 - 0.1 - 0.11)
    assert t.side is PositionSide.LONG


def test_spot_flat_equity_equals_sum_trade_pnl():
    """The core old-engine fix: when flat, equity change == sum of trade PnLs."""
    led = Ledger(1000.0, MarketType.SPOT, "X")
    fills = [
        (Side.BUY, 100.0, 1.0, 0.1),
        (Side.BUY, 95.0, 1.0, 0.095),
        (Side.SELL, 105.0, 1.0, 0.105),
        (Side.SELL, 102.0, 1.0, 0.102),
    ]
    for i, (s, p, q, f) in enumerate(fills):
        led.apply_fill(mk_fill(s, p, q, fee=f), bar_index=i)
    assert led.long_qty == pytest.approx(0.0)
    equity_change = led.equity(102.0) - 1000.0
    sum_pnl = sum(t.pnl for t in led.closed_trades)
    assert equity_change == pytest.approx(sum_pnl, abs=1e-9)


def test_fifo_matches_oldest_lot_first():
    led = Ledger(10_000.0, MarketType.SPOT, "X")
    led.apply_fill(mk_fill(Side.BUY, 100.0, 1.0), bar_index=0)
    led.apply_fill(mk_fill(Side.BUY, 120.0, 1.0), bar_index=1)
    trades = led.apply_fill(mk_fill(Side.SELL, 130.0, 1.0), bar_index=2)
    # FIFO: first lot (100) is closed, not the 120 lot.
    assert trades[0].entry_price == pytest.approx(100.0)
    assert led.long_qty == pytest.approx(1.0)


def test_bootstrap_inventory_produces_trade_on_sell():
    """Bootstrap inventory must be a real lot so later sells create trades."""
    led = Ledger(1000.0, MarketType.SPOT, "X")
    boot = mk_fill(Side.BUY, 100.0, 2.0, fee=0.2, reason="bootstrap")
    led.apply_fill(boot, bar_index=0)
    trades = led.apply_fill(mk_fill(Side.SELL, 110.0, 1.0, fee=0.11), bar_index=5)
    assert len(trades) == 1
    assert trades[0].entry_price == pytest.approx(100.0)
    assert trades[0].bars_held == 5


def test_partial_lot_consumption_allocates_fees():
    led = Ledger(10_000.0, MarketType.SPOT, "X")
    led.apply_fill(mk_fill(Side.BUY, 100.0, 2.0, fee=0.2), bar_index=0)
    trades = led.apply_fill(mk_fill(Side.SELL, 110.0, 1.0, fee=0.11), bar_index=1)
    # Only half the buy lot consumed -> half its entry fee allocated.
    assert trades[0].entry_fee == pytest.approx(0.1)
    assert led.long_qty == pytest.approx(1.0)


def test_futures_short_realizes_on_buyback():
    led = Ledger(1000.0, MarketType.FUTURES, "X")
    led.apply_fill(mk_fill(Side.SELL, 100.0, 1.0, fee=0.1), bar_index=0)
    assert led.net_qty == pytest.approx(-1.0)
    assert led.short_qty == pytest.approx(1.0)
    trades = led.apply_fill(mk_fill(Side.BUY, 90.0, 1.0, fee=0.09), bar_index=1)
    assert len(trades) == 1
    assert trades[0].side is PositionSide.SHORT
    assert trades[0].gross_pnl == pytest.approx(10.0)  # sold 100, bought 90
    # Futures wallet: only fees + realized move cash.
    assert led.cash == pytest.approx(1000.0 + 10.0 - 0.1 - 0.09)


def test_futures_unrealized_pnl_sign():
    led = Ledger(1000.0, MarketType.FUTURES, "X")
    led.apply_fill(mk_fill(Side.BUY, 100.0, 1.0), bar_index=0)
    assert led.unrealized_pnl(110.0) == pytest.approx(10.0)
    assert led.unrealized_pnl(90.0) == pytest.approx(-10.0)


def test_net_position_aggregates_weighted_entry():
    led = Ledger(10_000.0, MarketType.SPOT, "X")
    led.apply_fill(mk_fill(Side.BUY, 100.0, 1.0), bar_index=0)
    led.apply_fill(mk_fill(Side.BUY, 200.0, 1.0), bar_index=1)
    pos = led.net_position()
    assert pos.side is PositionSide.LONG
    assert pos.qty == pytest.approx(2.0)
    assert pos.entry_price == pytest.approx(150.0)
