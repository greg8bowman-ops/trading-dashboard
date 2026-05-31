"""
config.py — Central configuration for the trading dashboard.

All account rules, the instrument universe, and tunable parameters live here so
they can be changed in one place. Nothing in this file is a promise about
returns; these are the *rules of engagement* the system enforces on itself.
"""

# ---------------------------------------------------------------------------
# ACCOUNT RULES  (hard limits — the system must never recommend breaching these)
# ---------------------------------------------------------------------------
ACCOUNT = {
    "starting_capital": 1000.0,      # £
    "currency": "GBP",
    "max_risk_per_trade_pct": 1.0,   # % of equity risked per trade
    "max_daily_loss_pct": 3.0,       # stop trading for the day if hit
    "max_weekly_drawdown_pct": 6.0,  # stop trading for the week if hit
    "max_simultaneous_positions": 3,
}

# ---------------------------------------------------------------------------
# INSTRUMENT UNIVERSE
# yfinance tickers. FX/commodities use Yahoo's '=X' and '=F' conventions.
# ---------------------------------------------------------------------------
UNIVERSE = {
    "Equities": {
        "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
        "AMZN": "Amazon", "META": "Meta", "GOOGL": "Alphabet",
        "TSLA": "Tesla", "JPM": "JPMorgan", "XOM": "Exxon",
        "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF",
    },
    "FX": {
        "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "JPY=X": "USD/JPY",
        "CHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "NZDUSD=X": "NZD/USD",
        "CAD=X": "USD/CAD",
    },
    "Indices": {
        "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones",
        "^FTSE": "FTSE 100", "^GDAXI": "DAX", "^N225": "Nikkei 225",
    },
    "Commodities": {
        "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil",
    },
}

def all_tickers():
    out = {}
    for group in UNIVERSE.values():
        out.update(group)
    return out

def ticker_group(ticker):
    for group_name, group in UNIVERSE.items():
        if ticker in group:
            return group_name
    return "Unknown"

# ---------------------------------------------------------------------------
# DATA SETTINGS
# ---------------------------------------------------------------------------
DATA = {
    "lookback_days": 250,     # daily bars for regime/indicator calc
    "intraday_period": "5d",  # for intraday context
    "intraday_interval": "15m",
}

# ---------------------------------------------------------------------------
# IMPORTANT HONESTY NOTE surfaced in the UI
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "All probabilities, win rates and expected-value figures shown are MODEL "
    "ESTIMATES derived from historical price behaviour and rule-based heuristics. "
    "They are NOT measured edges and NOT predictions. A real edge can only be "
    "confirmed after you have logged a large sample of your own live trades. "
    "Most retail day traders lose money. This tool is for education and "
    "structured decision-making, not financial advice."
)
