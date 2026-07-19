"""Core enumerations for gridlab."""
from __future__ import annotations

from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        return 1 if self is Side.BUY else -1

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"            # stop-market
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class TimeInForce(str, Enum):
    GTC = "GTC"   # good-til-cancelled
    IOC = "IOC"   # immediate-or-cancel
    FOK = "FOK"   # fill-or-kill


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is PositionSide.LONG else -1


class Liquidity(str, Enum):
    MAKER = "MAKER"
    TAKER = "TAKER"


class MarketType(str, Enum):
    SPOT = "SPOT"
    FUTURES = "FUTURES"


class FillMode(str, Enum):
    """How intrabar fills are resolved against OHLC data."""
    OPTIMISTIC = "optimistic"      # same-bar fills; touch == fill (documented bias)
    CONSERVATIVE = "conservative"  # orders only eligible on the bar AFTER placement
