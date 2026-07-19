"""Exchange symbol-filter enforcement (tick size, lot size, minimums).

This is the bridge between a clean backtest and an order a real venue will
actually accept. The :class:`ExchangeQuantizer` rounds prices to the symbol's
tick size and floors quantities to its step (lot) size, then reports whether
the rounded order still clears the venue's minimum quantity and notional. The
engine applies this *before* risk checks, so the equity curve only contains
fills that Binance / Interactive Brokers would have permitted.

``preset(name)`` returns realistic filters for common spot symbols so users can
opt in with one line instead of hand-entering exchange metadata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gridlab.config.models import ExchangeRulesConfig


def _floor_to_increment(value: float, increment: float) -> float:
    """Floor ``value`` to the nearest lower multiple of ``increment``."""
    if increment <= 0:
        return value
    # Work in integer multiples to avoid binary-float drift (e.g. 0.1 steps).
    n = math.floor(value / increment + 1e-9)
    return n * increment


def _round_to_increment(value: float, increment: float) -> float:
    """Round ``value`` to the nearest multiple of ``increment``."""
    if increment <= 0:
        return value
    n = math.floor(value / increment + 0.5)
    return n * increment


@dataclass(frozen=True, slots=True)
class QuantizedOrder:
    """Result of applying symbol filters to a candidate order."""

    price: float
    qty: float
    ok: bool
    reason: str = "ok"  # ok | min_qty | min_notional | zero_qty


class ExchangeQuantizer:
    """Applies a symbol's trading rules to candidate order price/qty."""

    __slots__ = ("_cfg",)

    def __init__(self, cfg: ExchangeRulesConfig) -> None:
        self._cfg = cfg

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def quantize_price(self, price: float) -> float:
        return _round_to_increment(price, self._cfg.tick_size)

    def quantize_qty(self, qty: float) -> float:
        return _floor_to_increment(qty, self._cfg.step_size)

    def apply(self, price: float, qty: float) -> QuantizedOrder:
        """Round price/qty and validate against the symbol minimums.

        ``price`` is the order's reference price (limit price, or the bar
        reference for market orders) used only for the min-notional check.
        """
        if not self._cfg.enabled:
            return QuantizedOrder(price=price, qty=qty, ok=True)

        q_price = self.quantize_price(price) if price > 0 else price
        q_qty = self.quantize_qty(qty)

        if q_qty <= 0:
            return QuantizedOrder(q_price, 0.0, ok=False, reason="zero_qty")
        if self._cfg.min_qty > 0 and q_qty + 1e-12 < self._cfg.min_qty:
            return QuantizedOrder(q_price, q_qty, ok=False, reason="min_qty")
        notional = q_qty * (q_price if q_price > 0 else price)
        if self._cfg.min_notional > 0 and notional + 1e-9 < self._cfg.min_notional:
            return QuantizedOrder(q_price, q_qty, ok=False, reason="min_notional")
        return QuantizedOrder(q_price, q_qty, ok=True)


# ---------------------------------------------------------------------------
# Venue presets
# ---------------------------------------------------------------------------
#
# Spot symbol filters approximated from public exchange metadata. They are
# realistic defaults for research, not a live source of truth — fetch the
# exchange's current filters before trading real size.


def _binance_spot_rules(symbol: str) -> ExchangeRulesConfig:
    presets = {
        "BTCUSDT": ExchangeRulesConfig(
            enabled=True, tick_size=0.01, step_size=0.00001, min_qty=0.00001, min_notional=5.0
        ),
        "ETHUSDT": ExchangeRulesConfig(
            enabled=True, tick_size=0.01, step_size=0.0001, min_qty=0.0001, min_notional=5.0
        ),
        "BNBUSDT": ExchangeRulesConfig(
            enabled=True, tick_size=0.01, step_size=0.001, min_qty=0.001, min_notional=5.0
        ),
        "SOLUSDT": ExchangeRulesConfig(
            enabled=True, tick_size=0.01, step_size=0.001, min_qty=0.001, min_notional=5.0
        ),
        "XRPUSDT": ExchangeRulesConfig(
            enabled=True, tick_size=0.0001, step_size=1.0, min_qty=1.0, min_notional=5.0
        ),
        # Generic USDT pair fallback (Binance default min_notional is 5 USDT).
        "_DEFAULT": ExchangeRulesConfig(
            enabled=True, tick_size=0.0001, step_size=0.0001, min_qty=0.0001, min_notional=5.0
        ),
    }
    return presets.get(symbol.upper(), presets["_DEFAULT"])


def preset(name: str, symbol: str = "") -> ExchangeRulesConfig:
    """Return exchange rules for a venue/symbol.

    ``name`` is one of ``"binance"`` / ``"binance_spot"`` or ``"ibkr"`` /
    ``"ibkr_stock"``. For Binance the ``symbol`` selects the per-pair filter
    (falling back to a generic USDT pair). Unknown names return a disabled
    config so callers can pass through user input safely.
    """
    key = name.strip().lower()
    if key in ("binance", "binance_spot"):
        return _binance_spot_rules(symbol)
    if key in ("ibkr", "ibkr_stock", "interactive_brokers"):
        # Penny tick above $1 and whole-share lots. Real IBKR has additional
        # sub-penny and commission rules supplied by outside adapters.
        return ExchangeRulesConfig(
            enabled=True,
            tick_size=0.01,
            step_size=1.0,
            min_qty=1.0,
            min_notional=1.0,
        )
    if key in ("", "none", "off"):
        return ExchangeRulesConfig(enabled=False)
    return ExchangeRulesConfig(enabled=False)


def available_presets() -> list[str]:
    return ["binance", "ibkr"]
