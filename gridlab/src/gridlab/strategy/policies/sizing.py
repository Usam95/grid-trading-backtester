"""Sizing policies: how large each grid rung order is (in base units)."""
from __future__ import annotations

from gridlab.strategy.base import StrategyContext


class FixedBaseSizing:
    """Constant base-asset size per rung (e.g. 0.01 BTC each)."""
    __slots__ = ("qty",)

    def __init__(self, qty: float) -> None:
        self.qty = qty

    def size(self, price: float, step_index: int, ctx: StrategyContext) -> float:
        return self.qty


class FixedQuoteSizing:
    """Constant quote value per rung (e.g. $50 each) -> qty = value / price."""
    __slots__ = ("quote",)

    def __init__(self, quote: float) -> None:
        self.quote = quote

    def size(self, price: float, step_index: int, ctx: StrategyContext) -> float:
        return self.quote / price if price > 0 else 0.0


class PercentEquitySizing:
    """Each rung risks a fixed fraction of current equity."""
    __slots__ = ("frac",)

    def __init__(self, frac: float) -> None:
        self.frac = frac

    def size(self, price: float, step_index: int, ctx: StrategyContext) -> float:
        notional = self.frac * ctx.account.equity
        return notional / price if price > 0 else 0.0


class MartingaleSizing:
    """Increase size geometrically per rung away from center (averaging down).

    `factor` > 1 scales each successive rung. `max_steps` caps the geometric
    growth to bound ruin risk — the single most important guard for any
    martingale-style grid. Beyond the cap, size is held flat.
    """
    __slots__ = ("base", "factor", "max_steps")

    def __init__(self, base_quote: float, factor: float = 1.5, max_steps: int = 5) -> None:
        self.base = base_quote
        self.factor = factor
        self.max_steps = max_steps

    def size(self, price: float, step_index: int, ctx: StrategyContext) -> float:
        step = min(step_index, self.max_steps) if self.max_steps > 0 else step_index
        quote = self.base * (self.factor ** step)
        return quote / price if price > 0 else 0.0
