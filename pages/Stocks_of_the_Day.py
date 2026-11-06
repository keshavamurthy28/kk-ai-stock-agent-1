import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="SuperTrend & Actionable Signal Terminal",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Pro SuperTrend & Actionable Signal Trading Terminal")
st.markdown(
    "Interactive TradingView-style terminal featuring **ATR SuperTrend Band Confluence**, **Dynamic Buy/Sell Signal Callouts**, and **Orderflow Delta**."
)

# -------------------------------------------------------------------
# 1. SIDEBAR TRADING CONTROLS & STRATEGY PARAMETERS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ SuperTrend Strategy Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., HDFCBANK, INFY, RELIANCE)", value="HDFCBANK"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["5m", "15m", "30m", "1h", "1d"], index=1
)
fetch_period = "60d" if timeframe in ["5m", "15m", "30m", "1h"] else "max"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ SuperTrend Parameters")
atr_period = st.sidebar.slider("ATR Period", 5, 20, 10)
atr_multiplier = st.sidebar.slider("ATR Multiplier", 1.0, 5.0, 3.0, 0.1)

show_candlestick = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_supertrend = st.sidebar.checkbox("Show SuperTrend Band Line", value=True)
show_signals = st.sidebar.checkbox("Show Buy / Sell Signal Markers", value=True)

# -------------------------------------------------------------------
# 2. DATA FETCHER & SUPERTREND STRATEGY ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_and_calculate_supertrend(ticker, period, interval, period_atr, mult):
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty or len(df) < period_atr:
        return df

    # --- True Range & ATR Calculation ---
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period_atr).mean()

    # --- SuperTrend Logic ---
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_Upper'] = hl2 + (mult * df['ATR'])
    df['Basic_Lower'] = hl2 - (mult * df['ATR'])

    df['Final_Upper'] = 0.0
    df['Final_Lower'] = 0.0
    df['SuperTrend'] = 0.0
    df['Trend'] = 1  # 1 = Bullish, -1 = Bearish

    upper_list = [0.0] * len(df)
    lower_list = [0.0] * len(df)
    st_list = [0.0] * len(df)
    trend_list = [1] * len(df)

    close = df['Close'].values
    basic_upper = df['Basic_Upper'].values
    basic_lower = df['Basic_Lower'].values
    final_upper = df['Final_Upper'].values
    final_lower = df['Final_Lower'].values
    
    for i in range(1, len(df)):
        # Upper Band
        if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
            upper_list[i] = basic_upper[i]
        else:
            upper_list[i] = final_upper[i-1]

        # Lower Band
        if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
            lower_list[i] = basic_lower[i]
        else:
            lower_list[i] = final_lower[i-1]

        # Trend and SuperTrend assignment
        if trend_list[i-1] == 1:
            if close[i] <= lower_list[i]:
                trend_list[i] = -1
                st_list[i] = upper_list[i]
            else:
                trend_list[i] = 1
                st_list[i] = lower_list[i]
        else:
            if close[i] >= upper_list[i]:
                trend_list[i] = 1
                st_list[i] = lower_list[i]
            else:
                trend_list[i] = -1
                st_list[i] = upper_list[i]

    df['SuperTrend'] = st_list
    df['Trend'] = trend_list

    # Generate Actionable Buy/Sell Crossover Signals
    df['Signal'] = "HOLD"
    df['Signal_Label'] = ""
    for i in range(1, len(df)):
        if df['Trend'].iloc[i] == 1 and df['Trend'].iloc[i-1] == -1:
            df.loc[df.index[i], 'Signal'] = "BUY"
            df.loc[df.index[i], 'Signal_Label'] = "Buy long"
        elif df['Trend'].iloc[i] == -1 and df['Trend'].iloc[i-1] == 1:
            df.loc[df.index[i], 'Signal'] = "SELL"
            df.loc[df.index[i], 'Signal_Label'] = "Sell short"

    # Volume Delta for Subplot
    range_hl = (df['High'] - df['Low']).replace(0, 0.001)
    buy_ratio = (df['Close'] - df['Low']) / range_hl
    df['Delta'] = df['Volume'] * (2 * buy_ratio - 1)
    
    return df

with st.spinner(f"Computing SuperTrend indicators for `{symbol_str}`..."):
    df = fetch_and_calculate_supertrend(symbol_str, fetch_period, timeframe, atr_period, atr_multiplier)

if df.empty or len(df) < 10:
    st.error(f"Could not retrieve enough data for `{symbol_str}` on interval `{timeframe}`.")
else:
    latest = df.iloc.to_list()[-1] if hasattr(df.iloc[-1], 'to_list') else df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

    # -------------------------------------------------------------------
    # 3. EXECUTIVE METRICS BAR
    # -------------------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Last Traded Price", f"₹{latest['Close']:.2f}", f"{price_change:+.2f}%")
    c2.metric("SuperTrend Status", "BULLISH (UP)" if latest['Trend'] == 1 else "BEARISH (DOWN)")
    c3.metric("ATR Band Value", f"₹{latest['SuperTrend']:.2f}")
    c4.metric("Active ATR", f"₹{latest['ATR']:.2f}")
    c5.metric("Trend Signal", "🟢 BUY Active" if latest['Trend'] == 1 else "🔴 SELL Active")

    # -------------------------------------------------------------------
    # 4. TRADINGVIEW-STYLE DYNAMIC PLOTLY CHART GENERATION
    # -------------------------------------------------------------------
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=(
            f"{symbol_str} Price Action & SuperTrend Strategy Overlay",
            "Net Volume Delta (Orderflow Momentum)"
        )
    )

    # Candlestick Pane
    if show_candlestick:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="OHLC"
        ), row=1, col=1)

    # SuperTrend Line Split into Bullish (Green) and Bearish (Red) Segments
    if show_supertrend:
        bullish_st = df.copy()
        bullish_st.loc[bullish_st['Trend'] == -1, 'SuperTrend'] = np.nan
        
        bearish_st = df.copy()
        bearish_st.loc[bearish_st['Trend'] == 1, 'SuperTrend'] = np.nan

        fig.add_trace(go.Scatter(
            x=bullish_st.index, y=bullish_st['SuperTrend'],
            mode='lines', name='SuperTrend (Bullish)',
            line=dict(color='#00E676', width=2.5)
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=bearish_st.index, y=bearish_st['SuperTrend'],
            mode='lines', name='SuperTrend (Bearish)',
            line=dict(color='#FF1744', width=2.5)
        ), row=1, col=1)

    # Plot Buy/Sell Signal Callout Markers (Matching your screenshot tags)
    if show_signals:
        buy_pts = df[df['Signal'] == 'BUY']
        sell_pts = df[df['Signal'] == 'SELL']

        if not buy_pts.empty:
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['Low'] * 0.994,
                mode='text+markers',
                text=['Buy long'] * len(buy_pts),
                textposition='bottom center',
                textfont=dict(color='#00E676', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-up', size=14, color='#00E676'),
                name='Buy Signal Marker'
            ), row=1, col=1)

        if not sell_pts.empty:
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['High'] * 1.006,
                mode='text+markers',
                text=['Sell short'] * len(sell_pts),
                textposition='top center',
                textfont=dict(color='#FF1744', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-down', size=14, color='#FF1744'),
                name='Sell Signal Marker'
            ), row=1, col=1)

    # Orderflow Delta Subplot
    delta_colors = ['#00E676' if v >= 0 else '#FF1744' for v in df['Delta']]
    fig.add_trace(go.Bar(
        x=df.index, y=df['Delta'], marker_color=delta_colors, name="Volume Delta"
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=750,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # 5. STRATEGY GUIDE
    # -------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📋 SuperTrend Execution & Strategy Guide")
    st.markdown(
        "- **Green SuperTrend Line:** Acts as an active trailing stop support. As long as price stays above the green line, hold your long position.\n"
        "- **Red SuperTrend Line:** Acts as resistance. When price flips below, the line turns red, signaling short/sell momentum.\n"
        "- **'Buy long' / 'Sell short' Callouts:** Automatically placed on candles where trend direction flips, exactly matching professional TradingView indicator layouts."
    )
