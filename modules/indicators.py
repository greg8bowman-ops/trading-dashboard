"""
indicators.py — Technical analysis primitives.

Pure functions on pandas Series/DataFrames. No look-ahead: every indicator at
bar t uses only data up to and including t. These are the building blocks the
regime and strategy engines consume.
"""

import numpy as np
import pandas as pd


def sma(series, n):
    return series.rolling(n).mean()


def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(n).mean()


def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def adx(df, n=14):
    """Average Directional Index — trend strength (not direction)."""
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr_ = tr.rolling(n).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(n).mean() / atr_
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(n).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(n).mean()


def bollinger(series, n=20, k=2):
    mid = sma(series, n)
    sd = series.rolling(n).std()
    return mid + k * sd, mid, mid - k * sd


def vwap(df):
    """Rolling VWAP proxy on daily data (true VWAP is intraday)."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


def realized_vol(series, n=20):
    """Annualised realised volatility from daily returns."""
    rets = series.pct_change()
    return rets.rolling(n).std() * np.sqrt(252)


def rolling_return(series, n):
    return series / series.shift(n) - 1


def enrich(df):
    """Attach a standard indicator set to a copy of the OHLCV frame."""
    d = df.copy()
    d["SMA20"] = sma(d["Close"], 20)
    d["SMA50"] = sma(d["Close"], 50)
    d["EMA20"] = ema(d["Close"], 20)
    d["ATR"] = atr(d, 14)
    d["RSI"] = rsi(d["Close"], 14)
    d["ADX"] = adx(d, 14)
    d["BB_up"], d["BB_mid"], d["BB_dn"] = bollinger(d["Close"])
    d["RVOL"] = realized_vol(d["Close"], 20)
    d["VolAvg20"] = d["Volume"].rolling(20).mean()
    return d
