import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced Educational Intraday Terminal",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Pro Intraday Orderflow & Educational Trading Terminal")
st.markdown(
    "Learn live market mechanics! This terminal overlays **VWAP**, **EMA Confluence**, **Orderflow Delta**, and **Educational Annotations** directly on your charts."
)

# -------------------------------------------------------------------
# 1. CLEAN SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Terminal Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., INFY, RELIANCE, TCS)", value="INFY"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["5m", "15m", "30m", "1h", "1d"], index=1
)

fetch_period = "60d" if timeframe in ["5m", "15m", "30m", "1h"] else "max"

st.sidebar.markdown("---")
st.sidebar.header("📊 Interactive Overlays")
show_candlestick = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_vwap = st.sidebar.checkbox("Show VWAP Benchmark", value=True)
show_ema20 = st.sidebar.checkbox("Show 20 EMA Line", value=True)
show_ema50 = st.sidebar.checkbox("Show 50 EMA Line", value=True)
show_signals = st.sidebar.checkbox(
    "Show Educational Buy/Sell Signals on Chart", value=True
)

# -------------------------------------------------------------------
# 2. DATA FETCHER & TECHNICAL ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_intraday_data(ticker, period, interval):
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

with st.spinner(f"Loading live data & calculating indicators for `{symbol_str}`..."):
    df = fetch_intraday_data(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 10:
    st.error(f"Could not retrieve data for `{symbol_str}` on interval `{timeframe}`. Please check the ticker symbol.")
else:
    # Technical Calculations
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # VWAP Calculation
    q = df["Volume"]
    p = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (p * q).cumsum() / q.cumsum()

    # RSI Calculation
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Volume Delta Calculation
    range_hl = (df["High"] - df["Low"]).replace(0, 0.001)
    buy_ratio = (df["Close"] - df["Low"]) / range_hl
    df["Buy_Volume"] = df["Volume"] * buy_ratio
    df["Sell_Volume"] = df["Volume"] * (1 - buy_ratio)
    df["Delta"] = df["Buy_Volume"] - df["Sell_Volume"]

    # RVOL Calculation
    df["Avg_Volume_20"] = df["Volume"].rolling(window=20).mean()
    df["RVOL"] = df["Volume"] / df["Avg_Volume_20"]

    # Identify Learning/Trade Signals on Candles
    df["Signal_Type"] = "NONE"
    for i in range(1, len(df)):
        if (
            df["Close"].iloc[i] > df["VWAP"].iloc[i]
            and df["Close"].iloc[i - 1] <= df["VWAP"].iloc[i - 1]
            and df["Delta"].iloc[i] > 0
        ):
            df.loc[df.index[i], "Signal_Type"] = "BUY"
        elif (
            df["Close"].iloc[i] < df["VWAP"].iloc[i]
            and df["Close"].iloc[i - 1] >= df["VWAP"].iloc[i - 1]
            and df["Delta"].iloc[i] < 0
        ):
            df.loc[df.index[i], "Signal_Type"] = "SELL"

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100

    # -------------------------------------------------------------------
    # 3. METRICS OVERVIEW BAR
    # -------------------------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Last Traded Price", f"₹{latest['Close']:.2f}", f"{price_change:+.2f}%")
    col2.metric("Relative Volume (RVOL)", f"{latest['RVOL']:.2f}x")
    col3.metric("VWAP Trend", f"₹{latest['VWAP']:.2f}", "Bullish" if latest["Close"] > latest["VWAP"] else "Bearish")
    col4.metric("RSI (14)", f"{latest['RSI']:.1f}")
    col5.metric("Net Delta", f"{int(latest['Delta']):,}", "Net Buyers" if latest["Delta"] > 0 else "Net Sellers")

    # -------------------------------------------------------------------
    # 4. TRADINGVIEW-STYLE MULTI-PANE CHART GENERATION
    # -------------------------------------------------------------------
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.22, 0.23],
        subplot_titles=(
            f"{symbol_str} Price Action, VWAP & EMAs (With Educational Signals)",
            "Net Buy/Sell Volume Delta (Orderflow)",
            "RSI (14) Momentum",
        ),
    )

    # Pane 1: Price Action
    if show_candlestick:
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
            ),
            row=1,
            col=1,
        )

    if show_vwap:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["VWAP"], mode="lines", name="VWAP (Fair Value)", line=dict(color="#FFA726", width=2)),
            row=1, col=1,
        )

    if show_ema20:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["EMA_20"], mode="lines", name="20 EMA (Fast Trend)", line=dict(color="#29B6F6", width=1.2)),
            row=1, col=1,
        )

    if show_ema50:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["EMA_50"], mode="lines", name="50 EMA (Slow Trend)", line=dict(color="#AB47BC", width=1.2)),
            row=1, col=1,
        )

    if show_signals:
        buy_signals = df[df["Signal_Type"] == "BUY"]
        sell_signals = df[df["Signal_Type"] == "SELL"]

        if not buy_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals["Low"] * 0.995,
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=12, color="#00E676"),
                    name="🟢 Learn: BUY Signal (VWAP Cross + Delta)",
                ),
                row=1, col=1,
            )

        if not sell_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals["High"] * 1.005,
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=12, color="#FF1744"),
                    name="🔴 Learn: SELL Signal (VWAP Breakdown)",
                ),
                row=1, col=1,
            )

    # Pane 2: Orderflow Delta Bar Chart
    bar_colors = ["#00E676" if v >= 0 else "#FF1744" for v in df["Delta"]]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Delta"], marker_color=bar_colors, name="Net Delta Volume"),
        row=2, col=1,
    )

    # Pane 3: RSI Momentum
    fig.add_trace(
        go.Scatter(x=df.index, y=df["RSI"], mode="lines", name="RSI (14)", line=dict(color="#7E57C2", width=1.5)),
        row=3, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="#EF5350", row=3, col=1, annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#66BB6A", row=3, col=1, annotation_text="Oversold (30)")

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=800,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # 5. EDUCATIONAL TRADER'S GUIDE
    # -------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🎓 Interactive Trading Guide: How to Learn from This Chart")

    col_guide1, col_guide2, col_guide3 = st.columns(3)

    with col_guide1:
        st.markdown("#### 1️⃣ VWAP (Orange Line)")
        st.markdown(
            "- **What it is:** The Volume Weighted Average Price represents the true institutional 'fair value' price of the day.\n"
            "- **How to Trade:** If price stays **above VWAP**, institutions are accumulating (look for Buy setups). If price stays **below**, sellers are in control."
        )

    with col_guide2:
        st.markdown("#### 2️⃣ Orderflow Delta (Middle Pane)")
        st.markdown(
            "- **What it is:** Shows whether aggressive buyers (Green) or aggressive sellers (Red) dominated each candle.\n"
            "- **How to Trade:** A breakout candle accompanied by tall **Green Bars** means the move is backed by real capital. Low bars mean weak momentum."
        )

    with col_guide3:
        st.markdown("#### 3️⃣ Signals & EMAs (Green/Red Arrows)")
        st.markdown(
            "- **Green Arrows (🟢):** Triggered when price crosses above VWAP supported by net buying pressure. Ideal entry for intraday long momentum.\n"
            "- **Red Arrows (🔴):** Triggered when price breaks below VWAP with heavy selling pressure."
        )
