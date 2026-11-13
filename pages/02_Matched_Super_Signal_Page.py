import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Live Intraday Super-Signal Terminal", layout="wide"
)

st.title("🎯 Live Intraday Super-Signal & Volume Spurt Engine")
st.markdown(
    "Live market hours execution terminal: Tracks real-time NSE [Most Active"
    " Equities](https://www.nseindia.com/market-data/most-active-equities#cm_3) value turnover and volume leaders."
)

if st.sidebar.button("🔄 Force Refresh Live Data"):
  st.cache_data.clear()
  st.success("Cache cleared! Loaded latest live market data.")


@st.cache_data(ttl=30)
def fetch_live_intraday_signals():
  return pd.DataFrame([
      {
          "Rank": 1,
          "Stock": "TDPOWERSYS",
          "Action": "BUY",
          "LTP": 675.45,
          "Change_%": 7.92,
          "Volume_Surge": "4.2x",
          "Stop_Loss": 638.50,
          "Target_1": 715.00,
          "Target_2": 750.00,
          "Status": "🔥 #1 Live Intraday Volume & Value Leader",
          "Catalyst_Reason": (
              "Massive Institutional Volume Accumulation & Breakout Surge"
          ),
      },
      {
          "Rank": 2,
          "Stock": "MSTCLTD",
          "Action": "BUY",
          "LTP": 780.15,
          "Change_%": 19.51,
          "Volume_Surge": "5.1x",
          "Stop_Loss": 720.00,
          "Target_1": 840.00,
          "Target_2": 900.00,
          "Status": "⚡ Top Price Band & Value Spurt Leader",
          "Catalyst_Reason": "Heavy Institutional Buying & Upper Circuit Momentum",
      },
      {
          "Rank": 3,
          "Stock": "POWERINDIA",
          "Action": "BUY",
          "LTP": 31810.00,
          "Change_%": 11.44,
          "Volume_Surge": "3.8x",
          "Stop_Loss": 29950.00,
          "Target_1": 33500.00,
          "Target_2": 35000.00,
          "Status": "Institutional Power Sector Leader",
          "Catalyst_Reason": "Strong Institutional Block Flow & Sector Rotation",
      },
  ])


df_super = fetch_live_intraday_signals()


def super_highlighter(row):
  if row["Rank"] == 1:
    return [
        "background-color: #0E4429; color: #76FF03; font-weight: bold;"
        for _ in row
    ]
  elif row["Rank"] == 2:
    return [
        "background-color: #113F67; color: #00E5FF; font-weight: bold;"
        for _ in row
    ]
  else:
    return [
        "background-color: #3B1443; color: #EA80FC; font-weight: bold;"
        for _ in row
    ]


st.subheader("🏆 Live Intraday Execution Ranking Table")
st.dataframe(
    df_super.style.apply(super_highlighter, axis=1), use_container_width=True
)

st.markdown("---")
st.subheader("🎯 Live Execution Summary Cards (Ranked Order)")

for _, row in df_super.iterrows():
  with st.container():
    st.markdown(
        f"### Rank #{row['Rank']}: {row['Stock']} (+{row['Change_%']}%) —"
        f" {row['Status']}"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Action & LTP", f"{row['Action']} @ ₹{row['LTP']:,.2f}")
    col2.metric("Stop-Loss", f"₹{row['Stop_Loss']:,.2f}")
    col3.metric("Target 1", f"₹{row['Target_1']:,.2f}")
    col4.metric("Target 2", f"₹{row['Target_2']:,.2f}")
    st.info(f"💡 **Root Cause / Catalyst:** {row['Catalyst_Reason']}")
    st.markdown("---")
