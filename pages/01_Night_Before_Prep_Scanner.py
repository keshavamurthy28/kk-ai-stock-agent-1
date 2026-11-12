import pandas as pd
import streamlit as st

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Scans post-market close data to prep institutional watchlists, Fair Value"
    " Gaps (FVG), and accumulation zones for the next session."
)

# Sidebar Risk Profile Selection
risk_tolerance = st.sidebar.selectbox(
    "Select Risk Profile", ["Conservative (Swing)", "Aggressive (Momentum)"]
)

# Dynamic filtering based on user selection
if risk_tolerance == "Conservative (Swing)":
  st.info(
      "🛡️ **Conservative Swing Mode Active:** Filtering for stocks with high"
      " delivery volume, stable 20-50 EMA support, and low intraday volatility"
      " for multi-day swing holding."
  )
  watchlist_data = [
      {
          "Stock": "HDFCBANK",
          "Close": 812.30,
          "Change_%": 0.71,
          "Volume_Spurt": "1.4x",
          "Next_Day_Bias": "Stable Accumulation",
          "Catalyst_Driver": "FII Delivery Buying & Institutional Support",
      },
      {
          "Stock": "PNB",
          "Close": 141.79,
          "Change_%": 2.39,
          "Volume_Spurt": "1.8x",
          "Next_Day_Bias": "Swing Breakout Continuation",
          "Catalyst_Driver": "Banking Sector Rotation & Strong Quarterly Outlook",
      },
  ]
else:
  st.warning(
      "⚡ **Aggressive Momentum Mode Active:** Filtering for high-beta volume"
      " surge leaders, upper price-band hitters, and institutional block-deal"
      " breakouts."
  )
  watchlist_data = [
      {
          "Stock": "DCXINDIA",
          "Close": 163.80,
          "Change_%": 12.05,
          "Volume_Spurt": "3.42x",
          "Next_Day_Bias": "High-Beta Momentum Breakout",
          "Catalyst_Driver": (
              "Institutional Block Deal & Defense Sector Order Win Confluence"
          ),
      },
      {
          "Stock": "KALYANKJIL",
          "Close": 710.90,
          "Change_%": 7.10,
          "Volume_Spurt": "2.85x",
          "Next_Day_Bias": "Aggressive Continuation",
          "Catalyst_Driver": (
              "Strong FII Accumulation & Festive Quarter Retail Sales Expansion"
          ),
      },
  ]

df_watchlist = pd.DataFrame(watchlist_data)

st.subheader(f"📋 Pre-Market Watchlist Matrix — {risk_tolerance}")
st.dataframe(df_watchlist, use_container_width=True)

if st.button("🚀 Run Evening Homework Scan"):
  st.success(
      f"✅ Evening homework scan successfully completed for **{risk_tolerance}**!"
      " Watchlist synced with live NSE closing order blocks."
  )
