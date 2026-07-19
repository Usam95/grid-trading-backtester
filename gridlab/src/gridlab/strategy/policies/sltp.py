"""Exit policies: stop-loss / take-profit overlays on the whole position."""
from __future__ import annotations

from typing import Optional

from gridlab.strategy.policies.base import GridPlan
from gridlab.strategy.base import StrategyContext


class NoExit:
    """No global SL/TP — rungs exit each other (pure grid)."""

    def stop_take_prices(self, plan: GridPlan, ctx: StrategyContext
                         ) -> tuple[Optional[float], Optional[float]]:
        return (None, None)


class StopTakeExit:
    """Static stop-loss below the grid and take-profit above it.

    `stop_frac` places the stop a fraction below the lower bound; `take_frac`
    places a take-profit a fraction above the upper bound. Either may be 0 to
    disable that leg. These bound the catastrophic-trend risk of a grid.
    """
    __slots__ = ("stop_frac", "take_frac")

    def __init__(self, stop_frac: float = 0.0, take_frac: float = 0.0) -> None:
        self.stop_frac = stop_frac
        self.take_frac = take_frac

    def stop_take_prices(self, plan: GridPlan, ctx: StrategyContext
                         ) -> tuple[Optional[float], Optional[float]]:
        stop = plan.lower * (1 - self.stop_frac) if self.stop_frac > 0 else None
        take = plan.upper * (1 + self.take_frac) if self.take_frac > 0 else None
        return (stop, take)


class TrailingStopExit:
    """Trailing stop that ratchets up with the running high-water price.

    Tracks the highest close seen since construction and trails the stop a fixed
    fraction below it. Useful for long-biased grids to lock in trend gains while
    still capturing oscillation.
    """
    __slots__ = ("trail_frac", "_hw")

    def __init__(self, trail_frac: float = 0.05) -> None:
        self.trail_frac = trail_frac
        self._hw = 0.0

    def stop_take_prices(self, plan: GridPlan, ctx: StrategyContext
                         ) -> tuple[Optional[float], Optional[float]]:
        self._hw = max(self._hw, ctx.candle.close)
        if self._hw <= 0:
            return (None, None)
        return (self._hw * (1 - self.trail_frac), None)
