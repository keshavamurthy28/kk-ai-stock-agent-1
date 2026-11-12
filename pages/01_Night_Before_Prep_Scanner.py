import numpy as np
import pandas as pd
import streamlit as st

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")

risk_tolerance = st.sidebar.selectbox(
    "Select Risk Profile", ["Conservative (Swing)", "Aggressive (Momentum)"]
)

# Sample data showing different statuses
watchlist_data = [
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

df_watchlist = pd.DataFrame(watchlist_data)


# Function to apply distinct, non-similar colors
def distinct_color_highlighter(row):
  status = str(row["Status"])
  if "Super Signal" in status:
    # Emerald Green for Master Overlaps
    return [
        "background-color: #0E4429; color: #76FF03; font-weight: bold;"
        for _ in row
    ]
  elif "Top 2" in status:
    # Electric Blue for Top 2 Picks
    return [
        "background-color: #113F67; color: #00E5FF; font-weight: bold;"
        for _ in row
    ]
  else:
    # Purple for general watchlist
    return [
        "background-color: #3B1443; color: #EA80FC; font-weight: bold;"
        for _ in row
    ]


st.subheader(f"📋 Pre-Market Watchlist Matrix — {risk_tolerance}")

# Render table with distinct styling
styled_df = df_watchlist.style.apply(distinct_color_highlighter, axis=1)
st.dataframe(styled_df, use_container_width=True)

# Dedicated Color Legend Card
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
      " Purple<br>Night Watchlist Candidate</div>",
      unsafe_allow_html=True,
  )
