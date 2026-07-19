"""Market data sources.

The engine consumes an iterable of `Candle`. A `DataSource` is any object with
a `candles()` method yielding Candle objects in time order, plus metadata used
for metric annualisation. Keeping this behind a Protocol means a frontend can
later plug in a live exchange feed or a database cursor without touching the
engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator, Protocol, Sequence, runtime_checkable

import numpy as np
import pandas as pd

from gridlab.core.models import Candle


@runtime_checkable
class DataSource(Protocol):
    symbol: str

    def candles(self) -> Iterator[Candle]: ...

    def __len__(self) -> int: ...


@dataclass(slots=True)
class InMemoryDataSource:
    """A materialized list of candles."""
    symbol: str
    _candles: list[Candle]

    def candles(self) -> Iterator[Candle]:
        return iter(self._candles)

    def as_list(self) -> list[Candle]:
        return self._candles

    def __len__(self) -> int:
        return len(self._candles)

    def median_interval_seconds(self) -> float:
        if len(self._candles) < 2:
            return 60.0
        ts = np.array([c.timestamp.timestamp() for c in self._candles])
        diffs = np.diff(ts)
        diffs = diffs[diffs > 0]
        return float(np.median(diffs)) if diffs.size else 60.0


_COLUMN_ALIASES = {
    "timestamp": ["timestamp", "time", "date", "datetime", "open_time"],
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c"],
    "volume": ["volume", "vol", "v"],
}


def _resolve(columns: Sequence[str], names: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for n in names:
        if n in lower:
            return lower[n]
    return None


def from_dataframe(df: pd.DataFrame, symbol: str = "SYMBOL",
                   extra_columns: Iterable[str] | None = None) -> InMemoryDataSource:
    """Build a data source from an OHLCV DataFrame.

    Recognises common column aliases. Any `extra_columns` (e.g. precomputed
    indicators) are attached to each candle's `extra` dict so strategies can use
    them without recomputation.
    """
    cols = {key: _resolve(df.columns, aliases) for key, aliases in _COLUMN_ALIASES.items()}
    missing = [k for k in ("open", "high", "low", "close") if cols[k] is None]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    ts_col = cols["timestamp"]
    vol_col = cols["volume"]
    extra_cols = list(extra_columns) if extra_columns else []

    candles: list[Candle] = []
    o, h, l, c = cols["open"], cols["high"], cols["low"], cols["close"]

    for i, (_, row) in enumerate(df.iterrows()):
        if ts_col is not None:
            raw = row[ts_col]
            ts = pd.to_datetime(raw, utc=True).to_pydatetime()
        else:
            ts = datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
        extra = {col: float(row[col]) for col in extra_cols if col in df.columns and pd.notna(row[col])}
        candles.append(Candle(
            timestamp=ts,
            open=float(row[o]),
            high=float(row[h]),
            low=float(row[l]),
            close=float(row[c]),
            volume=float(row[vol_col]) if vol_col is not None else 0.0,
            index=i,
            extra=extra,
        ))
    return InMemoryDataSource(symbol=symbol, _candles=candles)


def synthetic(n: int = 1000, start_price: float = 100.0, *, seed: int = 7,
              mu: float = 0.0, sigma: float = 0.01, interval_minutes: int = 60,
              symbol: str = "SYNTH", regime: str = "range") -> InMemoryDataSource:
    """Generate synthetic OHLCV data for tests/examples.

    regime: 'range' (mean-reverting), 'trend' (drift), or 'random' (GBM).
    """
    rng = np.random.default_rng(seed)
    prices = np.empty(n, dtype=float)
    prices[0] = start_price
    level = start_price
    for i in range(1, n):
        shock = rng.normal(mu, sigma)
        if regime == "range":
            # Ornstein-Uhlenbeck style pull back to start_price
            pull = 0.02 * (start_price - prices[i - 1]) / start_price
            prices[i] = prices[i - 1] * (1.0 + pull + shock)
        elif regime == "trend":
            prices[i] = prices[i - 1] * (1.0 + abs(mu) + 0.0005 + shock)
        else:
            prices[i] = prices[i - 1] * (1.0 + shock)
        prices[i] = max(prices[i], 1e-9)

    candles: list[Candle] = []
    t0 = datetime(2021, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        close = prices[i]
        open_ = prices[i - 1] if i > 0 else close
        hi = max(open_, close) * (1.0 + abs(rng.normal(0, sigma / 2)))
        lo = min(open_, close) * (1.0 - abs(rng.normal(0, sigma / 2)))
        vol = float(abs(rng.normal(1000, 200)))
        candles.append(Candle(
            timestamp=t0 + timedelta(minutes=i * interval_minutes),
            open=open_, high=hi, low=lo, close=close, volume=vol, index=i,
        ))
    return InMemoryDataSource(symbol=symbol, _candles=candles)
