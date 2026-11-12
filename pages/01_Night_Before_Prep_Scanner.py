import numpy as np
import pandas as pd
import streamlit as st

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")

# Sidebar Risk Profile Selection
risk_tolerance = st.sidebar.selectbox(
    "Select Risk Profile", ["Conservative (Swing)", "Aggressive (Momentum)"]
)

# Sample data representing current session scans
watchlist_data = [
    {
        "Stock": "DCXINDIA",
        "Close": 163.80,
        "Change_%": 12.05,
        "Volume_Spurt": "3.42x",
        "Status": "Top 2 Pick Overlap",
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


# Function to highlight overlapping high-conviction stocks in color code
def highlight_overlaps(row):
  if "Super Signal" in str(row["Status"]):
    return [
        "background-color: #1e4620; color: #a3ffb1; font-weight: bold;"
        for _ in row
    ]  # Deep green glow for multi-page master overlaps
  elif "Top 2" in str(row["Status"]):
    return [
        "background-color: #2b3a1a; color: #d4ff80; font-weight: bold;"
        for _ in row
    ]  # Olive/Yellow-green for Top 2 overlap
  return ["" for _ in row]


st.subheader(
    f"📋 Pre-Market Watchlist Matrix with Overlap Highlighting —"
    f" {risk_tolerance}"
)

# Applying color-coded styling to the dataframe table
styled_df = df_watchlist.style.apply(highlight_overlaps, axis=1)
st.dataframe(styled_df, use_container_width=True)

st.success(
    "🟢 **Color-Code Guide:** Rows highlighted in **bright green** indicate"
    " multi-page overlaps (present in Super Signals & Top 2), signaling elite"
    " institutional accumulation!"
)
