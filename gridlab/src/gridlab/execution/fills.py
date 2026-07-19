"""Intrabar fill resolution.

Given a working order and the current candle, decide whether it fills and at
what price. This module encodes the engine's market microstructure assumptions
explicitly — the single most important place for backtest realism.

Key rules (vs. the optimistic-only old engine):

* LIMIT orders fill only if the bar's range touches the limit price. They fill
  at the limit price, except on a gap through the price, where they fill at the
  (more realistic, better-for-resting-order) open price.
* MARKET orders fill at a supplied reference price (bar open in conservative
  mode, bar close in optimistic same-bar mode) plus adverse slippage.
* STOP orders trigger when the bar trades through the stop, and fill at the
  STOP PRICE plus adverse slippage — not at the bar close (a real old-engine
  bug that made stop-losses look better than they are).
* Eligibility (same-bar vs next-bar) and adverse intrabar ordering are decided
  by the engine; this function only answers "does it fill, and where".
"""

from __future__ import annotations

from dataclasses import dataclass

from gridlab.config.models import FillConfig
from gridlab.core.enums import Side, OrderType, Liquidity
from gridlab.core.models import Candle, Order
from gridlab.execution.slippage import SlippageModel


@dataclass(slots=True, frozen=True)
class FillResult:
    filled: bool
    price: float = 0.0
    liquidity: Liquidity = Liquidity.MAKER
    reason: str = ""


def _no_fill() -> FillResult:
    return FillResult(False)


def resolve_fill(
    order: Order,
    candle: Candle,
    fill_cfg: FillConfig,
    slip: SlippageModel,
    *,
    market_ref_price: float,
) -> FillResult:
    """Resolve a single order against a single candle."""
    if order.type is OrderType.LIMIT:
        return _resolve_limit(order, candle, fill_cfg)
    if order.type is OrderType.MARKET:
        price = slip.apply(market_ref_price, order.side)
        return FillResult(True, price, Liquidity.TAKER, "market")
    if order.type in (OrderType.STOP, OrderType.STOP_LIMIT):
        return _resolve_stop(order, candle, fill_cfg, slip)
    return _no_fill()


def _touches(level: float, candle: Candle, on_touch: bool) -> bool:
    if on_touch:
        return candle.low <= level <= candle.high
    return candle.low < level < candle.high


def _resolve_limit(order: Order, candle: Candle, cfg: FillConfig) -> FillResult:
    price = order.price
    assert price is not None
    if order.side is Side.BUY:
        # Buy limit fills if price drops to/below the limit.
        touched = candle.low <= price if cfg.fill_on_touch else candle.low < price
        if not touched:
            return _no_fill()
        # Gap down through the limit: fill at the better (lower) open.
        fill_price = (
            min(price, candle.open) if (cfg.fill_gaps_at_open and candle.open < price) else price
        )
        return FillResult(True, fill_price, Liquidity.MAKER, "limit")
    else:
        touched = candle.high >= price if cfg.fill_on_touch else candle.high > price
        if not touched:
            return _no_fill()
        # Gap up through the limit: fill at the better (higher) open.
        fill_price = (
            max(price, candle.open) if (cfg.fill_gaps_at_open and candle.open > price) else price
        )
        return FillResult(True, fill_price, Liquidity.MAKER, "limit")


def _resolve_stop(order: Order, candle: Candle, cfg: FillConfig, slip: SlippageModel) -> FillResult:
    stop = order.stop_price
    assert stop is not None
    if order.side is Side.BUY:
        triggered = candle.high >= stop
    else:
        triggered = candle.low <= stop
    if not triggered:
        return _no_fill()
    if order.type is OrderType.STOP:
        # Stop-market: execute at the stop price with adverse slippage.
        exec_price = slip.apply(stop, order.side)
        return FillResult(True, exec_price, Liquidity.TAKER, "stop")
    # STOP_LIMIT: once triggered, behaves like a limit at order.price.
    limit_price = order.price if order.price is not None else stop
    limit_order = Order(order.symbol, order.side, OrderType.LIMIT, order.qty, price=limit_price)
    res = _resolve_limit(limit_order, candle, cfg)
    if res.filled:
        return FillResult(True, res.price, Liquidity.TAKER, "stop_limit")
    return _no_fill()
