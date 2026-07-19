"""Maker/taker fee model.

Resting limit orders that fill are charged the maker fee; market orders and
triggered stop orders pay the taker fee. Modeling these separately matters a
lot for grid trading, where the entire edge can be a few basis points per
round-trip and most fills are maker fills.
"""
from __future__ import annotations

from gridlab.config.models import FeeConfig
from gridlab.core.enums import Liquidity


class FeeModel:
    __slots__ = ("_cfg",)

    def __init__(self, cfg: FeeConfig) -> None:
        self._cfg = cfg

    def rate(self, liquidity: Liquidity) -> float:
        return self._cfg.maker if liquidity is Liquidity.MAKER else self._cfg.taker

    def fee(self, notional: float, liquidity: Liquidity) -> float:
        """Fee in quote currency for a fill of the given notional."""
        return abs(notional) * self.rate(liquidity)
