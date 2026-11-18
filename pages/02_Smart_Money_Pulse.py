from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Smart Money Pulse & Flow Terminal", layout="wide")

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

st.title("⚡ Step 2: Smart Money Pulse & Institutional Flow Terminal")
st.caption(
    "Real-time Sector-to-Stock Capital Flow, Net Inflows in Crores, and Swing"
    " Breakout Scanners."
)

SECTOR_STOCKS = {
    "Bank & PSU": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
    ],
    "IT & Tech": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Defence & CapGoods": ["HAL.NS", "BEL.NS", "LT.NS", "SIEMENS.NS"],
    "Auto": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Energy": ["RELIANCE.NS", "NTPC.NS", "ONGC.NS", "TATAPOWER.NS"],
}


def analyze_stock(symbol, sector):
  try:
    df = yf.download(symbol, period="2mo", interval="1d", progress=False)
    if df.empty or len(df) < 20:
      return None
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)

    close, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
    high, low, vol = df["High"].iloc[-1], df["Low"].iloc[-1], df["Volume"].iloc[-1]
    pct_chg = ((close - prev) / prev) * 100
    turnover_cr = (close * vol) / 1e7
    net_flow_cr = round(
        turnover_cr * (pct_chg / 100) * (vol / df["Volume"].rolling(10).mean().iloc[-1]),
        2,
    )

    return {
        "Symbol": symbol.replace(".NS", ""),
        "Sector": sector,
        "Price": round(close, 2),
        "Change %": round(pct_chg, 2),
        "Net Flow (Cr)": net_flow_cr,
    }
  except Exception:
    return None


@st.cache_data(ttl=300)
def fetch_market_flow():
  tasks = [(sym, sec) for sec, syms in SECTOR_STOCKS.items() for sym in syms]
  results = []
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(analyze_stock, sym, sec) for sym, sec in tasks]
    for f in futures:
      if f.result():
        results.append(f.result())
  return pd.DataFrame(results)


with st.spinner("Calculating institutional capital flows..."):
  df_flow = fetch_market_flow()

if not df_flow.empty:
  total_in = df_flow[df_flow["Net Flow (Cr)"] > 0]["Net Flow (Cr)"].sum()
  total_out = abs(df_flow[df_flow["Net Flow (Cr)"] < 0]["Net Flow (Cr)"].sum())

  c1, c2, c3 = st.columns(3)
  c1.metric("🟢 Total Institutional Inflow", f"₹{total_in:,.0f} Cr")
  c2.metric("🔴 Total Institutional Outflow", f"₹{total_out:,.0f} Cr")
  c3.metric(
      "⚖️ Net Market Bias", f"₹{total_in - total_out:,.0f} Cr", delta="Bullish"
  )

  st.markdown("---")
  st.subheader("📋 Institutional Capital Flow Table")
  st.dataframe(
      df_flow.sort_values(by="Net Flow (Cr)", ascending=False),
      use_container_width=True,
      hide_index=True,
  )

  st.success(
      "💡 **Next Workflow Step:** Proceed to **Night-Before Prep & Coiling** to"
      " identify stocks forming multi-day accumulation coils."
  )
