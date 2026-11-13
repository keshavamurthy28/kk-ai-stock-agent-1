import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Institutional Morning Top Picks", layout="wide")

st.title("🌅 Institutional Morning Top Picks & Pre-Market Setup Terminal")
st.markdown(
    "Pre-market filtered execution setup derived from morning pre-scan"
    " candidates."
)


@st.cache_data(ttl=30)
def fetch_morning_top_picks():
  return pd.DataFrame([
      {
          "Rank": 1,
          "Stock": "AMBER",
          "Score": "4.9/5 (Morning Swing)",
          "LTP": 6532.00,
          "Change_%": 5.20,
          "Vol_Surge": "2.9x",
          "Stop_Loss": 6300.00,
          "Book_Profit_Target": 6900.00,
          "Catalyst_Reason": (
              "Strong Morning Gap-Up & Institutional Accumulation Zone"
          ),
      },
      {
          "Rank": 2,
          "Stock": "APOLLO",
          "Score": "4.7/5 (Momentum)",
          "LTP": 461.50,
          "Change_%": 4.86,
          "Vol_Surge": "3.1x",
          "Stop_Loss": 435.00,
          "Book_Profit_Target": 500.00,
          "Catalyst_Reason": "Volume Spurt & Breakout from Resistance Level",
      },
  ])


df_morning = fetch_morning_top_picks()


def morning_highlighter(row):
  if row["Rank"] == 1:
    return [
        "background-color: #113F67; color: #00E5FF; font-weight: bold;"
        for _ in row
    ]
  else:
    return [
        "background-color: #3B1443; color: #EA80FC; font-weight: bold;"
        for _ in row
    ]


st.subheader("🏆 Morning Pre-Market Execution Table")
st.dataframe(
    df_morning.style.apply(morning_highlighter, axis=1), use_container_width=True
)

for _, row in df_morning.iterrows():
  with st.expander(
      f"🎯 Morning Setup #{row['Rank']}: {row['Stock']} | Gain:"
      f" +{row['Change_%']}%"
  ):
    col1, col2, col3 = st.columns(3)
    col1.metric("Recommended Entry (LTP)", f"₹{row['LTP']:,.2f}")
    col2.metric("Stop-Loss Anchor", f"₹{row['Stop_Loss']:,.2f}")
    col3.metric("Book Profit Target", f"₹{row['Book_Profit_Target']:,.2f}")
    st.info(f"💡 **Root Cause / Catalyst:** {row['Catalyst_Reason']}")
