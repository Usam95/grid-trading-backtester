"""Spacing policies: how rung prices are distributed between the bounds."""
from __future__ import annotations

import numpy as np

from gridlab.strategy.base import StrategyContext


class ArithmeticSpacing:
    """Equal absolute spacing (classic arithmetic grid)."""

    def levels(self, lower: float, upper: float, n: int, ctx: StrategyContext) -> list[float]:
        return list(np.linspace(lower, upper, n))


class GeometricSpacing:
    """Equal *ratio* spacing — rungs are evenly spaced in log-price.

    Preferred for assets that move in percentage terms (most crypto), so each
    round trip captures a constant percentage rather than constant dollar move.
    """

    def levels(self, lower: float, upper: float, n: int, ctx: StrategyContext) -> list[float]:
        lower = max(lower, 1e-9)
        return list(np.geomspace(lower, upper, n))


class ATRSpacing:
    """Rungs spaced a fixed multiple of ATR apart, anchored at the lower bound.

    The number of rungs that fit between the bounds is derived from ATR rather
    than fixed, capped at `n`. Falls back to arithmetic if ATR is unavailable.
    """
    __slots__ = ("atr_mult", "atr_key")

    def __init__(self, atr_mult: float = 0.5, atr_key: str = "atr") -> None:
        self.atr_mult = atr_mult
        self.atr_key = atr_key

    def levels(self, lower: float, upper: float, n: int, ctx: StrategyContext) -> list[float]:
        atr = ctx.indicator(self.atr_key, 0.0)
        step = self.atr_mult * atr
        if step <= 0:
            return list(np.linspace(lower, upper, n))
        levels = []
        p = lower
        while p <= upper and len(levels) < n:
            levels.append(p)
            p += step
        if levels and levels[-1] < upper:
            levels.append(upper)
        return levels
