import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Institutional Order Block Flow", layout="wide")

st.title("🌊 Institutional Order Block & Liquidity Flow Terminal")
st.markdown("Tracks institutional order blocks, market displacement, and supply/demand zones across NSE F&O stocks.")

# Sidebar Controls
st.sidebar.header("Flow Parameters")
STOCK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ITC.NS",
    "SUNPHARMA.NS", "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS"
]

selected_stock = st.sidebar.selectbox("Select Asset for Flow Analysis", STOCK_UNIVERSE)
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
period_map = {"1d": "6mo", "1h": "1mo", "15m": "5d"}

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, tf, period):
    df = yf.download(ticker, period=period, interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

with st.spinner(f"Analyzing institutional order flow for {selected_stock}..."):
    data = fetch_stock_data(selected_stock, timeframe, period_map[timeframe])

if data.empty:
    st.error("Could not retrieve market data. Try another symbol.")
    st.stop()

# 2. Algorithm for Order Blocks & Liquidity Displacements
data['Body'] = (data['Close'] - data['Open']).abs()
data['ATR'] = data['Body'].rolling(14).mean()
# Displacement condition: Candle body is significantly larger than average
data['Displacement'] = data['Body'] > (1.3 * data['ATR'])
data['Bullish_Impulse'] = (data['Close'] > data['Open']) & data['Displacement']
data['Bearish_Impulse'] = (data['Close'] < data['Open']) & data['Displacement']

order_blocks = []
total_bullish_count = 0
total_bearish_count = 0

for i in range(2, len(data)):
    # Bullish OB: Last bearish candle before a strong bullish impulse
    if data['Bullish_Impulse'].iloc[i] and data['Close'].iloc[i-1] < data['Open'].iloc[i-1]:
        total_bullish_count += 1
        order_blocks.append({
            'Index': data.index[i-1],
            'Type': 'Bullish OB (Demand)',
            'Zone Low': data['Low'].iloc[i-1],
            'Zone High': data['High'].iloc[i-1],
            'Status': 'Active' if data['Close'].iloc[-1] > data['Low'].iloc[i-1] else 'Mitigated'
        })
    # Bearish OB: Last bullish candle before a strong bearish impulse
    elif data['Bearish_Impulse'].iloc[i] and data['Close'].iloc[i-1] > data['Open'].iloc[i-1]:
        total_bearish_count += 1
        order_blocks.append({
            'Index': data.index[i-1],
            'Type': 'Bearish OB (Supply)',
            'Zone Low': data['Low'].iloc[i-1],
            'Zone High': data['High'].iloc[i-1],
            'Status': 'Active' if data['Close'].iloc[-1] < data['High'].iloc[i-1] else 'Mitigated'
        })

# 3. Top Metrics Ribbon (Similar to Orderblock.com header layout)
col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Bullish Order Blocks", total_bullish_count, delta="Institutional Demand")
col2.metric("🔴 Bearish Order Blocks", total_bearish_count, delta="Institutional Supply", delta_color="inverse")
net_flow_ratio = (total_bullish_count / (total_bullish_count + total_bearish_count + 1e-5)) * 100
col3.metric("📊 Flow Bias Index", f"{net_flow_ratio:.1f}% Bullish")
col4.metric("💰 Last Traded Price", f"₹{data['Close'].iloc[-1]:.2f}")

st.markdown("---")

# 4. Advanced Interactive Flow Chart (Plotly Candlestick + OB Zones)
fig = go.Figure()

# Candlestick chart
fig.add_trace(go.Candlestick(
    x=data.index,
    open=data['Open'], high=data['High'],
    low=data['Low'], close=data['Close'],
    name="Price Action"
))

# Plot recent active Order Block zones as rectangular overlays
recent_obs = order_blocks[-8:] if len(order_blocks) >= 8 else order_blocks
for ob in recent_obs:
    color = "rgba(0, 255, 128, 0.25)" if "Bullish" in ob['Type'] else "rgba(255, 75, 75, 0.25)"
    fig.add_shape(
        type="rect",
        x0=ob['Index'], x1=data.index[-1],
        y0=ob['Zone Low'], y1=ob['Zone High'],
        fillcolor=color,
        line=dict(width=0),
        layer="below"
    )

fig.update_layout(
    title=f"{selected_stock} - Institutional Order Flow & Liquidity Bands",
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    height=600,
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# 5. Detected Order Blocks Matrix Table
st.subheader("📋 Active Institutional Order Block Zones")
if order_blocks:
    ob_df = pd.DataFrame(order_blocks).sort_values(by='Index', ascending=False)
    
    # Custom color styling function for dataframe
    def highlight_status(val):
        color = 'green' if val == 'Active' else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    st.dataframe(ob_df, use_container_width=True)
else:
    st.info("No significant institutional order blocks detected in the current window.")
