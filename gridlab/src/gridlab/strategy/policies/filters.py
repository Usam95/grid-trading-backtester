"""Filter policies: gate new exposure based on trend / regime.

Grid trading bleeds money in strong trends. A trend or regime filter that
pauses *adding* exposure on the wrong side is one of the most effective ways to
make a grid robust, per the research summary.
"""
from __future__ import annotations

from gridlab.core.enums import Side
from gridlab.strategy.base import StrategyContext


class NoFilter:
    """Always allow (pure grid)."""

    def allow(self, side: Side, ctx: StrategyContext) -> bool:
        return True


class TrendFilter:
    """Block buys when price is below a slow EMA, block sells when above.

    Reads `extra['trend_ema']`. When the market trends down, buy rungs (which
    would catch a falling knife) are suppressed; in an uptrend, sell rungs are
    suppressed. This converts a neutral grid into a trend-aware grid.
    """
    __slots__ = ("ema_key",)

    def __init__(self, ema_key: str = "trend_ema") -> None:
        self.ema_key = ema_key

    def allow(self, side: Side, ctx: StrategyContext) -> bool:
        ema = ctx.indicator(self.ema_key, 0.0)
        if ema <= 0:
            return True
        price = ctx.candle.close
        if side is Side.BUY:
            return price >= ema
        return price <= ema


class RegimeFilter:
    """Pause adding exposure when ADX signals a strong trend (range-only grid).

    Reads `extra['adx']`. Above `adx_threshold` the market is trending, so new
    grid entries are paused entirely; existing rungs/exits still work.
    """
    __slots__ = ("adx_key", "adx_threshold")

    def __init__(self, adx_threshold: float = 30.0, adx_key: str = "adx") -> None:
        self.adx_key = adx_key
        self.adx_threshold = adx_threshold

    def allow(self, side: Side, ctx: StrategyContext) -> bool:
        adx = ctx.indicator(self.adx_key, 0.0)
        return adx < self.adx_threshold


class RsiFilter:
    """Mean-reversion gate: only buy when oversold, only sell when overbought.

    Reads `extra['rsi']`. Below `oversold` the asset is stretched down, so buy
    rungs (which add long inventory cheaply) are encouraged and sell rungs are
    suppressed; above `overbought`, vice versa. Between the bands both sides are
    allowed so the grid still oscillates. This biases a spot grid toward
    accumulating low and distributing high — the core edge of a ranging grid —
    and is one of the most common discretionary overlays on real grid bots.
    """
    __slots__ = ("oversold", "overbought", "rsi_key")

    def __init__(self, oversold: float = 35.0, overbought: float = 65.0,
                 rsi_key: str = "rsi") -> None:
        if not 0 <= oversold < overbought <= 100:
            raise ValueError("require 0 <= oversold < overbought <= 100")
        self.oversold = oversold
        self.overbought = overbought
        self.rsi_key = rsi_key

    def allow(self, side: Side, ctx: StrategyContext) -> bool:
        rsi = ctx.indicator(self.rsi_key, 50.0)
        if side is Side.BUY:
            return rsi <= self.overbought      # don't buy into overbought strength
        return rsi >= self.oversold            # don't sell into oversold weakness
