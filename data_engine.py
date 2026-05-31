"""
data_engine.py — Market data acquisition.

Uses yfinance when a network connection is available. If data can't be fetched
(no network, rate limit, weekend), it falls back to clearly-labelled SYNTHETIC
demo data so the dashboard remains explorable. Synthetic data is flagged loudly
in the UI so it can never be mistaken for the real market.
"""

import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta

try:
    import yfinance as yf
    _HAS_YF = True
except Exception:
    _HAS_YF = False


def fetch_daily(ticker, lookback_days=250, retries=2):
    """Return a daily OHLCV DataFrame and a flag indicating if it's real."""
    if _HAS_YF:
        for attempt in range(retries + 1):
            try:
                df = yf.download(
                    ticker,
                    period=f"{lookback_days + 50}d",
                    interval="1d",
                    progress=False,
                    auto_adjust=True,
                    threads=False,
                )
                if df is not None and len(df) > 30:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df = df.rename(columns=str.capitalize)
                    return df.tail(lookback_days), True
            except Exception:
                if attempt < retries:
                    time.sleep(0.6 * (attempt + 1))  # back off, then retry
                continue
    return _synthetic_series(ticker, lookback_days), False


def _synthetic_series(ticker, n):
    """Deterministic pseudo-random walk so demo data is stable per ticker."""
    seed = abs(hash(ticker)) % (2**32)
    rng = np.random.default_rng(seed)
    # Base price varies by instrument type for realism
    base = 100 + (seed % 400)
    drift = rng.normal(0.0003, 0.0002)
    vol = 0.008 + (seed % 7) * 0.002
    rets = rng.normal(drift, vol, n)
    # Inject a regime: trend in first half, chop in second, for teaching variety
    rets[: n // 2] += vol * 0.4
    close = base * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, vol / 2, n)))
    low = close * (1 - np.abs(rng.normal(0, vol / 2, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = rng.integers(1_000_000, 8_000_000, n)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}
    )
    # Build a business-day index of exactly len(df) by over-generating then slicing
    idx = pd.bdate_range(end=datetime.today(), periods=len(df) + 5)[-len(df):]
    df.index = idx
    return df


def fetch_universe(tickers, lookback_days=250):
    """Fetch all tickers. Returns dict[ticker] -> (df, is_real)."""
    out = {}
    for t in tickers:
        out[t] = fetch_daily(t, lookback_days)
    return out
