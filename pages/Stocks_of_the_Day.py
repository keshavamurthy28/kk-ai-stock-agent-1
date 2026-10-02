import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced Intraday & Institutional Terminal",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Pro Intraday Orderflow & Institutional Execution Terminal")
st.markdown(
    "Analyze momentum and orderflow using **VWAP**, **Buy/Sell Volume Delta**, **RVOL (Relative Volume)**, and comprehensive multi-timeframe support."
)

# -------------------------------------------------------------------
# 1. SIDEBAR TRADING CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Intraday Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., INFY, RELIANCE, TCS)", value="INFY"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

# Expanded timeframe selection (1m up to 1 Month)
timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    [
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "1h",
        "90m",
        "1d",
        "5d",
        "1wk",
        "1mo",
    ],
    index=3,
)

# Extended period mapping to safely accommodate higher timeframes
period_map = {
    "1m": "7d",
    "2m": "60d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "1h": "730d",
    "90m": "60d",
    "1d": "max",
    "5d": "max",
    "1wk": "max",
    "1mo": "max",
}
fetch_period = period_map.get(timeframe, "60d")

st.sidebar.markdown("---")
st.sidebar.header("📊 Chart Overlays")
show_candlestick = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_vwap = st.sidebar.checkbox("Show VWAP Benchmark", value=True)
show_ema20 = st.sidebar.checkbox("Show 20 EMA Line", value=True)
show_ema50 = st.sidebar.checkbox("Show 50 EMA Line", value=True)
show_orderflow = st.sidebar.checkbox(
    "Show Buy/Sell Orderflow Delta Subplot", value=True
)
show_rsi = st.sidebar.checkbox("Show RSI Subplot", value=True)

# -------------------------------------------------------------------
# 2. DATA FETCHER & TECHNICAL CALCULATOR
# -------------------------------------------------------------------


@st.cache_data(ttl=300)
def fetch_intraday_data(ticker, period, interval):
  df = yf.download(
      ticker, period=period, interval=interval, progress=False, auto_adjust=True
  )
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  return df


with st.spinner(
    f"Fetching tick data and computing orderflow for `{symbol_str}` on `{timeframe}`..."
):
  df = fetch_intraday_data(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 10:
  st.error(
      f"Could not retrieve data for `{symbol_str}` on interval `{timeframe}`. Please check the ticker symbol or try a different timeframe."
  )
else:
  # Technical Calculations
  df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

  # VWAP Calculation (Session Approximate)
  q = df["Volume"]
  p = (df["High"] + df["Low"] + df["Close"]) / 3
  df["VWAP"] = (p * q).cumsum() / q.cumsum()

  # RSI Calculation
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

  # -------------------------------------------------------------------
  # Exact Candle Buy vs Sell Volume Estimation (Close Location Value)
  # -------------------------------------------------------------------
  high = df["High"]
  low = df["Low"]
  close = df["Close"]
  volume = df["Volume"]

  range_hl = high - low
  range_hl = range_hl.replace(0, 0.001)  # Avoid division by zero

  # Buying pressure ratio based on where the close is relative to high/low
  buy_ratio = (close - low) / range_hl
  df["Buy_Volume"] = volume * buy_ratio
  df["Sell_Volume"] = volume * (1 - buy_ratio)
  df["Delta"] = df["Buy_Volume"] - df["Sell_Volume"]

  # Relative Volume (RVOL)
  df["Avg_Volume_20"] = df["Volume"].rolling(window=20).mean()
  df["RVOL"] = df["Volume"] / df["Avg_Volume_20"]

  # Latest Metrics
  latest = df.iloc[-1]
  prev = df.iloc[-2]
  price_change = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100

  # -------------------------------------------------------------------
  # 3. EXECUTIVE INTRA-DAY METRICS BAR
  # -------------------------------------------------------------------
  col1, col2, col3, col4, col5 = st.columns(5)
  col1.metric(
      "Last Traded Price", f"₹{latest['Close']:.2f}", f"{price_change:+.2f}%"
  )
  col2.metric("Relative Volume (RVOL)", f"{latest['RVOL']:.2f}x")
  col3.metric(
      "VWAP Benchmark",
      f"₹{latest['VWAP']:.2f}",
      "Bullish" if latest["Close"] > latest["VWAP"] else "Bearish",
  )
  col4.metric("RSI (14)", f"{latest['RSI']:.1f}")
  col5.metric(
      "Candle Net Delta",
      f"{int(latest['Delta']):,}",
      "Net Buying" if latest["Delta"] > 0 else "Net Selling",
  )

  # -------------------------------------------------------------------
  # 4. ADVANCED PLOTLY SUBPLOT CHART GENERATION
  # -------------------------------------------------------------------
  row_count = 1
  row_heights = [0.6]
  subplot_titles = [f"{symbol_str} Price Action ({timeframe})"]

  if show_orderflow:
    row_count += 1
    row_heights.append(0.2)
    subplot_titles.append(
        "Buy vs Sell Volume Delta (Green = Buyers, Red = Sellers)"
    )

  if show_rsi:
    row_count += 1
    row_heights.append(0.2)
    subplot_titles.append("RSI (14) Momentum")

  fig = make_subplots(
      rows=row_count,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=row_heights,
      subplot_titles=subplot_titles,
  )

  # Main Price Chart Row
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
  else:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(color="#1f77b4", width=2),
        ),
        row=1,
        col=1,
    )

  if show_vwap:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["VWAP"],
            mode="lines",
            name="VWAP",
            line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        ),
        row=1,
        col=1,
    )

  if show_ema20:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["EMA_20"],
            mode="lines",
            name="20 EMA",
            line=dict(color="#2ca02c", width=1),
        ),
        row=1,
        col=1,
    )

  if show_ema50:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["EMA_50"],
            mode="lines",
            name="50 EMA",
            line=dict(color="#d62728", width=1),
        ),
        row=1,
        col=1,
    )

  current_row = 2

  # Orderflow Subplot (Buy/Sell breakdown bars)
  if show_orderflow:
    colors = ["#00E676" if val >= 0 else "#FF1744" for val in df["Delta"]]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Delta"],
            marker_color=colors,
            name="Net Delta",
            customdata=np.stack(
                (df["Buy_Volume"], df["Sell_Volume"]), axis=-1
            ),
            hovertemplate=(
                "Time: %{x}<br>Net Delta: %{y:,.0f}<br>Est. Buy Vol:"
                " %{customdata[0]:,.0f}<br>Est. Sell Vol:"
                " %{customdata[1]:,.0f}<extra></extra>"
            ),
        ),
        row=current_row,
        col=1,
    )
    current_row += 1

  # RSI Subplot
  if show_rsi:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI"],
            mode="lines",
            name="RSI",
            line=dict(color="#9467bd", width=1.5),
        ),
        row=current_row,
        col=1,
    )
    fig.add_hline(
        y=70, line_dash="dash", line_color="red", row=current_row, col=1
    )
    fig.add_hline(
        y=30, line_dash="dash", line_color="green", row=current_row, col=1
    )

  fig.update_layout(
      template="plotly_white",
      xaxis_rangeslider_visible=False,
      height=750,
      margin=dict(l=20, r=20, t=40, b=20),
      legend=dict(
          orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
      ),
  )

  st.plotly_chart(fig, use_container_width=True)

  # -----------------
  # 5. INTRA-DAY TRADE SETUP AI ADVISOR
  # -----------------
  st.markdown("### 🤖 Institutional Action Summary")
  if latest["Close"] > latest["VWAP"] and latest["RVOL"] > 1.3:
    st.success(
        f"**Bullish Institutional Accumulation Detected:** `{symbol_str}` is trading above its VWAP benchmark with high relative volume (`{latest['RVOL']:.2f}x`). Look for intraday pullbacks to the 20 EMA for long setups."
    )
  elif latest["Close"] < latest["VWAP"] and latest["RVOL"] > 1.3:
    st.error(
        f"**Bearish Institutional Distribution Detected:** `{symbol_str}` is trading below its VWAP benchmark with a heavy volume surge. Watch for breakdown continuation."
    )
  else:
    st.info(
        f"**Neutral / Consolidating Action:** `{symbol_str}` is currently moving within average volume parameters on the `{timeframe}` timeframe. Wait for a breakout or volume expansion."
    )
