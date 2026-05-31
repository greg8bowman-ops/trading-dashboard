"""
strategies.py — Setup detection and regime-suitability scoring.

Each strategy is a function that inspects an enriched frame and returns either
None (no setup) or a dict describing the setup: direction, entry reference, a
structural stop, and the raw signal quality. Win-rate / R:R figures attached
here are HEURISTIC PRIORS calibrated to typical published behaviour of each
style — they are explicitly NOT measured edges and are labelled as such in the
UI. They exist to rank setups consistently, not to promise outcomes.
"""

import numpy as np
from . import indicators as ind


# Heuristic priors per strategy: (base_win_rate, base_rr)
# These are conservative, literature-informed placeholders, NOT guarantees.
STRATEGY_PRIORS = {
    "Trend Pullback": (0.45, 2.2),
    "Momentum Continuation": (0.42, 2.5),
    "Relative Strength Breakout": (0.40, 2.8),
    "Mean Reversion (range)": (0.55, 1.3),
    "Support/Resistance Breakout": (0.43, 2.4),
}

# Which strategies suit which regimes (suitability multiplier 0..1)
REGIME_FIT = {
    "Trend Pullback":            {"trend": 1.0, "range": 0.2, "transitional": 0.4},
    "Momentum Continuation":     {"trend": 0.9, "range": 0.2, "transitional": 0.4},
    "Relative Strength Breakout":{"trend": 0.9, "range": 0.3, "transitional": 0.5},
    "Mean Reversion (range)":    {"trend": 0.2, "range": 1.0, "transitional": 0.4},
    "Support/Resistance Breakout":{"trend": 0.7, "range": 0.6, "transitional": 0.7},
}


def _regime_bucket(regime_label):
    r = regime_label.lower()
    if "trend" in r:
        return "trend"
    if "range" in r or "mean" in r:
        return "range"
    return "transitional"


def detect_trend_pullback(d):
    last, prev = d.iloc[-1], d.iloc[-2]
    if last["Close"] > last["SMA50"] and last["EMA20"] > last["SMA50"]:
        # pullback: price dipped toward EMA20 then turned up
        near_ema = abs(last["Close"] - last["EMA20"]) / last["Close"] < 0.02
        turning_up = last["Close"] > prev["Close"] and prev["RSI"] < 50
        if near_ema and turning_up:
            stop = last["Close"] - 1.5 * last["ATR"]
            return {"direction": "long", "entry": last["Close"], "stop": stop,
                    "quality": 0.6 + min(last["ADX"], 40) / 100}
    if last["Close"] < last["SMA50"] and last["EMA20"] < last["SMA50"]:
        near_ema = abs(last["Close"] - last["EMA20"]) / last["Close"] < 0.02
        turning_dn = last["Close"] < prev["Close"] and prev["RSI"] > 50
        if near_ema and turning_dn:
            stop = last["Close"] + 1.5 * last["ATR"]
            return {"direction": "short", "entry": last["Close"], "stop": stop,
                    "quality": 0.6 + min(last["ADX"], 40) / 100}
    return None


def detect_momentum_continuation(d):
    last = d.iloc[-1]
    mom20 = ind.rolling_return(d["Close"], 20).iloc[-1]
    if last["ADX"] > 22 and mom20 > 0.04 and last["RSI"] > 55 and last["Close"] > last["SMA20"]:
        stop = last["Close"] - 1.8 * last["ATR"]
        return {"direction": "long", "entry": last["Close"], "stop": stop,
                "quality": 0.55 + min(mom20, 0.2)}
    if last["ADX"] > 22 and mom20 < -0.04 and last["RSI"] < 45 and last["Close"] < last["SMA20"]:
        stop = last["Close"] + 1.8 * last["ATR"]
        return {"direction": "short", "entry": last["Close"], "stop": stop,
                "quality": 0.55 + min(abs(mom20), 0.2)}
    return None


def detect_breakout(d):
    last = d.iloc[-1]
    hi20 = d["High"].iloc[-21:-1].max()
    lo20 = d["Low"].iloc[-21:-1].max()
    lo20 = d["Low"].iloc[-21:-1].min()
    vol_surge = last["Volume"] > 1.3 * last["VolAvg20"] if not np.isnan(last["VolAvg20"]) else False
    if last["Close"] > hi20 and vol_surge:
        stop = hi20 - 0.5 * last["ATR"]
        return {"direction": "long", "entry": last["Close"], "stop": stop,
                "quality": 0.55 + (0.1 if vol_surge else 0)}
    if last["Close"] < lo20 and vol_surge:
        stop = lo20 + 0.5 * last["ATR"]
        return {"direction": "short", "entry": last["Close"], "stop": stop,
                "quality": 0.55 + (0.1 if vol_surge else 0)}
    return None


def detect_mean_reversion(d):
    last = d.iloc[-1]
    if last["ADX"] < 20:  # only in non-trending conditions
        if last["Close"] <= last["BB_dn"] and last["RSI"] < 30:
            stop = last["Close"] - 1.2 * last["ATR"]
            return {"direction": "long", "entry": last["Close"], "stop": stop,
                    "quality": 0.6}
        if last["Close"] >= last["BB_up"] and last["RSI"] > 70:
            stop = last["Close"] + 1.2 * last["ATR"]
            return {"direction": "short", "entry": last["Close"], "stop": stop,
                    "quality": 0.6}
    return None


DETECTORS = {
    "Trend Pullback": detect_trend_pullback,
    "Momentum Continuation": detect_momentum_continuation,
    "Support/Resistance Breakout": detect_breakout,
    "Mean Reversion (range)": detect_mean_reversion,
}


def scan_instrument(df, regime_label, rs_rank=0.5):
    """
    Run all detectors on one instrument. Return a list of candidate setups,
    each enriched with EV math and a suitability-adjusted confidence.
    rs_rank: 0..1 relative-strength percentile in the universe (momentum tilt).
    """
    d = ind.enrich(df)
    if len(d) < 60:
        return []
    bucket = _regime_bucket(regime_label)
    candidates = []

    for name, fn in DETECTORS.items():
        setup = fn(d)
        if setup is None:
            continue
        base_wr, base_rr = STRATEGY_PRIORS.get(name, (0.45, 2.0))
        fit = REGIME_FIT.get(name, {}).get(bucket, 0.4)

        # Adjust win prob by regime fit, signal quality, relative strength.
        rs_adj = (rs_rank - 0.5) * 0.1  # +/-5% from RS extremes
        if setup["direction"] == "short":
            rs_adj = -rs_adj
        win_prob = np.clip(base_wr * (0.7 + 0.6 * fit) * (0.8 + 0.4 * setup["quality"]) + rs_adj,
                           0.20, 0.70)

        entry, stop = setup["entry"], setup["stop"]
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            continue
        rr = base_rr
        if setup["direction"] == "long":
            target1 = entry + rr * risk_per_unit
            target2 = entry + (rr + 1.0) * risk_per_unit
        else:
            target1 = entry - rr * risk_per_unit
            target2 = entry - (rr + 1.0) * risk_per_unit

        avg_win = rr            # in R units
        avg_loss = 1.0          # in R units
        ev_R = win_prob * avg_win - (1 - win_prob) * avg_loss  # expectancy in R

        candidates.append({
            "strategy": name,
            "direction": setup["direction"],
            "entry": entry,
            "stop": stop,
            "target1": target1,
            "target2": target2,
            "risk_per_unit": risk_per_unit,
            "rr": rr,
            "win_prob": win_prob,
            "loss_prob": 1 - win_prob,
            "ev_R": ev_R,
            "regime_fit": fit,
            "quality": setup["quality"],
            "confidence": int(np.clip(50 + ev_R * 40 + (fit - 0.5) * 30, 5, 95)),
        })
    return candidates
