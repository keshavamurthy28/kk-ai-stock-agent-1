from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

# --- UNIFIED WORKFLOW SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.page_link(
    "pages/01_Sector_Rotation_Scanner.py",
    label="1️⃣ Sector Rotation & Macro Pulse",
    icon="🗺️",
)
st.sidebar.page_link(
    "pages/02_Smart_Money_Pulse.py",
    label="2️⃣ Smart Money Flow Terminal",
    icon="⚡",
)
st.sidebar.page_link(
    "pages/02_Night_Before_Prep_Scanner.py",
    label="3️⃣ Night-Before Prep & Coiling",
    icon="🌙",
)
st.sidebar.page_link(
    "pages/02_Matched_Super_Signal_Page.py",
    label="4️⃣ Live Super-Signal Triggers",
    icon="🎯",
)
st.sidebar.page_link(
    "pages/02_PRIME 2-5 INTRADAY SNIPER.py",
    label="5️⃣ Intraday Sniper & Top Picks",
    icon="📈",
)
st.sidebar.markdown("---")

if "nav_sector" not in st.session_state:
  st.session_state.nav_sector = None
if "nav_stock" not in st.session_state:
  st.session_state.nav_stock = None

MACRO_INDICES = {
    "Nifty 50": "^NSEI",
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO",
    "Nifty FMCG": "^CNXFMCG",
}

SECTOR_STOCKS = {
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
    ],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Pharma": [
        "SUNPHARMA.NS",
        "CIPLA.NS",
        "DRREDDY.NS",
        "DIVISLAB.NS",
        "MAXHEALTH.NS",
    ],
    "Energy & Oil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
}


@st.cache_data(ttl=900)
def fetch_macro_data():
  all_syms = list(MACRO_INDICES.values()) + [
      t for stocks in SECTOR_STOCKS.values() for t in stocks
  ]
  raw = yf.download(
      all_syms,
      period="3mo",
      interval="1d",
      group_by="ticker",
      progress=False,
      threads=True,
  )

  index_metrics = {}
  for name, symbol in MACRO_INDICES.items():
    try:
      df = raw[symbol]["Close"].dropna()
      if not df.empty:
        ltp, prev = float(df.iloc[-1]), float(df.iloc[-2])
        chg = ((ltp - prev) / prev) * 100
        index_metrics[name] = {"LTP": round(ltp, 2), "Chg%": round(chg, 2)}
    except Exception:
      pass
  return index_metrics


st.title("🗺️ Step 1: Institutional Sector Rotation & Macro Pulse")
st.markdown(
    "Analyze headline index performance and sector momentum *before* drilling"
    " down into individual stock flows."
)

metrics = fetch_macro_data()
cols = st.columns(len(MACRO_INDICES))
for i, (name, _) in enumerate(MACRO_INDICES.items()):
  with cols[i]:
    if name in metrics:
      st.metric(
          name,
          f"₹{metrics[name]['LTP']:,.2f}",
          f"{metrics[name]['Chg%']:+.2f}%",
      )

st.markdown("---")
st.success(
    "💡 **Next Workflow Step:** Proceed to **Smart Money Flow Terminal** in the"
    " sidebar to inspect real-time institutional capital inflows/outflows in"
    " Crores."
)
