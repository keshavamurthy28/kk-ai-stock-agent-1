import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="AI Intraday & Trend Analysis Agent", page_icon="⚡", layout="wide"
)

st.title("⚡ AI Intraday & Trend Analysis Agent")
st.markdown(
    "Interactive Candlestick & Technical Indicator Dashboard with Multi-Tier Volume Delta Color-Coding, Stop Loss levels, and automated signals."
)

# -------------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🎯 Trading Controls")
ticker_input = (
    st.sidebar.text_input("Stock Ticker (e.g., INFY, RELIANCE, TCS)", value="INFY")
    .strip()
    .upper()
)
timeframe_option = st.sidebar.selectbox(
    "Select Timeframe", ["1m", "5m", "15m", "1h", "1d"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Chart Customization")
show_candles = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_ema20 = st.sidebar.checkbox("Show 20 EMA Line", value=True)
show_ema50 = st.sidebar.checkbox("Show 50 EMA Line", value=True)
show_delta = st.sidebar.checkbox("Show Orderflow Delta Subplot", value=True)
show_rsi = st.sidebar.checkbox("Show RSI Subplot", value=True)

# Format ticker for Yahoo Finance (defaulting to .NS for NSE if no suffix)
if ticker_input and not any(
    ticker_input.endswith(s) for s in [".NS", ".BO", ".US"]
):
    ticker_symbol = f"{ticker_input}.NS"
else:
    ticker_symbol = ticker_input


# -------------------------------------------------------------------
# DATA FETCHER & INDICATOR ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_stock_data(symbol, interval):
    period = (
        "5d"
        if interval in ["1m", "5m", "15m"]
        else ("60d" if interval == "1h" else "1y")
    )
    t = yf.Ticker(symbol)
    df = t.history(period=period, interval=interval)
    return df


df_data = load_stock_data(ticker_symbol, timeframe_option)

if df_data.empty or len(df_data) < 15:
    st.error(
        f"Unable to fetch valid data for **{ticker_symbol}** at timeframe **{timeframe_option}**. Please try another ticker or timeframe."
    )
else:
    # Calculations
    df_data["20_EMA"] = df_data["Close"].ewm(span=20, adjust=False).mean()
    df_data["50_EMA"] = df_data["Close"].ewm(span=50, adjust=False).mean()

    # RSI Calculation
    delta_prices = df_data["Close"].diff()
    gain = (delta_prices.where(delta_prices > 0, 0)).rolling(window=14).mean()
    loss = (-delta_prices.where(delta_prices < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, 0.001)
    df_data["RSI"] = 100 - (100 / (1 + rs))

    # Orderflow Delta Proxy calculation
    hl_range = (df_data["High"] - df_data["Low"]).replace(0, 0.01)
    clv = (2 * df_data["Close"] - df_data["High"] - df_data["Low"]) / hl_range
    df_data["Buy Vol"] = (df_data["Volume"] * (0.5 + (0.5 * clv))).fillna(0)
    df_data["Sell Vol"] = (df_data["Volume"] * (0.5 - (0.5 * clv))).fillna(0)
    df_data["Delta"] = df_data["Buy Vol"] - df_data["Sell Vol"]

    # Volume Surge Multi-Tier Mapping
    vol_ma = df_data["Volume"].rolling(window=20).mean()
    df_data["Vol_Ratio"] = df_data["Volume"] / vol_ma.replace(0, 1)


    # Dynamic Color Assignment Function
    def get_delta_color(row):
        delta = row["Delta"]
        v_ratio = row["Vol_Ratio"]
        if delta >= 0:
            # High Volume Surge Buy vs Normal Buy
            return "#00E676" if v_ratio >= 2.0 else "#26a69a"
        else:
            # High Volume Surge Sell vs Normal Sell
            return "#FF1744" if v_ratio >= 2.0 else "#ef5350"


    df_data["Bar_Color"] = df_data.apply(get_delta_color, axis=1)

    latest_close = float(df_data["Close"].iloc[-1])
    recent_low = float(df_data["Low"].tail(10).min())
    stop_loss = round(recent_low * 0.992, 2)
    target_price = round(latest_close + (2 * (latest_close - stop_loss)), 2)

    net_delta = float(df_data["Delta"].tail(5).sum())
    ema20_val = float(df_data["20_EMA"].iloc[-1])
    rsi_val = float(df_data["RSI"].iloc[-1])

    # Signal logic
    if latest_close > ema20_val and net_delta > 0:
        intraday_signal = "🟢 BUY / LONG"
    elif latest_close < ema20_val and net_delta < 0:
        intraday_signal = "🔴 SELL / SHORT"
    else:
        intraday_signal = "⚪ HOLD / WATCH"

    # -------------------------------------------------------------------
    # METRICS TOP BAR
    # -------------------------------------------------------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Price (LTP)", f"₹{latest_close:,.2f}")
    m2.metric("Intraday Signal", intraday_signal)
    m3.metric("Target Price", f"₹{target_price:,.2f}")
    m4.metric("Stop Loss (SL)", f"₹{stop_loss:,.2f}")
    m5.metric("RSI (14)", f"{rsi_val:.2f}")

    st.markdown("---")

    # Legend info explaining colors
    st.markdown(
        """
        🎨 **Orderflow Delta Color Guide:** 
        * <span style="color:#00E676; font-weight:bold;">■ Bright Green (#00E676)</span>: Heavy Volume Surge ($\ge 2x$) + Aggressive Buying
        * <span style="color:#26a69a; font-weight:bold;">■ Normal Green (#26a69a)</span>: Standard Buying Delta
        * <span style="color:#ef5350; font-weight:bold;">■ Normal Red (#ef5350)</span>: Standard Selling Delta
        * <span style="color:#FF1744; font-weight:bold;">■ Bright Red (#FF1744)</span>: Heavy Volume Surge ($\ge 2x$) + Aggressive Selling Dump
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # -------------------------------------------------------------------
    # DYNAMIC SUBPLOT CHART GENERATION
    # -------------------------------------------------------------------
    subplot_rows = 1
    row_heights = [1.0]
    subplot_titles_list = [f"{ticker_symbol} Price Action"]

    if show_delta:
        subplot_rows += 1
        row_heights.append(0.3)
        subplot_titles_list.append(
            "Orderflow Delta Volume (Surge Highlighted)"
        )

    if show_rsi:
        subplot_rows += 1
        row_heights.append(0.3)
        subplot_titles_list.append("RSI (14) Indicator")

    total_h = sum(row_heights)
    normalized_heights = [h / total_h for h in row_heights]

    fig = make_subplots(
        rows=subplot_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=normalized_heights,
        subplot_titles=subplot_titles_list,
    )

    current_row = 1

    # Row 1: Candlesticks & EMAs
    if show_candles:
        fig.add_trace(
            go.Candlestick(
                x=df_data.index,
                open=df_data["Open"],
                high=df_data["High"],
                low=df_data["Low"],
                close=df_data["Close"],
                name="OHLC Price",
            ),
            row=current_row,
            col=1,
        )

    if show_ema20:
        fig.add_trace(
            go.Scatter(
                x=df_data.index,
                y=df_data["20_EMA"],
                line=dict(color="#2979FF", width=1.5),
                name="20 EMA",
            ),
            row=current_row,
            col=1,
        )

    if show_ema50:
        fig.add_trace(
            go.Scatter(
                x=df_data.index,
                y=df_data["50_EMA"],
                line=dict(color="#FF9100", width=1.5),
                name="50 EMA",
            ),
            row=current_row,
            col=1,
        )

    current_row += 1

    # Row 2: Orderflow Delta with Multi-Tier Colors
    if show_delta:
        fig.add_trace(
            go.Bar(
                x=df_data.index,
                y=df_data["Delta"],
                name="Orderflow Delta",
                marker_color=df_data["Bar_Color"],
            ),
            row=current_row,
            col=1,
        )
        current_row += 1

    # Row 3: RSI Subplot
    if show_rsi:
        fig.add_trace(
            go.Scatter(
                x=df_data.index,
                y=df_data["RSI"],
                line=dict(color="#AB47BC", width=1.5),
                name="RSI",
            ),
            row=current_row,
            col=1,
        )
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="red",
            row=current_row,
            col=1,
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="green",
            row=current_row,
            col=1,
        )

    fig.update_layout(
        height=650 + (150 * (subplot_rows - 1)),
        margin=dict(l=10, r=10, t=30, b=10),
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    st.subheader(f"📊 Interactive Hands-On Chart ({ticker_symbol})")
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # RECENT CANDLE DATA TABLE
    # -------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📋 Recent Candle Data & Indicator Metrics")
    display_df = df_data[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Delta",
            "20_EMA",
            "50_EMA",
            "RSI",
        ]
    ].tail(10)
    display_df.columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Delta",
        "20 EMA",
        "50 EMA",
        "RSI",
    ]
    st.dataframe(display_df.style.format("{:.2f}"), use_container_width=True)
