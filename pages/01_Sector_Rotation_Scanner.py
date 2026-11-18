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

# Navigation State
if "nav_sector" not in st.session_state:
  st.session_state.nav_sector = None
if "nav_stock" not in st.session_state:
  st.session_state.nav_stock = None


def reset_to_all():
  st.session_state.nav_sector = None
  st.session_state.nav_stock = None


def reset_to_sector():
  st.session_state.nav_stock = None


SECTOR_STOCKS = {
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "BAJFINANCE.NS",
        "SHRIRAMFIN.NS",
        "CHOLAFIN.NS",
        "PFC.NS",
        "RECLTD.NS",
    ],
    "IT & Software": [
        "TCS.NS",
        "INFY.NS",
        "HCLTECH.NS",
        "WIPRO.NS",
        "TECHM.NS",
        "LTIM.NS",
        "PERSISTENT.NS",
        "COFORGE.NS",
        "KPITTECH.NS",
        "TATAELXSI.NS",
    ],
    "Automobiles & Auto Comp": [
        "M&M.NS",
        "MARUTI.NS",
        "TATAMOTORS.NS",
        "BAJAJ-AUTO.NS",
        "EICHERMOT.NS",
        "TVSMOTOR.NS",
        "HEROMOTOCO.NS",
        "BHARATFORG.NS",
        "SONACOMS.NS",
        "MOTHERSON.NS",
    ],
    "Pharma & Healthcare": [
        "SUNPHARMA.NS",
        "CIPLA.NS",
        "DRREDDY.NS",
        "DIVISLAB.NS",
        "APOLLOHOSP.NS",
        "LUPIN.NS",
        "AUROPHARMA.NS",
        "TORNTPHARM.NS",
        "ALKEM.NS",
        "MAXHEALTH.NS",
    ],
    "Capital Goods & Defence": [
        "LT.NS",
        "SIEMENS.NS",
        "ABB.NS",
        "HAL.NS",
        "BEL.NS",
        "BHEL.NS",
        "CUMMINSIND.NS",
        "THERMAX.NS",
        "CGPOWER.NS",
        "SOLARINDS.NS",
    ],
    "Metals & Mining": [
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "VEDL.NS",
        "JINDALSTEL.NS",
        "NMDC.NS",
        "NATIONALUM.NS",
        "SAIL.NS",
        "HINDZINC.NS",
        "APLAPOLLO.NS",
    ],
    "Oil, Gas & Power": [
        "RELIANCE.NS",
        "ONGC.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "TATAPOWER.NS",
        "ADANIPOWER.NS",
        "BPCL.NS",
        "IOC.NS",
        "GAIL.NS",
        "NHPC.NS",
    ],
    "Realty & Infrastructure": [
        "DLF.NS",
        "MACROTECH.NS",
        "GODREJPROP.NS",
        "OBEROIRLTY.NS",
        "PRESTIGE.NS",
        "PHOENIXLTD.NS",
        "BRIGADE.NS",
        "IRB.NS",
        "NCC.NS",
        "KPIL.NS",
    ],
    "FMCG & Consumer": [
        "ITC.NS",
        "HINDUNILVR.NS",
        "NESTLEIND.NS",
        "BRITANNIA.NS",
        "VBL.NS",
        "TATACONSUM.NS",
        "GODREJCP.NS",
        "DABUR.NS",
        "TRENT.NS",
        "TITAN.NS",
    ],
    "Chemicals & Fertilizers": [
        "PIDILITIND.NS",
        "SRF.NS",
        "UPL.NS",
        "PIIND.NS",
        "DEEPAKNTR.NS",
        "NAVINFLUOR.NS",
        "TATACHEM.NS",
        "COROMANDEL.NS",
        "CHAMBLFERT.NS",
        "AARTIIND.NS",
    ],
}

MACRO_INDICES = {
    "Nifty 50": "^NSEI",
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO",
    "Nifty FMCG": "^CNXFMCG",
}


@st.cache_data(ttl=900)
def fetch_market_data():
  all_stocks = [t for stocks in SECTOR_STOCKS.values() for t in stocks]
  index_tickers = list(MACRO_INDICES.values())
  raw = yf.download(
      index_tickers + all_stocks,
      period="6mo",
      interval="1d",
      group_by="ticker",
      progress=False,
      threads=True,
  )

  index_metrics = {}
  for name, symbol in MACRO_INDICES.items():
    try:
      idx_df = raw[symbol]["Close"].dropna()
      if not idx_df.empty:
        ltp = float(idx_df.iloc[-1])
        prev = float(idx_df.iloc[-2])
        chg = ((ltp - prev) / prev) * 100
        w_chg = ((ltp / float(idx_df.iloc[-6]) - 1)) * 100
        index_metrics[name] = {
            "LTP": round(ltp, 2),
            "Chg%": round(chg, 2),
            "1W%": round(w_chg, 2),
        }
    except Exception:
      pass

  nifty_close = raw["^NSEI"]["Close"].dropna()
  nifty_5d = (nifty_close.iloc[-1] / nifty_close.iloc[-6] - 1) * 100
  nifty_10d = (nifty_close.iloc[-1] / nifty_close.iloc[-11] - 1) * 100

  records = []
  ohlcv_store = {}

  for sector, tickers in SECTOR_STOCKS.items():
    for ticker in tickers:
      try:
        df = raw[ticker].dropna()
        if len(df) < 35:
          continue
        sym = ticker.replace(".NS", "")
        ohlcv_store[sym] = df
        close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
        ltp = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        day_chg = (ltp / prev_close - 1) * 100
        week_chg = (ltp / float(close.iloc[-6]) - 1) * 100
        month_chg = (ltp / float(close.iloc[-22]) - 1) * 100
        ten_day_chg = (ltp / float(close.iloc[-11]) - 1) * 100

        rs_5d = week_chg - nifty_5d
        rs_10d = ten_day_chg - nifty_10d
        avg_vol_20 = vol.iloc[-21:-1].mean()
        rvol = float(vol.iloc[-1] / avg_vol_20) if avg_vol_20 > 0 else 1.0

        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_width = (4 * std20) / sma20
        is_squeezed = float(bb_width.iloc[-1]) <= (
            float(bb_width.iloc[-60:].min()) * 1.25
        )

        ema20 = float(close.ewm(span=20).mean().iloc[-1])
        ema50 = float(close.ewm(span=50).mean().iloc[-1])

        score = 0
        if rs_5d > 1.5:
          score += 25
        if rs_10d > 2.0:
          score += 15
        if rvol >= 1.3 and -0.5 <= day_chg <= 3.5:
          score += 30
        elif rvol >= 1.8 and day_chg > 3.5:
          score += 10
        if is_squeezed:
          score += 15
        if ltp > ema20 and ltp > ema50:
          score += 15

        sparkline = [round(float(x), 2) for x in close.iloc[-60:].tolist()]
        m_low, m_high = (
            float(low.iloc[-22:].min()),
            float(high.iloc[-22:].max()),
        )
        pos_in_month = (
            ((ltp - m_low) / (m_high - m_low) * 100) if m_high > m_low else 50
        )

        records.append({
            "Symbol": sym,
            "Sector": sector,
            "LTP": round(ltp, 2),
            "Day %": round(day_chg, 2),
            "Week %": round(week_chg, 2),
            "Month %": round(month_chg, 2),
            "RS vs Nifty (5D)": round(rs_5d, 2),
            "RS vs Nifty (10D)": round(rs_10d, 2),
            "RVOL (x)": round(rvol, 2),
            "Squeeze": "🔥 Yes" if is_squeezed else "No",
            "Above 20EMA": ltp > ema20,
            "Pre-Breakout Score": score,
            "Month Range %": round(pos_in_month, 1),
            "3M Trend": sparkline,
            "EMA20": round(ema20, 2),
            "EMA50": round(ema50, 2),
        })
      except Exception:
        continue

  return pd.DataFrame(records), ohlcv_store, round(nifty_5d, 2), index_metrics


with st.spinner("Loading live macroeconomic pulse & sector rotation..."):
  df_stocks, ohlcv_store, nifty_5d_ret, index_metrics = fetch_market_data()

if df_stocks.empty:
  st.error("Market data unavailable. Please refresh.")
  st.stop()

sector_summary = (
    df_stocks.groupby("Sector")
    .agg(
        Stocks_Count=("Symbol", "count"),
        Day_Chg=("Day %", "mean"),
        Week_Chg=("Week %", "mean"),
        RS_5D=("RS vs Nifty (5D)", "mean"),
        RS_10D=("RS vs Nifty (10D)", "mean"),
        Avg_RVOL=("RVOL (x)", "mean"),
        Advances=("Day %", lambda x: (x > 0).sum()),
        Above_20EMA_Pct=(
            "Above 20EMA",
            lambda x: round(x.mean() * 100, 1),
        ),
        Avg_Breakout_Score=("Pre-Breakout Score", "mean"),
    )
    .reset_index()
)
sector_summary["Declines"] = (
    sector_summary["Stocks_Count"] - sector_summary["Advances"]
)
sector_summary["A/D Ratio"] = (
    sector_summary["Advances"] / sector_summary["Declines"].replace(0, 1)
).round(2)

st.title("🎯 Institutional Sector Rotation & Macro Pulse Terminal")
st.markdown(
    "**Step 1:** Read the live Nifty macro pulse below, evaluate sector"
    " momentum, and cross-reference setups with the **Smart Money Flow** page."
)

idx_cols = st.columns(len(MACRO_INDICES))
for i, (idx_name, _) in enumerate(MACRO_INDICES.items()):
  with idx_cols[i]:
    if idx_name in index_metrics:
      m_val = index_metrics[idx_name]
      st.metric(
          label=idx_name,
          value=f"₹{m_val['LTP']:,.2f}",
          delta=f"{m_val['Chg%']:+.2f}% (1W: {m_val['1W%']:+.2f}%)",
      )

st.markdown("---")

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

if st.session_state.nav_stock:
  sym = st.session_state.nav_stock
  row = df_stocks[df_stocks["Symbol"] == sym].iloc[0]
  hist = ohlcv_store[sym].copy()

  st.header(f"📈 {sym} — Pre-Breakout Setup ({row['Sector']})")
  m1, m2, m3, m4 = st.columns(4)
  m1.metric("LTP", f"₹{row['LTP']}", f"{row['Day %']:+.2f}%")
  m2.metric("Early-Move Score", f"{row['Pre-Breakout Score']} / 100")
  m3.metric("5D RS vs Nifty", f"{row['RS vs Nifty (5D)']:+.2f}%")
  m4.metric("Volume Surge", f"{row['RVOL (x)']}x")

  fig = go.Figure(
      data=[
          go.Candlestick(
              x=hist.index,
              open=hist["Open"],
              high=hist["High"],
              low=hist["Low"],
              close=hist["Close"],
          )
      ]
  )
  fig.update_layout(
      height=500, xaxis_rangeslider_visible=False, template="plotly_dark"
  )
  st.plotly_chart(fig, use_container_width=True)

elif st.session_state.nav_sector:
  sec = st.session_state.nav_sector
  sec_df = df_stocks[df_stocks["Sector"] == sec].sort_values(
      by="Pre-Breakout Score", ascending=False
  )
  st.header(f"🟢 {sec} — Constituent Stocks")

  table_event = st.dataframe(
      sec_df[[
          "Symbol",
          "Pre-Breakout Score",
          "LTP",
          "Day %",
          "Week %",
          "RS vs Nifty (5D)",
          "RVOL (x)",
          "Squeeze",
      ]],
      use_container_width=True,
      hide_index=True,
      on_select="rerun",
      selection_mode="single-row",
      key="peer_table",
  )
  if table_event and table_event.selection and table_event.selection.rows:
    row_idx = table_event.selection.rows[0]
    st.session_state.nav_stock = sec_df.iloc[row_idx]["Symbol"]
    st.rerun()

else:
  st.header("🗺️ NSE Sector Heatmap & Rotation Scanner")
  fig_tree = px.treemap(
      sector_summary,
      path=["Sector"],
      values="Avg_RVOL",
      color="Day_Chg",
      color_continuous_scale=["#990000", "#d9534f", "#f5f5f5", "#5cb85c", "#006400"],
      color_continuous_midpoint=0,
  )
  fig_tree.update_layout(height=450, margin=dict(t=10, l=10, r=10, b=10))
  sector_event = st.plotly_chart(
      fig_tree, use_container_width=True, on_select="rerun", key="main_sector_tree"
  )
  if sector_event and sector_event.selection and sector_event.selection.points:
    clicked_sector = sector_event.selection.points[0].get("label")
    if clicked_sector and clicked_sector in SECTOR_STOCKS:
      st.session_state.nav_sector = clicked_sector
      st.rerun()
