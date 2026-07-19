"""Strategy -> engine commands (the command pattern).

A strategy never mutates account or order state directly. Instead, on each bar
it returns a list of `EngineAction` objects that the engine validates and
applies. This keeps the engine the single authority over money and order state,
and keeps strategies pure and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from gridlab.core.enums import Side, OrderType, TimeInForce


class ActionType(str, Enum):
    PLACE_ORDER = "PLACE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    CANCEL_ALL = "CANCEL_ALL"
    FLATTEN = "FLATTEN"          # market-close the whole position


@dataclass(slots=True)
class EngineAction:
    """A single command from a strategy to the engine.

    Validation happens in __post_init__ so malformed actions fail fast at the
    point of creation rather than deep inside the engine loop.
    """
    type: ActionType

    # PLACE_ORDER fields
    side: Optional[Side] = None
    order_type: OrderType = OrderType.LIMIT
    price: Optional[float] = None
    stop_price: Optional[float] = None
    qty: Optional[float] = None
    tif: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    client_tag: Optional[str] = None

    # CANCEL_ORDER field
    order_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.type is ActionType.PLACE_ORDER:
            if self.side is None:
                raise ValueError("PLACE_ORDER requires a side")
            if self.qty is None or self.qty <= 0:
                raise ValueError(f"PLACE_ORDER requires qty > 0, got {self.qty!r}")
            if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.price is None:
                raise ValueError(f"{self.order_type} requires a limit price")
            if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
                raise ValueError(f"{self.order_type} requires a stop_price")
        elif self.type is ActionType.CANCEL_ORDER:
            if self.order_id is None:
                raise ValueError("CANCEL_ORDER requires an order_id")

    # ---- ergonomic constructors -------------------------------------------

    @classmethod
    def place_limit(cls, side: Side, price: float, qty: float, *,
                    reduce_only: bool = False, client_tag: str | None = None,
                    tif: TimeInForce = TimeInForce.GTC) -> "EngineAction":
        return cls(ActionType.PLACE_ORDER, side=side, order_type=OrderType.LIMIT,
                   price=price, qty=qty, reduce_only=reduce_only,
                   client_tag=client_tag, tif=tif)

    @classmethod
    def place_market(cls, side: Side, qty: float, *, reduce_only: bool = False,
                     client_tag: str | None = None) -> "EngineAction":
        return cls(ActionType.PLACE_ORDER, side=side, order_type=OrderType.MARKET,
                   qty=qty, reduce_only=reduce_only, client_tag=client_tag,
                   tif=TimeInForce.IOC)

    @classmethod
    def place_stop(cls, side: Side, stop_price: float, qty: float, *,
                   reduce_only: bool = True, client_tag: str | None = None) -> "EngineAction":
        return cls(ActionType.PLACE_ORDER, side=side, order_type=OrderType.STOP,
                   stop_price=stop_price, qty=qty, reduce_only=reduce_only,
                   client_tag=client_tag, tif=TimeInForce.GTC)

    @classmethod
    def cancel(cls, order_id: str) -> "EngineAction":
        return cls(ActionType.CANCEL_ORDER, order_id=order_id)

    @classmethod
    def cancel_all(cls) -> "EngineAction":
        return cls(ActionType.CANCEL_ALL)

    @classmethod
    def flatten(cls, client_tag: str | None = None) -> "EngineAction":
        return cls(ActionType.FLATTEN, client_tag=client_tag)
