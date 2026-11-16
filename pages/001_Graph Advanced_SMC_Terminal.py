import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced SMC & FVG Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS: Ample top padding so title, input, and interval pills are fully visible
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 5rem !important;
            padding-bottom: 2rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- TOP CONTROL BAR (Fully Visible Below Streamlit Header) ---
st.markdown("### 📊 Institutional SMC & FVG Execution Terminal")

col1, col2, col3 = st.columns([2, 6, 2])

with col1:
  stock_input = (
      st.text_input(
          "NSE Symbol",
          value="RELIANCE",
          placeholder="Symbol (e.g., RELIANCE, AMBER)",
      )
      .upper()
      .strip()
  )

ticker_symbol = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

with col2:
  interval_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"]
  selected_tf = st.radio(
      "Candle Interval",
      options=interval_options,
      index=2,  # Default to 15m execution timeframe
      horizontal=True,
  )

with col3:
  show_mtf_zones = st.toggle("Show 1D & 4H Zones", value=True)

st.markdown("---")


# --- DATA FETCHING & RESAMPLING ENGINE ---
@st.cache_data(ttl=60)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
  try:
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if df.empty:
      return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    dt_col = "Datetime" if "Datetime" in df.columns else "Date"
    df.rename(columns={dt_col: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
      df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df
  except Exception:
    return pd.DataFrame()


def get_timeframe_data(ticker: str, tf: str) -> pd.DataFrame:
  config = {
      "1m": ("5d", "1m"),
      "5m": ("15d", "5m"),
      "15m": ("30d", "15m"),
      "30m": ("30d", "30m"),
      "1h": ("60d", "1h"),
      "4h": ("60d", "1h"),
      "1D": ("2y", "1d"),
      "1W": ("5y", "1wk"),
  }
  period, yf_int = config.get(tf, ("30d", "15m"))
  df = fetch_data(ticker, period, yf_int)

  if not df.empty and tf == "4h":
    df = (
        df.set_index("Time")
        .resample("4h")
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
        .dropna()
