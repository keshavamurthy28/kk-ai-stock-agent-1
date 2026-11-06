import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Terminal - Full History",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Advanced Indian Stock Terminal (Full History & Instant Search)")

# -------------------------------------------------------------------
# EXTENSIVE INDIAN STOCKS DIRECTORY (NSE/BSE)
# -------------------------------------------------------------------
INDIAN_STOCKS = {
    "RELIANCE - Reliance Industries Ltd": "RELIANCE.NS",
    "HDFCBANK - HDFC Bank Ltd": "HDFCBANK.NS",
    "INFY - Infosys Ltd": "INFY.NS",
    "TCS - Tata Consultancy Services Ltd": "TCS.NS",
    "ICICIBANK - ICICI Bank Ltd": "ICICIBANK.NS",
    "SBIN - State Bank of India": "SBIN.NS",
    "BHARTIARTL - Bharti Airtel Ltd": "BHARTIARTL.NS",
    "ITC - ITC Ltd": "ITC.NS",
    "KOTAKBANK - Kotak Mahindra Bank Ltd": "KOTAKBANK.NS",
    "LT - Larsen & Toubro Ltd": "LT.NS",
    "AXISBANK - Axis Bank Ltd": "AXISBANK.NS",
    "ASIANPAINT - Asian Paints Ltd": "ASIANPAINT.NS",
    "MARUTI - Maruti Suzuki India Ltd": "MARUTI.NS",
    "SUNPHARMA - Sun Pharmaceutical Industries Ltd": "SUNPHARMA.NS",
    "TITAN - Titan Company Ltd": "TITAN.NS",
    "BAJFINANCE - Bajaj Finance Ltd": "BAJFINANCE.NS",
    "WIPRO - Wipro Ltd": "WIPRO.NS",
    "TATAMOTORS - Tata Motors Ltd": "TATAMOTORS.NS",
    "NTPC - NTPC Ltd": "NTPC.NS",
    "POWERGRID - Power Grid Corporation": "POWERGRID.NS",
    "TATASTEEL - Tata Steel Ltd": "TATASTEEL.NS",
    "ADANIENT - Adani Enterprises Ltd": "ADANIENT.NS"
}

# -------------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Terminal Controls")

# Searchable dropdown: Type letters like 'rel', 'tcs', 'tat' to instantly filter
selected_stock_label = st.sidebar.selectbox(
    "🔍 Search & Select Stock",
    options=list(INDIAN_STOCKS.keys()),
    index=0
)
symbol_str = INDIAN_STOCKS[selected_stock_label]

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["5m", "15m", "1h", "1d"], index=3
)

# Automatically adjust period to maximize history available safely
if timeframe in ["5m", "15m"]:
    fetch_period = "59d"  # Yahoo Finance intraday limit constraint
elif timeframe == "1h":
    fetch_period = "730d" # Max 2 years for hourly data
else:
    fetch_period = "max"  # Pulls absolute maximum history from listing date for Daily charts

# -------------------------------------------------------------------
# FAST CACHED DATA LOADER
# -------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def load_stock_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

with st.spinner(f"Fetching complete data archive for `{symbol_str}`..."):
    df = load_stock_data(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 5:
    st.error(f"Could not retrieve history for `{symbol_str}` on `{timeframe}` timeframe.")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

    # Metric Display
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest Price", f"₹{latest['Close']:.2f}", f"{change:+.2f}%")
    c2.metric("Total Bars Loaded", f"{len(df):,}")
    c3.metric("Data Range", f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")

    # Native interactive chart display (Fast & responsive)
    st.line_chart(df['Close'])
