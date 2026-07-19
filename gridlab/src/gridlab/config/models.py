"""Frozen configuration objects describing market microstructure and risk.

All configs are immutable (frozen dataclasses) so a run's parameters cannot be
mutated mid-backtest, and so they hash/serialize cleanly for caching and for
the research layer (grid search / walk-forward).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gridlab.core.enums import FillMode, MarketType, PositionSide


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FeeConfig:
    """Maker/taker fees as fractions (e.g. 0.001 == 0.10%).

    Limit orders that rest and get filled are charged the maker fee; market and
    triggered stop orders are charged the taker fee. This is the single biggest
    correctness gap fixed relative to a flat-fee model.
    """
    maker: float = 0.0002
    taker: float = 0.0005

    def __post_init__(self) -> None:
        if self.maker < 0 or self.taker < 0:
            raise ValueError("fees must be non-negative")


# ---------------------------------------------------------------------------
# Slippage / spread
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SlippageConfig:
    """Slippage applied to *market* and *triggered stop* fills only.

    Resting limit orders fill at their limit price (no slippage) — that's the
    whole point of a limit order. `spread_frac` models half the bid/ask spread;
    `impact_frac` models size-independent market-impact slippage. Both are
    fractions of price and are applied adversely (buy higher, sell lower).
    """
    spread_frac: float = 0.0
    impact_frac: float = 0.0005

    def __post_init__(self) -> None:
        if self.spread_frac < 0 or self.impact_frac < 0:
            raise ValueError("slippage components must be non-negative")


# ---------------------------------------------------------------------------
# Fill model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FillConfig:
    """How intrabar fills are resolved.

    OPTIMISTIC: an order is eligible the same bar it is placed and fills if the
        bar's range touches its price. Fast, but optimistic — documented bias.
    CONSERVATIVE: an order becomes eligible only on the bar AFTER it was placed,
        and within a bar the engine processes the adverse leg first (sells then
        buys for a falling bar, etc.). Removes the worst of the lookahead bias.

    `fill_on_touch` controls whether price == level counts as a fill (True) or
    strict penetration is required (False).
    """
    mode: FillMode = FillMode.CONSERVATIVE
    fill_on_touch: bool = True
    # If a bar gaps through a limit price, fill at the (better) open price
    # rather than the limit price. Realistic for gap opens.
    fill_gaps_at_open: bool = True
    # Partial fills: cap the base qty filled per bar per order at this fraction
    # of the bar's volume. None = unlimited (always full fill). This is a coarse
    # but useful liquidity model for thinly traded markets.
    participation: Optional[float] = None

    def __post_init__(self) -> None:
        if self.participation is not None and self.participation <= 0:
            raise ValueError("participation must be > 0 or None")


# ---------------------------------------------------------------------------
# Exchange trading rules (symbol filters)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExchangeRulesConfig:
    """Exchange symbol filters: price/qty rounding and minimum order size.

    Real venues (Binance spot, Interactive Brokers) reject orders that violate
    a symbol's tick size (price increment), step/lot size (qty increment),
    minimum quantity, or minimum notional. A grid backtest that ignores these
    silently models orders the exchange would never accept — making the result
    untradeable. When ``enabled`` the engine rounds every order's price to
    ``tick_size`` and floors its quantity to ``step_size`` before risk checks,
    then drops the order if it falls below ``min_qty`` / ``min_notional``.

    All values are in the symbol's own units. ``tick_size``/``step_size`` of 0
    mean "no rounding on that axis". Defaults are off so existing runs are
    unchanged; use :func:`gridlab.execution.exchange_rules.preset` for venues.
    """
    enabled: bool = False
    tick_size: float = 0.0       # price increment (e.g. 0.01 USDT)
    step_size: float = 0.0       # base-qty increment / lot size (e.g. 0.00001 BTC)
    min_qty: float = 0.0         # minimum base quantity per order
    min_notional: float = 0.0    # minimum quote notional per order

    def __post_init__(self) -> None:
        for name in ("tick_size", "step_size", "min_qty", "min_notional"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


# ---------------------------------------------------------------------------
# Margin / leverage / liquidation (futures)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MarginConfig:
    """Leverage and liquidation settings. Ignored for SPOT markets."""
    leverage: float = 1.0
    maintenance_margin_frac: float = 0.005   # 0.5% maintenance margin
    liquidation_fee_frac: float = 0.0        # extra fee on forced liquidation
    allow_short: bool = False

    def __post_init__(self) -> None:
        if self.leverage < 1.0:
            raise ValueError("leverage must be >= 1.0")
        if not 0 <= self.maintenance_margin_frac < 1:
            raise ValueError("maintenance_margin_frac must be in [0, 1)")


# ---------------------------------------------------------------------------
# Bootstrap (initial inventory)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Seed initial inventory so a neutral/long grid can sell from bar 0.

    `base_fraction` of starting equity is converted to base inventory at the
    first candle's price (charged a taker fee). This inventory is registered
    with the ledger so the trade list and equity curve agree (a bug in the old
    engine where bootstrap inventory bypassed the trade builder).
    """
    base_fraction: float = 0.0     # 0.0 == start flat; 0.5 == half in base
    side: PositionSide = PositionSide.LONG

    def __post_init__(self) -> None:
        if not 0 <= self.base_fraction <= 1:
            raise ValueError("base_fraction must be in [0, 1]")


# ---------------------------------------------------------------------------
# Constraints (inventory / exposure caps)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConstraintConfig:
    """Risk caps enforced before an order is accepted."""
    max_base_inventory: Optional[float] = None     # absolute base units
    max_gross_exposure_frac: Optional[float] = None  # |notional| / equity cap
    max_open_orders: Optional[int] = None
    min_order_qty: float = 0.0
    min_notional: float = 0.0
    allow_negative_cash: bool = False


# ---------------------------------------------------------------------------
# Sizing (default order size policy when strategy doesn't override)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SizingConfig:
    """Default per-rung sizing. Strategies/policies may override per order."""
    mode: str = "fixed_quote"     # fixed_base | fixed_quote | percent_equity
    value: float = 50.0           # base units, quote units, or fraction
    # Martingale multiplier for averaging-down rungs (1.0 == off).
    martingale_factor: float = 1.0
    max_martingale_steps: int = 0   # ruin guard; 0 == unlimited disabled


# ---------------------------------------------------------------------------
# Grid geometry config
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GridConfig:
    """High-level description of the grid the GridStrategy should run."""
    levels: int = 10
    lower: Optional[float] = None    # absolute lower bound (static grid)
    upper: Optional[float] = None    # absolute upper bound (static grid)
    spacing: str = "arithmetic"      # arithmetic | geometric | atr
    direction: str = "neutral"       # neutral | long | short
    # Adaptive grids: derive range from rolling window / ATR instead of fixed bounds
    adaptive: bool = False
    lookback: int = 100
    atr_period: int = 14
    atr_mult: float = 2.0
    recenter_drift_frac: float = 0.0   # >0 enables recentre when price drifts out
    take_profit_frac: float = 0.0      # per-rung TP offset (0 == grid-paired exits)
    stop_loss_frac: float = 0.0        # global SL as fraction below/above range

    def __post_init__(self) -> None:
        if self.levels < 2:
            raise ValueError("grid needs at least 2 levels")
        if not self.adaptive and (self.lower is None or self.upper is None):
            raise ValueError("static grid requires lower and upper bounds")
        if self.lower is not None and self.upper is not None and self.lower >= self.upper:
            raise ValueError("lower must be < upper")
        if self.direction not in ("neutral", "long", "short"):
            raise ValueError("direction must be neutral|long|short")
        if self.spacing not in ("arithmetic", "geometric", "atr"):
            raise ValueError("spacing must be arithmetic|geometric|atr")
