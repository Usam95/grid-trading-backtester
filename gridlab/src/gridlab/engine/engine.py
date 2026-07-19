"""The backtest engine: one correct event loop, one order book, one ledger.

Design goals (fixing the old engine):

* **One engine** — no fast/slow divergence. An optional numba kernel can later
  accelerate hot loops behind this same interface and is parity-tested.
* **Pluggable fill model** — OPTIMISTIC (same-bar) vs CONSERVATIVE (next-bar
  eligibility + adverse intrabar path) selected by config, so lookahead bias is
  a deliberate choice, not an accident.
* **Single ledger** — equity curve and trade list derive from the same fills,
  including bootstrap inventory and forced liquidations.
* **Correct stops** — stop orders fill at the trigger price (+slippage), and
  liquidation is checked against intrabar extremes.

The engine is I/O-free: it consumes candles and a strategy and returns an
`EngineResult` of plain arrays + records, ready for the metrics/report layer or
JSON serialization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from gridlab.config.config import BacktestConfig
from gridlab.core.actions import ActionType, EngineAction
from gridlab.core.enums import (
    FillMode, Liquidity, MarketType, OrderStatus, OrderType, Side, TimeInForce,
)
from gridlab.core.events import (
    LiquidationEvent, OrderCancelledEvent, OrderFilledEvent, OrderPlacedEvent,
)
from gridlab.core.models import AccountState, Candle, Fill, Order
from gridlab.accounting.ledger import ClosedTrade, Ledger
from gridlab.data.source import DataSource
from gridlab.execution.constraints import ConstraintChecker, RejectReason
from gridlab.execution.fees import FeeModel
from gridlab.execution.fills import resolve_fill
from gridlab.execution.exchange_rules import ExchangeQuantizer
from gridlab.execution.margin import MarginModel
from gridlab.execution.slippage import SlippageModel
from gridlab.strategy.base import Strategy, StrategyContext


@dataclass(slots=True)
class EngineResult:
    """Raw output of a run. The results layer turns this into metrics/report."""
    config: BacktestConfig
    symbol: str
    timestamps: list[datetime]
    equity: list[float]
    equity_high: list[float]
    equity_low: list[float]
    close: list[float]
    invested_frac: list[float]
    closed_trades: list[ClosedTrade]
    fills: list[Fill]
    events: list[object]
    rejections: dict[str, int]
    initial_cash: float
    final_equity: float
    fees_paid: float
    realized_pnl: float
    periods_per_year: float
    bars: int
    liquidated: bool = False


class BacktestEngine:
    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.fee_model = FeeModel(config.fees)
        self.slip_model = SlippageModel(config.slippage)
        self.margin_model = MarginModel(config.margin)
        self.quantizer = ExchangeQuantizer(config.exchange_rules)
        self.constraints = ConstraintChecker(
            config.constraints, config.market_type, config.margin.allow_short,
            leverage=config.margin.leverage)

    # ------------------------------------------------------------------ run

    def run(self, data: DataSource, strategy: Strategy) -> EngineResult:
        cfg = self.config
        candles: list[Candle] = list(data.candles())
        n = len(candles)

        ledger = Ledger(cfg.initial_cash, cfg.market_type, cfg.symbol)
        open_orders: dict[str, Order] = {}
        reserved_cash: dict[str, float] = {}   # order_id -> reserved quote
        reserved_base: dict[str, float] = {}   # order_id -> reserved base (spot sells)
        order_seq = 0

        timestamps: list[datetime] = []
        equity_curve: list[float] = []
        equity_high: list[float] = []
        equity_low: list[float] = []
        closes: list[float] = []
        invested_curve: list[float] = []   # per-bar fraction of equity in the asset
        fills_log: list[Fill] = []
        events: list[object] = []
        rejections: dict[str, int] = {}
        liquidated = False

        conservative = cfg.fill.mode is FillMode.CONSERVATIVE
        part = cfg.fill.participation

        # -- helpers --------------------------------------------------------

        def reserved_cash_total() -> float:
            return sum(reserved_cash.values())

        def reserved_base_total() -> float:
            return sum(reserved_base.values())

        def make_account(candle: Candle, idx: int) -> AccountState:
            price = candle.close
            equity = ledger.equity(price)
            if cfg.market_type is MarketType.SPOT:
                avail_cash = ledger.cash - reserved_cash_total()
                avail_base = ledger.long_qty - reserved_base_total()
                used_margin = 0.0
            else:
                pos = ledger.net_position()
                used_margin = (self.margin_model.initial_margin(pos.qty * price)
                               if pos else 0.0)
                avail_cash = equity - used_margin - reserved_cash_total()
                avail_base = 0.0
            return AccountState(
                cash=ledger.cash, equity=equity, available_cash=avail_cash,
                base_inventory=ledger.net_qty, used_margin=used_margin,
                reserved_cash=reserved_cash_total(),
                unrealized_pnl=ledger.unrealized_pnl(price), last_price=price,
                bar_index=idx, timestamp=candle.timestamp,
            )

        def record_rejection(reason: RejectReason) -> None:
            rejections[reason.value] = rejections.get(reason.value, 0) + 1

        def reserve_for(order: Order, price_ref: float) -> bool:
            """Reserve cash/base for a newly accepted order. Returns False if blocked."""
            if order.side is Side.BUY:
                if cfg.market_type is MarketType.SPOT:
                    need = order.remaining_qty * (order.price or price_ref)
                else:
                    need = self.margin_model.initial_margin(
                        order.remaining_qty * (order.price or price_ref))
                reserved_cash[order.id] = need
            else:  # SELL
                if cfg.market_type is MarketType.SPOT and not cfg.margin.allow_short:
                    reserved_base[order.id] = order.remaining_qty
                else:
                    need = self.margin_model.initial_margin(
                        order.remaining_qty * (order.price or price_ref))
                    reserved_cash[order.id] = need
            return True

        def release_reservation(order_id: str) -> None:
            reserved_cash.pop(order_id, None)
            reserved_base.pop(order_id, None)

        def place_order(action: EngineAction, candle: Candle, idx: int,
                        created_bar: int) -> None:
            nonlocal order_seq
            price_ref = candle.close
            limit_price = action.price if action.price is not None else price_ref

            # Exchange symbol filters: round price to tick and qty to lot size,
            # then drop the order if it no longer clears the venue minimums.
            q_qty = action.qty
            q_price = action.price
            q_stop = action.stop_price
            if self.quantizer.enabled:
                ref_price = action.price if action.price is not None else price_ref
                if action.reduce_only:
                    # Never strand inventory: round price only, keep the close qty.
                    if action.price is not None and ref_price > 0:
                        q_price = self.quantizer.quantize_price(ref_price)
                        limit_price = q_price
                    if action.stop_price is not None:
                        q_stop = self.quantizer.quantize_price(action.stop_price)
                else:
                    res = self.quantizer.apply(ref_price, action.qty)
                    if not res.ok:
                        record_rejection(RejectReason.MIN_NOTIONAL
                                         if res.reason == "min_notional"
                                         else RejectReason.MIN_QTY)
                        return
                    q_qty = res.qty
                    if action.price is not None:
                        q_price = res.price
                        limit_price = q_price
                    if action.stop_price is not None:
                        q_stop = self.quantizer.quantize_price(action.stop_price)

            acct = make_account(candle, idx)
            reason = self.constraints.check(
                side=action.side, qty=q_qty, price=limit_price,
                base_inventory=ledger.net_qty, equity=acct.equity,
                last_price=price_ref,
                open_orders=len(open_orders),
                available_cash=acct.available_cash,
                available_base=acct.available_cash if cfg.market_type is not MarketType.SPOT
                else (ledger.long_qty - reserved_base_total()),
            )
            if action.reduce_only:
                # reduce-only orders never need fresh cash/inventory checks beyond qty
                if reason in (RejectReason.INSUFFICIENT_CASH, RejectReason.INSUFFICIENT_BASE,
                              RejectReason.MAX_INVENTORY, RejectReason.MAX_EXPOSURE,
                              RejectReason.SHORT_NOT_ALLOWED):
                    reason = RejectReason.OK
            if reason is not RejectReason.OK:
                record_rejection(reason)
                return
            order_seq += 1
            oid = f"o{order_seq}"
            order = Order(
                symbol=cfg.symbol, side=action.side, type=action.order_type,
                qty=q_qty, price=q_price, stop_price=q_stop,
                tif=action.tif, reduce_only=action.reduce_only, id=oid,
                client_tag=action.client_tag, status=OrderStatus.OPEN,
                created_at=candle.timestamp, created_bar=created_bar,
            )
            # Market orders execute immediately at the reference price.
            if order.type is OrderType.MARKET:
                _execute(order, self.slip_model.apply(price_ref, order.side),
                         Liquidity.TAKER, candle, idx, "market")
                return
            if not action.reduce_only:
                reserve_for(order, price_ref)
            open_orders[oid] = order
            events.append(OrderPlacedEvent(idx, candle.timestamp, oid, order.side,
                                           limit_price, order.qty, order.client_tag))

        def cancel_order(oid: str, idx: int, ts: datetime, why: str = "cancel") -> None:
            order = open_orders.pop(oid, None)
            if order is None:
                return
            order.status = OrderStatus.CANCELLED
            release_reservation(oid)
            events.append(OrderCancelledEvent(idx, ts, oid, why))

        def _execute(order: Order, price: float, liq: Liquidity, candle: Candle,
                     idx: int, reason: str, qty_override: Optional[float] = None) -> float:
            """Fill (part of) an order at `price`. Returns filled qty."""
            qty = order.remaining_qty if qty_override is None else min(qty_override, order.remaining_qty)
            if qty <= 0:
                return 0.0
            # Partial-fill liquidity cap.
            if part is not None and candle.volume > 0 and order.type is not OrderType.MARKET:
                cap = part * candle.volume
                qty = min(qty, cap)
                if qty <= 0:
                    return 0.0
            notional = price * qty
            fee = self.fee_model.fee(notional, liq)
            fill = Fill(order_id=order.id, symbol=order.symbol, side=order.side,
                        price=price, qty=qty, fee=fee, liquidity=liq,
                        timestamp=candle.timestamp, bar_index=idx,
                        client_tag=order.client_tag, reason=reason)
            ledger.apply_fill(fill, bar_index=idx)
            fills_log.append(fill)
            events.append(OrderFilledEvent(idx, candle.timestamp, fill))
            order.filled_qty += qty
            # Release reservation proportionally / fully when done.
            if order.remaining_qty <= 1e-15:
                order.status = OrderStatus.FILLED
                release_reservation(order.id)
                open_orders.pop(order.id, None)
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
            return qty

        def match_resting(candle: Candle, idx: int) -> None:
            """Resolve resting limit/stop orders against this candle.

            Uses an adverse two-segment intrabar path so fills and liquidation
            are sequenced pessimistically in conservative mode.
            """
            down_bar = candle.close <= candle.open
            # Segment order: (first extreme reached, then second).
            first_high = not down_bar  # up bar goes to low first, then high
            # Build eligible order list.
            eligible = [
                o for o in list(open_orders.values())
                if o.is_active and (not conservative or o.created_bar < idx)
            ]

            def try_fill(o: Order) -> None:
                res = resolve_fill(o, candle, cfg.fill, self.slip_model,
                                   market_ref_price=candle.open)
                if res.filled:
                    _execute(o, res.price, res.liquidity, candle, idx, res.reason)

            # Process in two passes following the adverse path. For a down bar the
            # price rises to the high first (sell limits / buy stops), then falls
            # to the low (buy limits / sell stops). For an up bar, vice versa.
            if down_bar:
                first_pass = [o for o in eligible if _hits_high_leg(o)]
                second_pass = [o for o in eligible if not _hits_high_leg(o)]
            else:
                first_pass = [o for o in eligible if not _hits_high_leg(o)]
                second_pass = [o for o in eligible if _hits_high_leg(o)]

            for o in first_pass:
                if o.is_active:
                    try_fill(o)
            for o in second_pass:
                if o.is_active:
                    try_fill(o)

        def check_liquidation(candle: Candle, idx: int) -> None:
            nonlocal liquidated
            if cfg.market_type is not MarketType.FUTURES:
                return
            pos = ledger.net_position()
            if pos is None:
                return
            liq_price = self.margin_model.liquidation_price(
                pos.side, pos.entry_price, pos.qty, ledger.cash)
            if liq_price is None:
                return
            breached = (candle.low <= liq_price) if pos.side.name == "LONG" else (candle.high >= liq_price)
            if not breached:
                return
            equity_before = ledger.equity(liq_price)
            fee_rate = self.fee_model.rate(Liquidity.TAKER) + cfg.margin.liquidation_fee_frac
            fill = ledger.force_flatten_fill(liq_price, fee_rate, candle.timestamp, idx, "liquidation")
            if fill is not None:
                ledger.apply_fill(fill, bar_index=idx)
                fills_log.append(fill)
                # Cancel all open orders on liquidation.
                for oid in list(open_orders.keys()):
                    cancel_order(oid, idx, candle.timestamp, "liquidation")
                equity_after = ledger.equity(candle.close)
                events.append(LiquidationEvent(idx, candle.timestamp, cfg.symbol,
                                               pos.side, pos.qty, liq_price,
                                               equity_before, equity_after))
                liquidated = True

        def apply_actions(actions: list[EngineAction], candle: Candle, idx: int,
                          created_bar: int) -> None:
            for a in actions:
                if a.type is ActionType.PLACE_ORDER:
                    place_order(a, candle, idx, created_bar)
                elif a.type is ActionType.CANCEL_ORDER:
                    cancel_order(a.order_id, idx, candle.timestamp)
                elif a.type is ActionType.CANCEL_ALL:
                    for oid in list(open_orders.keys()):
                        cancel_order(oid, idx, candle.timestamp)
                elif a.type is ActionType.FLATTEN:
                    _flatten(candle, idx)

        def _flatten(candle: Candle, idx: int) -> None:
            net = ledger.net_qty
            if abs(net) <= 1e-15:
                return
            side = Side.SELL if net > 0 else Side.BUY
            price = self.slip_model.apply(candle.close, side)
            tmp = Order(symbol=cfg.symbol, side=side, type=OrderType.MARKET,
                        qty=abs(net), id="flatten", reduce_only=True,
                        created_bar=idx, status=OrderStatus.OPEN)
            _execute(tmp, price, Liquidity.TAKER, candle, idx, "flatten")

        def record_equity(candle: Candle) -> None:
            net = ledger.net_qty
            if cfg.market_type is MarketType.SPOT:
                base_cash = ledger.cash
                equity_high.append(base_cash + max(net, 0.0) * candle.high)
                equity_low.append(base_cash + max(net, 0.0) * candle.low)
            else:
                equity_high.append(ledger.cash + ledger.unrealized_pnl(candle.high))
                equity_low.append(ledger.cash + ledger.unrealized_pnl(candle.low))
            timestamps.append(candle.timestamp)
            eq = ledger.equity(candle.close)
            equity_curve.append(eq)
            closes.append(candle.close)
            # Fraction of equity currently deployed in the asset (capital usage).
            if cfg.market_type is MarketType.SPOT:
                invested = max(net, 0.0) * candle.close
            else:
                invested = abs(net) * candle.close
            invested_curve.append(invested / eq if eq > 0 else 0.0)

        # -- bootstrap inventory -------------------------------------------

        if n and cfg.bootstrap.base_fraction > 0:
            c0 = candles[0]
            spend = cfg.bootstrap.base_fraction * cfg.initial_cash
            qty = spend / c0.open if c0.open > 0 else 0.0
            if self.quantizer.enabled:
                qty = self.quantizer.quantize_qty(qty)   # respect exchange lot size
            if qty > 0:
                side = Side.BUY if cfg.bootstrap.side.name == "LONG" else Side.SELL
                price = self.slip_model.apply(c0.open, side)
                fee = self.fee_model.fee(price * qty, Liquidity.TAKER)
                boot = Fill(order_id="bootstrap", symbol=cfg.symbol, side=side,
                            price=price, qty=qty, fee=fee, liquidity=Liquidity.TAKER,
                            timestamp=c0.timestamp, bar_index=0, reason="bootstrap")
                ledger.apply_fill(boot, bar_index=0)
                fills_log.append(boot)

        # -- on_start (seed orders) ----------------------------------------

        if n:
            ctx0 = StrategyContext(candles[0], make_account(candles[0], 0),
                                   tuple(open_orders.values()), (), 0)
            apply_actions(strategy.on_start(ctx0), candles[0], 0, created_bar=-1)

        # -- main loop ------------------------------------------------------

        for idx, candle in enumerate(candles):
            bar_fills_start = len(fills_log)

            if conservative:
                match_resting(candle, idx)
                check_liquidation(candle, idx)
                fills_this_bar = tuple(fills_log[bar_fills_start:])
                ctx = StrategyContext(candle, make_account(candle, idx),
                                      tuple(open_orders.values()), fills_this_bar, idx)
                apply_actions(strategy.on_bar(ctx), candle, idx, created_bar=idx)
            else:  # optimistic same-bar
                ctx = StrategyContext(candle, make_account(candle, idx),
                                      tuple(open_orders.values()), (), idx)
                apply_actions(strategy.on_bar(ctx), candle, idx, created_bar=idx - 1)
                match_resting(candle, idx)
                check_liquidation(candle, idx)

            record_equity(candle)

        # -- on_finish (optional flatten) ----------------------------------

        if n:
            last = candles[-1]
            ctx_end = StrategyContext(last, make_account(last, n - 1),
                                      tuple(open_orders.values()), (), n - 1)
            apply_actions(strategy.on_finish(ctx_end), last, n - 1, created_bar=n - 1)
            if equity_curve:
                equity_curve[-1] = ledger.equity(last.close)

        periods = cfg.periods_per_year or _infer_periods_per_year(timestamps)
        final_equity = equity_curve[-1] if equity_curve else cfg.initial_cash

        return EngineResult(
            config=cfg, symbol=cfg.symbol, timestamps=timestamps,
            equity=equity_curve, equity_high=equity_high, equity_low=equity_low,
            close=closes, invested_frac=invested_curve,
            closed_trades=ledger.closed_trades, fills=fills_log,
            events=events, rejections=rejections, initial_cash=cfg.initial_cash,
            final_equity=final_equity, fees_paid=ledger.fees_paid,
            realized_pnl=ledger.realized_pnl, periods_per_year=periods,
            bars=n, liquidated=liquidated,
        )


def _hits_high_leg(order: Order) -> bool:
    """True if the order is resolved on the upward leg of the bar.

    Sell limits and buy stops trigger as price rises (upward leg); buy limits
    and sell stops trigger as price falls (downward leg).
    """
    if order.type is OrderType.LIMIT:
        return order.side is Side.SELL
    if order.type in (OrderType.STOP, OrderType.STOP_LIMIT):
        return order.side is Side.BUY
    return False


def _infer_periods_per_year(timestamps: list[datetime]) -> float:
    if len(timestamps) < 2:
        return 365.0
    secs = [
        (timestamps[i + 1] - timestamps[i]).total_seconds()
        for i in range(len(timestamps) - 1)
    ]
    secs = [s for s in secs if s > 0]
    if not secs:
        return 365.0
    secs.sort()
    median = secs[len(secs) // 2]
    year_seconds = 365.0 * 24 * 3600
    return year_seconds / median
