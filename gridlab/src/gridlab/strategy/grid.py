"""The unified grid strategy.

One implementation covers classic and adaptive grids by composing policies:
range + spacing build the rung ladder; sizing sets order size; filters gate new
exposure; an exit policy overlays SL/TP; a recenter policy rebuilds a drifting
grid. The core grid mechanic is fill-driven and lives in `on_bar`:

    when a BUY rung fills  -> ensure a SELL exists one rung higher (take profit)
    when a SELL rung fills -> ensure a BUY exists one rung lower (re-buy dip)

This pairing works for long-only spot grids (no seed inventory needed — sells
appear only after a buy fills) and for neutral grids (seeded both sides from
bootstrap inventory). All order placement goes through EngineActions, so the
engine remains the single authority over cash and order state.
"""
from __future__ import annotations

from typing import Optional

from gridlab.config.models import GridConfig
from gridlab.core.actions import EngineAction
from gridlab.core.enums import Side
from gridlab.strategy.base import Strategy, StrategyContext
from gridlab.strategy.policies.base import (
    ExitPolicy, FilterPolicy, GridPlan, RangePolicy, RecenterPolicy,
    SizingPolicy, SpacingPolicy,
)
from gridlab.strategy.policies.filters import NoFilter
from gridlab.strategy.policies.range import StaticRange, ATRRange, RollingRange
from gridlab.strategy.policies.recenter import DriftRecenter, NoRecenter
from gridlab.strategy.policies.sltp import NoExit, StopTakeExit
from gridlab.strategy.policies.sizing import (
    FixedBaseSizing, FixedQuoteSizing, MartingaleSizing, PercentEquitySizing,
)
from gridlab.strategy.policies.spacing import (
    ArithmeticSpacing, ATRSpacing, GeometricSpacing,
)

_EPS = 1e-9


class GridStrategy(Strategy):
    def __init__(
        self,
        *,
        range_policy: RangePolicy,
        spacing_policy: SpacingPolicy,
        sizing_policy: SizingPolicy,
        levels: int = 10,
        direction: str = "neutral",
        filter_policy: Optional[FilterPolicy] = None,
        exit_policy: Optional[ExitPolicy] = None,
        recenter_policy: Optional[RecenterPolicy] = None,
    ) -> None:
        self.range_policy = range_policy
        self.spacing_policy = spacing_policy
        self.sizing_policy = sizing_policy
        self.levels = levels
        self.direction = direction
        self.filter_policy = filter_policy or NoFilter()
        self.exit_policy = exit_policy or NoExit()
        self.recenter_policy = recenter_policy or NoRecenter()

        self.plan: Optional[GridPlan] = None
        self._seeded = False
        self._stop_price: Optional[float] = None
        self._take_price: Optional[float] = None

    # ---------------------------------------------------------------- factory

    @classmethod
    def from_config(cls, gc: GridConfig, sizing_policy: SizingPolicy,
                    *, filter_policy: Optional[FilterPolicy] = None,
                    exit_policy: Optional[ExitPolicy] = None) -> "GridStrategy":
        # Range policy
        if gc.adaptive:
            if gc.spacing == "atr" or gc.atr_mult:
                range_policy: RangePolicy = ATRRange(atr_mult=gc.atr_mult)
            else:
                range_policy = RollingRange()
            recenter: RecenterPolicy = DriftRecenter(
                drift_frac=gc.recenter_drift_frac or 0.25)
        else:
            range_policy = StaticRange(gc.lower, gc.upper)
            recenter = (DriftRecenter(gc.recenter_drift_frac)
                        if gc.recenter_drift_frac > 0 else NoRecenter())

        # Spacing policy
        if gc.spacing == "geometric":
            spacing: SpacingPolicy = GeometricSpacing()
        elif gc.spacing == "atr":
            spacing = ATRSpacing(atr_mult=gc.atr_mult)
        else:
            spacing = ArithmeticSpacing()

        # Exit policy
        if exit_policy is None and (gc.stop_loss_frac > 0 or gc.take_profit_frac > 0):
            exit_policy = StopTakeExit(stop_frac=gc.stop_loss_frac,
                                       take_frac=gc.take_profit_frac)

        return cls(
            range_policy=range_policy, spacing_policy=spacing,
            sizing_policy=sizing_policy, levels=gc.levels, direction=gc.direction,
            filter_policy=filter_policy, exit_policy=exit_policy,
            recenter_policy=recenter,
        )

    # ------------------------------------------------------------------ hooks

    def on_start(self, ctx: StrategyContext) -> list[EngineAction]:
        return self._maybe_build_and_seed(ctx)

    def on_bar(self, ctx: StrategyContext) -> list[EngineAction]:
        actions: list[EngineAction] = []

        # 1) (Re)build the grid if needed (warmup completion or drift).
        if self.plan is None or self.recenter_policy.should_recenter(self.plan, ctx):
            if self.plan is not None:
                actions.append(EngineAction.cancel_all())
                self._seeded = False
            actions += self._maybe_build_and_seed(ctx)
            # After a rebuild we still process this bar's fills below.

        if self.plan is None:
            return actions

        # 2) Fill-driven pairing: react to this bar's fills.
        actions += self._react_to_fills(ctx)

        # 3) Exit overlay (SL / TP) as reduce-only resting orders.
        actions += self._manage_exits(ctx)

        return actions

    def on_finish(self, ctx: StrategyContext) -> list[EngineAction]:
        # Leave positions open by default; the engine/report mark-to-market the
        # final bar. Callers that want realized-only results can flatten here.
        return []

    # -------------------------------------------------------------- internals

    def _level_price(self, i: int) -> float:
        return self.plan.levels[i]

    def _nearest_index_below(self, price: float) -> int:
        idx = 0
        for i, lv in enumerate(self.plan.levels):
            if lv <= price + _EPS:
                idx = i
            else:
                break
        return idx

    def _maybe_build_and_seed(self, ctx: StrategyContext) -> list[EngineAction]:
        bounds = self.range_policy.compute(ctx)
        if bounds is None:
            return []  # warmup; try again next bar
        lower, upper = bounds
        if lower >= upper:
            return []
        levels = self.spacing_policy.levels(lower, upper, self.levels, ctx)
        levels = sorted(p for p in levels if p > 0)
        if len(levels) < 2:
            return []
        self.plan = GridPlan(lower=lower, upper=upper, levels=levels)
        self._stop_price = None
        self._take_price = None
        return self._seed(ctx)

    def _seed(self, ctx: StrategyContext) -> list[EngineAction]:
        """Place the initial ladder of resting orders straddling current price."""
        actions: list[EngineAction] = []
        price = ctx.candle.close
        split = self._nearest_index_below(price)
        center = len(self.plan.levels) // 2

        for i, lv in enumerate(self.plan.levels):
            if abs(lv - price) <= _EPS:
                continue
            below = lv < price
            if below:
                if self.direction == "short":
                    continue  # short grid sells above only
                side = Side.BUY
            else:
                if self.direction == "long":
                    # long grid: no resting sells until a buy fills
                    continue
                side = Side.SELL
            if not self.filter_policy.allow(side, ctx):
                continue
            qty = self.sizing_policy.size(lv, abs(i - center), ctx)
            if qty <= 0:
                continue
            actions.append(EngineAction.place_limit(
                side, lv, qty, client_tag=f"grid:{i}"))
        self._seeded = True
        return actions

    def _react_to_fills(self, ctx: StrategyContext) -> list[EngineAction]:
        actions: list[EngineAction] = []
        active_tags = {o.client_tag for o in ctx.open_orders if o.client_tag}
        top = len(self.plan.levels) - 1

        for fill in ctx.fills_this_bar:
            tag = fill.client_tag
            if not tag or not tag.startswith("grid:"):
                continue
            try:
                i = int(tag.split(":", 1)[1])
            except ValueError:
                continue

            if fill.side is Side.BUY:
                # Bought at rung i -> place a take-profit SELL one rung up.
                j = i + 1
                if j <= top and f"grid:{j}" not in active_tags:
                    if self.filter_policy.allow(Side.SELL, ctx):
                        price = self._level_price(j)
                        qty = fill.qty
                        actions.append(EngineAction.place_limit(
                            Side.SELL, price, qty, client_tag=f"grid:{j}"))
                        active_tags.add(f"grid:{j}")
            else:
                # Sold at rung i -> place a re-buy BUY one rung down.
                j = i - 1
                if j >= 0 and f"grid:{j}" not in active_tags:
                    allow_buy = self.direction != "short" and self.filter_policy.allow(Side.BUY, ctx)
                    if allow_buy:
                        price = self._level_price(j)
                        qty = self.sizing_policy.size(price, abs(j - len(self.plan.levels) // 2), ctx)
                        actions.append(EngineAction.place_limit(
                            Side.BUY, price, qty, client_tag=f"grid:{j}"))
                        active_tags.add(f"grid:{j}")
        return actions

    def _manage_exits(self, ctx: StrategyContext) -> list[EngineAction]:
        stop, take = self.exit_policy.stop_take_prices(self.plan, ctx)
        if stop is None and take is None:
            return []
        actions: list[EngineAction] = []
        net = ctx.account.base_inventory
        if abs(net) <= _EPS:
            return []
        side = Side.SELL if net > 0 else Side.BUY
        qty = abs(net)

        # Replace stop only when its level changes (keeps it resting & eligible).
        if stop is not None and (self._stop_price is None or abs(stop - self._stop_price) > _EPS):
            for o in ctx.open_orders:
                if o.client_tag == "grid:stop":
                    actions.append(EngineAction.cancel(o.id))
            actions.append(EngineAction.place_stop(
                side, stop, qty, reduce_only=True, client_tag="grid:stop"))
            self._stop_price = stop
        if take is not None and (self._take_price is None or abs(take - self._take_price) > _EPS):
            for o in ctx.open_orders:
                if o.client_tag == "grid:take":
                    actions.append(EngineAction.cancel(o.id))
            actions.append(EngineAction.place_limit(
                side, take, qty, reduce_only=True, client_tag="grid:take"))
            self._take_price = take
        return actions
