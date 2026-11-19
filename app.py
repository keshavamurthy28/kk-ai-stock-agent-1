from datetime import datetime, time as dt_time
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="MU₹A Rendezvous | Institutional Alpha & Catalyst Terminal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import load_ledger as _load_ledger
except Exception:
    _load_ledger = None

# ---------------------------------------------------------
# 1. CUSTOM CSS & FRONT HERO HEADER
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .hero-banner {
        background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 55%, #0F3D3E 100%);
        border: 1px solid rgba(0, 230, 118, 0.35);
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    .hero-title {
        font-size: 2.05rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0 0 6px 0;
        letter-spacing: -0.4px;
    }
    .hero-subtitle {
        font-size: 1.02rem;
        color: #CFD8DC;
        margin: 0 0 14px 0;
    }
    .status-pill-live {
        display: inline-block;
        background: rgba(0, 230, 118, 0.18);
        color: #00E676;
        border: 1px solid #00E676;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-right: 10px;
    }
    .status-pill-closed {
        display: inline-block;
        background: rgba(255, 215, 0, 0.16);
        color: #FFD700;
        border: 1px solid #FFD700;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-right: 10px;
    }
    .time-pill {
        display: inline-block;
        background: rgba(255, 255, 255, 0.08);
        color: #E0E0E0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .module-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 12px;
        padding: 16px 18px;
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pill_html = (
    '<span class="status-pill-live">🟢 LIVE NSE SESSION (9:15 AM – 3:30 PM IST)</span>'
    if is_market_open
    else '<span class="status-pill-closed">🟡 PRE-MARKET / POST-CLOSE RESEARCH MODE</span>'
)

st.markdown(
    f"""
    <div class="hero-banner">
        <div class="hero-title">🎯 MU₹A Rendezvous — Institutional Alpha & Catalyst Terminal</div>
        <div class="hero-subtitle">
            Centralized NSE Intraday Sniper, Smart Money Flow, Sector Rotation & Automated Pick-Ledger Command Center.
        </div>
        <div>
            {pill_html}
            <span class="time-pill">🕒 Synced: {now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 2. LIVE BENCHMARK & VOLATILITY PULSE (NIFTY, BANKNIFTY, VIX)
# ---------------------------------------------------------
@st.cache_data(ttl=120)
def fetch_market_pulse_indices():
    indices = {
        "NIFTY 50": "^NSEI",
        "NIFTY BANK": "^NSEBANK",
        "INDIA VIX": "^INDIAVIX",
    }
    results = {}
    try:
        raw = yf.download(
            list(indices.values()),
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            auto_adjust=True,
        )
        for label, ticker in indices.items():
            sub = pd.DataFrame()
            if isinstance(raw.columns, pd.MultiIndex) and ticker in raw.columns.get_level_values(0):
                sub = raw[ticker].dropna(subset=["Close"])
            if len(sub) >= 2:
                last_c = float(sub["Close"].iloc[-1])
                prev_c = float(sub["Close"].iloc[-2])
                chg_pct = ((last_c - prev_c) / prev_c) * 100.0 if prev_c > 0 else 0.0
                results[label] = (last_c, chg_pct)
            elif len(sub) == 1:
                results[label] = (float(sub["Close"].iloc[-1]), 0.0)
    except Exception:
        pass
    return results


pulse = fetch_market_pulse_indices()
m1, m2, m3, m4 = st.columns([1.3, 1.3, 1.3, 0.9])

with m1:
    if "NIFTY 50" in pulse:
        val, chg = pulse["NIFTY 50"]
        st.metric("🇮🇳 NIFTY 50", f"{val:,.2f}", f"{chg:+.2f}%")
    else:
        st.metric("🇮🇳 NIFTY 50", "Market Standby", "Click Refresh")

with m2:
    if "NIFTY BANK" in pulse:
        val, chg = pulse["NIFTY BANK"]
        st.metric("🏦 NIFTY BANK", f"{val:,.2f}", f"{chg:+.2f}%")
    else:
        st.metric("🏦 NIFTY BANK", "Market Standby", "Click Refresh")

with m3:
    if "INDIA VIX" in pulse:
        val, chg = pulse["INDIA VIX"]
        vix_note = "Calm / Trend-Friendly" if val < 15 else ("Elevated Volatility" if val < 20 else "High Volatility — Tight Size")
        st.metric("⚡ INDIA VIX", f"{val:.2f}", f"{chg:+.2f}% • {vix_note}", delta_color="inverse")
    else:
        st.metric("⚡ INDIA VIX", "Standby", "Volatility Gauge")

with m4:
    st.write("")
    if st.button("🔄 Refresh Pulse", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 3. QUICK-LAUNCH COMMAND MODULES (WITH SAFE PAGE LINKS)
# ---------------------------------------------------------
st.subheader("🧭 Terminal Execution & Research Modules")
st.caption("Launch any scanner directly below or use the left sidebar navigation.")


def _safe_page_link(rel_path: str, label: str, icon: str):
    target_file = REPO_ROOT / rel_path
    if target_file.exists():
        st.page_link(rel_path, label=label, icon=icon, use_container_width=True)
    else:
        st.caption(f"{icon} **{label}** *(available in sidebar)*")


col_a, col_b, col_c = st.columns(3)

with col_a:
    with st.container(border=True):
        st.markdown("### 🎯 Intraday Sniper & Breakouts")
        st.markdown(
            "- **PRIME Top 3 Sniper:** VWAP + 20 EMA + RVOL + ATR target matrix.\n"
            "- **Matched Super Signal:** Cross-checks live breakouts against Night-Before prep.\n"
            "- **Bearish Short Terminal:** Same-day VWAP breakdown shorts (cover before 3:30 PM)."
        )
        _safe_page_link("pages/05_PRIME_2-5_INTRADAY_SNIPER.py", "Open PRIME Intraday Sniper", "🎯")
        _safe_page_link("pages/04_Matched_Super_Signal_Page.py", "Open Matched Super Signal", "⚡")
        _safe_page_link("pages/Bearish.py", "Open Bearish Short Terminal", "🔻")

with col_b:
    with st.container(border=True):
        st.markdown("### 🌊 Smart Money & Sector Rotation")
        st.markdown(
            "- **Smart Money Pulse:** Top 2 Green Inflow & Top 2 Red Outflow + 15m charts.\n"
            "- **Sector Rotation Heatmap:** Nifty relative strength drill-down & sector leaders.\n"
            "- **MUDRA Advance Callouts:** Multi-factor swing & intraday execution setups."
        )
        _safe_page_link("pages/02_Smart_Money_Pulse.py", "Open Smart Money Pulse", "🌊")
        _safe_page_link("pages/01_Sector_Rotation_Scanner.py", "Open Sector Rotation Scanner", "🗺️")
        _safe_page_link("pages/MUDRA_Rendezvous_Callout_Terminal.py", "Open MUDRA Callout Terminal", "💎")

with col_c:
    with st.container(border=True):
        st.markdown("### 🧪 Ledger, Audit & Discipline")
        st.markdown(
            "- **App & Profit Analyser:** Evaluates logged Target 1 vs. Stop-Loss outcomes.\n"
            "- **Forever History Vault:** Tracks weekly hit rates & exports CSV backups.\n"
            "- **Risk Rule:** Book partial/full gains at **Target 1** and honor **Stop-Loss**."
        )
        _safe_page_link("pages/99_App_And_Profit_Analyser.py", "Open App & Profit Analyser", "🧪")
        st.info("🛡️ **Discipline Reminder:** Never average down on a losing intraday trade.")

st.markdown("---")

# ---------------------------------------------------------
# 4. LIVE SNAPSHOT OF RECENTLY LOGGED PICKS
# ---------------------------------------------------------
st.subheader("📌 Recent Logged Picks (Master History Ledger Snapshot)")

ledger_df = pd.DataFrame()
if callable(_load_ledger):
    try:
        ledger_df = _load_ledger()
    except Exception:
        ledger_df = pd.DataFrame()

if ledger_df.empty:
    fallback_csv = REPO_ROOT / "data_ledger" / "pick_click_ledger.csv"
    if fallback_csv.exists():
        try:
            ledger_df = pd.read_csv(fallback_csv)
        except Exception:
            ledger_df = pd.DataFrame()

if ledger_df.empty:
    st.info(
        "No picks logged in your Master History Ledger yet. Open any scanner above and click "
        "**Log Top Picks to History Ledger** to start building your track record."
    )
else:
    recent_cols = [
        c
        for c in ["logged_at_ist", "module", "symbol", "side", "entry_price", "stop_loss", "target_1", "target_2", "notes"]
        if c in ledger_df.columns
    ]
    st.caption(f"Showing latest **{min(8, len(ledger_df))}** of **{len(ledger_df)}** total saved picks.")
    st.dataframe(
        ledger_df[recent_cols].tail(8).iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )
