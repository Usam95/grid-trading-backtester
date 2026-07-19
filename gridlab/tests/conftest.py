"""Shared fixtures and helpers for the gridlab test suite."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from gridlab.core.models import Candle
from gridlab.data.source import InMemoryDataSource, synthetic


def make_candles(closes, *, spread=0.0, start=None, interval_minutes=60):
    """Build candles from a list of closes. High/low extend by `spread` fraction."""
    t0 = start or datetime(2021, 1, 1, tzinfo=timezone.utc)
    out = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        hi = max(o, c) * (1 + spread)
        lo = min(o, c) * (1 - spread)
        out.append(Candle(timestamp=t0 + timedelta(minutes=i * interval_minutes),
                          open=o, high=hi, low=lo, close=c, volume=1000.0, index=i))
        prev = c
    return out


@pytest.fixture
def ranging_data():
    return synthetic(n=800, start_price=100.0, regime="range", seed=11, sigma=0.012)


@pytest.fixture
def trending_data():
    return synthetic(n=800, start_price=100.0, regime="trend", seed=11, sigma=0.01, mu=0.001)


def ds(candles, symbol="TEST"):
    return InMemoryDataSource(symbol=symbol, _candles=list(candles))
