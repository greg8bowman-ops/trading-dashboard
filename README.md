# 📈 Quant Day Trading Desk

A professional, education-first day-trading dashboard built in Python + Streamlit.
It scans equities, FX, indices and commodities each day, classifies the market
regime, ranks setups by **expected value**, enforces strict risk rules, journals
your trades, tracks performance, and teaches you how professionals think — using
*that day's actual analysis*, not generic lessons.

---

## ⚠️ Read this first (honest expectations)

- **Every probability, win-rate and EV number is a MODEL ESTIMATE**, derived from
  rule-based heuristics and historical price behaviour. They are **not predictions
  and not a measured edge.** A real edge can only be confirmed after you log a
  large sample (100+) of your own live trades.
- **Most retail day traders lose money** over time. This tool exists to make you a
  more *disciplined decision-maker* and to teach process — not to promise profit.
- On a £1,000 account, spreads, commissions and slippage consume a meaningful
  share of any per-trade edge. Size and cost reality matter.
- **This is not financial advice.**

The most valuable habit this dashboard builds: it will frequently tell you the
best action is **to do nothing.** Cash is a position.

---

## 🚀 Setup

```bash
cd trading_dashboard
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

> **Data:** With internet access, it pulls real daily prices via `yfinance`.
> If no feed is reachable (offline / weekend / rate-limit), it falls back to
> clearly-labelled **synthetic demo data** so you can still explore — never
> mistake demo numbers for the market.

---

## 🧱 Architecture

```
trading_dashboard/
├── app.py                  # Streamlit UI — 9 sections
├── requirements.txt
├── data/                   # journal.csv persists here
└── modules/
    ├── config.py           # account rules, instrument universe, disclaimer
    ├── data_engine.py      # yfinance fetch + synthetic fallback
    ├── indicators.py       # SMA/EMA/ATR/RSI/ADX/Bollinger/VWAP/vol
    ├── regime.py           # regime classification + breadth/internals
    ├── strategies.py       # setup detectors + EV scoring + regime fit
    ├── risk.py             # position sizing + checklist + portfolio risk
    ├── scanner.py          # orchestrator: the daily pipeline & ranking
    ├── opening_range.py    # US 09:30 ET opening-range breakout (intraday)
    ├── journal.py          # CSV persistence + performance analytics
    └── education.py        # daily learning content from real analysis
```

Each module is independent and unit-testable. Swap `data_engine` for a broker
API, or tune `STRATEGY_PRIORS` / `REGIME_FIT` in `strategies.py` as you gather
real results.

---

## 🖥️ The 9 sections

1. **Overview** — breadth, momentum, relative-strength map.
2. **Regime** — benchmark + per-instrument regime with the *evidence* used, plus candle charts.
3. **Scanner** — every detected setup ranked by expectancy; shows which pass the checklist.
4. **Recommendations** — 0–3 trades with entry/stop/targets, sizing, EV, thesis, checklist, one-click journaling.
5. **Opening Range** — US 09:30 ET opening-range breakout. Waits for the first 15–30 min range to *form*, then flags a breakout only after it completes AND price closes beyond it with confirmation (daily-trend aligned or volume surge). Uses **delayed** intraday data — a planning prompt, not a live execution trigger.
6. **Risk** — portfolio heat vs daily/weekly/per-trade limits.
7. **Performance** — win rate, profit factor, expectancy, Sharpe, max DD, equity curve (with small-sample warnings).
8. **Journal** — full trade log; record outcomes to feed analytics.
9. **Learning Centre** — lesson of the day, why-selected, institutional thinking, mistakes, skill drill, vocabulary — all generated from today's scan.

---

## ⏱️ Update cadence

- **Daily Recommendations** run on **daily** price bars — they meaningfully change **once per day**, after the prior session closes. Check once each morning; re-scanning intraday shows the same daily-bar analysis.
- **Opening Range** is the one intraday section. After the US 09:30 ET open it tracks the forming range, then evaluates breakouts once the 15/30-min range completes. Data is delayed ~15 min, so it's for planning, not split-second entries.

---

## 🔧 How the ranking works

1. Fetch the universe → compute breadth, momentum, relative strength.
2. Classify each instrument's regime (ADX trend strength + MA alignment + volatility).
3. Run every strategy detector; keep setups whose style **fits the regime**.
4. Score each: `EV = WinProb × AvgWin − LossProb × AvgLoss` (in R-multiples).
5. Rank by EV → apply the 7-point professional checklist → size the top 3 that pass.
6. If none pass: **recommend cash.**

---

## 🛣️ Sensible next steps

- Replace heuristic priors with **your own logged statistics** once you have a sample.
- Add intraday timeframes / a proper backtester to *measure* (not assume) expectancy.
- Wire in a real broker/data API and account for spread + commission per instrument.
- Paper-trade the recommendations for months before risking real capital.

---

## 📂 Extra guides in this folder

- **`DEPLOY_TO_ANDROID.md`** — put this on a free public URL via Streamlit Cloud and
  add it to your Android home screen (acts like an app).
- **`SETUP_GOOGLE_SHEETS.md`** — make the trade journal **persist across redeploys**
  by connecting a Google Sheet. Without it, the journal uses a local CSV that resets
  on each cloud redeploy. The Journal tab shows which backend is active.
