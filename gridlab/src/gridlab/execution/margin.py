"""Margin, leverage and liquidation model for futures grids.

For SPOT markets this is a no-op (leverage 1.0, no liquidation). For FUTURES,
the model computes used margin from notional/leverage and a liquidation price
for the net position from the maintenance-margin requirement. The engine checks
each bar's low/high against the liquidation price and force-closes if breached —
filling at the liquidation price plus a liquidation fee.
"""
from __future__ import annotations

from typing import Optional

from gridlab.config.models import MarginConfig
from gridlab.core.enums import PositionSide


class MarginModel:
    __slots__ = ("_cfg",)

    def __init__(self, cfg: MarginConfig) -> None:
        self._cfg = cfg

    @property
    def leverage(self) -> float:
        return self._cfg.leverage

    @property
    def allow_short(self) -> bool:
        return self._cfg.allow_short

    def initial_margin(self, notional: float) -> float:
        return abs(notional) / self._cfg.leverage

    def maintenance_margin(self, notional: float) -> float:
        return abs(notional) * self._cfg.maintenance_margin_frac

    def liquidation_price(self, side: PositionSide, entry_price: float,
                          qty: float, wallet_balance: float) -> Optional[float]:
        """Approximate isolated-margin liquidation price for a net position.

        Liquidation occurs when equity falls to the maintenance margin:
            wallet + pnl = maint_margin
        For a long: pnl = qty*(P - entry); maint = qty*P*mm
            wallet + qty*(P-entry) = qty*P*mm
            P = (qty*entry - wallet) / (qty*(1 - mm))
        For a short, signs flip:
            P = (qty*entry + wallet) / (qty*(1 + mm))
        Returns None when leverage is 1.0 and the position is fully cash-backed
        (spot-like) — i.e. no liquidation risk.
        """
        if self._cfg.leverage <= 1.0 and side is PositionSide.LONG:
            return None
        if qty <= 0:
            return None
        mm = self._cfg.maintenance_margin_frac
        if side is PositionSide.LONG:
            denom = qty * (1.0 - mm)
            if denom <= 0:
                return None
            price = (qty * entry_price - wallet_balance) / denom
            return max(0.0, price)
        else:
            denom = qty * (1.0 + mm)
            price = (qty * entry_price + wallet_balance) / denom
            return max(0.0, price)

    def liquidation_fee(self, notional: float) -> float:
        return abs(notional) * self._cfg.liquidation_fee_frac
