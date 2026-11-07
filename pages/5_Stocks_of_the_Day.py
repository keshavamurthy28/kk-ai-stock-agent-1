import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional SMC & ICT Execution Terminal",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Institutional Smart Money Concepts (SMC) & ICT Master Terminal")
st.markdown(
    "Advanced multi-timeframe execution suite featuring **Structure Breaks (BOS/CHoCH)**, "
    "**Liquidity Pools (Stop Hunts)**, **Fair Value Gaps (FVG)**, **VWAP Order Flow**, and **Automated Risk Management**."
)

# -------------------------------------------------------------------
# 1. SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Terminal Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., RELIANCE, TCS, HDFCBANK)", value="RELIANCE"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe / Resolution", ["5m", "15m", "30m", "1h", "1d"], index=4
)
fetch_period = "60d" if timeframe in ["5m", "15m", "30m", "1h"] else "max"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Institutional Overlays & Layers")
show_fvg = st.sidebar.checkbox("Show Fair Value Gaps (FVG)", value=True)
show_ob = st.sidebar.checkbox("Show Order Blocks (Support/Resistance)", value=True)
show_liquidity = st.sidebar.checkbox("Show Liquidity Pools (Equal Highs/Lows)", value=True)
show_vwap = st.sidebar.checkbox("Show Institutional VWAP", value=True)
show_signals = st.sidebar.checkbox("Show BOS / CHoCH & Entry Triggers", value=True)

# -------------------------------------------------------------------
# 2. ADVANCED INSTITUTIONAL SMC & ICT ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_and_calculate_institutional_smc(ticker, period, interval):
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty or len(df) < 30:
        return df

    # --- True Range & ATR ---
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()

    # --- Institutional VWAP ---
    q = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * q).cumsum() / q.cumsum()

    # --- Swing Highs & Lows for BOS / CHoCH ---
    window = 5
    df['Swing_High'] = df['High'][(df['High'] == df['High'].rolling(window*2+1, center=True).max())]
    df['Swing_Low'] = df['Low'][(df['Low'] == df['Low'].rolling(window*2+1, center=True).min())]

    # --- Market Structure (BOS & CHoCH) & Trend ---
    df['Structure'] = "NEUTRAL"
    df['Signal'] = "HOLD"
    df['Stop_Loss'] = np.nan
    df['Target'] = np.nan

    # Simple EMA Trend Baseline for structural alignment
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    for i in range(20, len(df)):
        if df['Close'].iloc[i] > df['EMA_50'].iloc[i] and df['EMA_50'].iloc[i] > df['EMA_200'].iloc[i]:
            df.loc[df.index[i], 'Structure'] = "BULLISH_BOS"
        elif df['Close'].iloc[i] < df['EMA_50'].iloc[i] and df['EMA_50'].iloc[i] < df['EMA_200'].iloc[i]:
            df.loc[df.index[i], 'Structure'] = "BEARISH_BOS"

    # --- Fair Value Gaps (FVG) ---
    df['FVG_Type'] = "NONE"
    df['FVG_Top'] = np.nan
    df['FVG_Bottom'] = np.nan

    for i in range(2, len(df)):
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:  # Bullish FVG
            df.loc[df.index[i], 'FVG_Type'] = "BULLISH_FVG"
            df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i-2]
            df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i]
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:  # Bearish FVG
            df.loc[df.index[i], 'FVG_Type'] = "BEARISH_FVG"
            df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i-2]
            df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i]

    # --- Order Blocks (Institutional Accumulation/Distribution Zones) ---
    df['OB_Type'] = "NONE"
    df['OB_Level'] = np.nan
    for i in range(5, len(df) - 1):
        if df['Close'].iloc[i] > df['High'].iloc[i-1] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
            df.loc[df.index[i], 'OB_Type'] = "BULLISH_OB"
            df.loc[df.index[i], 'OB_Level'] = df['Low'].iloc[i-1]
        elif df['Close'].iloc[i] < df['Low'].iloc[i-1] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
            df.loc[df.index[i], 'OB_Type'] = "BEARISH_OB"
            df.loc[df.index[i], 'OB_Level'] = df['High'].iloc[i-1]

    # --- Execution Signals ---
    for i in range(1, len(df)):
        if df['Structure'].iloc[i] == "BULLISH_BOS" and df['Structure'].iloc[i-1] != "BULLISH_BOS":
            df.loc[df.index[i], 'Signal'] = "BUY"
            df.loc[df.index[i], 'Stop_Loss'] = df['Low'].iloc[i] - (1.5 * df['ATR'].iloc[i])
            df.
