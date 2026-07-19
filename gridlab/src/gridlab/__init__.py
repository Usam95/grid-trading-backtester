"""gridlab — a correct, fast, extensible grid-trading backtesting engine.

Public API is intentionally small and stable so a frontend/service can depend
on it:

    from gridlab import run_backtest, BacktestConfig, GridStrategy
    result = run_backtest(spec)          # JSON-serializable dict
"""

from __future__ import annotations

from gridlab._version import __version__

from gridlab.core.enums import (
    Side,
    OrderType,
    OrderStatus,
    TimeInForce,
    PositionSide,
    MarketType,
    FillMode,
)
from gridlab.core.models import Candle, Order, Fill, Position, AccountState
from gridlab.core.actions import EngineAction, ActionType
from gridlab.config.config import BacktestConfig
from gridlab.config.models import (
    FeeConfig,
    SlippageConfig,
    FillConfig,
    MarginConfig,
    BootstrapConfig,
    ConstraintConfig,
    SizingConfig,
    GridConfig,
    ExchangeRulesConfig,
)
from gridlab.engine.engine import BacktestEngine
from gridlab.strategy.base import Strategy
from gridlab.strategy.grid import GridStrategy
from gridlab.api.facade import run_backtest
from gridlab.execution.exchange_rules import (
    ExchangeQuantizer,
    preset as exchange_preset,
    available_presets,
)
from gridlab.data.loaders import (
    load_binance_klines,
    fetch_binance_klines_df,
    load_csv,
    bars_per_year,
)
from gridlab.research.robustness import robustness_report

__all__ = [
    "__version__",
    "Side",
    "OrderType",
    "OrderStatus",
    "TimeInForce",
    "PositionSide",
    "MarketType",
    "FillMode",
    "Candle",
    "Order",
    "Fill",
    "Position",
    "AccountState",
    "EngineAction",
    "ActionType",
    "BacktestConfig",
    "FeeConfig",
    "SlippageConfig",
    "FillConfig",
    "MarginConfig",
    "BootstrapConfig",
    "ConstraintConfig",
    "SizingConfig",
    "GridConfig",
    "ExchangeRulesConfig",
    "BacktestEngine",
    "Strategy",
    "GridStrategy",
    "run_backtest",
    "ExchangeQuantizer",
    "exchange_preset",
    "available_presets",
    "load_binance_klines",
    "fetch_binance_klines_df",
    "load_csv",
    "bars_per_year",
    "robustness_report",
]
