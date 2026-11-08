import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Page Configuration Optimized for Mobile
st.set_page_config(
    page_title="Mobile Order Block Signal Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Mobile Touch Friendliness and Cards
st.markdown("""
    <style>
    .mobile-card-buy {
        background-color: #132a1c;
        border-left: 5px solid #00c853;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .mobile-card-sell {
        background-color: #3a1518;
        border-left: 5px solid #ff3d00;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .badge-buy {
        background-color: #00c853;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-sell {
        background-color: #ff3d00;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📱 Order Block & SMC Trade Terminal")

# Sidebar Configuration
st.sidebar.header("⚙️ Scanner Settings")
STOCK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ITC.NS",
    "SUNPHARMA.NS", "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS"
]

selected_stock = st.sidebar.selectbox("Select Stock", STOCK_UNIVERSE)
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (Target 1)", 1.5, 4.0, 2.0, 0.5)

period_map = {"1d": "6mo", "1h": "1mo", "15m": "5d"}

# Data Engine
@st.cache_data(ttl=300)
def fetch_stock_data(ticker, tf, period):
    df = yf.download(ticker, period=period, interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

def analyze_order_blocks(df, risk_reward=2.0):
    df['Body'] = (df['Close'] - df['Open']).abs()
    df['ATR'] = df['Body'].rolling(14).mean()
    df['Displacement'] = df['Body'] > (1.2 * df['ATR'])
    df['Bullish_Impulse'] = (df['Close'] > df['Open']) & df['Displacement']
    df['Bearish_Impulse'] = (df['Close'] < df['Open']) & df['Displacement']

    signals = []
    
    for i in range(2, len(df)):
        # Bullish Order Block (BUY)
        if df['Bullish_Impulse'].iloc[i] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
            entry_min = round(df['Low'].iloc[i-1], 2)
            entry_max = round(df['High'].iloc[i-1], 2)
            sl = round(entry_min * 0.995, 2) # 0.5% buffer below OB Low
            risk = entry_max - sl
            t1 = round(entry_max + (risk * risk_reward), 2)
            t2 = round(entry_max + (risk * (risk_reward + 1.0)), 2)
            
            signals.append({
                'Time': df.index[i-1],
                'Stock': selected_stock.replace(".NS", ""),
                'Action': 'BUY',
                'Entry Zone': f"₹{entry_min} - ₹{entry_max}",
                'Entry_Max': entry_max,
                'SL': sl,
                'Target 1': t1,
                'Target 2': t2,
                'Risk': round(risk, 2),
                'Status': 'ACTIVE' if df['Close'].iloc[-1] >= sl else 'STOPPED'
            })
            
        # Bearish
