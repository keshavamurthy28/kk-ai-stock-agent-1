import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(
    page_title="Mobile Order Block Signal Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📱 Order Block & SMC Trade Terminal")

# Custom CSS for Mobile Cards
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
        background-color: #00c853; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .badge-sell {
        background-color: #ff3d00; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("⚙️ Scanner Settings")
STOCK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ITC.NS"
]

selected_stock = st.sidebar.selectbox("Select Stock", STOCK_UNIVERSE)
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1h"], index=0)
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio", 1.5, 4.0, 2.0, 0.5)

# Safe Data Loader with yfinance and fallback simulation if network fails
@st.cache_data(ttl=300)
def fetch_stock_data(ticker, tf):
    try:
        import yfinance as yf
        period = "3mo" if tf == "1d" else "1mo"
        df = yf.download(ticker, period=period, interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        if not df.empty:
            return df
    except Exception as e:
        st.warning(f"Network warning: {e}. Using fallback data frame.")
    
    # Fallback dummy data frame if yfinance fails or blocks connection
    dates = pd.date_range(end=pd.Timestamp.today(), periods=100, freq='H' if tf=='1h' else 'D')
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(100) * 10)
    df_dummy = pd.DataFrame({
        'Open': close - 5,
        'High': close + 10,
        'Low': close - 10,
        'Close': close,
        'Volume': np.random.randint(1000, 50000, 100)
    }, index=dates)
    return df_dummy

with st.spinner("Fetching market data..."):
    data = fetch_stock_data(selected_stock, timeframe)

if data is None or data.empty:
    st.error("Data could not be loaded. Please check your internet connection or try a different stock.")
    st.stop()

# Order block analysis function
def analyze_order_blocks(df, risk_reward=2.0):
    df['Body'] = (df['Close'] - df['Open']).abs()
    df['ATR'] = df['Body'].rolling(14, min_periods=1).mean()
    df['Displacement'] = df['Body'] > (1.2 * df['ATR'])
    df['Bullish_Impulse'] = (df['Close'] > df['Open']) & df['Displacement']
    df['Bearish_Impulse'] = (df['Close'] < df['Open']) & df['Displacement']

    signals = []
    for i in range(2, len(df)):
        if df['Bullish_Impulse'].iloc[i] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
            entry_min = round(float(df['Low'].iloc[i-1]), 2)
            entry_max = round(float(df['High'].iloc[i-1]), 2)
            sl = round(entry_min * 0.995, 2)
            risk = entry_max - sl
            t1 = round(entry_max + (risk * risk_reward), 2)
            t2 = round(entry_max + (risk * (risk_reward + 1.0)), 2)
            signals.append({
                'Time': df.index[i-1],
                'Action': 'BUY',
                'Entry Zone': f"₹{entry_min} - ₹{entry_max}",
                'SL': sl, 'Target 1': t1, 'Target 2': t2, 'Status': 'ACTIVE'
            })
        elif df['Bearish_Impulse'].iloc[i] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
            entry_min = round(float(df['Low'].iloc[i-1]), 2)
            entry_max = round(float(df['High'].iloc[i-1]), 2)
            sl = round(entry_max * 1.005, 2)
            risk = sl - entry_min
            t1 = round(entry_min - (risk * risk_reward), 2)
            t2 = round(entry_min - (risk * (risk_reward + 1.0)), 2)
            signals.append({
                'Time': df.index[i-1],
                'Action': 'SELL',
                'Entry Zone': f"₹{entry_min} - ₹{entry_max}",
                'SL': sl, 'Target 1': t1, 'Target 2': t2, 'Status': 'ACTIVE'
            })
    return signals

signals = analyze_order_blocks(data, rr_ratio)
latest_price = round(float(data['Close'].iloc[-1]), 2)

# Tabs
tab1, tab2 = st.tabs(["📲 Mobile Signals", "📊 Chart View"])

with tab1:
    st.subheader(f"⚡ Signals ({selected_stock.replace('.NS', '')})")
    st.metric("Current Market Price", f"₹{latest_price}")
    
    if signals:
        for sig in reversed(signals[-5:]):
            is_buy = sig['Action'] == 'BUY'
            card_class = "mobile-card-buy" if is_buy else "mobile-card-sell"
            badge_class = "badge-buy" if is_buy else "badge-sell"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between;">
                    <span class="{badge_class}">{sig['Action']} SIGNAL</span>
                    <span style="color: #aaa; font-size: 11px;">{str(sig['Time'])[:16]}</span>
                </div>
                <div style="margin-top: 8px; font-size: 15px; font-weight: bold;">
                    Entry Zone: {sig['Entry Zone']}
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px;">
                    <div>🛑 SL: ₹{sig['SL']}</div>
                    <div>🎯 T1: ₹{sig['Target 1']}</div>
                    <div>🚀 T2: ₹{sig['Target 2']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active order blocks found in current timeframe. Try changing timeframe to 1h.")

with tab2:
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'], name="Price"
    )])
    fig.update_layout(
        template="plotly_dark", height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)
