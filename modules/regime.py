"""
regime.py — Market regime classification and internals.

Classifies a single instrument's regime from objective indicator evidence, and
aggregates across the universe to estimate breadth and risk-on/risk-off tone.
Every classification returns the *evidence* used, so the UI can teach, not just
assert.
"""

import numpy as np
import pandas as pd
from . import indicators as ind


def classify_regime(df):
    """Return (regime_label, score_dict, evidence_list) for an enriched frame."""
    d = ind.enrich(df)
    last = d.iloc[-1]
    evidence = []

    adx_val = last["ADX"]
    rsi_val = last["RSI"]
    price = last["Close"]
    sma20, sma50 = last["SMA20"], last["SMA50"]
    rvol = last["RVOL"]
    rvol_median = d["RVOL"].median()

    # Trend strength from ADX
    if adx_val >= 30:
        trend_strength = "strong"
    elif adx_val >= 20:
        trend_strength = "moderate"
    else:
        trend_strength = "weak"
    evidence.append(f"ADX(14) = {adx_val:.1f} → {trend_strength} trend strength")

    # Direction from MA stack
    if price > sma20 > sma50:
        direction = "up"
    elif price < sma20 < sma50:
        direction = "down"
    else:
        direction = "mixed"
    evidence.append(
        f"Price {price:.2f} vs SMA20 {sma20:.2f} vs SMA50 {sma50:.2f} → {direction} alignment"
    )

    # Volatility regime
    vol_state = "high" if rvol > rvol_median * 1.3 else (
        "low" if rvol < rvol_median * 0.7 else "normal"
    )
    evidence.append(
        f"Realised vol {rvol*100:.1f}% vs median {rvol_median*100:.1f}% → {vol_state} volatility"
    )

    # Mean-reversion vs trending decision
    if trend_strength == "strong" and direction in ("up", "down"):
        regime = f"Strongly Trending ({direction})"
    elif trend_strength == "moderate" and direction in ("up", "down"):
        regime = f"Trending ({direction})"
    elif trend_strength == "weak":
        if rsi_val > 70:
            regime = "Range-bound (overbought edge)"
        elif rsi_val < 30:
            regime = "Range-bound (oversold edge)"
        else:
            regime = "Range-bound / Mean-reverting"
    else:
        regime = "Transitional"

    if vol_state == "high":
        regime += " · High-Vol"

    score = {
        "adx": float(adx_val) if not np.isnan(adx_val) else 0.0,
        "rsi": float(rsi_val) if not np.isnan(rsi_val) else 50.0,
        "trend_strength": trend_strength,
        "direction": direction,
        "vol_state": vol_state,
    }
    return regime, score, evidence


def universe_internals(data_map):
    """
    Aggregate breadth/momentum across the universe.
    data_map: dict[ticker] -> (df, is_real)
    Returns a dict of internals plus a per-ticker momentum table.
    """
    rows = []
    for ticker, (df, _real) in data_map.items():
        if df is None or len(df) < 60:
            continue
        d = ind.enrich(df)
        last = d.iloc[-1]
        ret_20 = ind.rolling_return(d["Close"], 20).iloc[-1]
        ret_5 = ind.rolling_return(d["Close"], 5).iloc[-1]
        above_50 = last["Close"] > last["SMA50"]
        rows.append(
            {
                "ticker": ticker,
                "ret_5d": ret_5,
                "ret_20d": ret_20,
                "above_sma50": above_50,
                "rsi": last["RSI"],
                "adx": last["ADX"],
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return {"breadth_pct": np.nan, "avg_mom_20d": np.nan, "table": table}

    breadth = 100 * table["above_sma50"].mean()
    avg_mom = table["ret_20d"].mean()
    return {
        "breadth_pct": breadth,
        "avg_mom_20d": avg_mom,
        "table": table.sort_values("ret_20d", ascending=False),
    }


def risk_tone(internals):
    """Heuristic risk-on / risk-off read from breadth + momentum."""
    b = internals.get("breadth_pct", np.nan)
    m = internals.get("avg_mom_20d", np.nan)
    if np.isnan(b):
        return "Unknown", "Insufficient data"
    if b >= 60 and m > 0:
        return "Risk-On", f"{b:.0f}% of instruments above their 50-day average with positive average momentum"
    if b <= 40 and m < 0:
        return "Risk-Off", f"Only {b:.0f}% above 50-day average with negative average momentum"
    return "Neutral / Mixed", f"{b:.0f}% above 50-day average — no decisive tone"
