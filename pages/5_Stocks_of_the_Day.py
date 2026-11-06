from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# Page Configuration
try:
  st.set_page_config(
      page_title="Institutional Trading Terminal - SMC & Advanced Analytics",
      layout="wide",
      initial_sidebar_state="expanded",
  )
except:
  pass

# Clear cache to prevent old versions from persisting on Streamlit Cloud
st.cache_data.clear()

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

st.title(
    "⚡ Institutional Terminal: SMC, FVG, Volume Surge & Intraday Engine"
)

# Sidebar Controls
st.sidebar.header("🛠️ Terminal Controls")

# Universal Free-Text Stock Symbol Input (Type ANY stock: HEG, TATAPOWER, ZOMATO, etc.)
ticker_input = st.sidebar.text_input(
    "🔍 Type Any Stock Symbol (Press Enter)", value="HEG"
)

# Clean and format ticker for Yahoo Finance (NSE/BSE handling)
ticker_symbol = ticker_input.strip().upper()
if (
    not ticker_symbol.endswith(".NS")
    and not ticker_symbol.endswith(".BO")
    and not ticker_symbol.startswith("^")
):
  ticker_symbol += ".NS"

# Timeframe Controls
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
      f"No market data found for '{ticker_symbol}'. Please verify the symbol"
      " (e.g., HEG or HEG.NS) or market hours."
  )
  st.stop()


# --- TECHNICAL INDICATORS & SMC CALCULATIONS ---
def compute_analytics(df):
  # Moving Averages
  df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
  df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
  df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

  # Volume Surge (1.5x of 20-period volume average)
  df["Vol_SMA20"] = df["Volume"].rolling(window=20).mean()
  df["Volume_Surge"] = df["Volume"] > (1.5 * df["Vol_SMA20"])

  # RSI (14)
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

  # Algorithmic Buy / Sell Crossover Signals
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

  # Smart Money Concepts: Fair Value Gaps (FVG)
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

  # SMC Accumulation / Distribution Phase Detection
  df["Price_Range"] = df["High"] - df["Low"]
  df["Avg_Range"] = df["Price_Range"].rolling(window=20).mean()
  df["Phase"] = "Normal"
  df.loc[
      (df["Price_Range"] < 0.7 * df["Avg_Range"])
      & (df["Volume"] > df["Vol_SMA20"]),
      "Phase",
  ] = "Accumulation"
  df.loc[
      (df["Price_Range"] > 1.4 * df["Avg_Range"])
      & (df["Close"] < df["Open"])
      & (df["Volume"] > df["Vol_SMA20"]),
      "Phase",
  ] = "Distribution"

  return df


df = compute_analytics(data)

# Dashboard Metrics Bar
latest_close = float(df["Close"].iloc[-1])
prev_close = float(df["Close"].iloc[-2])
price_change = latest_close - prev_close
pct_change = (price_change / prev_close) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Active Ticker",
    ticker_symbol,
    f"{pct_change:+.2f}%",
    delta_color="normal",
)
col2.metric("Latest Price", f"₹{latest_close:,.2f}")
col3.metric("Total Bars Loaded", f"{len(df):,}")
col4.metric(
    "Volume Surge Events", int(df["Volume_Surge"].fillna(False).sum())
)

# --- 3-TIER ADVANCED SUBPLOTTED TRADING VIEW CHART ---
fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.6, 0.2, 0.2],
)

# 1. Candlestick Chart (Row 1)
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price Action",
    ),
    row=1,
    col=1,
)

# EMAs Overlays
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

# Fair Value Gaps (FVG Zones)
recent_df = df.tail(150)
for idx, row in recent_df.iterrows():
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

# Buy / Sell Execution Markers
buy_signals = df[df["Signal"] == 1]
sell_signals = df[df["Signal"] == -1]

fig.add_trace(
    go.Scatter(
        x=buy_signals.index,
        y=buy_signals["Low"] * 0.995,
        mode="markers",
        marker=dict(symbol="triangle-up", size=14, color="#00E676"),
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
        marker=dict(symbol="triangle-down", size=14, color="#FF1744"),
        name="SELL Signal",
    ),
    row=1,
    col=1,
)

# 2. Volume Subplot with Surge Highlighting (Row 2)
vol_colors = [
    "#FFD700"
    if row["Volume_Surge"]
    else ("#00E676" if row["Close"] >= row["Open"] else "#FF1744")
    for _, row in df.iterrows()
]
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=vol_colors,
        name="Volume (Gold = Surge)",
        opacity=0.85,
    ),
    row=2,
    col=1,
)

# 3. RSI Subplot (Row 3)
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

# Data Table & SMC Inspect View
if st.checkbox("🔍 Inspect Raw Data, SMC Phases & Signals"):
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
              "Phase",
              "Signal",
          ]
      ].tail(100),
      use_container_width=True,
  )
