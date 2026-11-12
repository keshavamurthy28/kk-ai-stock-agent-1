import numpy as np
import pandas as pd
import streamlit as st

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Pre-market institutional scan results split into **Conservative Swing**"
    " and **Aggressive Momentum** tables for instant comparative review."
)

# --- 1. CONSERVATIVE SWING TABLE ---
st.subheader("🛡️ Conservative Swing Watchlist")

conservative_data = [
    {
        "Stock": "HDFCBANK",
        "Close": 812.30,
        "Change_%": 0.71,
        "Volume_Spurt": "1.4x",
        "Status": "Night Watchlist Candidate",
        "Catalyst_Driver": "FII Delivery Buying & Institutional Support",
    },
    {
        "Stock": "PNB",
        "Close": 141.79,
        "Change_%": 2.39,
        "Volume_Spurt": "1.8x",
        "Status": "Night Watchlist Candidate",
        "Catalyst_Driver": "Banking Sector Rotation & Strong Quarterly Outlook",
    },
]

df_conservative = pd.DataFrame(conservative_data)


def conservative_highlighter(row):
  return [
      "background-color: #3B1443; color: #EA80FC; font-weight: bold;"
      for _ in row
  ]  # Rich Purple


styled_conservative = df_conservative.style.apply(
    conservative_highlighter, axis=1
)
st.dataframe(styled_conservative, use_container_width=True)


# --- 2. AGGRESSIVE MOMENTUM TABLE ---
st.subheader("⚡ Aggressive Momentum Watchlist")

aggressive_data = [
    {
        "Stock": "DCXINDIA",
        "Close": 163.80,
        "Change_%": 12.05,
        "Volume_Spurt": "3.42x",
        "Status": "Top 2 Pick Only",
        "Catalyst_Driver": (
            "Institutional Block Deal & Defense Sector Order Win Confluence"
        ),
    },
    {
        "Stock": "KALYANKJIL",
        "Close": 710.90,
        "Change_%": 7.10,
        "Volume_Spurt": "2.85x",
        "Status": "🔥 Super Signal & Top 2 Overlap",
        "Catalyst_Driver": (
            "Strong FII Accumulation & Festive Quarter Retail Sales Expansion"
        ),
    },
]

df_aggressive = pd.DataFrame(aggressive_data)


def aggressive_highlighter(row):
  status = str(row["Status"])
  if "Super Signal" in status:
    return [
        "background-color: #0E4429; color: #76FF03; font-weight: bold;"
        for _ in row
    ]  # Emerald Green
  else:
    return [
        "background-color: #113F67; color: #00E5FF; font-weight: bold;"
        for _ in row
    ]  # Electric Blue


styled_aggressive = df_aggressive.style.apply(aggressive_highlighter, axis=1)
st.dataframe(styled_aggressive, use_container_width=True)


# --- COLOR CODE LEGEND CARD ---
st.markdown("### 🎨 Distinct Color-Code Legend")
col1, col2, col3 = st.columns(3)
with col1:
  st.markdown(
      '<div style="background-color: #0E4429; color: #76FF03; padding: 10px;'
      ' border-radius: 5px; text-align: center; font-weight: bold;">🟢 Emerald'
      " Green<br>Multi-Page Master Overlap</div>",
      unsafe_allow_html=True,
  )
with col2:
  st.markdown(
      '<div style="background-color: #113F67; color: #00E5FF; padding: 10px;'
      ' border-radius: 5px; text-align: center; font-weight: bold;">🔵 Electric'
      " Blue<br>Top 2 Pick Only</div>",
      unsafe_allow_html=True,
  )
with col3:
  st.markdown(
      '<div style="background-color: #3B1443; color: #EA80FC; padding: 10px;'
      ' border-radius: 5px; text-align: center; font-weight: bold;">🟣 Rich'
      " Purple<br>Conservative Swing Candidate</div>",
      unsafe_allow_html=True,
  )
