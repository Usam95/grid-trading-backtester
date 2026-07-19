"""Pydantic request/response schemas for the studio API.

Every nested config block mirrors a gridlab config object but keeps all fields
optional. We dump with ``exclude_none=True`` before handing the dict to gridlab,
so the engine remains the single source of default values and validation — the
API never silently disagrees with the engine about what a default is.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Block(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GridSpec(_Block):
    levels: Optional[int] = Field(default=None, ge=2, le=500)
    lower: Optional[float] = None
    upper: Optional[float] = None
    spacing: Optional[Literal["arithmetic", "geometric", "atr"]] = None
    direction: Optional[Literal["neutral", "long", "short"]] = None
    adaptive: Optional[bool] = None
    lookback: Optional[int] = Field(default=None, ge=2)
    atr_period: Optional[int] = Field(default=None, ge=2)
    atr_mult: Optional[float] = Field(default=None, gt=0)
    recenter_drift_frac: Optional[float] = Field(default=None, ge=0)
    take_profit_frac: Optional[float] = Field(default=None, ge=0)
    stop_loss_frac: Optional[float] = Field(default=None, ge=0)


class SizingSpec(_Block):
    mode: Optional[Literal["fixed_quote", "fixed_base", "percent_equity", "martingale"]] = None
    value: Optional[float] = Field(default=None, gt=0)
    martingale_factor: Optional[float] = Field(default=None, ge=1)
    max_martingale_steps: Optional[int] = Field(default=None, ge=0)


class FeesSpec(_Block):
    maker: Optional[float] = Field(default=None, ge=0, le=0.05)
    taker: Optional[float] = Field(default=None, ge=0, le=0.05)


class SlippageSpec(_Block):
    spread_frac: Optional[float] = Field(default=None, ge=0, le=0.1)
    impact_frac: Optional[float] = Field(default=None, ge=0, le=0.1)


class FillSpec(_Block):
    mode: Optional[Literal["optimistic", "conservative"]] = None
    fill_on_touch: Optional[bool] = None
    fill_gaps_at_open: Optional[bool] = None
    participation: Optional[float] = Field(default=None, gt=0)


class MarginSpec(_Block):
    leverage: Optional[float] = Field(default=None, ge=1)
    maintenance_margin_frac: Optional[float] = Field(default=None, ge=0, lt=1)
    liquidation_fee_frac: Optional[float] = Field(default=None, ge=0)
    allow_short: Optional[bool] = None


class BootstrapSpec(_Block):
    base_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    side: Optional[Literal["LONG", "SHORT"]] = None


class ConstraintsSpec(_Block):
    max_base_inventory: Optional[float] = Field(default=None, ge=0)
    max_gross_exposure_frac: Optional[float] = Field(default=None, ge=0)
    max_open_orders: Optional[int] = Field(default=None, ge=1)
    min_order_qty: Optional[float] = Field(default=None, ge=0)
    min_notional: Optional[float] = Field(default=None, ge=0)


class DataSpec(_Block):
    kind: Optional[Literal["synthetic", "dataframe", "binance", "csv"]] = None
    # synthetic
    n: Optional[int] = Field(default=None, ge=50, le=200_000)
    start_price: Optional[float] = Field(default=None, gt=0)
    seed: Optional[int] = None
    sigma: Optional[float] = Field(default=None, gt=0, le=1)
    regime: Optional[Literal["range", "trend", "random"]] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1)
    records: Optional[list[dict[str, Any]]] = None
    # real data (binance / csv)
    symbol: Optional[str] = None
    interval: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    max_candles: Optional[int] = Field(default=None, ge=50, le=200_000)
    path: Optional[str] = None


class ExchangeRulesSpec(_Block):
    enabled: Optional[bool] = None
    tick_size: Optional[float] = Field(default=None, ge=0)
    step_size: Optional[float] = Field(default=None, ge=0)
    min_qty: Optional[float] = Field(default=None, ge=0)
    min_notional: Optional[float] = Field(default=None, ge=0)


class FilterSpec(_Block):
    kind: Optional[Literal["none", "trend", "regime", "rsi"]] = None
    adx_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    oversold: Optional[float] = Field(default=None, ge=0, le=100)
    overbought: Optional[float] = Field(default=None, ge=0, le=100)


class BacktestRequest(_Block):
    """A full declarative backtest spec accepted by the API."""
    symbol: str = "BTCUSDT"
    market_type: Literal["spot", "futures"] = "spot"
    venue: Optional[str] = None        # "binance" | "ibkr" cost+filter preset
    initial_cash: float = Field(default=10_000.0, gt=0)
    grid: GridSpec = Field(default_factory=GridSpec)
    sizing: SizingSpec = Field(default_factory=SizingSpec)
    fees: FeesSpec = Field(default_factory=FeesSpec)
    slippage: SlippageSpec = Field(default_factory=SlippageSpec)
    fill: FillSpec = Field(default_factory=FillSpec)
    margin: MarginSpec = Field(default_factory=MarginSpec)
    bootstrap: BootstrapSpec = Field(default_factory=BootstrapSpec)
    constraints: ConstraintsSpec = Field(default_factory=ConstraintsSpec)
    exchange_rules: ExchangeRulesSpec = Field(default_factory=ExchangeRulesSpec)
    data: DataSpec = Field(default_factory=DataSpec)
    filter: FilterSpec = Field(default_factory=FilterSpec)
    n_trials: int = Field(default=1, ge=1)
    periods_per_year: Optional[float] = None

    def to_spec(self) -> dict:
        """Collapse to the plain dict gridlab's facade expects (no None leaves)."""
        raw = self.model_dump(exclude_none=True)
        # Drop empty nested blocks so gridlab falls back to its own defaults.
        return {k: v for k, v in raw.items() if not (isinstance(v, dict) and not v)}


class BacktestOptions(_Block):
    with_report: bool = False
    include_trades: bool = True


class RunBacktestBody(_Block):
    spec: BacktestRequest = Field(default_factory=BacktestRequest)
    options: BacktestOptions = Field(default_factory=BacktestOptions)


class GridPreviewBody(_Block):
    """Lightweight request to compute grid rung prices for the live preview."""
    spec: BacktestRequest = Field(default_factory=BacktestRequest)


class GridSearchBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    objective: str = "deflated_sharpe"
    maximize: bool = True
    top_k: Optional[int] = Field(default=None, ge=1)


class WalkForwardBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    n_splits: int = Field(default=4, ge=2, le=20)
    objective: str = "deflated_sharpe"


class MonteCarloBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    method: Literal["trades", "returns"] = "trades"
    n_sims: int = Field(default=2000, ge=100, le=20000)
    seed: int = 0


class RobustnessBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    n_splits: int = Field(default=3, ge=2, le=12)
    mc_sims: int = Field(default=800, ge=100, le=10000)
