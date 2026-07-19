"""The Ledger — single source of truth for cash and positions.

This is the central correctness fix relative to the old engine, which kept two
independent FIFO ledgers (one for the equity curve, one for the trade list) that
could disagree, and which never registered bootstrap inventory with the trade
builder. Here, **one** ledger holds cash plus FIFO position lots and derives
*both* the equity curve and the closed-trade list from the same fills. Every
fill — including bootstrap inventory and forced liquidations — flows through
`apply_fill`, so the trade ledger and equity curve can never diverge.

Supports spot (long-only, cash fully debited on buy) and futures (long/short,
only fees debited on open, realized PnL credited on close).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from gridlab.core.enums import Side, PositionSide, MarketType
from gridlab.core.models import Fill, Lot, Position


@dataclass(slots=True, frozen=True)
class ClosedTrade:
    """A FIFO-matched round trip (one entry lot slice vs one exit fill slice)."""
    symbol: str
    side: PositionSide          # side of the position that was closed
    qty: float
    entry_price: float
    exit_price: float
    entry_fee: float
    exit_fee: float
    gross_pnl: float
    pnl: float                  # net of both fees
    opened_at: datetime
    closed_at: datetime
    bars_held: int
    entry_reason: str
    exit_reason: str

    @property
    def return_pct(self) -> float:
        cost = self.entry_price * self.qty
        return self.pnl / cost if cost > 0 else 0.0

    @property
    def is_win(self) -> bool:
        return self.pnl > 0.0


class Ledger:
    """Cash + FIFO position lots. Derives equity and the closed-trade list."""

    __slots__ = (
        "market_type", "symbol", "cash", "_long", "_short",
        "realized_pnl", "fees_paid", "closed_trades", "_lot_seq",
    )

    def __init__(self, initial_cash: float, market_type: MarketType, symbol: str) -> None:
        self.market_type = market_type
        self.symbol = symbol
        self.cash = float(initial_cash)
        self._long: deque[Lot] = deque()
        self._short: deque[Lot] = deque()
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.closed_trades: list[ClosedTrade] = []
        self._lot_seq = 0

    # ------------------------------------------------------------------ state

    @property
    def long_qty(self) -> float:
        return sum(lot.qty for lot in self._long)

    @property
    def short_qty(self) -> float:
        return sum(lot.qty for lot in self._short)

    @property
    def net_qty(self) -> float:
        """Signed base inventory: +long, -short."""
        return self.long_qty - self.short_qty

    @property
    def open_lot_count(self) -> int:
        return len(self._long) + len(self._short)

    def net_position(self) -> Optional[Position]:
        lq, sq = self.long_qty, self.short_qty
        if lq > sq + 1e-15:
            qty = lq - sq
            avg = self._weighted_entry(self._long)
            return Position(self.symbol, PositionSide.LONG, qty, avg,
                            self._long[0].opened_at if self._long else _epoch())
        if sq > lq + 1e-15:
            qty = sq - lq
            avg = self._weighted_entry(self._short)
            return Position(self.symbol, PositionSide.SHORT, qty, avg,
                            self._short[0].opened_at if self._short else _epoch())
        return None

    @staticmethod
    def _weighted_entry(lots: "deque[Lot]") -> float:
        tot = sum(lot.qty for lot in lots)
        if tot <= 0:
            return 0.0
        return sum(lot.entry_price * lot.qty for lot in lots) / tot

    def unrealized_pnl(self, price: float) -> float:
        upl = 0.0
        for lot in self._long:
            upl += (price - lot.entry_price) * lot.qty
        for lot in self._short:
            upl += (lot.entry_price - price) * lot.qty
        return upl

    def equity(self, price: float) -> float:
        if self.market_type is MarketType.SPOT:
            # Cash already reflects spent quote; long inventory marked to market.
            return self.cash + self.long_qty * price
        # Futures: collateral wallet plus unrealized PnL.
        return self.cash + self.unrealized_pnl(price)

    # ------------------------------------------------------------------- fills

    def apply_fill(self, fill: Fill, *, bar_index: int) -> list[ClosedTrade]:
        """Apply a fill, updating cash + lots and emitting any closed trades."""
        if fill.qty <= 0:
            return []
        per_unit_fee = fill.fee / fill.qty
        self.fees_paid += fill.fee

        if fill.side is Side.BUY:
            closing, closing_side, opening, opening_side = (
                self._short, PositionSide.SHORT, self._long, PositionSide.LONG)
        else:
            closing, closing_side, opening, opening_side = (
                self._long, PositionSide.LONG, self._short, PositionSide.SHORT)

        remaining = fill.qty
        gross_realized = 0.0
        new_trades: list[ClosedTrade] = []

        # 1) Close opposite-side lots FIFO.
        while remaining > 1e-15 and closing:
            lot = closing[0]
            m = min(remaining, lot.qty)
            entry_fee_portion = lot.entry_fee * (m / lot.qty)
            exit_fee_portion = per_unit_fee * m
            gross = closing_side.sign * (fill.price - lot.entry_price) * m
            net = gross - entry_fee_portion - exit_fee_portion
            gross_realized += gross
            self.realized_pnl += net
            trade = ClosedTrade(
                symbol=fill.symbol, side=closing_side, qty=m,
                entry_price=lot.entry_price, exit_price=fill.price,
                entry_fee=entry_fee_portion, exit_fee=exit_fee_portion,
                gross_pnl=gross, pnl=net,
                opened_at=lot.opened_at, closed_at=fill.timestamp,
                bars_held=max(0, bar_index - lot.opened_bar),
                entry_reason="lot", exit_reason=fill.reason,
            )
            self.closed_trades.append(trade)
            new_trades.append(trade)
            lot.qty -= m
            lot.entry_fee -= entry_fee_portion
            remaining -= m
            if lot.qty <= 1e-15:
                closing.popleft()

        # 2) Any remainder opens a new lot on the fill side.
        opened_qty = remaining
        if opened_qty > 1e-15:
            opening.append(Lot(
                side=opening_side,
                entry_price=fill.price,
                qty=opened_qty,
                entry_fee=per_unit_fee * opened_qty,
                opened_at=fill.timestamp,
                opened_bar=bar_index,
            ))

        # 3) Cash accounting.
        if self.market_type is MarketType.SPOT:
            if fill.side is Side.BUY:
                self.cash -= fill.price * fill.qty + fill.fee
            else:
                self.cash += fill.price * fill.qty - fill.fee
        else:
            # Futures: only fees and realized PnL move the wallet.
            self.cash += gross_realized - fill.fee

        return new_trades

    def force_flatten_fill(self, price: float, fee_rate: float, timestamp: datetime,
                           bar_index: int, reason: str) -> Optional[Fill]:
        """Build (but do not apply) a fill that closes the entire net position."""
        net = self.net_qty
        if abs(net) <= 1e-15:
            return None
        side = Side.SELL if net > 0 else Side.BUY
        qty = abs(net)
        fee = qty * price * fee_rate
        return Fill(order_id="flatten", symbol=self.symbol, side=side, price=price,
                    qty=qty, fee=fee, liquidity=_taker(), timestamp=timestamp,
                    bar_index=bar_index, reason=reason)


def _epoch() -> datetime:
    from datetime import timezone
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _taker():
    from gridlab.core.enums import Liquidity
    return Liquidity.TAKER
