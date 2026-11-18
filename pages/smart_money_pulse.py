from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Smart Money Pulse & Institutional Flow Terminal", layout="wide"
)

# Sidebar Navigation Bridge
st.sidebar.markdown("### 🧭 Institutional Terminal Navigation")
st.sidebar.page_link(
    "pages/01_sector_rotation_scanner.py",
    label="🗺️ Sector Rotation & Macro Pulse",
    icon="📊",
)
st.sidebar.page_link(
    "pages/02_smart_money_pulse.py",
    label="⚡ Smart Money Flow & Swing Screener",
    icon="💸",
)
st.sidebar.markdown("---")

st.title("⚡ Smart Money Pulse & Institutional Flow Terminal")
st.caption(
    "**Step 2:** Analyze real-time net institutional inflows/outflows in"
    " Crores, capital stream Sankey diagrams, and"
    " 10–15% swing breakout setups."
)

SECTOR_STOCKS = {
    "Bank & PSU": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "BANKBARODA.NS",
        "PNB.NS",
    ],
    "IT & Tech": [
        "TCS.NS",
        "INFY.NS",
        "HCLTECH.NS",
        "WIPRO.NS",
        "TECHM.NS",
        "PERSISTENT.NS",
        "COFORGE.NS",
    ],
    "Pharma & Health": [
        "SUNPHARMA.NS",
        "DIVISLAB.NS",
        "CIPLA.NS",
        "DRREDDY.NS",
        "LUPIN.NS",
        "LAURUSLABS.NS",
        "GLAXO.NS",
    ],
    "Defence & CapGoods": [
        "HAL.NS",
        "BEL.NS",
        "MAZDOCK.NS",
        "DATAPATTNS.NS",
        "LT.NS",
        "SIEMENS.NS",
        "POWERINDIA.NS",
    ],
    "Auto & EV": [
        "M&M.NS",
        "MARUTI.NS",
        "TATAMOTORS.NS",
        "BAJAJ-AUTO.NS",
        "EICHERMOT.NS",
        "TVSMOTOR.NS",
    ],
    "NBFC & Finance": [
        "BAJFINANCE.NS",
        "BAJAJFINSV.NS",
        "CHOLAFIN.NS",
        "SHRIRAMFIN.NS",
        "JIOFIN.NS",
        "IREDA.NS",
    ],
    "Metals & Energy": [
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "RELIANCE.NS",
        "NTPC.NS",
        "ONGC.NS",
        "TATAPOWER.NS",
    ],
    "Consumer & FMCG": [
        "ITC.NS",
        "HINDUNILVR.NS",
        "TRENT.NS",
        "TITAN.NS",
        "JUBLFOOD.NS",
        "VBL.NS",
    ],
}


def analyze_stock(symbol, sector):
  try:
    df = yf.download(symbol, period="3mo", interval="1d", progress=False)
    if df.empty or len(df) < 25:
      return None
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)

    close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]
    high = df["High"].iloc[-1]
    low = df["Low"].iloc[-1]
    vol = df["Volume"].iloc[-1]
    avg_vol_20 = df["Volume"].iloc[-21:-1].mean()

    pct_chg = ((close - prev_close) / prev_close) * 100
    vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    hl_range = (high - low) if (high - low) > 0 else 0.01
    clv = ((close - low) - (high - close)) / hl_range
    turnover_cr = (close * vol) / 1e7
    net_flow_cr = round(turnover_cr * clv, 2)

    high_20d = df["High"].iloc[-21:-1].max()
    low_20d = df["Low"].iloc[-21:-1].min()
    range_20d_pct = ((high_20d - low_20d) / low_20d) * 100

    is_breakout = (
        (close >= high_20d * 0.985) and (vol_ratio >= 1.3) and (pct_chg > 1.0)
    )
    is_tight_base = (range_20d_pct <= 14.0) and (
        close > df["Close"].rolling(20).mean().iloc[-1]
    )

    setup_tag = (
        "🔥 Breakout + Vol"
        if is_breakout
        else ("📦 Tight Smart Base" if is_tight_base else "Watchlist")
    )

    return {
        "Symbol": symbol.replace(".NS", ""),
        "Sector": sector,
        "Price": round(close, 2),
        "Change %": round(pct_chg, 2),
        "Turnover (Cr)": round(turnover_cr, 1),
        "Net Flow (Cr)": net_flow_cr,
        "Vol Surge (x)": round(vol_ratio, 2),
        "20D Range %": round(range_20d_pct, 1),
        "Swing Setup": setup_tag,
    }
  except Exception:
    return None


@st.cache_data(ttl=300)
def fetch_market_flow():
  tasks = [(sym, sec) for sec, syms in SECTOR_STOCKS.items() for sym in syms]
  results = []
  with ThreadPoolExecutor(max_workers=12) as executor:
    futures = [executor.submit(analyze_stock, sym, sec) for sym, sec in tasks]
    for f in futures:
      res = f.result()
      if res:
        results.append(res)
  return pd.DataFrame(results)


if st.button("🔄 Refresh Live Smart Money Flow"):
  st.cache_data.clear()

with st.spinner("Scanning Institutional Capital Flows..."):
  df_flow = fetch_market_flow()

if df_flow.empty:
  st.error("Unable to fetch data. Please try refreshing.")
  st.stop()

inflows_df = df_flow[df_flow["Net Flow (Cr)"] > 0].sort_values(
    by="Net Flow (Cr)", ascending=False
)
outflows_df = df_flow[df_flow["Net Flow (Cr)"] < 0].sort_values(
    by="Net Flow (Cr)", ascending=True
)

total_inflow = inflows_df["Net Flow (Cr)"].sum()
total_outflow = abs(outflows_df["Net Flow (Cr)"].sum())
net_market_flow = total_inflow - total_outflow

c1, c2, c3, c4 = st.columns(4)
c1.metric("🟢 Total Smart Inflow", f"₹{total_inflow:,.0f} Cr")
c2.metric("🔴 Total Smart Outflow", f"₹{total_outflow:,.0f} Cr")
c3.metric(
    "⚖️ Net Institutional Flow",
    f"₹{net_market_flow:,.0f} Cr",
    delta=f"{'Bullish' if net_market_flow > 0 else 'Bearish'}",
)
c4.metric(
    "🚀 Swing Breakout Candidates",
    len(df_flow[df_flow["Swing Setup"] != "Watchlist"]),
)

st.divider()

st.subheader("🎯 Smart Money Swing Trade Screener (10–15% Rally Setups)")
st.dataframe(
    df_flow[df_flow["Net Flow (Cr)"] > 0].sort_values(
        by=["Swing Setup", "Vol Surge (x)"], ascending=[True, False]
    ),
    use_container_width=True,
    hide_index=True,
)
