"""Slippage / spread model for market and triggered-stop fills.

Resting limit orders fill at their limit price (that is the contract of a limit
order), so slippage is applied only to *aggressive* fills: market orders and
stop orders that have triggered. Slippage is adverse: buyers pay up, sellers
receive less.
"""
from __future__ import annotations

from gridlab.config.models import SlippageConfig
from gridlab.core.enums import Side


class SlippageModel:
    __slots__ = ("_cfg",)

    def __init__(self, cfg: SlippageConfig) -> None:
        self._cfg = cfg

    @property
    def total_frac(self) -> float:
        return self._cfg.spread_frac + self._cfg.impact_frac

    def apply(self, price: float, side: Side) -> float:
        """Return the adverse execution price for an aggressive fill."""
        frac = self.total_frac
        if frac <= 0.0:
            return price
        if side is Side.BUY:
            return price * (1.0 + frac)
        return price * (1.0 - frac)
