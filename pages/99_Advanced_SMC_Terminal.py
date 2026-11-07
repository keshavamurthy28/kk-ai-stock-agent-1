from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Institutional Trading Terminal - Advanced Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Dark Professional Look
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚡ Professional Institutional Trading Terminal: SMC, FVG & Multi-Indicator Suite")

# --- COMPREHENSIVE INDIAN STOCK UNIVERSE ---
ALL_STOCKS = {
    "RELIANCE - Reliance Industries Ltd": "RELIANCE.NS",
    "TCS - Tata Consultancy Services Ltd": "TCS.NS",
    "HDFCBANK - HDFC Bank Ltd": "HDFCBANK.NS",
    "INFY - Infosys Ltd": "INFY.NS",
    "ICICIBANK - ICICI Bank Ltd": "ICICIBANK.NS",
    "SBIN - State Bank of India": "SBIN.NS",
    "BHARTIARTL - Bharti Airtel Ltd": "BHARTIARTL.NS",
    "ITC - ITC Ltd": "ITC.NS",
    "KOTAKBANK - Kotak Mahindra Bank Ltd": "KOTAKBANK.NS",
    "LT - Larsen & Toubro Ltd": "LT.NS",
    "AXISBANK - Axis Bank Ltd": "AXISBANK.NS",
    "HINDUNILVR - Hindustan Unilever Ltd": "HINDUNILVR.NS",
    "BAJFINANCE - Bajaj Finance Ltd": "BAJFINANCE.NS",
    "MARUTI - Maruti Suzuki India Ltd": "MARUTI.NS",
    "TATAMOTORS - Tata Motors Ltd": "TATAMOTORS.NS",
    "SUNPHARMA - Sun Pharmaceutical Industries": "SUNPHARMA.NS",
    "TITAN - Titan Company Ltd": "TITAN.NS",
    "NTPC - NTPC Ltd": "NTPC.NS",
    "ONGC - Oil & Natural Gas Corporation": "ONGC.NS",
    "TATASTEEL - Tata Steel Ltd": "TATASTEEL.NS",
    "HEG - HEG Ltd": "HEG.NS",
    "TATAPOWER - Tata Power Co Ltd": "TATAPOWER.NS",
    "ZOMATO - Zomato Ltd": "ZOMATO.NS",
    "SUZLON - Suzlon Energy Ltd": "SUZLON.NS",
    "IRCTC - IRCTC Ltd": "IRCTC.NS",
    "WIPRO - Wipro Ltd": "WIPRO.NS",
    "BAJAJFINSV - Bajaj Finserv Ltd": "BAJAJFINSV.NS",
    "ASIANPAINT - Asian Paints Ltd": "ASIANPAINT.NS",
    "ADANIENT - Adani Enterprises Ltd": "ADANIENT.NS",
    "ADANIPORTS - Adani Ports & SEZ Ltd": "ADANIPORTS.NS",
    "POWERGRID - Power Grid Corp": "POWERGRID.NS",
    "JSWSTEEL - JSW Steel Ltd": "JSWSTEEL.NS",
    "GRASIM - Grasim Industries Ltd": "GRASIM.NS",
    "HINDALCO - Hindalco Industries Ltd": "HINDALCO.NS",
    "TECHM - Tech Mahindra Ltd": "TECHM.NS",
    "NESTLEIND - Nestle India Ltd": "NESTLEIND.NS",
    "CIPLA - Cipla Ltd": "CIPLA.NS",
    "DRREDDY - Dr. Reddy's Laboratories": "DRREDDY.NS",
    "SBILIFE - SBI Life Insurance Co Ltd": "SBILIFE.NS",
    "BPCL - Bharat Petroleum Corp Ltd": "BPCL.NS",
    "EICHERMOT - Eicher Motors Ltd": "EICHERMOT.NS",
    "TATACONSUM - Tata Consumer Products": "TATACONSUM.NS",
    "DIVISLAB - Divi's Laboratories Ltd": "DIVISLAB.NS",
    "APOLLOHOSP - Apollo Hospitals Enterprise": "APOLLOHOSP.NS",
    "HEROMOTOCO - Hero MotoCorp Ltd": "HEROMOTOCO.NS",
    "INDUSINDBK - IndusInd Bank Ltd": "INDUSINDBK.NS",
    "HDFCLIFE - HDFC Life Insurance": "HDFCLIFE.NS",
    "BRITANNIA - Britannia Industries Ltd": "BRITANNIA.NS",
    "SHRIRAMFIN - Shriram Finance Ltd": "SHRIRAMFIN.NS",
    "LTIM - LTIMindtree Ltd": "LTIM.NS",
    "TRENT - Trent Ltd": "TRENT.NS",
    "BEL - Bharat Electronics Ltd": "BEL.NS",
    "HAL - Hindustan Aeronautics Ltd": "HAL.NS",
    "NIFTY 50 - Index": "^NSEI",
    "BANK NIFTY - Index": "^NSEBANK",
}

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🛠️ Terminal Controls")

selected_stock_name = st.sidebar.selectbox(
    "Search & Select Stock", list(ALL_STOCKS.keys()), index=0
)
ticker_symbol = ALL_STOCKS[selected_stock_name]

# Unrestricted Custom Manual Ticker Input
custom_input = st.sidebar.text_input(
    "Or Type Any Ticker Manually (e.g., IOC.NS,IRFC.NS)"
)
if custom_input:
    ticker_symbol = custom_input.strip().upper()
    if (
        not ticker_symbol.endswith(".NS")
        and not ticker_symbol.endswith(".BO")
        and not ticker_symbol.startswith("^")
    ):
        ticker_symbol += ".NS"

timeframe = st.sidebar.selectbox(
    "Select Timeframe / Interval", ["1m", "5m", "15m", "1h", "1d"], index=2
)
period_map = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "730d",
    "1d": "max",
}
period = period_map.get(timeframe, "60d")


# --- DATA ENGINE ---
@st.cache_data(ttl=30)
def load_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df


data = load_data(ticker_symbol, period, timeframe)

if data.empty:
    st.error(
        f"No market data found for {ticker_symbol}. Check symbol accuracy or exchange trading status."
    )
    st.stop()


# --- TECHNICAL & ANALYTICS ENGINE ---
def compute_analytics(df):
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

    df["Vol_SMA20"] = df["Volume"].rolling(window=20).mean()
    df["Volume_Surge"] = df["Volume"] > (1.5 * df["Vol_SMA20"])

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    df["Signal"] = 0
    df.loc[
        (df["EMA_9"] > df["EMA_21"])
        & (df["EMA_9"].shift(1) <= df["EMA_21"].shift(1))
        & (df["Volume_Surge"]),
        "Signal",
    ] = 1
    df.loc[
        (df["EMA_9"] < df["EMA_21"])
        & (df["EMA_9"].shift(1) >= df["EMA_21"].shift(1))
        & (df["Volume_Surge"]),
        "Signal",
    ] = -1

    df["Bull_FVG_Low"] = np.nan
    df["Bull_FVG_High"] = np.nan
    df["Bear_FVG_Low"] = np.nan
    df["Bear_FVG_High"] = np.nan

    for i in range(1, len(df) - 1):
        if df["Low"].iloc[i + 1] > df["High"].iloc[i - 1]:
            df.iloc[i, df.columns.get_loc("Bull_FVG_Low")] = df["High"].iloc[
                i - 1
            ]
            df.iloc[i, df.columns.get_loc("Bull_FVG_High")] = df["Low"].iloc[
                i + 1
            ]
        elif df["High"].iloc[i + 1] < df["Low"].iloc[i - 1]:
            df.iloc[i, df.columns.get_loc("Bear_FVG_Low")] = df["High"].iloc[
                i + 1
            ]
            df.iloc[i, df.
