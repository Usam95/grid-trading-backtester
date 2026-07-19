"""Strategy base class and the per-bar context handed to strategies.

A strategy is pure with respect to money: it observes a read-only snapshot
(`StrategyContext`) and returns a list of `EngineAction` commands. It never
mutates the ledger or the order book directly. This makes strategies trivially
unit-testable and keeps the engine the single authority over state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from gridlab.core.actions import EngineAction
from gridlab.core.models import AccountState, Candle, Fill, Order


@dataclass(slots=True)
class StrategyContext:
    """Read-only snapshot passed to `Strategy.on_bar` each candle."""
    candle: Candle
    account: AccountState
    open_orders: Sequence[Order]
    fills_this_bar: Sequence[Fill] = field(default_factory=tuple)
    bar_index: int = -1

    def indicator(self, name: str, default: float = 0.0) -> float:
        """Read a precomputed indicator value attached to the candle."""
        return self.candle.extra.get(name, default)

    def open_orders_by_tag(self, prefix: str) -> list[Order]:
        return [o for o in self.open_orders if o.client_tag and o.client_tag.startswith(prefix)]


class Strategy:
    """Subclass and implement `on_bar`. Other hooks are optional."""

    def on_start(self, ctx: StrategyContext) -> list[EngineAction]:
        """Called once before the first bar is processed. Seed orders here."""
        return []

    def on_bar(self, ctx: StrategyContext) -> list[EngineAction]:
        """Called every bar. Return commands for the engine to apply."""
        raise NotImplementedError

    def on_finish(self, ctx: StrategyContext) -> list[EngineAction]:
        """Called once after the last bar (e.g. to flatten). Default: no-op."""
        return []
