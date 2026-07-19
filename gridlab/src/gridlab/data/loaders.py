"""Real market-data loaders (Binance spot klines, generic CSV).

The engine is data-source agnostic, but research needs *real* candles. These
loaders turn live history into the same :class:`InMemoryDataSource` the engine
already consumes:

* :func:`load_binance_klines` pulls public spot OHLCV from Binance's REST API
  (no API key needed), paginating in 1000-candle pages and caching each
  ``symbol/interval/range`` to a local CSV so repeat runs are instant and
  offline-friendly. This is the path to backtesting BTCUSDT/ETHUSDT on the
  actual venue you would trade.
* :func:`load_csv` reads any OHLCV CSV (Binance dumps, TradingView exports,
  Interactive Brokers history) via the shared column-alias resolver.

Network access uses only the standard library (``urllib``) so there is no extra
dependency. If the network is unavailable the error is explicit, and a cached
file (if present) is used without any network call.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from gridlab.data.source import InMemoryDataSource, from_dataframe

# Binance spot kline intervals -> milliseconds (for pagination math).
_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
    "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
    "1d": 86_400_000, "3d": 259_200_000, "1w": 604_800_000,
}

_BINANCE_BASES = (
    "https://api.binance.com",
    "https://data-api.binance.vision",   # public market-data mirror, no geo-block
)

# Approx bars/year per interval, for honest metric annualisation on real data.
_BARS_PER_YEAR = {
    "1m": 525_600, "3m": 175_200, "5m": 105_120, "15m": 35_040, "30m": 17_520,
    "1h": 8_760, "2h": 4_380, "4h": 2_190, "6h": 1_460, "8h": 1_095,
    "12h": 730, "1d": 365, "3d": 121.67, "1w": 52,
}


def bars_per_year(interval: str) -> Optional[float]:
    """Annualisation factor for a Binance interval, or None if unknown."""
    return _BARS_PER_YEAR.get(interval)


def _to_ms(value) -> Optional[int]:
    """Coerce a date/datetime/ISO-string/epoch into epoch milliseconds (UTC)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Heuristic: seconds vs milliseconds.
        return int(value) if value > 1e12 else int(value * 1000)
    ts = pd.to_datetime(value, utc=True)
    return int(ts.timestamp() * 1000)


def _cache_path(cache_dir: Path, symbol: str, interval: str,
                start_ms: Optional[int], end_ms: Optional[int]) -> Path:
    s = start_ms if start_ms is not None else "min"
    e = end_ms if end_ms is not None else "max"
    return cache_dir / f"binance_{symbol.upper()}_{interval}_{s}_{e}.csv"


def _http_get_json(url: str, *, timeout: float) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "gridlab/1.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8"))


def _fetch_klines_page(base: str, symbol: str, interval: str,
                       start_ms: Optional[int], end_ms: Optional[int],
                       limit: int, timeout: float) -> list:
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    if end_ms is not None:
        params["endTime"] = end_ms
    url = f"{base}/api/v3/klines?" + urllib.parse.urlencode(params)
    return _http_get_json(url, timeout=timeout)


def _klines_to_dataframe(rows: list) -> pd.DataFrame:
    """Binance kline rows -> OHLCV DataFrame (UTC open-time index column)."""
    recs = []
    for k in rows:
        recs.append({
            "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
            "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
            "close": float(k[4]), "volume": float(k[5]),
        })
    return pd.DataFrame.from_records(recs)


def fetch_binance_klines_df(
    symbol: str = "BTCUSDT", interval: str = "1h", *,
    start: object = None, end: object = None, limit: int = 1000,
    max_candles: int = 50_000, timeout: float = 20.0,
    sleep: float = 0.0,
) -> pd.DataFrame:
    """Fetch raw Binance spot klines as an OHLCV DataFrame (no caching).

    Paginates forward from ``start`` until ``end`` (or ``max_candles``). Tries
    the primary API host and the public data mirror in turn so a regional block
    on one host still works. Raises ``RuntimeError`` if every host fails.
    """
    if interval not in _INTERVAL_MS:
        raise ValueError(f"unsupported interval {interval!r}; "
                         f"use one of {sorted(_INTERVAL_MS)}")
    start_ms = _to_ms(start)
    end_ms = _to_ms(end)
    step = _INTERVAL_MS[interval]

    frames: list[pd.DataFrame] = []
    fetched = 0
    cursor = start_ms
    last_err: Optional[Exception] = None

    while fetched < max_candles:
        page = None
        for base in _BINANCE_BASES:
            try:
                page = _fetch_klines_page(base, symbol, interval, cursor, end_ms,
                                          limit, timeout)
                last_err = None
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    OSError) as exc:
                last_err = exc
                continue
        if page is None:
            raise RuntimeError(
                f"failed to fetch Binance klines for {symbol} {interval}: {last_err}")
        if not page:
            break
        frames.append(_klines_to_dataframe(page))
        fetched += len(page)
        last_open = page[-1][0]
        cursor = last_open + step
        if len(page) < limit:
            break  # reached the end of available history
        if end_ms is not None and cursor > end_ms:
            break
        if sleep:
            time.sleep(sleep)

    if not frames:
        raise RuntimeError(f"no klines returned for {symbol} {interval}")
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
    df = df.reset_index(drop=True)
    if len(df) > max_candles:
        df = df.iloc[:max_candles].reset_index(drop=True)
    return df


def load_binance_klines(
    symbol: str = "BTCUSDT", interval: str = "1h", *,
    start: object = None, end: object = None,
    cache_dir: object = None, use_cache: bool = True,
    max_candles: int = 50_000, timeout: float = 20.0,
) -> InMemoryDataSource:
    """Load Binance spot klines as a DataSource, caching to local CSV.

    On a cache hit (and ``use_cache``) no network call is made — handy for
    repeatable research and offline work. On a miss it fetches via REST and
    writes the CSV for next time.
    """
    cache = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache, symbol, interval, _to_ms(start), _to_ms(end))

    if use_cache and path.exists():
        df = pd.read_csv(path, parse_dates=["timestamp"])
    else:
        df = fetch_binance_klines_df(symbol, interval, start=start, end=end,
                                     max_candles=max_candles, timeout=timeout)
        if use_cache:
            df.to_csv(path, index=False)
    return from_dataframe(df, symbol=symbol)


def load_csv(path: object, symbol: str = "SYMBOL") -> InMemoryDataSource:
    """Load an OHLCV CSV (any common column naming) as a DataSource."""
    df = pd.read_csv(path)
    return from_dataframe(df, symbol=symbol)


def _default_cache_dir() -> Path:
    return Path.home() / ".gridlab" / "data_cache"
