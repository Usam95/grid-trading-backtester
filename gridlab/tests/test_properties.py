"""Property-based invariants (hypothesis): cash conservation & FIFO integrity.

These encode the guarantees the single-ledger design is supposed to provide,
and are the strongest defence against the class of bug that plagued the old
engine (trade list and equity curve silently disagreeing).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from gridlab.accounting.ledger import Ledger
from gridlab.core.enums import Liquidity, MarketType, Side
from gridlab.core.models import Fill

TS = datetime(2021, 1, 1, tzinfo=timezone.utc)


def _fill(side, price, qty, fee):
    return Fill(order_id="o", symbol="X", side=side, price=price, qty=qty,
                fee=fee, liquidity=Liquidity.MAKER, timestamp=TS, bar_index=0)


# A sequence of (is_buy, price, qty) with modest ranges.
_ops = st.lists(
    st.tuples(
        st.booleans(),
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
    ),
    min_size=1, max_size=40,
)


@given(_ops)
@settings(max_examples=200, deadline=None)
def test_spot_cash_identity_holds(ops):
    """For spot, cash must always equal the exact running sum of fill cash flows."""
    led = Ledger(100_000.0, MarketType.SPOT, "X")
    expected_cash = 100_000.0
    fee_rate = 0.001
    for is_buy, price, qty in ops:
        if is_buy:
            fee = price * qty * fee_rate
            led.apply_fill(_fill(Side.BUY, price, qty, fee), bar_index=0)
            expected_cash -= price * qty + fee
        else:
            sell_qty = min(qty, led.long_qty)  # never oversell in spot
            if sell_qty <= 1e-12:
                continue
            fee = price * sell_qty * fee_rate
            led.apply_fill(_fill(Side.SELL, price, sell_qty, fee), bar_index=0)
            expected_cash += price * sell_qty - fee
        assert led.cash == pytest.approx(expected_cash, rel=1e-9, abs=1e-6)


@given(_ops)
@settings(max_examples=200, deadline=None)
def test_spot_equity_equals_cash_plus_inventory(ops):
    led = Ledger(100_000.0, MarketType.SPOT, "X")
    for is_buy, price, qty in ops:
        if is_buy:
            led.apply_fill(_fill(Side.BUY, price, qty, 0.0), bar_index=0)
        else:
            sell_qty = min(qty, led.long_qty)
            if sell_qty <= 1e-12:
                continue
            led.apply_fill(_fill(Side.SELL, price, sell_qty, 0.0), bar_index=0)
    mark = 123.45
    assert led.equity(mark) == pytest.approx(led.cash + led.long_qty * mark, rel=1e-9)


@given(_ops)
@settings(max_examples=200, deadline=None)
def test_fully_closed_spot_equity_change_equals_trade_pnl_sum(ops):
    """When the book ends flat, equity change == sum of closed-trade PnLs."""
    led = Ledger(100_000.0, MarketType.SPOT, "X")
    for is_buy, price, qty in ops:
        if is_buy:
            led.apply_fill(_fill(Side.BUY, price, qty, price * qty * 0.001), bar_index=0)
        else:
            sell_qty = min(qty, led.long_qty)
            if sell_qty <= 1e-12:
                continue
            led.apply_fill(_fill(Side.SELL, price, sell_qty, price * sell_qty * 0.001), bar_index=0)
    # Liquidate any remaining inventory at a fixed price to reach flat.
    if led.long_qty > 1e-12:
        p = 500.0
        led.apply_fill(_fill(Side.SELL, p, led.long_qty, p * led.long_qty * 0.001), bar_index=0)
    assert led.long_qty == pytest.approx(0.0, abs=1e-9)
    equity_change = led.cash - 100_000.0
    sum_pnl = sum(t.pnl for t in led.closed_trades)
    assert equity_change == pytest.approx(sum_pnl, abs=1e-6)


@given(_ops)
@settings(max_examples=150, deadline=None)
def test_fifo_entry_prices_consumed_in_order(ops):
    """Closed-trade entry prices must match an independent FIFO replay."""
    from collections import deque

    led = Ledger(1_000_000.0, MarketType.SPOT, "X")
    ref: deque[list[float]] = deque()   # reference FIFO of [price, qty]
    expected: list[float] = []

    for is_buy, price, qty in ops:
        if is_buy:
            led.apply_fill(_fill(Side.BUY, price, qty, 0.0), bar_index=0)
            ref.append([price, qty])
        else:
            sell_qty = min(qty, led.long_qty)
            if sell_qty <= 1e-12:
                continue
            led.apply_fill(_fill(Side.SELL, price, sell_qty, 0.0), bar_index=0)
            # Drain the reference FIFO by the same quantity.
            remaining = sell_qty
            while remaining > 1e-12 and ref:
                lot = ref[0]
                m = min(remaining, lot[1])
                expected.append(lot[0])
                lot[1] -= m
                remaining -= m
                if lot[1] <= 1e-12:
                    ref.popleft()

    consumed = [t.entry_price for t in led.closed_trades]
    assert len(consumed) == len(expected)
    for a, b in zip(consumed, expected):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-9)
