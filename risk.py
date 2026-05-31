"""
risk.py — Position sizing and portfolio risk enforcement.

Turns a setup into a concrete, rule-compliant trade: how many units, how much
money at risk, and whether the trade is even allowed given account limits. The
checklist function encodes the professional 'would a prop trader take this?'
gate — if any item fails, the trade is rejected.
"""

from . import config


def position_size(equity, entry, stop, risk_pct=None):
    """
    Compute units and monetary risk for a given stop distance.
    Returns dict with units, monetary_risk, stop_distance, exposure.
    """
    risk_pct = risk_pct if risk_pct is not None else config.ACCOUNT["max_risk_per_trade_pct"]
    monetary_risk = equity * (risk_pct / 100.0)
    stop_distance = abs(entry - stop)
    if stop_distance <= 0:
        return None
    units = monetary_risk / stop_distance
    exposure = units * entry
    return {
        "units": units,
        "monetary_risk": monetary_risk,
        "stop_distance": stop_distance,
        "exposure": exposure,
        "risk_pct": risk_pct,
    }


def checklist(setup, regime_label, liquidity_ok=True):
    """
    Professional gate. Returns (passed: bool, results: list[(question, answer)]).
    """
    bucket = "trend" if "trend" in regime_label.lower() else (
        "range" if ("range" in regime_label.lower() or "mean" in regime_label.lower())
        else "transitional"
    )
    checks = []

    checks.append(("Is there a measurable (modelled) edge?", setup["ev_R"] > 0.05))
    checks.append(("Is risk clearly defined?", setup["risk_per_unit"] > 0))
    checks.append(("Is reward adequate (R:R >= 1.5)?", setup["rr"] >= 1.5))
    checks.append(("Is market structure supportive?", setup["quality"] >= 0.55))
    checks.append(("Is market regime supportive?", setup["regime_fit"] >= 0.5))
    checks.append(("Is liquidity sufficient?", liquidity_ok))
    checks.append(("Would a prop trader take this (EV & fit)?",
                   setup["ev_R"] > 0.05 and setup["regime_fit"] >= 0.5))

    passed = all(ok for _, ok in checks)
    return passed, checks


def portfolio_risk(open_trades, equity):
    """Summarise current portfolio risk against account limits."""
    total_risk = sum(t.get("monetary_risk", 0) for t in open_trades)
    total_risk_pct = 100 * total_risk / equity if equity else 0
    n = len(open_trades)
    return {
        "open_positions": n,
        "total_monetary_risk": total_risk,
        "total_risk_pct": total_risk_pct,
        "positions_remaining": max(0, config.ACCOUNT["max_simultaneous_positions"] - n),
        "daily_loss_limit": equity * config.ACCOUNT["max_daily_loss_pct"] / 100,
        "weekly_dd_limit": equity * config.ACCOUNT["max_weekly_drawdown_pct"] / 100,
    }
