"""Recenter policies: when to tear down and rebuild a drifting grid."""
from __future__ import annotations

from gridlab.strategy.policies.base import GridPlan
from gridlab.strategy.base import StrategyContext


class NoRecenter:
    """Never recenter (classic static grid)."""

    def should_recenter(self, plan: GridPlan, ctx: StrategyContext) -> bool:
        return False


class DriftRecenter:
    """Recenter when price escapes the grid by more than `drift_frac` of width.

    When price runs past the upper/lower bound by a margin, a static grid stops
    working (all orders are on one side). This rebuilds the grid around the new
    price, the key mechanism that turns a static grid into a rolling/adaptive one.
    """
    __slots__ = ("drift_frac",)

    def __init__(self, drift_frac: float = 0.25) -> None:
        self.drift_frac = drift_frac

    def should_recenter(self, plan: GridPlan, ctx: StrategyContext) -> bool:
        width = max(plan.upper - plan.lower, 1e-9)
        price = ctx.candle.close
        if price > plan.upper + self.drift_frac * width:
            return True
        if price < plan.lower - self.drift_frac * width:
            return True
        return False
