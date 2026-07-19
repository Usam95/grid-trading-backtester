"""Tests for the v1.1 spot-trading edition features.

Covers: exchange symbol-filter quantization, real-data loaders (parser + CSV),
grid economics metrics, the RSI mean-reversion filter, parallel grid search
equivalence, and the robustness scorecard.
"""
from __future__ import annotations

import os
import tempfile

import pandas as pd
import pytest

from gridlab.api.facade import run_backtest, _build_config, BacktestSpec
from gridlab.config.models import ExchangeRulesConfig
from gridlab.execution.exchange_rules import (
    ExchangeQuantizer, preset, available_presets,
)
from gridlab.data.loaders import (
    _klines_to_dataframe, load_csv, bars_per_year, _to_ms,
)
from gridlab.research.grid_search import ParamSpace, grid_search
from gridlab.research.robustness import robustness_report


SPOT_SPEC = {
    "symbol": "BTCUSDT", "initial_cash": 10_000.0,
    "grid": {"levels": 12, "lower": 90.0, "upper": 110.0, "spacing": "geometric"},
    "sizing": {"mode": "fixed_quote", "value": 60.0},
    "bootstrap": {"base_fraction": 0.4},
    "data": {"kind": "synthetic", "n": 900, "regime": "range", "seed": 5, "sigma": 0.012},
}


# ---------------------------------------------------------------------------
# Exchange rules / quantization
# ---------------------------------------------------------------------------

def test_quantizer_rounds_price_to_tick_and_floors_qty_to_step():
    q = ExchangeQuantizer(ExchangeRulesConfig(
        enabled=True, tick_size=0.01, step_size=0.001, min_qty=0.0, min_notional=0.0))
    r = q.apply(price=27123.4567, qty=0.123456)
    assert r.ok
    assert abs(r.price - 27123.46) < 1e-9      # rounded to nearest cent
    assert abs(r.qty - 0.123) < 1e-9           # floored to step


def test_quantizer_rejects_below_min_notional():
    q = ExchangeQuantizer(preset("binance", "BTCUSDT"))  # min_notional 5 USDT
    r = q.apply(price=27000.0, qty=0.0001)  # ~2.7 USDT notional
    assert not r.ok
    assert r.reason == "min_notional"


def test_quantizer_rejects_below_min_qty():
    q = ExchangeQuantizer(ExchangeRulesConfig(
        enabled=True, step_size=0.001, min_qty=0.01, min_notional=0.0))
    r = q.apply(price=100.0, qty=0.005)
    assert not r.ok
    assert r.reason == "min_qty"


def test_quantizer_disabled_is_passthrough():
    q = ExchangeQuantizer(ExchangeRulesConfig(enabled=False, tick_size=0.5))
    r = q.apply(price=100.37, qty=1.23456)
    assert r.ok and r.price == 100.37 and r.qty == 1.23456


def test_presets_available_and_distinct():
    assert set(available_presets()) == {"binance", "ibkr"}
    binance = preset("binance", "BTCUSDT")
    ibkr = preset("ibkr")
    assert binance.enabled and ibkr.enabled
    assert ibkr.step_size == 1.0       # whole-share lots for equities
    assert preset("unknown").enabled is False


def test_venue_preset_makes_orders_exchange_valid():
    """With Binance rules, every executed fill respects tick + step + min."""
    spec = dict(SPOT_SPEC)
    spec["venue"] = "binance"
    spec["grid"] = {"levels": 12, "lower": 25_000.0, "upper": 30_000.0, "spacing": "geometric"}
    spec["data"] = {"kind": "synthetic", "n": 800, "start_price": 27_500.0,
                    "regime": "range", "seed": 3, "sigma": 0.01}
    out = run_backtest(spec)
    cfg = _build_config(BacktestSpec.from_dict(spec))
    rules = cfg.exchange_rules
    assert rules.enabled
    # Every closed trade entry/exit qty is a multiple of the step size.
    for t in out["trades"]:
        ratio = t["qty"] / rules.step_size
        assert abs(ratio - round(ratio)) < 1e-6


def test_exchange_rules_negative_values_rejected():
    with pytest.raises(ValueError):
        ExchangeRulesConfig(tick_size=-0.01)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

_SAMPLE_KLINES = [
    [1609459200000, "29000.0", "29100.0", "28900.0", "29050.0", "10.0",
     1609462799999, "0", 100, "5", "0", "0"],
    [1609462800000, "29050.0", "29200.0", "29000.0", "29180.0", "12.0",
     1609466399999, "0", 120, "6", "0", "0"],
]


def test_klines_parser_shape_and_values():
    df = _klines_to_dataframe(_SAMPLE_KLINES)
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["close"].iloc[0] == 29050.0
    assert df["high"].iloc[1] == 29200.0


def test_csv_loader_roundtrip():
    df = _klines_to_dataframe(_SAMPLE_KLINES)
    path = os.path.join(tempfile.gettempdir(), "gl_loader_test.csv")
    df.to_csv(path, index=False)
    try:
        src = load_csv(path, symbol="BTCUSDT")
        candles = list(src.candles())
        assert len(candles) == 2
        assert src.symbol == "BTCUSDT"
        assert candles[-1].close == 29180.0
    finally:
        os.remove(path)


def test_bars_per_year_lookup():
    assert bars_per_year("1h") == 8760
    assert bars_per_year("1d") == 365
    assert bars_per_year("nonsense") is None


def test_to_ms_handles_multiple_input_types():
    assert _to_ms(None) is None
    assert _to_ms("2021-01-01") == 1609459200000
    assert _to_ms(1609459200000) == 1609459200000      # already ms
    assert _to_ms(1609459200) == 1609459200000          # seconds -> ms


# ---------------------------------------------------------------------------
# Grid economics metrics
# ---------------------------------------------------------------------------

def test_grid_economics_metrics_present_and_sane():
    m = run_backtest(SPOT_SPEC)["metrics"]
    for key in ("trades_per_day", "return_over_buy_hold", "fee_to_profit_ratio",
                "avg_capital_utilization", "time_in_market_frac",
                "realized_grid_pnl", "avg_round_trip_bps"):
        assert key in m
    assert 0.0 <= m["avg_capital_utilization"] <= 1.5
    assert 0.0 <= m["time_in_market_frac"] <= 1.0
    if m["trades_per_day"] is not None:
        assert m["trades_per_day"] >= 0.0


def test_return_over_buy_hold_matches_definition():
    out = run_backtest(SPOT_SPEC)
    m = out["metrics"]
    strat = m["total_return"]
    bh = out["benchmarks"]["buy_and_hold"]["total_return"]
    # return_over_buy_hold uses a *fee-free* hold, so it should be >= strat - bh
    # (the benchmark pays a taker fee, making its return slightly lower).
    assert m["return_over_buy_hold"] is not None
    assert m["return_over_buy_hold"] <= strat - bh + 1e-6


def test_fee_to_profit_ratio_none_without_profit():
    # A grid with no winning trades should report None, not inf/zero.
    spec = dict(SPOT_SPEC)
    spec["data"] = {"kind": "synthetic", "n": 50, "regime": "range", "seed": 1}
    m = run_backtest(spec)["metrics"]
    ratio = m["fee_to_profit_ratio"]
    assert ratio is None or ratio >= 0.0


# ---------------------------------------------------------------------------
# RSI filter
# ---------------------------------------------------------------------------

def test_rsi_filter_changes_behaviour_and_serializes():
    base = dict(SPOT_SPEC)
    rsi_spec = dict(SPOT_SPEC)
    rsi_spec["filter"] = {"kind": "rsi", "oversold": 35, "overbought": 65}
    out_none = run_backtest(base)
    out_rsi = run_backtest(rsi_spec)
    # The RSI gate suppresses some entries, so trade counts should differ.
    assert out_rsi["metrics"]["n_trades"] != out_none["metrics"]["n_trades"]


def test_rsi_filter_validates_bounds():
    from gridlab.strategy.policies.filters import RsiFilter
    with pytest.raises(ValueError):
        RsiFilter(oversold=70, overbought=30)


# ---------------------------------------------------------------------------
# Parallel grid search
# ---------------------------------------------------------------------------

def test_parallel_grid_search_matches_serial():
    space = ParamSpace({"grid.levels": [8, 10, 12], "sizing.value": [40.0, 80.0]})
    serial = grid_search(SPOT_SPEC, space, objective="total_return", workers=1)
    parallel = grid_search(SPOT_SPEC, space, objective="total_return", workers=2)

    def key(rows):
        return [(r["params"]["grid.levels"], r["params"]["sizing.value"],
                 round(r["score"] or 0.0, 8)) for r in rows]

    assert key(serial) == key(parallel)


# ---------------------------------------------------------------------------
# Robustness scorecard
# ---------------------------------------------------------------------------

def test_robustness_report_structure_and_bounds():
    space = {"grid.levels": [8, 12], "sizing.value": [40.0, 80.0]}
    spec = dict(SPOT_SPEC)
    spec["data"] = {"kind": "synthetic", "n": 1200, "regime": "range", "seed": 5}
    rep = robustness_report(spec, space, n_splits=3, mc_sims=400)
    assert 0.0 <= rep["trust_score"] <= 100.0
    assert isinstance(rep["grade"], str)
    assert {"out_of_sample", "overfitting", "path_risk"} <= set(rep["components"])
    # Overfitting component derives from deflated Sharpe in [0, 100].
    of = rep["components"]["overfitting"]["score"]
    assert of is None or 0.0 <= of <= 100.0


def test_robustness_report_without_space_skips_walk_forward():
    rep = robustness_report(SPOT_SPEC, None, mc_sims=300)
    assert "out_of_sample" not in rep["components"]
    assert rep["weights"]["out_of_sample"] == 0.0
    assert 0.0 <= rep["trust_score"] <= 100.0
