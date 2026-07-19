"""Engine -> observer events emitted during a backtest run.

These are informational records (not commands). The engine appends them to a
log that the results layer can inspect. Strategies normally do not consume
events; they react to candles + account state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gridlab.core.enums import Side, PositionSide
from gridlab.core.models import Fill


@dataclass(slots=True, frozen=True)
class OrderPlacedEvent:
    bar_index: int
    timestamp: datetime
    order_id: str
    side: Side
    price: float
    qty: float
    client_tag: str | None = None


@dataclass(slots=True, frozen=True)
class OrderFilledEvent:
    bar_index: int
    timestamp: datetime
    fill: Fill


@dataclass(slots=True, frozen=True)
class OrderCancelledEvent:
    bar_index: int
    timestamp: datetime
    order_id: str
    reason: str = "cancel"


@dataclass(slots=True, frozen=True)
class LiquidationEvent:
    bar_index: int
    timestamp: datetime
    symbol: str
    side: PositionSide
    qty: float
    price: float
    equity_before: float
    equity_after: float
