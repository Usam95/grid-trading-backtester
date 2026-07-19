"""Range policies: where the grid's lower/upper bounds come from."""
from __future__ import annotations

from typing import Optional

from gridlab.strategy.base import StrategyContext


class StaticRange:
    """Fixed bounds supplied at construction (classic grid)."""
    __slots__ = ("lower", "upper")

    def __init__(self, lower: float, upper: float) -> None:
        if lower >= upper:
            raise ValueError("lower must be < upper")
        self.lower = lower
        self.upper = upper

    def compute(self, ctx: StrategyContext) -> Optional[tuple[float, float]]:
        return (self.lower, self.upper)


class RollingRange:
    """Bounds derived from recent price extremes (Donchian-style).

    Reads precomputed rolling min/max from the candle's `extra` dict
    (`roll_low`, `roll_high`) which the GridStrategy populates from indicators.
    Falls back to a +/- pct band around price during warmup.
    """
    __slots__ = ("pct", "low_key", "high_key")

    def __init__(self, fallback_pct: float = 0.1,
                 low_key: str = "roll_low", high_key: str = "roll_high") -> None:
        self.pct = fallback_pct
        self.low_key = low_key
        self.high_key = high_key

    def compute(self, ctx: StrategyContext) -> Optional[tuple[float, float]]:
        lo = ctx.indicator(self.low_key, 0.0)
        hi = ctx.indicator(self.high_key, 0.0)
        if hi > lo > 0:
            return (lo, hi)
        p = ctx.candle.close
        return (p * (1 - self.pct), p * (1 + self.pct))


class ATRRange:
    """Volatility-adaptive bounds: center +/- atr_mult * ATR.

    Center is the current close (or an EMA if provided as `center` in extra).
    ATR is read from `extra['atr']`. Returns None until ATR is available.
    """
    __slots__ = ("atr_mult", "atr_key", "center_key")

    def __init__(self, atr_mult: float = 2.0, atr_key: str = "atr",
                 center_key: str = "center") -> None:
        self.atr_mult = atr_mult
        self.atr_key = atr_key
        self.center_key = center_key

    def compute(self, ctx: StrategyContext) -> Optional[tuple[float, float]]:
        atr = ctx.indicator(self.atr_key, 0.0)
        if atr <= 0:
            return None
        center = ctx.indicator(self.center_key, 0.0) or ctx.candle.close
        half = self.atr_mult * atr
        return (max(1e-9, center - half), center + half)
