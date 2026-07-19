"""Technical indicators implemented in pure pandas/numpy.

These are used to precompute per-candle values (attached to `Candle.extra`)
for adaptive grid policies (ATR spacing, trend filters, regime detection).
Keeping them as vectorised functions over a DataFrame avoids per-bar recompute
inside the engine loop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=1).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False, min_periods=1).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.fillna(high - low)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's ATR (RMA smoothing)."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(50.0)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index — used by regime/trend filters."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(high, low, close)
    atr_ = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    plus_di = 100.0 * pd.Series(plus_dm, index=high.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=1).mean() / atr_.replace(0.0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=high.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=1).mean() / atr_.replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean().fillna(0.0)


def bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0
              ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (lower, mid, upper) Bollinger bands."""
    mid = close.rolling(period, min_periods=1).mean()
    std = close.rolling(period, min_periods=1).std(ddof=0).fillna(0.0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return lower, mid, upper
