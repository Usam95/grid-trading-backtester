"""Composable grid policies.

A grid is assembled from small, swappable policy objects so that classic and
adaptive grids share one strategy implementation:

* RangePolicy   -> where are the grid bounds? (static / rolling / ATR)
* SpacingPolicy -> how are rungs distributed? (arithmetic / geometric / ATR)
* SizingPolicy  -> how big is each rung? (fixed base / fixed quote / %equity / martingale)
* FilterPolicy  -> should we add exposure now? (trend / regime filter)
* ExitPolicy    -> stop-loss / take-profit overlay
* RecenterPolicy-> when price drifts out of range, rebuild the grid

This is the open/closed extension point: new behaviours are new policy classes,
not edits to the engine or strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from gridlab.core.enums import Side
from gridlab.strategy.base import StrategyContext


@dataclass(slots=True)
class GridPlan:
    """The concrete rung layout produced by range + spacing policies."""
    lower: float
    upper: float
    levels: list[float]   # ascending rung prices

    @property
    def center(self) -> float:
        return (self.lower + self.upper) / 2.0

    @property
    def step(self) -> float:
        return (self.upper - self.lower) / max(1, len(self.levels) - 1)


@runtime_checkable
class RangePolicy(Protocol):
    def compute(self, ctx: StrategyContext) -> Optional[tuple[float, float]]:
        """Return (lower, upper) bounds, or None if not ready yet (warmup)."""
        ...


@runtime_checkable
class SpacingPolicy(Protocol):
    def levels(self, lower: float, upper: float, n: int, ctx: StrategyContext) -> list[float]:
        ...


@runtime_checkable
class SizingPolicy(Protocol):
    def size(self, price: float, step_index: int, ctx: StrategyContext) -> float:
        """Return order size in base units for a rung at `price`."""
        ...


@runtime_checkable
class FilterPolicy(Protocol):
    def allow(self, side: Side, ctx: StrategyContext) -> bool:
        """Gate new entries on a given side (e.g. block buys in a downtrend)."""
        ...


@runtime_checkable
class ExitPolicy(Protocol):
    def stop_take_prices(self, plan: GridPlan, ctx: StrategyContext
                         ) -> tuple[Optional[float], Optional[float]]:
        """Return (stop_loss_price, take_profit_price) for the whole position."""
        ...


@runtime_checkable
class RecenterPolicy(Protocol):
    def should_recenter(self, plan: GridPlan, ctx: StrategyContext) -> bool:
        ...
