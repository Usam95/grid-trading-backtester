"""The top-level BacktestConfig that aggregates all sub-configs."""
from __future__ import annotations

from dataclasses import dataclass, field

from gridlab.core.enums import MarketType
from gridlab.config.models import (
    FeeConfig,
    SlippageConfig,
    FillConfig,
    MarginConfig,
    BootstrapConfig,
    ConstraintConfig,
    SizingConfig,
    ExchangeRulesConfig,
)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Everything the engine needs except the strategy and the data.

    Immutable so a configuration can be reused across many runs (grid search,
    walk-forward) without risk of mutation.
    """
    symbol: str = "BTCUSDT"
    market_type: MarketType = MarketType.SPOT
    initial_cash: float = 10_000.0
    quote_currency: str = "USDT"

    fees: FeeConfig = field(default_factory=FeeConfig)
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    fill: FillConfig = field(default_factory=FillConfig)
    margin: MarginConfig = field(default_factory=MarginConfig)
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    exchange_rules: ExchangeRulesConfig = field(default_factory=ExchangeRulesConfig)

    # Annualisation factor override (periods per year). If None, inferred from
    # the median candle interval — but stored explicitly to keep metrics stable.
    periods_per_year: float | None = None

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if self.market_type is MarketType.SPOT and self.margin.leverage != 1.0:
            raise ValueError("SPOT market cannot use leverage > 1.0")
        if self.market_type is MarketType.SPOT and self.margin.allow_short:
            raise ValueError("SPOT market cannot allow shorting")
