"""
scanner.py — The orchestrator. Runs the full daily pipeline:
fetch -> internals -> per-instrument regime -> setup detection -> EV ranking ->
checklist gate -> final 0-3 recommendations with position sizing.

This is the 'what is the highest-probability action today?' engine.
"""

import numpy as np
import pandas as pd
from . import config, data_engine, regime as regime_mod, strategies, risk


def run_daily_scan(equity=None, lookback=None):
    equity = equity or config.ACCOUNT["starting_capital"]
    lookback = lookback or config.DATA["lookback_days"]

    tickers = list(config.all_tickers().keys())
    data_map = data_engine.fetch_universe(tickers, lookback)
    any_real = any(real for (_df, real) in data_map.values())

    internals = regime_mod.universe_internals(data_map)
    tone_label, tone_reason = regime_mod.risk_tone(internals)

    # Relative-strength percentile per ticker (by 20d return)
    rs_rank = {}
    tbl = internals.get("table")
    if tbl is not None and not tbl.empty:
        tbl = tbl.copy()
        tbl["rs_pct"] = tbl["ret_20d"].rank(pct=True)
        rs_rank = dict(zip(tbl["ticker"], tbl["rs_pct"]))

    # Determine a 'market' regime from the main index (S&P 500) if present
    market_regime = "Transitional"
    market_evidence = []
    if "^GSPC" in data_map and data_map["^GSPC"][0] is not None:
        market_regime, _score, market_evidence = regime_mod.classify_regime(data_map["^GSPC"][0])

    # Scan every instrument
    all_candidates = []
    names = config.all_tickers()
    for ticker, (df, real) in data_map.items():
        if df is None or len(df) < 60:
            continue
        inst_regime, _s, _e = regime_mod.classify_regime(df)
        rsr = rs_rank.get(ticker, 0.5)
        cands = strategies.scan_instrument(df, inst_regime, rsr)
        for c in cands:
            c["instrument"] = names.get(ticker, ticker)
            c["ticker"] = ticker
            c["group"] = config.ticker_group(ticker)
            c["inst_regime"] = inst_regime
            c["is_real_data"] = real
            all_candidates.append(c)

    # Rank: expectancy first, then confidence, then regime fit
    all_candidates.sort(key=lambda c: (c["ev_R"], c["confidence"], c["regime_fit"]),
                        reverse=True)

    # Apply checklist gate and position sizing; keep top 3 that pass
    recommendations = []
    for c in all_candidates:
        passed, checks = risk.checklist(c, c["inst_regime"], liquidity_ok=True)
        c["checklist"] = checks
        c["checklist_passed"] = passed
        if not passed:
            continue
        sizing = risk.position_size(equity, c["entry"], c["stop"])
        if sizing is None:
            continue
        c.update(sizing)
        # Potential return at target1
        c["potential_return_t1"] = sizing["units"] * abs(c["target1"] - c["entry"])
        recommendations.append(c)
        if len(recommendations) >= config.ACCOUNT["max_simultaneous_positions"]:
            break

    # Environment classification
    env = _classify_environment(recommendations, internals, market_regime)

    return {
        "any_real_data": any_real,
        "internals": internals,
        "tone_label": tone_label,
        "tone_reason": tone_reason,
        "market_regime": market_regime,
        "market_evidence": market_evidence,
        "candidates": all_candidates,
        "recommendations": recommendations,
        "environment": env,
        "equity": equity,
    }


def _classify_environment(recs, internals, market_regime):
    if not recs:
        return ("Poor", "No setups cleared the checklist. Recommended action: stay in cash and "
                "preserve capital.")
    best_ev = max(r["ev_R"] for r in recs)
    n = len(recs)
    breadth = internals.get("breadth_pct", np.nan)
    if best_ev > 0.5 and n >= 2 and not np.isnan(breadth) and breadth > 55:
        return ("Excellent", "Multiple high-expectancy setups aligned with a supportive, broad market.")
    if best_ev > 0.3:
        return ("Good", "At least one solid positive-expectancy setup with acceptable regime fit.")
    if best_ev > 0.1:
        return ("Neutral", "Marginal edge present. Trade small or wait for cleaner confirmation.")
    return ("Poor", "Edges are thin. Capital preservation should take priority over activity.")
