from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

# --- CLEAN SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.markdown("- 🗺️ **[Sector Rotation & Macro Pulse](Sector_Rotation_Scanner)**")
st.sidebar.markdown("- ⚡ **[Smart Money Flow Terminal](Smart_Money_Pulse)**")
st.sidebar.markdown("- 🌙 **[Night-Before Prep & Coiling](Night_Before_Prep_Scanner)**")
st.sidebar.markdown("- 📈 **[Intraday Sniper Terminal](PRIME_2-5_INTRADAY_SNIPER)**")
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 0. NAVIGATION STATE (3-Level Drill-Down Router)
# ---------------------------------------------------------
if "nav_sector" not in st.session_state:
  st.session_state.nav_sector = None
if "nav_stock" not in st.session_state:
  st.session_state.nav_stock = None


def reset_to_all():
  st.session_state.nav_sector = None
  st.session_state.nav_stock = None


def reset_to_sector():
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
def fetch_comprehensive_market_data():
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

  nifty_close = raw["^NSEI"]["Close"].dropna()
  nifty_5d = (
      (nifty_close.iloc[-1] / nifty_close.iloc[-6] - 1) * 100
      if len(nifty_close) >= 6
      else 0.0
  )

  records = []
  ohlcv_store = {}

  for sector, tickers in SECTOR_STOCKS.items():
    for ticker in tickers:
      try:
        df = raw[ticker].dropna()
        if len(df) < 20:
          continue
        sym = ticker.replace(".NS", "")
        ohlcv_store[sym] = df

        close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
        ltp = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        day_chg = ((ltp - prev) / prev) * 100
        week_chg = (
            ((ltp / float(close.iloc[-6]) - 1) * 100)
            if len(close) >= 6
            else 0.0
        )
        rvol = (
            float(vol.iloc[-1] / vol.iloc[-21:-1].mean())
            if len(vol) >= 21
            else 1.0
        )
        rs_5d = week_chg - nifty_5d

        records.append({
            "Symbol": sym,
            "Sector": sector,
            "LTP": round(ltp, 2),
            "Day %": round(day_chg, 2),
            "Week %": round(week_chg, 2),
            "RS vs Nifty (5D)": round(rs_5d, 2),
            "RVOL (x)": round(rvol, 2),
        })
      except Exception:
        continue

  return (
      index_metrics,
      pd.DataFrame(records),
      ohlcv_store,
      round(nifty_5d, 2),
  )


with st.spinner("Loading macro indices & sector drill-down engine..."):
  index_metrics, df_stocks, ohlcv_store, nifty_5d_ret = (
      fetch_comprehensive_market_data()
  )

if df_stocks.empty:
  st.error("Market data unavailable. Please refresh.")
  st.stop()

# Aggregate Sector Metrics for Heatmap
sector_summary = (
    df_stocks.groupby("Sector")
    .agg(
        Stocks_Count=("Symbol", "count"),
        Day_Chg=("Day %", "mean"),
        Week_Chg=("Week %", "mean"),
        Avg_RVOL=("RVOL (x)", "mean"),
    )
    .reset_index()
)
sector_summary["Day_Chg"] = sector_summary["Day_Chg"].round(2)
sector_summary["Week_Chg"] = sector_summary["Week_Chg"].round(2)

# --- BREADCRUMB BAR ---
st.title("🗺️ Institutional Sector Rotation & Deep-Dive Terminal")
b1, b2, b3 = st.columns([1.2, 2, 4])
with b1:
  if st.button("🏠 All Sectors", use_container_width=True):
    reset_to_all()
    st.rerun()
with b2:
  if st.session_state.nav_sector:
    if st.button(
        f"📂 {st.session_state.nav_sector}", use_container_width=True
    ):
      reset_to_sector()
      st.rerun()

st.divider()

# =========================================================
# LEVEL 3 VIEW: STOCK TECHNICAL CHART TERMINAL
# =========================================================
if st.session_state.nav_stock:
  sym = st.session_state.nav_stock
  row = df_stocks[df_stocks["Symbol"] == sym].iloc[0]
  hist = ohlcv_store[sym].copy()

  st.header(f"📈 {sym} — Technical Chart & Institutional Setup ({row['Sector']})")

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("LTP", f"₹{row['LTP']}", f"{row['Day %']:+.2f}%")
  m2.metric("5D RS vs Nifty", f"{row['RS vs Nifty (5D)']:+.2f}%")
  m3.metric("Volume Surge (RVOL)", f"{row['RVOL (x)']}x")
  m4.metric("Sector", row["Sector"])

  # Indicators
  hist["EMA20"] = hist["Close"].ewm(span=20).mean()
  hist["VWAP"] = (
      (((hist["High"] + hist["Low"] + hist["Close"]) / 3.0) * hist["Volume"])
      .groupby(hist.index.date)
      .cumsum()
      / hist["Volume"].groupby(hist.index.date).cumsum().replace(0, np.nan)
  )

  # Candlestick Chart
  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=[0.75, 0.25],
  )
  fig.add_trace(
      go.Candlestick(
          x=hist.index,
          open=hist["Open"],
          high=hist["High"],
          low=hist["Low"],
          close=hist["Close"],
          name=sym,
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=hist.index,
          y=hist["VWAP"],
          line=dict(color="#FFD700", width=1.3),
          name="VWAP",
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=hist.index,
          y=hist["EMA20"],
          line=dict(color="#29B6F6", width=1.3),
          name="20 EMA",
      ),
      row=1,
      col=1,
  )

  v_colors = [
      "#00E676" if c >= o else "#FF5252"
      for c, o in zip(hist["Close"], hist["Open"])
  ]
  fig.add_trace(
      go.Bar(
          x=hist.index,
          y=hist["Volume"],
          marker_color=v_colors,
          name="Volume",
      ),
      row=2,
      col=1,
  )

  fig.update_layout(
      height=550,
      template="plotly_dark",
      xaxis_rangeslider_visible=False,
      margin=dict(t=20, l=10, r=10, b=10),
  )
  st.plotly_chart(fig, use_container_width=True)

# =========================================================
# LEVEL 2 VIEW: SECTOR CONSTITUENTS TABLE
# =========================================================
elif st.session_state.nav_sector:
  sec = st.session_state.nav_sector
  sec_df = df_stocks[df_stocks["Sector"] == sec].reset_index(drop=True)

  st.header(f"🟢 {sec} — Constituent Stocks")
  st.markdown("👆 **Click any row in the table below** to open its chart.")

  table_event = st.dataframe(
      sec_df[["Symbol", "LTP", "Day %", "Week %", "RS vs Nifty (5D)", "RVOL (x)"]],
      use_container_width=True,
      hide_index=True,
      on_select="rerun",
      selection_mode="single-row",
      key="sector_stocks_table",
  )
  if table_event and table_event.selection and table_event.selection.rows:
    row_idx = table_event.selection.rows[0]
    st.session_state.nav_stock = sec_df.iloc[row_idx]["Symbol"]
    st.rerun()

# =========================================================
# LEVEL 1 VIEW: MASTER SECTOR HEATMAP BOXES
# =========================================================
else:
  st.subheader("🗺️ Interactive Sector Heatmap (Click Box to Open Sector)")
  fig_tree = px.treemap(
      sector_summary,
      path=["Sector"],
      values="Avg_RVOL",
      color="Day_Chg",
      color_continuous_scale=["#990000", "#d9534f", "#f5f5f5", "#5cb85c", "#006400"],
      color_continuous_midpoint=0,
      custom_data=["Day_Chg", "Avg_RVOL"],
  )
  fig_tree.update_traces(
      texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}% Day",
      hovertemplate=(
          "<b>%{label}</b><br>Day Chg: %{customdata[0]:+.2f}%<br>Volume Surge:"
          " %{customdata[1]:.2f}x<extra></extra>"
      ),
  )
  fig_tree.update_layout(height=420, margin=dict(t=10, l=10, r=10, b=10))

  sector_event = st.plotly_chart(
      fig_tree, use_container_width=True, on_select="rerun", key="main_heatmap"
  )
  if sector_event and sector_event.selection and sector_event.selection.points:
    clicked_sec = sector_event.selection.points[0].get("label")
    if clicked_sec in SECTOR_STOCKS:
      st.session_state.nav_sector = clicked_sec
      st.rerun()
