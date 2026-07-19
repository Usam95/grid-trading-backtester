"""Core domain models for gridlab.

These are plain, dependency-free dataclasses. The engine, accounting and
strategy layers all speak this vocabulary. Money values are in the quote
currency (e.g. USDT) unless stated otherwise; sizes are in the base asset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from gridlab.core.enums import (
    Side,
    OrderType,
    OrderStatus,
    TimeInForce,
    PositionSide,
    Liquidity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Candle
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Candle:
    """A single OHLCV bar with optional precomputed indicator values in `extra`."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    index: int = -1
    extra: dict[str, float] = field(default_factory=dict)

    def typical_price(self) -> float:
        return (self.high + self.low + self.close) / 3.0


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Order:
    """A working order. `qty` is the original size; `filled_qty` accumulates fills."""
    symbol: str
    side: Side
    type: OrderType
    qty: float

    price: Optional[float] = None        # limit price (LIMIT / STOP_LIMIT)
    stop_price: Optional[float] = None   # trigger (STOP / STOP_LIMIT)
    tif: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False

    id: str = ""                         # assigned by the engine
    client_tag: Optional[str] = None     # strategy-side correlation key
    status: OrderStatus = OrderStatus.OPEN
    filled_qty: float = 0.0
    created_at: Optional[datetime] = None
    created_bar: int = -1
    triggered: bool = False              # for STOP / STOP_LIMIT

    @property
    def remaining_qty(self) -> float:
        return max(0.0, self.qty - self.filled_qty)

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    @property
    def is_buy(self) -> bool:
        return self.side is Side.BUY


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Fill:
    """An executed (possibly partial) trade against an order."""
    order_id: str
    symbol: str
    side: Side
    price: float
    qty: float
    fee: float
    liquidity: Liquidity
    timestamp: datetime
    bar_index: int
    client_tag: Optional[str] = None
    reason: str = "limit"   # limit | market | stop | liquidation | flatten | bootstrap

    @property
    def notional(self) -> float:
        return self.price * self.qty


# ---------------------------------------------------------------------------
# Lot — FIFO accounting unit (one open lot per directional fill)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Lot:
    side: PositionSide
    entry_price: float
    qty: float
    entry_fee: float
    opened_at: datetime
    opened_bar: int


# ---------------------------------------------------------------------------
# Position — aggregate view of net exposure in a symbol
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Position:
    symbol: str
    side: PositionSide
    qty: float                 # absolute base qty
    entry_price: float         # size-weighted average entry
    opened_at: datetime
    fees_paid: float = 0.0

    @property
    def signed_qty(self) -> float:
        return self.side.sign * self.qty

    def notional(self, price: float) -> float:
        return self.qty * price

    def unrealized_pnl(self, price: float) -> float:
        return self.side.sign * (price - self.entry_price) * self.qty


# ---------------------------------------------------------------------------
# AccountState — snapshot handed to strategies each bar
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AccountState:
    """Read-only snapshot of the account at a point in time.

    All values in quote currency. `available_cash` already excludes funds
    reserved by open orders and margin used by open positions.
    """
    cash: float
    equity: float
    available_cash: float
    base_inventory: float = 0.0     # net signed base qty (long positive, short negative)
    used_margin: float = 0.0
    reserved_cash: float = 0.0
    unrealized_pnl: float = 0.0
    last_price: float = 0.0
    bar_index: int = -1
    timestamp: Optional[datetime] = None

    @property
    def leverage_used(self) -> float:
        if self.equity <= 0:
            return 0.0
        return abs(self.base_inventory * self.last_price) / self.equity
