"""Core models, enums and action validation."""
from __future__ import annotations

import pytest

from gridlab.core.actions import ActionType, EngineAction
from gridlab.core.enums import OrderType, Side, PositionSide
from gridlab.core.models import Order, Position


def test_side_sign_and_opposite():
    assert Side.BUY.sign == 1
    assert Side.SELL.sign == -1
    assert Side.BUY.opposite is Side.SELL
    assert Side.SELL.opposite is Side.BUY


def test_order_remaining_and_active():
    o = Order(symbol="X", side=Side.BUY, type=OrderType.LIMIT, qty=2.0, price=10.0)
    assert o.remaining_qty == 2.0
    o.filled_qty = 0.5
    assert o.remaining_qty == 1.5
    assert o.is_active


def test_place_order_requires_qty():
    with pytest.raises(ValueError):
        EngineAction(ActionType.PLACE_ORDER, side=Side.BUY, qty=0.0,
                     order_type=OrderType.LIMIT, price=10.0)


def test_limit_requires_price():
    with pytest.raises(ValueError):
        EngineAction(ActionType.PLACE_ORDER, side=Side.BUY, qty=1.0,
                     order_type=OrderType.LIMIT)


def test_stop_requires_stop_price():
    with pytest.raises(ValueError):
        EngineAction(ActionType.PLACE_ORDER, side=Side.SELL, qty=1.0,
                     order_type=OrderType.STOP)


def test_cancel_requires_id():
    with pytest.raises(ValueError):
        EngineAction(ActionType.CANCEL_ORDER)


def test_ergonomic_constructors():
    a = EngineAction.place_limit(Side.BUY, 100.0, 1.0, client_tag="grid:1")
    assert a.type is ActionType.PLACE_ORDER and a.order_type is OrderType.LIMIT
    b = EngineAction.cancel("o1")
    assert b.order_id == "o1"
    c = EngineAction.flatten()
    assert c.type is ActionType.FLATTEN


def test_position_pnl():
    p = Position(symbol="X", side=PositionSide.LONG, qty=2.0, entry_price=100.0,
                 opened_at=None)
    assert p.unrealized_pnl(110.0) == pytest.approx(20.0)
    s = Position(symbol="X", side=PositionSide.SHORT, qty=2.0, entry_price=100.0,
                 opened_at=None)
    assert s.unrealized_pnl(90.0) == pytest.approx(20.0)
