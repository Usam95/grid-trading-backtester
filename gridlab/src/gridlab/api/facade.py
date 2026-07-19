"""Stable, JSON-friendly facade.

This is the single entry point a frontend, REST service, or CLI should call.
`run_backtest(spec)` accepts a plain dict (or `BacktestSpec`) describing the
market, costs, risk, grid and data, and returns a JSON-serializable dict of
metrics, benchmarks, a (downsampled) equity curve, and trades. Nothing in the
return value is a custom object, so it serializes with `json.dumps` directly.

Keeping this layer thin and declarative means the engine internals can evolve
without breaking the contract the UI depends on.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import numpy as np
import pandas as pd

from gridlab.config.config import BacktestConfig
from gridlab.config.models import (
    BootstrapConfig, ConstraintConfig, FeeConfig, FillConfig, GridConfig,
    MarginConfig, SizingConfig, SlippageConfig, ExchangeRulesConfig,
)
from gridlab.core.enums import FillMode, MarketType, PositionSide
from gridlab.data.source import DataSource, InMemoryDataSource, from_dataframe, synthetic
from gridlab.engine.engine import BacktestEngine, EngineResult
from gridlab.execution.exchange_rules import preset as exchange_preset
from gridlab.indicators.indicators import atr, ema, adx, rsi
from gridlab.results.benchmarks import buy_and_hold, dca_benchmark
from gridlab.results.metrics import compute_metrics
from gridlab.results.report import render_html_report
from gridlab.strategy.grid import GridStrategy
from gridlab.strategy.policies.filters import NoFilter, RegimeFilter, TrendFilter, RsiFilter
from gridlab.strategy.policies.sizing import (
    FixedBaseSizing, FixedQuoteSizing, MartingaleSizing, PercentEquitySizing,
)


# --------------------------------------------------------------------------
# Spec
# --------------------------------------------------------------------------

@dataclass(slots=True)
class BacktestSpec:
    """Declarative description of a run. All nested config is plain dicts."""
    symbol: str = "BTCUSDT"
    market_type: str = "spot"          # spot | futures
    initial_cash: float = 10_000.0
    grid: dict = field(default_factory=dict)
    sizing: dict = field(default_factory=dict)
    fees: dict = field(default_factory=dict)
    slippage: dict = field(default_factory=dict)
    fill: dict = field(default_factory=dict)
    margin: dict = field(default_factory=dict)
    bootstrap: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    exchange_rules: dict = field(default_factory=dict)  # tick/step/min_qty/min_notional
    venue: str = ""                                     # "binance" | "ibkr" preset shortcut
    data: dict = field(default_factory=dict)   # {"kind":"synthetic"/"dataframe", ...}
    filter: dict = field(default_factory=dict)  # {"kind":"trend"/"regime"/"none"}
    n_trials: int = 1
    periods_per_year: Optional[float] = None

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestSpec":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------

def _build_exchange_rules(spec: BacktestSpec) -> ExchangeRulesConfig:
    """Resolve exchange symbol filters from an explicit dict or a venue preset.

    An explicit ``exchange_rules`` dict always wins. Otherwise a ``venue``
    shortcut (``"binance"``/``"ibkr"``) loads realistic per-symbol filters.
    """
    if spec.exchange_rules:
        return ExchangeRulesConfig(**spec.exchange_rules)
    if spec.venue:
        return exchange_preset(spec.venue, spec.symbol)
    return ExchangeRulesConfig()


def _build_config(spec: BacktestSpec) -> BacktestConfig:
    market = MarketType.FUTURES if spec.market_type.lower() == "futures" else MarketType.SPOT
    fill = dict(spec.fill)
    if "mode" in fill and isinstance(fill["mode"], str):
        fill["mode"] = FillMode(fill["mode"])
    boot = dict(spec.bootstrap)
    if "side" in boot and isinstance(boot["side"], str):
        boot["side"] = PositionSide[boot["side"].upper()]
    return BacktestConfig(
        symbol=spec.symbol, market_type=market, initial_cash=spec.initial_cash,
        fees=FeeConfig(**spec.fees), slippage=SlippageConfig(**spec.slippage),
        fill=FillConfig(**fill), margin=MarginConfig(**spec.margin),
        bootstrap=BootstrapConfig(**boot), constraints=ConstraintConfig(**spec.constraints),
        sizing=SizingConfig(**spec.sizing), exchange_rules=_build_exchange_rules(spec),
        periods_per_year=spec.periods_per_year,
    )


def _build_sizing(spec: BacktestSpec):
    s = spec.sizing or {}
    mode = s.get("mode", "fixed_quote")
    value = s.get("value", 50.0)
    if mode == "fixed_base":
        return FixedBaseSizing(value)
    if mode == "percent_equity":
        return PercentEquitySizing(value)
    if mode == "martingale":
        return MartingaleSizing(value, s.get("martingale_factor", 1.5),
                                s.get("max_martingale_steps", 5))
    return FixedQuoteSizing(value)


def _build_filter(spec: BacktestSpec):
    f = spec.filter or {}
    kind = f.get("kind", "none")
    if kind == "trend":
        return TrendFilter()
    if kind == "regime":
        return RegimeFilter(f.get("adx_threshold", 30.0))
    if kind == "rsi":
        oversold = f.get("oversold", f.get("lower", 35.0))
        overbought = f.get("overbought", f.get("upper", 65.0))
        return RsiFilter(oversold, overbought)
    return NoFilter()


def _build_strategy(spec: BacktestSpec) -> GridStrategy:
    gc = GridConfig(**spec.grid)
    return GridStrategy.from_config(gc, _build_sizing(spec), filter_policy=_build_filter(spec))


def _build_data(spec: BacktestSpec) -> DataSource:
    d = spec.data or {}
    kind = d.get("kind", "synthetic")
    if kind == "dataframe":
        df = d["df"] if isinstance(d.get("df"), pd.DataFrame) else pd.DataFrame(d["records"])
        return from_dataframe(df, symbol=spec.symbol)
    if kind == "binance":
        from gridlab.data.loaders import load_binance_klines
        return load_binance_klines(
            symbol=d.get("symbol", spec.symbol), interval=d.get("interval", "1h"),
            start=d.get("start"), end=d.get("end"), cache_dir=d.get("cache_dir"),
            use_cache=d.get("use_cache", True), max_candles=d.get("max_candles", 50_000),
        )
    if kind == "csv":
        from gridlab.data.loaders import load_csv
        return load_csv(d["path"], symbol=spec.symbol)
    # synthetic default
    return synthetic(
        n=d.get("n", 1500), start_price=d.get("start_price", 100.0),
        seed=d.get("seed", 7), sigma=d.get("sigma", 0.012),
        regime=d.get("regime", "range"), symbol=spec.symbol,
        interval_minutes=d.get("interval_minutes", 60),
    )


def _enrich_indicators(data: DataSource, gc: GridConfig) -> DataSource:
    """Attach ATR/EMA/ADX/rolling extremes to candles for adaptive policies."""
    if not isinstance(data, InMemoryDataSource):
        data = InMemoryDataSource(symbol=getattr(data, "symbol", "SYMBOL"),
                                  _candles=list(data.candles()))
    candles = data.as_list()
    if not candles:
        return data
    df = pd.DataFrame({
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
    })
    atr_s = atr(df["high"], df["low"], df["close"], gc.atr_period)
    ema_s = ema(df["close"], max(2, gc.lookback))
    adx_s = adx(df["high"], df["low"], df["close"], gc.atr_period)
    rsi_s = rsi(df["close"], gc.atr_period)
    roll_lo = df["close"].rolling(gc.lookback, min_periods=1).min()
    roll_hi = df["close"].rolling(gc.lookback, min_periods=1).max()
    for i, c in enumerate(candles):
        c.extra["atr"] = float(atr_s.iloc[i])
        c.extra["center"] = float(ema_s.iloc[i])
        c.extra["trend_ema"] = float(ema_s.iloc[i])
        c.extra["adx"] = float(adx_s.iloc[i])
        c.extra["rsi"] = float(rsi_s.iloc[i])
        c.extra["roll_low"] = float(roll_lo.iloc[i])
        c.extra["roll_high"] = float(roll_hi.iloc[i])
    return data


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------

def _downsample(values: list[float], max_points: int = 500) -> list[float]:
    n = len(values)
    if n <= max_points:
        return [float(v) for v in values]
    idx = np.linspace(0, n - 1, max_points).astype(int)
    return [float(values[i]) for i in idx]


def _trades_to_dicts(trades, limit: int = 1000) -> list[dict]:
    out = []
    for t in trades[:limit]:
        out.append({
            "side": t.side.value, "qty": t.qty, "entry_price": t.entry_price,
            "exit_price": t.exit_price, "pnl": t.pnl, "gross_pnl": t.gross_pnl,
            "return_pct": t.return_pct, "bars_held": t.bars_held,
            "opened_at": t.opened_at.isoformat(), "closed_at": t.closed_at.isoformat(),
            "exit_reason": t.exit_reason,
        })
    return out


def result_to_dict(result: EngineResult, metrics: dict, benchmarks: dict,
                   *, include_trades: bool = True) -> dict:
    return {
        "symbol": result.symbol,
        "bars": result.bars,
        "start": result.timestamps[0].isoformat() if result.timestamps else None,
        "end": result.timestamps[-1].isoformat() if result.timestamps else None,
        "metrics": metrics,
        "benchmarks": benchmarks,
        "equity_curve": _downsample(result.equity),
        "price_curve": _downsample(result.close),
        "rejections": result.rejections,
        "trades": _trades_to_dicts(result.closed_trades) if include_trades else [],
        "liquidated": result.liquidated,
    }


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def run_backtest(spec: dict | BacktestSpec, *, with_report: bool = False,
                 include_trades: bool = True) -> dict:
    """Run a single backtest from a declarative spec. Returns a JSON-ready dict."""
    if isinstance(spec, dict):
        spec = BacktestSpec.from_dict(spec)

    config = _build_config(spec)
    gc = GridConfig(**spec.grid)
    data = _build_data(spec)
    if gc.adaptive or (spec.filter or {}).get("kind") in ("trend", "regime", "rsi"):
        data = _enrich_indicators(data, gc)

    strategy = _build_strategy(spec)
    engine = BacktestEngine(config)
    result = engine.run(data, strategy)

    metrics = compute_metrics(result, n_trials=spec.n_trials)
    benchmarks = {
        "buy_and_hold": buy_and_hold(result.close, config.initial_cash, config.fees.taker),
        "dca": dca_benchmark(result.close, config.initial_cash, fee=config.fees.taker),
    }
    out = result_to_dict(result, metrics, benchmarks, include_trades=include_trades)

    if with_report:
        out["html_report"] = render_html_report(
            result, metrics, benchmarks=benchmarks,
            config_summary=_config_summary(spec, config))
    return out


def _config_summary(spec: BacktestSpec, config: BacktestConfig) -> dict:
    return {
        "symbol": config.symbol,
        "market_type": config.market_type.value,
        "initial_cash": config.initial_cash,
        "fill_mode": config.fill.mode.value,
        "maker_fee": config.fees.maker,
        "taker_fee": config.fees.taker,
        "leverage": config.margin.leverage,
        "grid": spec.grid,
        "sizing": spec.sizing,
    }
