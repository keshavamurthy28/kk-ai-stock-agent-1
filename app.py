import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# Page setup
st.set_page_config(
    page_title="AI Intraday & Trend Stock Agent",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ AI Intraday & Trend Analysis Agent")
st.markdown(
    "Interactive **Candlestick & Technical Indicator Dashboard** with zoom, pan, hover inspection, and signal tracking."
)

# Sidebar controls
st.sidebar.header("🎯 Trading Controls")
ticker_symbol = st.sidebar.text_input(
    "Stock Ticker (e.g., INFY, RELIANCE, TCS)", value="INFY"
)
timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    ["1m", "5m", "15m", "1h", "1d"],
    index=0,  # Defaults to 1m
)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Chart Customization")
show_candlestick = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_ema20 = st.sidebar.checkbox("Show 20 EMA Line", value=True)
show_ema50 = st.sidebar.checkbox("Show 50 EMA Line", value=True)
show_rsi = st.sidebar.checkbox("Show RSI Subplot", value=True)

run_btn = st.sidebar.button("Run Technical Analysis")


def calculate_ema(series, span=20):
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def get_stock_data(symbol, timeframe_choice):
    ticker = (
        f"{symbol.upper()}.NS" if not symbol.endswith(".NS") else symbol.upper()
    )

    interval_map = {
        "1m": ("1m", "5d"),
        "5m": ("5m", "5d"),
        "15m": ("15m", "30d"),
        "1h": ("1h", "60d"),
        "1d": ("1d", "6mo"),
    }
    interval, period = interval_map.get(timeframe_choice, ("1m", "5d"))

    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )
    return df, ticker


if run_btn or ticker_symbol:
    if ticker_symbol:
        with st.spinner(
            f"Fetching {timeframe} intraday data for {ticker_symbol}..."
        ):
            df, full_ticker = get_stock_data(ticker_symbol, timeframe)

            if df.empty:
                st.error(
                    f"Could not fetch data for '{ticker_symbol}'. Please verify the ticker symbol."
                )
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    open_p = df["Open"][full_ticker]
                    high = df["High"][full_ticker]
                    low = df["Low"][full_ticker]
                    close = df["Close"][full_ticker]
                else:
                    open_p = df["Open"]
                    high = df["High"]
                    low = df["Low"]
                    close = df["Close"]

                # Indicators
                ema_20 = calculate_ema(close, 20)
                ema_50 = calculate_ema(close, 50)
                rsi = calculate_rsi(close, 14)

                df_calc = pd.DataFrame(
                    {"High": high, "Low": low, "Close": close}
                )
                atr = calculate_atr(df_calc, 14)

                latest_price = float(close.iloc[-1])
                latest_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
                latest_ema20 = (
                    float(ema_20.iloc[-1])
                    if not ema_20.empty
                    else latest_price
                )
                latest_ema50 = (
                    float(ema_50.iloc[-1])
                    if not ema_50.empty
                    else latest_price
                )
                latest_atr = (
                    float(atr.iloc[-1])
                    if not atr.dropna().empty
                    else (latest_price * 0.008)
                )

                # Intraday Signal Rules
                if (
                    latest_price > latest_ema20
                    and latest_ema20 > latest_ema50
                    and 40 <= latest_rsi <= 65
                ):
                    signal = "BUY / LONG"
                    stop_loss = latest_price - (1.2 * latest_atr)
                    target_price = latest_price + (1.8 * latest_atr)
                elif (
                    latest_price < latest_ema20 and latest_ema20 < latest_ema50
                ) or latest_rsi >= 70:
                    signal = "SELL / SHORT / EXIT"
                    stop_loss = latest_price + (1.2 * latest_atr)
                    target_price = latest_price - (1.8 * latest_atr)
                else:
                    signal = "HOLD / NEUTRAL"
                    stop_loss = latest_price * 0.99
                    target_price = latest_price * 1.015

                # Key Metrics Dashboard
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Current Price (LTP)", f"₹{latest_price:.2f}")
                m2.metric("Intraday Signal", signal)
                m3.metric("Target Price", f"₹{target_price:.2f}")
                m4.metric("Stop Loss (SL)", f"₹{stop_loss:.2f}")
                m5.metric("RSI (14)", f"{latest_rsi:.2f}")

                st.markdown("---")

                # Technical Summary
                c1, c2, c3 = st.columns(3)
                c1.info(f"**20 EMA (Short Trend):** ₹{latest_ema20:.2f}")
                c2.info(f"**50 EMA (Baseline):** ₹{latest_ema50:.2f}")
                c3.info(f"**ATR Volatility:** ₹{latest_atr:.2f}")

                # --- INTERACTIVE HANDS-ON PLOTLY CHART ---
                st.subheader(
                    f"📈 Interactive Hands-On Chart ({full_ticker} - {timeframe})"
                )

                rows = 2 if show_rsi else 1
                row_heights = [0.7, 0.3] if show_rsi else [1.0]

                fig = make_subplots(
                    rows=rows,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                    row_heights=row_heights,
                    subplot_titles=(
                        (f"{full_ticker} Price Action", "RSI (14) Indicator")
                        if show_rsi
                        else (f"{full_ticker} Price Action",)
                    ),
                )

                # Price Traces
                if show_candlestick:
                    fig.add_trace(
                        go.Candlestick(
                            x=close.index,
                            open=open_p,
                            high=high,
                            low=low,
                            close=close,
                            name="OHLC Price",
                        ),
                        row=1,
                        col=1,
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=close.index,
                            y=close,
                            mode="lines",
                            name="Close Price",
                            line=dict(color="#1f77b4", width=2),
                        ),
                        row=1,
                        col=1,
                    )

                # Moving Averages
                if show_ema20:
                    fig.add_trace(
                        go.Scatter(
                            x=close.index,
                            y=ema_20,
                            mode="lines",
                            name="20 EMA",
                            line=dict(color="#ff7f0e", width=1.5),
                        ),
                        row=1,
                        col=1,
                    )

                if show_ema50:
                    fig.add_trace(
                        go.Scatter(
                            x=close.index,
                            y=ema_50,
                            mode="lines",
                            name="50 EMA",
                            line=dict(color="#2ca02c", width=1.5),
                        ),
                        row=1,
                        col=1,
                    )

                # RSI Panel
                if show_rsi:
                    fig.add_trace(
                        go.Scatter(
                            x=close.index,
                            y=rsi,
                            mode="lines",
                            name="RSI (14)",
                            line=dict(color="#9467bd", width=1.5),
                        ),
                        row=2,
                        col=1,
                    )
                    fig.add_hline(
                        y=70,
                        line_dash="dash",
                        line_color="red",
                        row=2,
                        col=1,
                        annotation_text="Overbought (70)",
                    )
                    fig.add_hline(
                        y=30,
                        line_dash="dash",
                        line_color="green",
                        row=2,
                        col=1,
                        annotation_text="Oversold (30)",
                    )

                # Layout formatting
                fig.update_layout(
                    height=600,
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                    hovermode="x unified",
                    margin=dict(l=20, r=20, t=40, b=20),
                )

                # Auto-fit Y-axis to actual price bounds
                fig.update_yaxes(autorange=True, fixedrange=False, row=1, col=1)

                st.plotly_chart(fig, use_container_width=True)

                # Candle Table
                st.subheader("📋 Recent Candle Data")
                recent_df = pd.DataFrame(
                    {
                        "Close Price": close,
                        "RSI (14)": rsi,
                        "20 EMA": ema_20,
                        "50 EMA": ema_50,
                    }
                ).tail(15)
                st.dataframe(recent_df, use_container_width=True)
