"""
opening_range.py — Opening Range Breakout (ORB) for the US cash session.

Design philosophy (read before changing):
  • The opening 5 minutes is noise. This module DELIBERATELY waits for the
    opening range (default 15 or 30 min from the 09:30 ET open) to FORM, then
    only flags a breakout *after* the range is complete and price closes beyond
    it with confirmation. It never fires inside the range-building window.
  • A breakout is only reported if it ALIGNS with the daily regime we already
    compute elsewhere (no fading the higher-timeframe trend) OR is a clean,
    high-volume range expansion. This keeps it consistent with the rest of the
    risk-first system.
  • Intraday data is fetched at 5-minute bars via yfinance. This feed is delayed
    (typically ~15 min) and not a true real-time feed — so signals are labelled
    as based on DELAYED data and must never be treated as a live execution trigger.

US cash session open: 09:30 America/New_York. We compute everything in that
timezone regardless of the user's location.
"""

import numpy as np
import pandas as pd
from datetime import datetime, time as dtime

try:
    import yfinance as yf
    _HAS_YF = True
except Exception:
    _HAS_YF = False

# US-equity tickers eligible for ORB (liquid, tight at the open).
ORB_TICKERS = {
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "AMZN": "Amazon", "META": "Meta", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "JPM": "JPMorgan", "XOM": "Exxon",
}

SESSION_OPEN = dtime(9, 30)   # 09:30 ET
NY_TZ = "America/New_York"


def _fetch_intraday(ticker):
    """5-minute bars for today's US session. Returns (df_or_None, is_real)."""
    if not _HAS_YF:
        return None, False
    try:
        df = yf.download(ticker, period="1d", interval="5m",
                         progress=False, auto_adjust=True, threads=False)
        if df is None or len(df) == 0:
            return None, False
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.capitalize)
        # Ensure tz-aware in New York time
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(NY_TZ)
        else:
            df.index = df.index.tz_convert(NY_TZ)
        return df, True
    except Exception:
        return None, False


def _session_status(now_ny, range_minutes):
    """Return one of: 'pre-open', 'building', 'active', 'closed'."""
    t = now_ny.time()
    open_t = SESSION_OPEN
    # minutes since open
    open_dt = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    mins = (now_ny - open_dt).total_seconds() / 60.0
    if t < open_t:
        return "pre-open", mins
    if mins < range_minutes:
        return "building", mins
    if t <= dtime(16, 0):
        return "active", mins
    return "closed", mins


def compute_orb(ticker, daily_regime_direction, range_minutes=30,
                now_ny=None):
    """
    Compute the opening-range breakout state for one ticker.

    daily_regime_direction: 'up' | 'down' | 'mixed' from the daily regime engine,
        used to confirm the breakout aligns with the higher timeframe.
    Returns a dict describing range, status, and any signal (or None signal).
    """
    df, is_real = _fetch_intraday(ticker)
    if now_ny is None:
        now_ny = pd.Timestamp.now(tz=NY_TZ)

    status, mins_since_open = _session_status(now_ny, range_minutes)
    base = {
        "ticker": ticker, "name": ORB_TICKERS.get(ticker, ticker),
        "is_real_data": is_real, "status": status,
        "minutes_since_open": round(mins_since_open, 1),
        "range_minutes": range_minutes, "signal": None,
        "range_high": None, "range_low": None, "note": "",
    }

    if df is None or df.empty:
        base["note"] = "No intraday data available (feed offline or market closed)."
        return base

    # Slice today's session bars from 09:30
    session = df[df.index.time >= SESSION_OPEN]
    if session.empty:
        base["note"] = "No post-open bars yet."
        return base

    # Opening-range window: bars within the first `range_minutes`
    open_dt = session.index[0].replace(hour=9, minute=30, second=0, microsecond=0)
    cutoff = open_dt + pd.Timedelta(minutes=range_minutes)
    or_bars = session[session.index < cutoff]

    if status in ("pre-open",):
        base["note"] = "Session has not opened yet (US 09:30 ET)."
        return base

    if status == "building" or len(or_bars) < 1:
        if not or_bars.empty:
            base["range_high"] = float(or_bars["High"].max())
            base["range_low"] = float(or_bars["Low"].min())
        base["note"] = (f"Opening range still forming "
                        f"({base['minutes_since_open']:.0f} of {range_minutes} min). "
                        "No signal until the range completes — by design.")
        return base

    # Range is complete
    rng_high = float(or_bars["High"].max())
    rng_low = float(or_bars["Low"].min())
    base["range_high"], base["range_low"] = rng_high, rng_low
    rng_size = rng_high - rng_low
    if rng_size <= 0:
        base["note"] = "Degenerate opening range; skipping."
        return base

    # Post-range bars to detect a confirmed breakout
    post = session[session.index >= cutoff]
    if post.empty:
        base["note"] = "Range complete; waiting for the first post-range bar."
        return base

    last = post.iloc[-1]
    last_close = float(last["Close"])

    # Average opening-range volume to judge breakout conviction
    or_vol = or_bars["Volume"].mean() if "Volume" in or_bars else np.nan
    last_vol = float(last["Volume"]) if "Volume" in last else np.nan
    vol_ok = (not np.isnan(or_vol) and not np.isnan(last_vol)
              and last_vol >= 0.8 * or_vol)

    direction = None
    if last_close > rng_high:
        direction = "long"
    elif last_close < rng_low:
        direction = "short"

    if direction is None:
        base["note"] = ("Price still inside the opening range. No breakout — "
                        "waiting (this is normal and often the correct outcome).")
        return base

    # Confirmation: align with daily regime, OR allow a strong volume expansion.
    aligned = (
        (direction == "long" and daily_regime_direction == "up") or
        (direction == "short" and daily_regime_direction == "down")
    )
    confirmed = aligned or vol_ok

    if not confirmed:
        base["note"] = (f"{direction.upper()} breakout detected but NOT confirmed "
                        "(against daily trend and without a volume surge). "
                        "Skipping — fading the higher timeframe is low-edge.")
        return base

    # Build the signal. Stop sits just beyond the FAR side of the range plus a
    # small buffer, but risk is measured from entry; targets are R-multiples of
    # that risk so the reward:risk is controlled rather than dictated by range
    # width. Buffer = 10% of range to avoid getting wicked out at the edge.
    buffer = 0.10 * rng_size
    if direction == "long":
        entry = last_close
        stop = rng_low - buffer
        risk = entry - stop
        t1 = entry + 1.5 * risk
        t2 = entry + 2.5 * risk
    else:
        entry = last_close
        stop = rng_high + buffer
        risk = stop - entry
        t1 = entry - 1.5 * risk
        t2 = entry - 2.5 * risk

    if risk <= 0:
        base["note"] = "Invalid stop distance; skipping."
        return base

    rr = abs(t1 - entry) / risk
    base["signal"] = {
        "direction": direction,
        "entry": entry, "stop": stop, "target1": t1, "target2": t2,
        "risk_per_unit": risk, "rr": round(rr, 2),
        "aligned_with_daily": aligned, "volume_confirmed": bool(vol_ok),
    }
    base["note"] = (f"Confirmed {direction.upper()} breakout of the "
                    f"{range_minutes}-min opening range "
                    f"({'daily-trend aligned' if aligned else 'volume-confirmed'}).")
    return base


def scan_orb(daily_directions, range_minutes=30, now_ny=None):
    """
    Run ORB across all eligible US tickers.
    daily_directions: dict[ticker] -> 'up'|'down'|'mixed' from the daily engine.
    Returns (session_status, list_of_results_with_signals_first).
    """
    results = []
    status_seen = "closed"
    for t in ORB_TICKERS:
        d = daily_directions.get(t, "mixed")
        r = compute_orb(t, d, range_minutes=range_minutes, now_ny=now_ny)
        results.append(r)
        status_seen = r["status"]
    # signals first, then by R:R
    results.sort(key=lambda r: (r["signal"] is not None,
                                r["signal"]["rr"] if r["signal"] else 0),
                 reverse=True)
    return status_seen, results
