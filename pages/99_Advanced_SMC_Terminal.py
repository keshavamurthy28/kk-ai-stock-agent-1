from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Advanced SMC & Intraday Trading Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.cache_data.clear()

# Custom Styling
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("⚡ Advanced SMC & Intraday Trading Terminal (Full Analytics)")

# Complete Stock Universe
STOCKS_UNIVERSE = {
    "HEG - HEG Ltd": "HEG.NS",
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
    "TATAPOWER - Tata Power Co Ltd": "TATAPOWER.NS",
    "ZOMATO - Zomato Ltd": "ZOMATO.NS",
    "SUZLON - Suzlon Energy Ltd": "SUZLON.NS",
    "IRCTC - IRCTC Ltd": "IRCTC.NS",
    "SUNPHARMA - Sun Pharmaceutical Industries": "SUNPHARMA.NS",
    "TITAN - Titan Company Ltd": "TITAN.NS",
    "NTPC - NTPC Ltd": "NTPC.NS",
    "ONGC - Oil & Natural Gas Corporation": "ONGC.NS",
    "TATASTEEL - Tata Steel Ltd": "TATASTEEL.NS",
    "WIPRO - Wipro Ltd": "WIPRO.NS",
    "NIFTY 50 - Index": "^NSEI",
    "BANK NIFTY - Index": "^NSEBANK",
}

# Sidebar Controls
st.sidebar.header("🛠️ Terminal Controls")

selected_name = st.sidebar.selectbox(
    "Search & Select Stock", list(STOCKS_UNIVERSE.keys()), index=0
)
ticker_symbol = STOCKS_UNIVERSE[selected_name]

custom_ticker = st.sidebar.text_input("Or Enter Custom Ticker (e.g. IOC.NS)")
if custom_ticker:
  ticker_symbol = custom_ticker.strip().upper()
  if (
      not ticker_symbol.endswith(".NS")
      and not ticker_symbol.endswith(".BO")
      and not ticker_symbol.startswith("^")
  ):
    ticker_symbol += ".NS"

timeframe = st.sidebar.selectbox(
    "Select Timeframe / Interval", ["1m", "5m", "15m", "1h", "1d"], index=2
)

period_map = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "730d",
    "1d": "max",
}
period = period_map.get(timeframe, "60d")


@st.cache_data(ttl=30)
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


# --- TECHNICAL INDICATORS & SMC ENGINE ---
def compute_analytics(df):
  df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
  df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

  df["Vol_SMA20"] = df["Volume"].rolling(window=20).mean()
  df["Volume_Surge"] = df["Volume"] > (1.5 * df["Vol_SMA20"])

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

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

  df["Bull_FVG_Low"] = np.nan
  df["Bull_FVG_High"] = np.nan
  df["Bear_FVG_Low"] = np.nan
  df["Bear_FVG_High"] = np.nan

  for i in range(1, len(df) - 1):
    if df["Low"].iloc[i + 1] > df["High"].iloc[i - 1]:
      df.iloc[i, df.columns.get_loc("Bull_FVG_Low")] = df["High"].iloc[i - 1]
      df.iloc[i, df.columns.get_loc("Bull_FVG_High")] = df["Low"].iloc[i + 1]
    elif df["High"].iloc[i + 1] < df["Low"].iloc[i - 1]:
      df.iloc[i, df.columns.get_loc("Bear_FVG_Low")] = df["High"].iloc[i + 1]
      df.iloc[i, df.columns.get_loc("Bear_FVG_High")] = df["Low"].iloc[i - 1]

  return df


df = compute_analytics(data)

# Metrics bar
latest_close = float(df["Close"].iloc[-1])
prev_close = float(df["Close"].iloc[-2])
pct_change = ((latest_close - prev_close) / prev_close) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Active Asset", ticker_symbol, f"{pct_change:+.2f}%", delta_color="normal"
)
c2.metric("Latest Price", f"₹{latest_close:,.2f}")
c3.metric("Candles Loaded", f"{len(df):,}")
c4.metric("Volume Surge Alerts", int(df["Volume_Surge"].fillna(False).sum()))

# --- 3-TIER SUBPLOT CHART ---
fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.6, 0.2, 0.2],
)

# 1. Candlestick & EMAs
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

# FVG Zones
for idx, row in df.tail(150).iterrows():
  if not np.isnan(row["Bull_FVG_Low"]):
    fig.add_shape(
        type="rect",
        x0=idx,
        x1=df.index[-1],
        y0=row["Bull_FVG_Low"],
        y1=row["Bull_FVG_High"],
        fillcolor="rgba(0, 230, 118, 0.15)",
        line=dict(width=0),
        row=1,
        col=1,
    )
  if not np.isnan(row["Bear_FVG_Low"]):
    fig.add_shape(
        type="rect",
        x0=idx,
        x1=df.index[-1],
        y0=row["Bear_FVG_Low"],
        y1=row["Bear_FVG_High"],
        fillcolor="rgba(255, 23, 68, 0.15)",
        line=dict(width=0),
        row=1,
        col=1,
    )

# Signals
buys = df[df["Signal"] == 1]
sells = df[df["Signal"] == -1]
fig.add_trace(
    go.Scatter(
        x=buys.index,
        y=buys["Low"] * 0.995,
        mode="markers",
        marker=dict(symbol="triangle-up", size=13, color="#00E676"),
        name="BUY Signal",
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=sells.index,
        y=sells["High"] * 1.005,
        mode="markers",
        marker=dict(symbol="triangle-down", size=13, color="#FF1744"),
        name="SELL Signal",
    ),
    row=1,
    col=1,
)

# 2. Volume Subplot
vol_colors = [
    "#FFD700"
    if r["Volume_Surge"]
    else ("#00E676" if r["Close"] >= r["Open"] else "#FF1744")
    for _, r in df.iterrows()
]
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=vol_colors,
        name="Volume (Gold=Surge)",
    ),
    row=2,
    col=1,
)

# 3. RSI Subplot
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
fig.add_hline(y=70, line_dash="dash", line_color="#FF5252", row=3, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="#69F0AE", row=3, col=1)

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
