"""
journal.py — Trade journal persistence and performance analytics.

Storage backend is pluggable and chosen automatically:

  • Google Sheets — used when Streamlit secrets contain a [gcp_service_account]
    block AND a sheet name/URL. This PERSISTS across redeploys, so it's the right
    choice for the Streamlit Cloud / phone setup.
  • Local CSV — fallback for local runs or when Sheets isn't configured. Does NOT
    survive a cloud redeploy (Streamlit Cloud storage is ephemeral).

The public functions (load / add_entry / record_outcome / performance) are
unchanged from the CSV-only version, so the rest of the app doesn't care which
backend is active. backend_status() lets the UI show which one is live.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from . import config

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
COLUMNS = [
    "date", "instrument", "strategy", "direction", "entry", "stop",
    "target1", "target2", "risk_pct", "monetary_risk", "win_prob",
    "ev_R", "confidence", "regime", "status", "outcome_R", "pnl",
    "notes",
]

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "journal.csv")

# Worksheet/tab name inside the Google Sheet
WORKSHEET = "journal"


# ---------------------------------------------------------------------------
# Backend detection (cached so we only build the client once)
# ---------------------------------------------------------------------------
_sheet_cache = {"checked": False, "ws": None, "error": None}


def _get_secret(key, default=None):
    """Read a Streamlit secret without crashing when secrets aren't present."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


def _gsheet_worksheet():
    """
    Return an authorised gspread worksheet, or None if Sheets isn't configured
    / libraries are missing / auth fails. Result is cached for the session.
    """
    if _sheet_cache["checked"]:
        return _sheet_cache["ws"]
    _sheet_cache["checked"] = True

    try:
        import streamlit as st
        if "gcp_service_account" not in st.secrets:
            return None
        sheet_id = _get_secret("gsheet_name") or _get_secret("gsheet_url")
        if not sheet_id:
            _sheet_cache["error"] = "No 'gsheet_name' or 'gsheet_url' in secrets."
            return None

        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)

        if str(sheet_id).startswith("http"):
            spreadsheet = client.open_by_url(sheet_id)
        else:
            spreadsheet = client.open(sheet_id)

        try:
            ws = spreadsheet.worksheet(WORKSHEET)
        except Exception:
            ws = spreadsheet.add_worksheet(title=WORKSHEET, rows=1000, cols=len(COLUMNS))
        existing = ws.row_values(1)
        if existing != COLUMNS:
            ws.update([COLUMNS], "A1")
        _sheet_cache["ws"] = ws
        return ws
    except Exception as e:
        _sheet_cache["error"] = str(e)
        _sheet_cache["ws"] = None
        return None


def backend_status():
    """('Google Sheets' | 'Local CSV', detail_str) for display in the UI."""
    ws = _gsheet_worksheet()
    if ws is not None:
        return "Google Sheets", "Persists across redeploys"
    detail = "Ephemeral — resets on redeploy. Configure Google Sheets to persist."
    if _sheet_cache.get("error"):
        detail += f"  (Sheets not active: {_sheet_cache['error']})"
    return "Local CSV", detail


# ---------------------------------------------------------------------------
# CSV backend helpers
# ---------------------------------------------------------------------------
def _csv_ensure():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(CSV_PATH, index=False)


def _csv_load():
    _csv_ensure()
    try:
        df = pd.read_csv(CSV_PATH)
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""
        return df[COLUMNS]
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def _csv_save(df):
    _csv_ensure()
    df.to_csv(CSV_PATH, index=False)


# ---------------------------------------------------------------------------
# Google Sheets backend helpers
# ---------------------------------------------------------------------------
def _gs_load(ws):
    records = ws.get_all_records(expected_headers=COLUMNS)
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(records)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS]


def _gs_append(ws, row_dict):
    ordered = [row_dict.get(c, "") for c in COLUMNS]
    ordered = ["" if v is None else v for v in ordered]
    ws.append_row(ordered, value_input_option="USER_ENTERED")


def _gs_update_cell(ws, df_index, col_name, value):
    # +2: 1 for header row, 1 because gspread rows are 1-indexed.
    row_num = df_index + 2
    col_num = COLUMNS.index(col_name) + 1
    ws.update_cell(row_num, col_num, value)


# ---------------------------------------------------------------------------
# PUBLIC API  (identical signatures regardless of backend)
# ---------------------------------------------------------------------------
def load():
    ws = _gsheet_worksheet()
    if ws is not None:
        try:
            return _gs_load(ws)
        except Exception:
            pass
    return _csv_load()


def add_entry(row: dict):
    full = {c: row.get(c, "") for c in COLUMNS}
    ws = _gsheet_worksheet()
    if ws is not None:
        try:
            _gs_append(ws, full)
            return load()
        except Exception:
            pass
    df = _csv_load()
    df = pd.concat([df, pd.DataFrame([full])], ignore_index=True)
    _csv_save(df)
    return df


def record_outcome(index, outcome_R, pnl, status="closed", notes=""):
    ws = _gsheet_worksheet()
    if ws is not None:
        try:
            _gs_update_cell(ws, index, "outcome_R", outcome_R)
            _gs_update_cell(ws, index, "pnl", pnl)
            _gs_update_cell(ws, index, "status", status)
            if notes:
                _gs_update_cell(ws, index, "notes", notes)
            return load()
        except Exception:
            pass
    df = _csv_load()
    if 0 <= index < len(df):
        df["status"] = df["status"].astype("object")
        df["notes"] = df["notes"].astype("object")
        df.loc[index, "outcome_R"] = outcome_R
        df.loc[index, "pnl"] = pnl
        df.loc[index, "status"] = status
        if notes:
            df.loc[index, "notes"] = notes
        _csv_save(df)
    return df


def performance(equity_start=None):
    """Compute analytics from closed trades. Honest about small samples."""
    equity_start = equity_start or config.ACCOUNT["starting_capital"]
    df = load()
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)
    closed = df[df["status"] == "closed"].copy()
    closed["pnl"] = pd.to_numeric(closed["pnl"], errors="coerce")
    closed = closed.dropna(subset=["pnl"])

    n = len(closed)
    stats = {"n_trades": n, "sample_warning": n < 30}
    if n == 0:
        stats.update({
            "win_rate": np.nan, "avg_win": np.nan, "avg_loss": np.nan,
            "profit_factor": np.nan, "expectancy": np.nan, "sharpe": np.nan,
            "max_drawdown_pct": np.nan, "total_pnl": 0.0,
            "equity_curve": pd.Series([equity_start]),
        })
        return stats

    wins = closed[closed["pnl"] > 0]["pnl"]
    losses = closed[closed["pnl"] < 0]["pnl"]
    win_rate = len(wins) / n
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan
    expectancy = closed["pnl"].mean()

    daily = closed["pnl"]
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else np.nan

    equity_curve = equity_start + closed["pnl"].cumsum()
    equity_curve = pd.concat([pd.Series([equity_start]), equity_curve], ignore_index=True)
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min() * 100

    stats.update({
        "win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss,
        "profit_factor": profit_factor, "expectancy": expectancy,
        "sharpe": sharpe, "max_drawdown_pct": max_dd,
        "total_pnl": closed["pnl"].sum(), "equity_curve": equity_curve,
    })
    return stats
