from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Trading Terminal - SMC & Advanced Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Speed & Readability
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("⚡ Institutional Terminal: SMC, FVG & Intraday Engine")

# Expanded Stock Universe (Nifty 50 & High Liquidity Equities)
DEFAULT_STOCKS = {
    "RELIANCE - Reliance Industries Ltd": "RELIANCE.NS",
    "TCS - Tata Consultancy Services Ltd": "TCS.NS",
    "HDFCBANK - HDFC Bank Ltd": "HDFCBANK.NS",
    "INFY - Infosys Ltd": "INFY.NS",
    "ICICIBANK - ICICI Bank Ltd": "ICICIBANK.NS",
    "SBIN - State Bank of India": "SBIN.NS",
    "BHARTIARTL - Bharti Airtel Ltd": "BHARTIARTL.NS",
    "ITC - ITC Ltd": "ITC.NS",
    "KOTAKBANK - Kotak Mahindra Bank Ltd": "KOTAKBANK.NS",
    "LT - Larsen & Toubro Ltd": "LT.NS",
    "AXISBANK - Axis Bank Ltd": "AXISBANK.NS",
    "HINDUNILVR - Hindustan Unilever Ltd": "HINDUNILVR.NS",
    "BAJFINANCE - Bajaj Finance Ltd": "BAJFINANCE.NS",
    "MARUTI - Maruti Suzuki India Ltd": "MARUTI.NS",
    "TATAMOTORS - Tata Motors Ltd": "TATAMOTORS.NS",
    "SUNPHARMA - Sun Pharmaceutical Industries": "SUNPHARMA.NS",
    "TITAN - Titan Company Ltd": "TITAN.NS",
    "NTPC - NTPC Ltd": "NTPC.NS",
    "ONGC - Oil & Natural Gas Corporation": "ONGC.NS",
    "TATASTEEL - Tata Steel Ltd": "TATASTEEL.NS",
}

# Sidebar Controls
st.sidebar.header("🛠️ Terminal Controls")

selected_name = st.sidebar.selectbox(
    "Search & Select Stock", list(DEFAULT_STOCKS.keys())
)
ticker_symbol = DEFAULT_STOCKS[selected_name]

# Allow custom ticker entry if needed
custom_ticker = st.sidebar.text_input(
    "Or Enter Yahoo Ticker (e.g., ^NSEI, TATAPOWER.NS)"
)
if custom_ticker:
    ticker_symbol = custom_ticker.strip().upper()

timeframe = st.sidebar.selectbox(
    "Select Timeframe / Interval", ["1m", "5m", "15m", "1h", "1d"], index=2
)

# Adjust lookback period based on timeframe validity
period_map = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "730d",
    "1d": "max",
}
period = period_map.get(timeframe, "60d")


@st.cache_data(ttl=300)
def load_data(symbol, period, interval):
  df = yf.download(symbol, period=period, interval=interval, progress=False)
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  df.dropna(inplace=True)
  return df


data = load_data(ticker_symbol, period, timeframe)

if data.empty:
  st.error(
      f"No market data found for {ticker_symbol}. Check symbol or market hours."
  )
  st.stop()


# --- TECHNICAL INDICATORS & SMC CALCULATIONS ---
def compute_analytics(df):
  # Moving Averages
  df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
  df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

  # Volume Surge (2x of 20-period volume average)
  df["Vol_SMA20"] = df["Volume"].rolling(window=20).mean()
  df["Volume_Surge"] = df["Volume"] > (1.5 * df["Vol_SMA20"])

  # RSI
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

  # MACD
  exp1 = df["Close"].ewm(span=12, adjust=False).mean()
  exp2 = df["Close"].ewm(span=26, adjust=False).mean()
  df["MACD"] = exp1 - exp2
  df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

  # Buy / Sell Signals (EMA Crossover + Volume confirmation)
  df["Signal"] = 0
  df.loc[
      (df["EMA_9"] > df["EMA_21"])
      & (df["EMA_9"].shift(1) <= df["EMA_21"].shift(1))
      & (df["Volume_Surge"]),
      "Signal",
  ] = 1
  df.loc[
      (df["EMA_9"] < df["EMA_21"])
      & (df["EMA_9"].shift(1) >= df["EMA_21"].shift(1))
      & (df["Volume_Surge"]),
      "Signal",
  ] = -1

  # Fair Value Gap (FVG) Detection Logic
  # Bullish FVG: Low of candle [i+1] > High of candle [i-1]
  df["Bull_FVG"] = np.nan
  df["Bear_FVG"] = np.nan
  for i in range(1, len(df) - 1):
    if df["Low"].iloc[i + 1] > df["High"].iloc[i - 1]:
      df.loc[df.index[i], "Bull_FVG"] = (
          df["Low"].iloc[i + 1] + df["High"].iloc[i - 1]
      ) / 2
    elif df["High"].iloc[i + 1] < df["Low"].iloc[i - 1]:
      df.loc[df.index[i], "Bear_FVG"] = (
          df["High"].iloc[i + 1] + df["Low"].iloc[i - 1]
      ) / 2

  return df


df = compute_analytics(data)

# Dashboard Metrics Bar
latest_close = float(df["Close"].iloc[-1])
prev_close = float(df["Close"].iloc[-2])
price_change = latest_close - prev_close
pct_change = (price_change / prev_close) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Latest Price",
    f"₹{latest_close:,.2f}",
    f"{pct_change:+.2f}%",
    delta_color="normal",
)
col2.metric("Total Bars Loaded", f"{len(df):,}")
col3.metric("Data Range", f"{df.index[0].date()} to {df.index[-1].date()}")
col4.metric(
    "Volume Surge Events", int(df["Volume_Surge"].fillna(False).sum())
)

# --- ADVANCED PLOTLY CHART ---
fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.6, 0.2, 0.2],
)

# 1. Candlestick & Overlays
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
    ),
    row=1,
    col=1,
)

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["EMA_9"],
        line=dict(color="#2962FF", width=1),
        name="EMA 9",
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["EMA_21"],
        line=dict(color="#FF6D00", width=1),
        name="EMA 21",
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["EMA_50"],
        line=dict(color="#9C27B0", width=1.5),
        name="EMA 50",
    ),
    row=1,
    col=1,
)

# Buy / Sell Execution Markers
buy_signals = df[df["Signal"] == 1]
sell_signals = df[df["Signal"] == -1]

fig.add_trace(
    go.Scatter(
        x=buy_signals.index,
        y=buy_signals["Low"] * 0.995,
        mode="markers",
        marker=dict(symbol="triangle-up", size=12, color="#00E676"),
        name="BUY Signal",
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=sell_signals.index,
        y=sell_signals["High"] * 1.005,
        mode="markers",
        marker=dict(symbol="triangle-down", size=12, color="#FF1744"),
        name="SELL Signal",
    ),
    row=1,
    col=1,
)

# 2. Volume & Volume Surge Colors
colors = [
    "#00E676" if row["Close"] >= row["Open"] else "#FF1744"
    for index, row in df.iterrows()
]
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=colors,
        name="Volume",
        opacity=0.8,
    ),
    row=2,
    col=1,
)

# 3. RSI Indicator
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["RSI"],
        line=dict(color="#26A69A", width=1.5),
        name="RSI (14)",
    ),
    row=3,
    col=1,
)
fig.add_hline(
    y=70, line_dash="dash", line_color="#FF5252", row=3, col=1
)  # Overbought
fig.add_hline(
    y=30, line_dash="dash", line_color="#69F0AE", row=3, col=1
)  # Oversold

# Layout Configuration
fig.update_layout(
    template="plotly_dark",
    height=850,
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
    ),
)

st.plotly_chart(fig, use_container_width=True)

# Data Table view expansion
if st.checkbox("🔍 Inspect Raw OHLCV Data & SMC Signals"):
  st.dataframe(
      df[
          [
              "Open",
              "High",
              "Low",
              "Close",
              "Volume",
              "RSI",
              "Volume_Surge",
              "Signal",
          ]
      ].tail(100),
      use_container_width=True,
  )
