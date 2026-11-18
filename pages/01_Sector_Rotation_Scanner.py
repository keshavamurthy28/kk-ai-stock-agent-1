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

# --- CLEAN SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.markdown("- 🗺️ **[Sector Rotation & Macro Pulse](Sector_Rotation_Scanner)**")
st.sidebar.markdown("- ⚡ **[Smart Money Flow Terminal](Smart_Money_Pulse)**")
st.sidebar.markdown("- 🌙 **[Night-Before Prep & Coiling](Night_Before_Prep_Scanner)**")
st.sidebar.markdown("- 📈 **[Intraday Sniper Terminal](PRIME_2-5_INTRADAY_SNIPER)**")
st.sidebar.markdown("---")

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
def fetch_macro_and_sector_data():
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

  records = []
  for sector, tickers in SECTOR_STOCKS.items():
    sec_changes = []
    sec_vols = []
    for ticker in tickers:
      try:
        df = raw[ticker].dropna()
        if len(df) < 5:
          continue
        close, vol = df["Close"], df["Volume"]
        ltp = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        chg = ((ltp - prev) / prev) * 100
        rvol = float(vol.iloc[-1] / vol.iloc[-21:-1].mean())
        sec_changes.append(chg)
        sec_vols.append(rvol)
      except Exception:
        continue
    if sec_changes:
      records.append({
          "Sector": sector,
          "Day_Chg": round(np.mean(sec_changes), 2),
          "Avg_RVOL": round(np.mean(sec_vols), 2),
      })

  return index_metrics, pd.DataFrame(records)


st.title("🗺️ Institutional Sector Rotation & Macro Pulse")
st.markdown(
    "Analyze headline index performance and interactive sector heatmaps below."
)

metrics, sector_summary = fetch_macro_and_sector_data()

# Render Macro Index Cards
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

# Navigation Breadcrumbs
b1, b2 = st.columns([1, 4])
with b1:
  if st.button("🏠 All Sectors", use_container_width=True):
    reset_to_all()
    st.rerun()

st.divider()

# ==========================================
# RENDER RESTORED HEATMAP BOXES GRID
# ==========================================
if not sector_summary.empty:
  st.subheader("🗺️ Interactive Sector Heatmap (Click Box to Inspect)")
  st.caption(
      "🟢 **Dark Green to Light Green:** Bullish Momentum  |  🔴 **Light Red to"
      " Dark Red:** Distribution Pressure"
  )

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
          "<b>%{label}</b><br>Day Change: %{customdata[0]:+.2f}%<br>Volume"
          " Surge: %{customdata[1]:.2f}x<extra></extra>"
      ),
  )
  fig_tree.update_layout(height=420, margin=dict(t=10, l=10, r=10, b=10))

  sector_event = st.plotly_chart(
      fig_tree, use_container_width=True, on_select="rerun", key="sector_heatmap"
  )
  if sector_event and sector_event.selection and sector_event.selection.points:
    clicked_sec = sector_event.selection.points[0].get("label")
    if clicked_sec in SECTOR_STOCKS:
      st.session_state.nav_sector = clicked_sec
      st.rerun()
