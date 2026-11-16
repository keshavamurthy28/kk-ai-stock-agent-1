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
    stock_input = st.text_input("NSE Symbol", value="RELIANCE", placeholder="e.g., RELIANCE, AMBER").upper().strip()
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
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.reset_index()
        df.rename(columns={"Datetime" if "Datetime" in df.columns else "Date": "Time"}, inplace=True)
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is not None: df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()

def get_tf_data(ticker: str, tf: str) -> pd.DataFrame:
    cfg = {"1m": ("5d", "1m"), "5m": ("15d", "5m"), "15m": ("30d", "15m"), "30m": ("30d", "30m"), "1h": ("60d", "1h"), "4h": ("60d", "1h"), "1D": ("2y", "1d"), "1W": ("5y", "1wk")}
    p, i = cfg.get(tf, ("30d", "15m"))
    df = fetch_data(ticker, p, i)
    if not df.empty and tf == "4h":
        df = df.set_index("Time").resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna().reset_index()
    return df

def get_smc(df: pd.DataFrame, df_4h: pd.DataFrame):
    bull_fvg, bear_fvg = [], []
    for i in range(2, len(df_4h)):
        if df_4h["Low"].iloc[i] > df_4h["High"].iloc[i-2]: bull_fvg.append((df_4h["Time"].iloc[i-2], float(df_4h["High"].iloc[i-2]), float(df_4h["Low"].iloc[i])))
        if df_4h["High"].iloc[i] < df_4h["Low"].iloc[i-2]: bear_fvg.append((df_4h["Time"].iloc[i-2], float(df_4h["High"].iloc[i]), float(df_4h["Low"].iloc[i-2])))
    df = df.copy()
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    df["SL"] = df["Low"] == df["Low"].rolling(9, center=True).min()
    sigs, sh, sl, tr = [], None, None, "neutral"
    for i in range(4, len(df)):
        if df["SH"].iloc[i-4]: sh = (df["Time"].iloc[i-4], float(df["High"].iloc[i-4]))
        if df["SL"].iloc
