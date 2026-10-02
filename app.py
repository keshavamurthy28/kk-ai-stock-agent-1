import pandas as pd
import streamlit as st
import yfinance as yf

# Page setup
st.set_page_config(
    page_title="AI Stock Analysis & Intraday Signals",
    page_icon="📈",
    layout="wide",
)

st.title("📈 AI Stock Analysis & Intraday Signals")
st.markdown(
    "Analyze technical indicators and trend signals for individual stocks."
)

# Sidebar inputs
st.sidebar.header("Trading Controls")
ticker_symbol = st.sidebar.text_input(
    "Stock Ticker (e.g., INFY, RELIANCE, TCS)", value="INFY"
)
timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    ["15m (Intraday)", "1d (Daily)", "1h (Hourly)"],
    index=0,
)
run_btn = st.sidebar.button("Run Technical Analysis")


def calculate_ema(series, span=50):
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_stock_data(symbol, timeframe_choice):
    ticker = (
        f"{symbol.upper()}.NS" if not symbol.endswith(".NS") else symbol.upper()
    )

    interval_map = {
        "15m (Intraday)": ("15m", "5d"),
        "1h (Hourly)": ("1h", "1mo"),
        "1d (Daily)": ("1d", "6mo"),
    }
    interval, period = interval_map.get(timeframe_choice, ("15m", "5d"))

    df = yf.download(ticker, period=period, interval=interval, progress=False)
    return df, ticker


if run_btn or ticker_symbol:
    if ticker_symbol:
        with st.spinner(f"Fetching data for {ticker_symbol}..."):
            df, full_ticker = get_stock_data(ticker_symbol, timeframe)

            if df.empty:
                st.error(
                    f"Could not fetch data for '{ticker_symbol}'. Please check the symbol name."
                )
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    close = df["Close"][full_ticker]
                else:
                    close = df["Close"]

                # Calculate Technical Indicators directly
                rsi = calculate_rsi(close, 14)
                ema_50 = calculate_ema(close, 50)

                latest_price = float(close.iloc[-1])
                latest_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
                latest_ema50 = float(ema_50.iloc[-1]) if not ema_50.empty else 0.0

                # Recommendation Engine
                if latest_price > latest_ema50 and 45 < latest_rsi < 65:
                    signal = "STRONG BUY / ADD"
                elif latest_price < latest_ema50 or latest_rsi > 70:
                    signal = "SELL / TRIM"
                else:
                    signal = "HOLD / NEUTRAL"

                # Metrics display
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price (LTP)", f"₹{latest_price:.2f}")
                col2.metric("RSI (14)", f"{latest_rsi:.2f}")
                col3.metric("50 EMA", f"₹{latest_ema50:.2f}")
                col4.metric("Trend Signal", signal)

                st.markdown("---")
                st.subheader(f"Price Chart ({full_ticker})")

                # Display Price Chart
                st.line_chart(close)

                # Historical Table
                st.subheader("Recent Data & Technicals")
                chart_df = pd.DataFrame(
                    {
                        "Close Price": close,
                        "RSI (14)": rsi,
                        "50 EMA": ema_50,
                    }
                ).tail(20)
                st.dataframe(chart_df, use_container_width=True)
