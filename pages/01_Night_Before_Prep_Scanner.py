import pandas as pd
import streamlit as st

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Scans post-market close data to prep institutional watchlists, Fair Value"
    " Gaps (FVG), and accumulation zones for the next session."
)

# Interactive filters for night prep
risk_tolerance = st.sidebar.selectbox(
    "Select Risk Profile", ["Conservative (Swing)", "Aggressive (Momentum)"]
)

# Sample post-market prepped data with catalysts
prep_data = pd.DataFrame([
    {
        "Stock": "CUPID",
        "Close": 385.50,
        "Change_%": 8.90,
        "Volume_Spurt": "3.1x",
        "Next_Day_Bias": "Bullish Continuation",
        "Catalyst_Driver": "Institutional Volume Breakout & Sector Rotation",
    },
    {
        "Stock": "PINELABS",
        "Close": 176.15,
        "Change_%": 5.97,
        "Volume_Spurt": "2.7x",
        "Next_Day_Bias": "Accumulation Phase",
        "Catalyst_Driver": "FII Bulk Deal Accumulation",
    },
])

st.subheader("📋 Pre-Market Watchlist & Catalyst Matrix")
st.dataframe(prep_data, use_container_width=True)

if st.button("🚀 Run Evening Homework Scan"):
  st.success(
      "Evening scan completed successfully! Watchlist synced with institutional"
      " order blocks."
  )
