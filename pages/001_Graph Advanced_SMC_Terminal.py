import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container { padding-top: 5rem !important; padding-bottom: 2rem !important; } div[data-testid='stHorizontalBlock'] { align-items: center; }</style>", unsafe_allow_html=True)

st.markdown("### 📊 Institutional SMC & FVG Execution Terminal")
col1, col2, col3 = st.columns([2, 6, 2])
with col1:
    stock_input = st.text_input("NSE Symbol", value="RELIANCE", placeholder="Symbol (e.g., RELIANCE, AMBER)").upper().strip()
ticker_symbol = f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
with col2:
    selected_tf = st.radio("Candle Interval", ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"], index=2, horizontal=True)
with col3:
    show_mtf_zones = st.toggle("Show 1D & 4H Zones", value=True)
st.markdown("---")

@st.cache_data(ttl=60)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
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
    cfg = {"1m": ("5d", "1m"), "5m": ("15d", "5m"), "15m": ("30d", "15m"), "30m": ("30d", "30m"), "1h": ("60d", "1h"), "4h": ("60d", "1h"), "1D": ("2y", "1d"), "1W": ("5y", "1wk")}
    period, yf_int = cfg.get(tf, ("30d", "15m"))
    df = fetch_data(ticker, period, yf_int)
    if not df.empty and tf == "4h":
        df = df.set_index("Time").resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna().reset_index()
    return df

def detect_fvgs(df: pd.DataFrame, max_zones: int = 2):
    bull, bear = [], []
    for i in range(2, len(df)):
        if df["Low"].iloc[i] > df["High"].iloc[i - 2]:
            bull.append({"start": df["Time"].iloc[i - 2], "y0": float(df["High"].iloc[i - 2]), "y1": float(df["Low"].iloc[i])})
        if df["High"].iloc[i] < df["Low"].iloc[i - 2]:
            bear.append({"start": df["Time"].iloc[i - 2], "y0": float(df["High"].iloc[i]), "y1": float(df["Low"].iloc[i - 2])})
    return bull[-max_zones:], bear[-max_zones:]

def detect_structure_and_signals(df: pd.DataFrame, lookback: int = 4):
    df = df.copy()
    df["SH"] = df["High"] == df["High"].rolling(2 * lookback + 1, center=True).max()
    df["SL"] = df["Low"] == df["Low"].rolling(
