"""Pre-acceptance order constraints (risk caps).

The engine calls the checker before a placed order is accepted. Rejections are
explicit and enumerated so the results layer can report *why* a grid rung was
not placed (a frequent source of silent old-engine bugs, e.g. sell rungs being
dropped because there was no base inventory to back them).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from gridlab.config.models import ConstraintConfig
from gridlab.core.enums import Side, MarketType


class RejectReason(str, Enum):
    OK = "ok"
    MIN_QTY = "min_qty"
    MIN_NOTIONAL = "min_notional"
    MAX_OPEN_ORDERS = "max_open_orders"
    MAX_INVENTORY = "max_inventory"
    MAX_EXPOSURE = "max_exposure"
    INSUFFICIENT_CASH = "insufficient_cash"
    INSUFFICIENT_BASE = "insufficient_base"
    SHORT_NOT_ALLOWED = "short_not_allowed"


class ConstraintChecker:
    __slots__ = ("_cfg", "_market_type", "_allow_short", "_leverage")

    def __init__(self, cfg: ConstraintConfig, market_type: MarketType,
                 allow_short: bool, leverage: float = 1.0) -> None:
        self._cfg = cfg
        self._market_type = market_type
        self._allow_short = allow_short
        self._leverage = max(1.0, leverage)

    def check(self, *, side: Side, qty: float, price: float,
              base_inventory: float, equity: float, last_price: float,
              open_orders: int, available_cash: float,
              available_base: float) -> RejectReason:
        cfg = self._cfg

        if qty < cfg.min_order_qty or qty <= 0:
            return RejectReason.MIN_QTY
        notional = qty * price
        if notional < cfg.min_notional:
            return RejectReason.MIN_NOTIONAL
        if cfg.max_open_orders is not None and open_orders >= cfg.max_open_orders:
            return RejectReason.MAX_OPEN_ORDERS

        # Projected inventory after this order fully fills.
        delta = qty if side is Side.BUY else -qty
        projected = base_inventory + delta

        if cfg.max_base_inventory is not None and abs(projected) > cfg.max_base_inventory + 1e-12:
            return RejectReason.MAX_INVENTORY

        if cfg.max_gross_exposure_frac is not None and equity > 0:
            exposure = abs(projected) * last_price / equity
            if exposure > cfg.max_gross_exposure_frac + 1e-12:
                return RejectReason.MAX_EXPOSURE

        # Margin/cash needed is only for the portion that ADDS exposure; closing
        # an existing position frees, rather than consumes, capital. For futures
        # the requirement is notional/leverage, not the full notional.
        added_qty = max(0.0, abs(projected) - abs(base_inventory))
        required_cash = (added_qty * price) / self._leverage

        if side is Side.SELL and not self._allow_short:
            # Spot: cannot sell more base than is available, cannot go net short.
            if available_base + 1e-12 < qty:
                return RejectReason.INSUFFICIENT_BASE
            if projected < -1e-12:
                return RejectReason.SHORT_NOT_ALLOWED

        if not cfg.allow_negative_cash and required_cash > 0:
            if available_cash + 1e-9 < required_cash:
                return RejectReason.INSUFFICIENT_CASH

        return RejectReason.OK
