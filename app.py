"""
app.py — Professional Day Trading Dashboard (Streamlit)
=======================================================

Run locally with:

    pip install -r requirements.txt
    streamlit run app.py

Eight sections: Market Overview, Regime Analysis, Opportunity Scanner,
Trade Recommendations, Risk Dashboard, Performance Analytics, Trading Journal,
Daily Learning Centre.

IMPORTANT: All probabilities / win-rates / EV figures are MODEL ESTIMATES, not
predictions or measured edges. See the disclaimer banner. This is an education
and decision-discipline tool, not financial advice.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from modules import config, scanner, regime as regime_mod, indicators as ind
from modules import risk as risk_mod, journal, education, data_engine
from modules import opening_range as orb_mod

# ---------------------------------------------------------------------------
# PAGE CONFIG & THEME
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Quant Day Trading Desk", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main { background: #0c0e14; }
.stApp { background:
    radial-gradient(circle at 15% 10%, rgba(34,52,84,0.35), transparent 40%),
    radial-gradient(circle at 85% 20%, rgba(60,40,80,0.25), transparent 45%),
    #0c0e14; color: #e6e9f0; }
h1,h2,h3 { font-family: 'Fraunces', serif !important; letter-spacing:-0.01em; color:#f4f6fb; }
h1 { font-weight:700; }
.mono { font-family:'IBM Plex Mono', monospace; }
.banner { background: linear-gradient(90deg, rgba(180,60,60,0.18), rgba(180,60,60,0.05));
    border:1px solid rgba(220,90,90,0.4); border-radius:10px; padding:12px 16px;
    font-size:0.82rem; color:#f0c8c8; margin-bottom:14px; }
.card { background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);
    border-radius:14px; padding:18px 20px; margin-bottom:14px; }
.tag { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.72rem;
    font-family:'IBM Plex Mono',monospace; font-weight:600; letter-spacing:0.03em; }
.tag-long { background:rgba(60,180,120,0.18); color:#6fe0a8; border:1px solid rgba(60,180,120,0.4);}
.tag-short{ background:rgba(220,90,90,0.16); color:#f29b9b; border:1px solid rgba(220,90,90,0.4);}
.env-Excellent{ color:#6fe0a8;} .env-Good{color:#9fd1ff;} .env-Neutral{color:#e8d18a;} .env-Poor{color:#f29b9b;}
.metric-big { font-family:'IBM Plex Mono',monospace; font-size:1.9rem; font-weight:600; color:#f4f6fb;}
.metric-label{ font-size:0.74rem; text-transform:uppercase; letter-spacing:0.08em; color:#8b93a7;}
.evidence{ font-family:'IBM Plex Mono',monospace; font-size:0.8rem; color:#9aa3b8; padding:3px 0;}
hr { border-color: rgba(255,255,255,0.08); }
.stTabs [data-baseweb="tab"] { font-family:'IBM Plex Mono',monospace; font-size:0.8rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DATA LOAD (cached)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner="Running daily market scan…")
def load_scan(equity):
    return scanner.run_daily_scan(equity=equity)


def fmt(x, d=2):
    try:
        return f"{x:,.{d}f}"
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Desk Controls")
    equity = st.number_input("Account equity (£)", min_value=100.0,
                             value=config.ACCOUNT["starting_capital"], step=100.0)
    st.caption("Risk rules (hard limits)")
    st.markdown(
        f"- Max risk/trade: **{config.ACCOUNT['max_risk_per_trade_pct']}%**  "
        f"(£{equity*config.ACCOUNT['max_risk_per_trade_pct']/100:.2f})\n"
        f"- Max daily loss: **{config.ACCOUNT['max_daily_loss_pct']}%**\n"
        f"- Max weekly DD: **{config.ACCOUNT['max_weekly_drawdown_pct']}%**\n"
        f"- Max positions: **{config.ACCOUNT['max_simultaneous_positions']}**"
    )
    if st.button("🔄 Re-run scan", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption(datetime.now().strftime("Scan time: %Y-%m-%d %H:%M"))

scan = load_scan(equity)
recs = scan["recommendations"]
env_label, env_reason = scan["environment"]

# ---------------------------------------------------------------------------
# HEADER + DISCLAIMER
# ---------------------------------------------------------------------------
st.markdown("# 📈 Quant Day Trading Desk")
st.markdown(f"<div class='banner'>⚠️ {config.DISCLAIMER}</div>", unsafe_allow_html=True)

if not scan["any_real_data"]:
    st.warning("**SYNTHETIC DEMO DATA in use** — no live market feed reached. "
               "Install `yfinance` and run with internet for real prices. All numbers "
               "below are illustrative only.", icon="🧪")

# Executive summary strip
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("<div class='metric-label'>Market Regime</div>"
                f"<div class='metric-big' style='font-size:1.2rem'>{scan['market_regime']}</div>",
                unsafe_allow_html=True)
with c2:
    st.markdown("<div class='metric-label'>Risk Tone</div>"
                f"<div class='metric-big' style='font-size:1.2rem'>{scan['tone_label']}</div>",
                unsafe_allow_html=True)
with c3:
    st.markdown("<div class='metric-label'>Opportunities</div>"
                f"<div class='metric-big'>{len(recs)}</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='metric-label'>Environment</div>"
                f"<div class='metric-big env-{env_label}' style='font-size:1.4rem'>{env_label}</div>",
                unsafe_allow_html=True)

st.markdown(f"<div class='card'>{env_reason}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "🌐 Overview", "🧭 Regime", "🔍 Scanner", "🎯 Recommendations",
    "🔔 Opening Range", "🛡️ Risk", "📊 Performance", "📓 Journal", "🎓 Learning Centre",
])

# ===== 1. MARKET OVERVIEW =====
with tabs[0]:
    st.subheader("Market Internals & Breadth")
    internals = scan["internals"]
    tbl = internals.get("table")
    b1, b2 = st.columns([1, 2])
    with b1:
        breadth = internals.get("breadth_pct", float("nan"))
        st.markdown(f"<div class='card'><div class='metric-label'>Breadth (above 50-day MA)</div>"
                    f"<div class='metric-big'>{fmt(breadth,0)}%</div>"
                    f"<div class='evidence'>{scan['tone_reason']}</div></div>",
                    unsafe_allow_html=True)
        mom = internals.get("avg_mom_20d", float("nan"))
        st.markdown(f"<div class='card'><div class='metric-label'>Avg 20-day momentum</div>"
                    f"<div class='metric-big'>{fmt(mom*100,1)}%</div></div>",
                    unsafe_allow_html=True)
    with b2:
        if tbl is not None and not tbl.empty:
            disp = tbl.copy()
            disp["ret_5d"] = (disp["ret_5d"] * 100).round(2)
            disp["ret_20d"] = (disp["ret_20d"] * 100).round(2)
            disp["rsi"] = disp["rsi"].round(1)
            disp["adx"] = disp["adx"].round(1)
            disp = disp.rename(columns={"ret_5d": "5d %", "ret_20d": "20d %",
                                        "above_sma50": ">50MA", "rsi": "RSI", "adx": "ADX"})
            st.dataframe(disp.set_index("ticker"), use_container_width=True, height=380)

    if tbl is not None and not tbl.empty:
        st.subheader("Relative Strength Map (20-day return)")
        srt = tbl.sort_values("ret_20d", ascending=True)
        fig = go.Figure(go.Bar(
            x=srt["ret_20d"] * 100, y=srt["ticker"], orientation="h",
            marker_color=["#6fe0a8" if v > 0 else "#f29b9b" for v in srt["ret_20d"]],
        ))
        fig.update_layout(height=520, template="plotly_dark",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis_title="20-day return %", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ===== 2. REGIME =====
with tabs[1]:
    st.subheader("Market Regime Analysis")
    st.markdown(f"<div class='card'><div class='metric-label'>Benchmark (S&P 500) regime</div>"
                f"<div class='metric-big' style='font-size:1.3rem'>{scan['market_regime']}</div></div>",
                unsafe_allow_html=True)
    st.markdown("**Evidence used:**")
    for e in scan["market_evidence"]:
        st.markdown(f"<div class='evidence'>• {e}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Inspect any instrument's regime & chart:**")
    names = config.all_tickers()
    pick = st.selectbox("Instrument", options=list(names.keys()),
                        format_func=lambda t: f"{names[t]} ({t})")
    df, real = data_engine.fetch_daily(pick, config.DATA["lookback_days"])
    if df is not None and len(df) > 60:
        reg, score, ev = regime_mod.classify_regime(df)
        st.markdown(f"Regime: **{reg}**  ·  ADX {score['adx']:.1f}  ·  RSI {score['rsi']:.1f}")
        for e in ev:
            st.markdown(f"<div class='evidence'>• {e}</div>", unsafe_allow_html=True)
        d = ind.enrich(df).tail(120)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                            vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=d.index, open=d["Open"], high=d["High"],
                                     low=d["Low"], close=d["Close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=d.index, y=d["SMA20"], line=dict(color="#9fd1ff", width=1),
                                 name="SMA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=d.index, y=d["SMA50"], line=dict(color="#e8d18a", width=1),
                                 name="SMA50"), row=1, col=1)
        fig.add_trace(go.Bar(x=d.index, y=d["Volume"], marker_color="rgba(150,160,190,0.4)",
                             name="Vol"), row=2, col=1)
        fig.update_layout(height=560, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", xaxis_rangeslider_visible=False,
                          margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

# ===== 3. SCANNER =====
with tabs[2]:
    st.subheader("Opportunity Scanner — all detected setups, ranked by expectancy")
    st.caption("Every valid setup across the universe. The top 3 that pass the professional "
               "checklist become recommendations. EV is in R-multiples (units of risk).")
    cands = scan["candidates"]
    if cands:
        rows = []
        for c in cands:
            rows.append({
                "Instrument": c["instrument"], "Dir": c["direction"], "Strategy": c["strategy"],
                "EV (R)": round(c["ev_R"], 2), "Win%": round(c["win_prob"] * 100, 0),
                "R:R": c["rr"], "Conf": c["confidence"], "Fit": round(c["regime_fit"], 2),
                "Passed": "✅" if c.get("checklist_passed") else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=520)
    else:
        st.info("No setups detected in the current scan.")

# ===== 4. RECOMMENDATIONS =====
with tabs[3]:
    st.subheader("Ranked Trade Recommendations")
    if not recs:
        st.markdown("<div class='card'>🟡 <b>No trades recommended today.</b> No setup cleared the "
                    "professional checklist with positive modelled expectancy. The correct action is "
                    "to <b>stay in cash</b> and preserve capital. Not trading is a high-quality decision.</div>",
                    unsafe_allow_html=True)
    for i, r in enumerate(recs, 1):
        tag = "tag-long" if r["direction"] == "long" else "tag-short"
        st.markdown(f"<div class='card'>"
                    f"<h3 style='margin:0'>#{i} &nbsp; {r['instrument']} "
                    f"<span class='tag {tag}'>{r['direction'].upper()}</span> "
                    f"<span style='font-size:0.8rem;color:#8b93a7'>{r['strategy']} · {r['group']}</span></h3>",
                    unsafe_allow_html=True)
        m = st.columns(6)
        m[0].markdown(f"<div class='metric-label'>Entry</div><div class='mono'>{fmt(r['entry'],4)}</div>", unsafe_allow_html=True)
        m[1].markdown(f"<div class='metric-label'>Stop</div><div class='mono'>{fmt(r['stop'],4)}</div>", unsafe_allow_html=True)
        m[2].markdown(f"<div class='metric-label'>Target 1</div><div class='mono'>{fmt(r['target1'],4)}</div>", unsafe_allow_html=True)
        m[3].markdown(f"<div class='metric-label'>Target 2</div><div class='mono'>{fmt(r['target2'],4)}</div>", unsafe_allow_html=True)
        m[4].markdown(f"<div class='metric-label'>R:R</div><div class='mono'>{fmt(r['rr'],1)}</div>", unsafe_allow_html=True)
        m[5].markdown(f"<div class='metric-label'>Confidence</div><div class='mono'>{r['confidence']}</div>", unsafe_allow_html=True)

        m2 = st.columns(6)
        m2[0].markdown(f"<div class='metric-label'>Win prob*</div><div class='mono'>{fmt(r['win_prob']*100,0)}%</div>", unsafe_allow_html=True)
        m2[1].markdown(f"<div class='metric-label'>Loss prob*</div><div class='mono'>{fmt(r['loss_prob']*100,0)}%</div>", unsafe_allow_html=True)
        m2[2].markdown(f"<div class='metric-label'>EV (R)*</div><div class='mono'>{fmt(r['ev_R'],2)}</div>", unsafe_allow_html=True)
        m2[3].markdown(f"<div class='metric-label'>Position</div><div class='mono'>{fmt(r['units'],3)} u</div>", unsafe_allow_html=True)
        m2[4].markdown(f"<div class='metric-label'>Risk £</div><div class='mono'>£{fmt(r['monetary_risk'],2)}</div>", unsafe_allow_html=True)
        m2[5].markdown(f"<div class='metric-label'>Risk %</div><div class='mono'>{fmt(r['risk_pct'],1)}%</div>", unsafe_allow_html=True)

        with st.expander("Trade thesis & professional checklist"):
            st.markdown(f"**Instrument regime:** {r['inst_regime']}")
            st.markdown(f"**Why this trade exists:** A *{r['strategy']}* signal fired in the "
                        f"direction of the prevailing structure (regime fit {r['regime_fit']:.0%}). "
                        f"The stop sits {fmt(r['risk_per_unit'],4)} away — beyond normal noise — giving "
                        f"a {fmt(r['rr'],1)}:1 reward-to-risk to Target 1 and a modelled expectancy of "
                        f"{fmt(r['ev_R'],2)}R per unit risked.")
            st.markdown("**Checklist:**")
            for q, ok in r["checklist"]:
                st.markdown(f"{'✅' if ok else '❌'} {q}")
            st.caption("*Win prob / EV are model estimates, not measured edges.")

            st.markdown("---")
            st.markdown("**Size & log this trade**")
            # Editable order size — defaults to the suggested units, user can override
            # with their actual broker fill before logging.
            suggested_units = float(r["units"])
            user_units = st.number_input(
                "Order size (units) — edit to match your actual fill",
                min_value=0.0, value=round(suggested_units, 4),
                step=max(round(suggested_units / 20, 4), 0.0001),
                format="%.4f", key=f"units{i}",
            )

            # Recompute P&L from the USER's size, respecting direction.
            # For both long and short, distance to stop is a loss, distance to
            # target is a gain — sign handled by construction below.
            stop_dist = abs(r["entry"] - r["stop"])
            t1_dist = abs(r["target1"] - r["entry"])
            t2_dist = abs(r["target2"] - r["entry"])
            stop_pnl = -user_units * stop_dist          # always a loss
            t1_pnl = user_units * t1_dist               # gain at target 1
            t2_pnl = user_units * t2_dist               # gain at target 2
            actual_risk_pct = (abs(stop_pnl) / equity * 100) if equity else 0

            pcols = st.columns(4)
            pcols[0].markdown(f"<div class='metric-label'>If STOP hit</div>"
                              f"<div class='mono' style='color:#f29b9b'>−£{fmt(abs(stop_pnl),2)}</div>",
                              unsafe_allow_html=True)
            pcols[1].markdown(f"<div class='metric-label'>At Target 1</div>"
                              f"<div class='mono' style='color:#6fe0a8'>+£{fmt(t1_pnl,2)}</div>",
                              unsafe_allow_html=True)
            pcols[2].markdown(f"<div class='metric-label'>At Target 2</div>"
                              f"<div class='mono' style='color:#6fe0a8'>+£{fmt(t2_pnl,2)}</div>",
                              unsafe_allow_html=True)
            pcols[3].markdown(f"<div class='metric-label'>Actual risk</div>"
                              f"<div class='mono'>{fmt(actual_risk_pct,2)}%</div>",
                              unsafe_allow_html=True)

            # Warn if the manual size pushes risk beyond the account rule.
            if actual_risk_pct > config.ACCOUNT["max_risk_per_trade_pct"] + 0.001:
                st.warning(f"⚠️ This size risks {actual_risk_pct:.2f}% of equity — above your "
                           f"{config.ACCOUNT['max_risk_per_trade_pct']}% per-trade limit. "
                           "Consider reducing units.", icon="⚠️")

            if st.button(f"📓 Log #{i} to journal", key=f"log{i}"):
                journal.add_entry({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "instrument": r["instrument"], "strategy": r["strategy"],
                    "direction": r["direction"], "entry": r["entry"], "stop": r["stop"],
                    "target1": r["target1"], "target2": r["target2"],
                    "risk_pct": round(actual_risk_pct, 3),
                    "monetary_risk": round(abs(stop_pnl), 2),
                    "win_prob": r["win_prob"], "ev_R": r["ev_R"],
                    "confidence": r["confidence"], "regime": r["inst_regime"],
                    "status": "open", "outcome_R": "", "pnl": "", "notes": "",
                    "units": round(user_units, 4),
                    "stop_pnl": round(stop_pnl, 2),
                    "target1_pnl": round(t1_pnl, 2),
                })
                st.success(f"Logged {r['instrument']} — {user_units:.4f} units, "
                           f"£{abs(stop_pnl):.2f} at risk.")
        st.markdown("</div>", unsafe_allow_html=True)

# ===== 5. OPENING RANGE (US 09:30 ET) =====
with tabs[4]:
    st.subheader("🔔 Opening Range Breakout — US Session (09:30 ET)")
    st.caption("Tracks the first 15–30 minutes after the US open, lets the range "
               "FORM, then flags a breakout only after the range completes AND price "
               "closes beyond it with confirmation. It never fires in the opening "
               "minutes — that window is noise.")

    st.markdown("<div class='banner'>⚠️ Intraday data here is via yfinance and is "
                "<b>delayed (typically ~15 min)</b>, not a live feed. Treat signals as "
                "study/planning prompts, NOT real-time execution triggers. The opening "
                "range is a high-variance window even when traded with discipline.</div>",
                unsafe_allow_html=True)

    rng_choice = st.radio("Opening range length", [15, 30], index=1, horizontal=True,
                          format_func=lambda m: f"{m} minutes")

    # Daily direction per ORB ticker (from daily bars) to confirm breakouts.
    @st.cache_data(ttl=900, show_spinner="Checking opening range…")
    def _orb_scan(range_minutes):
        directions = {}
        for t in orb_mod.ORB_TICKERS:
            df, _real = data_engine.fetch_daily(t, 120)
            if df is not None and len(df) > 60:
                _reg, score, _ev = regime_mod.classify_regime(df)
                directions[t] = score.get("direction", "mixed")
            else:
                directions[t] = "mixed"
        return orb_mod.scan_orb(directions, range_minutes=range_minutes)

    session_status, orb_results = _orb_scan(rng_choice)

    status_msg = {
        "pre-open": "🌙 US session hasn't opened yet (opens 09:30 ET). Check back after the open.",
        "building": f"⏳ Opening range is still forming. No signals until the {rng_choice}-min range completes — by design.",
        "active": "🟢 Session active — range complete. Any confirmed breakouts appear below.",
        "closed": "🔒 US session closed for today. Showing the final read.",
    }.get(session_status, "")
    st.info(status_msg)

    any_real = any(r["is_real_data"] for r in orb_results)
    if not any_real:
        st.warning("No live intraday data reached (offline, or US market closed). "
                   "Signals require an active session with data.", icon="🧪")

    signals = [r for r in orb_results if r["signal"]]
    if signals:
        st.markdown(f"**{len(signals)} confirmed breakout(s):**")
        for r in signals:
            s = r["signal"]
            tag = "tag-long" if s["direction"] == "long" else "tag-short"
            conf = "daily-trend aligned" if s["aligned_with_daily"] else "volume-confirmed"
            sizing = risk_mod.position_size(equity, s["entry"], s["stop"])
            units = sizing["units"] if sizing else 0
            st.markdown(f"<div class='card'>"
                        f"<h3 style='margin:0'>{r['name']} "
                        f"<span class='tag {tag}'>{s['direction'].upper()}</span> "
                        f"<span style='font-size:0.78rem;color:#8b93a7'>{conf}</span></h3>",
                        unsafe_allow_html=True)
            cols = st.columns(5)
            cols[0].markdown(f"<div class='metric-label'>Entry</div><div class='mono'>{s['entry']:.2f}</div>", unsafe_allow_html=True)
            cols[1].markdown(f"<div class='metric-label'>Stop</div><div class='mono'>{s['stop']:.2f}</div>", unsafe_allow_html=True)
            cols[2].markdown(f"<div class='metric-label'>Target 1</div><div class='mono'>{s['target1']:.2f}</div>", unsafe_allow_html=True)
            cols[3].markdown(f"<div class='metric-label'>R:R</div><div class='mono'>{s['rr']}</div>", unsafe_allow_html=True)
            cols[4].markdown(f"<div class='metric-label'>Size (1%)</div><div class='mono'>{units:.2f} u</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='evidence'>Range: {r['range_low']:.2f} – {r['range_high']:.2f} "
                        f"({r['range_minutes']}-min) · {r['note']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    elif session_status in ("active", "closed"):
        st.markdown("<div class='card'>No confirmed opening-range breakouts. Most days "
                    "either stay inside the range or break out without confirmation — "
                    "and the disciplined response is to pass. No signal is a valid result.</div>",
                    unsafe_allow_html=True)

    with st.expander("All tracked tickers & their opening-range state"):
        rows = []
        for r in orb_results:
            rows.append({
                "Ticker": r["ticker"],
                "Status": r["status"],
                "Range low": None if r["range_low"] is None else round(r["range_low"], 2),
                "Range high": None if r["range_high"] is None else round(r["range_high"], 2),
                "Signal": r["signal"]["direction"] if r["signal"] else "—",
                "Note": r["note"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=380)

# ===== 6. RISK =====
with tabs[5]:
    st.subheader("Risk Dashboard")
    open_trades = recs  # treat current recs as prospective portfolio
    pr = risk_mod.portfolio_risk(open_trades, equity)
    r1 = st.columns(4)
    r1[0].markdown(f"<div class='card'><div class='metric-label'>Open positions</div>"
                   f"<div class='metric-big'>{pr['open_positions']}/{config.ACCOUNT['max_simultaneous_positions']}</div></div>", unsafe_allow_html=True)
    r1[1].markdown(f"<div class='card'><div class='metric-label'>Total risk on</div>"
                   f"<div class='metric-big'>£{fmt(pr['total_monetary_risk'],2)}</div>"
                   f"<div class='evidence'>{fmt(pr['total_risk_pct'],1)}% of equity</div></div>", unsafe_allow_html=True)
    r1[2].markdown(f"<div class='card'><div class='metric-label'>Daily loss limit</div>"
                   f"<div class='metric-big'>£{fmt(pr['daily_loss_limit'],2)}</div></div>", unsafe_allow_html=True)
    r1[3].markdown(f"<div class='card'><div class='metric-label'>Weekly DD limit</div>"
                   f"<div class='metric-big'>£{fmt(pr['weekly_dd_limit'],2)}</div></div>", unsafe_allow_html=True)

    if pr["total_risk_pct"] > config.ACCOUNT["max_daily_loss_pct"]:
        st.error("⚠️ Combined risk exceeds the daily loss limit. Reduce position count or size.")
    else:
        st.success("✅ Portfolio risk within all account limits.")

    st.markdown("**Per-trade risk breakdown:**")
    if open_trades:
        rb = pd.DataFrame([{
            "Instrument": t["instrument"], "Dir": t["direction"],
            "Risk £": round(t["monetary_risk"], 2), "Risk %": round(t["risk_pct"], 2),
            "Stop dist": round(t["risk_per_unit"], 4), "Units": round(t["units"], 3),
            "Exposure £": round(t["exposure"], 2),
        } for t in open_trades])
        st.dataframe(rb, use_container_width=True)
    else:
        st.info("No prospective positions — zero risk on. Capital fully preserved.")

    # ---- Spread-bet £/point converter ----
    st.markdown("---")
    st.markdown("### 🔁 Spread-bet sizing helper (e.g. IG)")
    st.caption("Spread betting sizes in £ per point, not units. This converts between "
               "your risk in £, your stop distance in POINTS, and the £/point stake to "
               "enter at your broker. Match the £ RISK — the unit numbers will never "
               "look alike, and that's fine.")

    cc = st.columns(3)
    risk_gbp = cc[0].number_input(
        "Risk (£)", min_value=0.0,
        value=round(equity * config.ACCOUNT["max_risk_per_trade_pct"] / 100, 2),
        step=5.0, key="sb_risk",
        help="Default = your 1% per-trade limit on current equity.")
    stop_pts = cc[1].number_input(
        "Stop distance (points)", min_value=0.1, value=73.0, step=1.0,
        key="sb_stop", help="The stop distance your broker shows, in points/pips.")
    # Forward: £/point you should stake
    stake = risk_gbp / stop_pts if stop_pts > 0 else 0
    cc[2].markdown(f"<div class='card' style='margin-top:6px'>"
                   f"<div class='metric-label'>Stake to enter</div>"
                   f"<div class='metric-big' style='font-size:1.4rem'>£{fmt(stake,2)}</div>"
                   f"<div class='evidence'>per point</div></div>", unsafe_allow_html=True)

    # Reverse check: given a stake, what's the actual £ risk?
    st.markdown("**Reverse check** — enter a £/point stake to see the real £ risk it carries:")
    rc = st.columns(3)
    stake_in = rc[0].number_input("£/point stake", min_value=0.0, value=round(stake, 2),
                                  step=0.1, key="sb_stake_in")
    actual_risk = stake_in * stop_pts
    actual_pct = (actual_risk / equity * 100) if equity else 0
    rc[1].markdown(f"<div class='card' style='margin-top:6px'>"
                   f"<div class='metric-label'>Risk at this stake</div>"
                   f"<div class='metric-big' style='font-size:1.4rem'>£{fmt(actual_risk,2)}</div></div>",
                   unsafe_allow_html=True)
    rc[2].markdown(f"<div class='card' style='margin-top:6px'>"
                   f"<div class='metric-label'>% of equity</div>"
                   f"<div class='metric-big' style='font-size:1.4rem'>{fmt(actual_pct,2)}%</div></div>",
                   unsafe_allow_html=True)
    if actual_pct > config.ACCOUNT["max_risk_per_trade_pct"] + 0.001:
        st.warning(f"⚠️ £{stake_in:.2f}/point over a {stop_pts:.0f}-point stop risks "
                   f"{actual_pct:.2f}% — above your {config.ACCOUNT['max_risk_per_trade_pct']}% "
                   "limit. Reduce the stake.", icon="⚠️")
    st.caption("Note: spread-bet P&L is in the instrument's points. Currency conversion "
               "(e.g. USD pairs settling to £) and overnight financing mean your broker's "
               "figure may differ slightly — always sanity-check against the broker's own "
               "risk display before submitting.")

# ===== 7. PERFORMANCE =====
with tabs[6]:
    st.subheader("Performance Analytics")
    perf = journal.performance(equity)
    if perf["n_trades"] == 0:
        st.info("No closed trades logged yet. Log trades in Recommendations, then record outcomes "
                "in the Journal tab. Analytics populate automatically.")
    else:
        if perf["sample_warning"]:
            st.warning(f"Only {perf['n_trades']} closed trades logged. Statistics are NOT yet "
                       "reliable — a meaningful edge needs ~30+ (ideally 100+) trades.", icon="📉")
        p = st.columns(4)
        p[0].markdown(f"<div class='card'><div class='metric-label'>Win rate</div><div class='metric-big'>{fmt(perf['win_rate']*100,1)}%</div></div>", unsafe_allow_html=True)
        p[1].markdown(f"<div class='card'><div class='metric-label'>Profit factor</div><div class='metric-big'>{fmt(perf['profit_factor'],2)}</div></div>", unsafe_allow_html=True)
        p[2].markdown(f"<div class='card'><div class='metric-label'>Expectancy/trade</div><div class='metric-big'>£{fmt(perf['expectancy'],2)}</div></div>", unsafe_allow_html=True)
        p[3].markdown(f"<div class='card'><div class='metric-label'>Max drawdown</div><div class='metric-big'>{fmt(perf['max_drawdown_pct'],1)}%</div></div>", unsafe_allow_html=True)
        p2 = st.columns(4)
        p2[0].markdown(f"<div class='card'><div class='metric-label'>Avg win</div><div class='metric-big'>£{fmt(perf['avg_win'],2)}</div></div>", unsafe_allow_html=True)
        p2[1].markdown(f"<div class='card'><div class='metric-label'>Avg loss</div><div class='metric-big'>£{fmt(perf['avg_loss'],2)}</div></div>", unsafe_allow_html=True)
        p2[2].markdown(f"<div class='card'><div class='metric-label'>Sharpe (ann.)</div><div class='metric-big'>{fmt(perf['sharpe'],2)}</div></div>", unsafe_allow_html=True)
        p2[3].markdown(f"<div class='card'><div class='metric-label'>Total P&L</div><div class='metric-big'>£{fmt(perf['total_pnl'],2)}</div></div>", unsafe_allow_html=True)

        eq = perf["equity_curve"]
        fig = go.Figure(go.Scatter(y=eq, mode="lines", line=dict(color="#6fe0a8", width=2),
                                   fill="tozeroy", fillcolor="rgba(111,224,168,0.08)"))
        fig.update_layout(height=360, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", title="Equity Curve",
                          margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ===== 8. JOURNAL =====
with tabs[7]:
    st.subheader("Trading Journal")
    _backend, _detail = journal.backend_status()
    if _backend == "Google Sheets":
        st.success(f"📒 Storage: **{_backend}** — {_detail}", icon="✅")
    else:
        st.info(f"📒 Storage: **{_backend}** — {_detail}")
    jdf = journal.load()
    if jdf.empty:
        st.info("Journal is empty. Log trades from the Recommendations tab.")
    else:
        st.dataframe(jdf, use_container_width=True, height=340)
        st.markdown("**Record an outcome** (close an open trade):")
        open_idx = jdf.index[jdf["status"] == "open"].tolist()
        if open_idx:
            oc = st.columns(4)
            sel = oc[0].selectbox("Trade row", open_idx,
                                  format_func=lambda i: f"{i}: {jdf.loc[i,'instrument']} {jdf.loc[i,'direction']}")
            out_r = oc[1].number_input("Outcome (R)", value=0.0, step=0.5)
            pnl = oc[2].number_input("P&L (£)", value=0.0, step=1.0)
            note = oc[3].text_input("Note", "")
            if st.button("Save outcome"):
                journal.record_outcome(int(sel), out_r, pnl, "closed", note)
                st.success("Outcome recorded.")
                st.rerun()
        else:
            st.caption("No open trades to close.")

# ===== 9. LEARNING CENTRE =====
with tabs[8]:
    st.subheader("🎓 Daily Learning Centre")
    st.caption("Generated from TODAY's actual analysis — not generic lessons.")

    concept, body = education.lesson_of_the_day(scan["market_regime"], scan["internals"], len(recs))
    st.markdown(f"<div class='card'><h3>Lesson of the Day — {concept}</h3>{body}</div>",
                unsafe_allow_html=True)

    st.markdown(f"<div class='card'><h3>Why Today's Trades Were Selected</h3>"
                f"{education.why_selected(recs)}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='card'><h3>Institutional Thinking</h3>"
                f"{education.institutional_thinking(scan['market_regime'], scan['tone_label'])}</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>Mistakes To Avoid Today</h3>", unsafe_allow_html=True)
    for title, why in education.mistakes_today(scan["market_regime"]):
        st.markdown(f"**❌ {title}** — {why}")
    st.markdown("</div>", unsafe_allow_html=True)

    level, ex = education.skill_exercise(scan["market_regime"], recs)
    st.markdown(f"<div class='card'><h3>Skill Development</h3>"
                f"<span class='tag tag-long'>{level}</span><br><br>{ex}</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>Trading Vocabulary</h3>", unsafe_allow_html=True)
    for term, definition, example in education.vocab_for_today(scan["market_regime"], recs):
        st.markdown(f"**{term}** — {definition}  \n*Today:* {example}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Built for education and decision discipline. Not financial advice. "
           "All estimates are model outputs, not predictions.")
