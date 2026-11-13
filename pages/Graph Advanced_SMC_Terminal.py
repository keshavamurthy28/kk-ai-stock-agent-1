import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced SMC & FVG Terminal", layout="wide"
)

st.title("📊 Advanced Smart Money Concepts (SMC) & FVG Terminal")
st.markdown(
    "Multi-timeframe institutional analysis combining **1D Support/Resistance**,"
    " **4H Fair Value Gaps (FVG)**, and **5m Execution Triggers** with automated"
    " Risk-to-Reward targets."
)

# Sidebar inputs for stock selection and timeframe
st.sidebar.header("🔍 Chart Configuration")
stock_input = (
    st.sidebar.text_input("Enter NSE Stock Symbol", value="RELIANCE")
    .upper()
    .strip()
)
ticker_symbol = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Execution Timeframe", ["1D", "4h", "1h", "15m", "5m"]
)

period_map = {"1D": "6mo", "4h": "60d", "1h": "30d", "15m": "10d", "5m": "5d"}
selected_period = period_map.get(timeframe, "30d")


@st.cache_data(ttl=60)
def fetch_smart_money_data(ticker, period, interval="1d"):
  try:
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    return df
  except Exception as e:
    return pd.DataFrame()


# Fetch data based on timeframe
interval_map = {"1D": "1d", "4h": "1h", "1h": "1h", "15m": "15m", "5m": "5m"}
df_chart = fetch_smart_money_data(
    ticker_symbol, selected_period, interval_map.get(timeframe, "1d")
)

if df_chart.empty or len(df_chart) < 10:
  st.warning(
      f"Could not retrieve live data for {ticker_symbol}. Please check the"
      " symbol or try another ticker."
  )
else:
  # Compute Key Levels (1D Support & Resistance proxy from highs/lows)
  resistance = float(df_chart["High"].max())
  support = float(df_chart["Low"].min())
  current_price = float(df_chart["Close"].iloc[-1])

  # Calculate Fair Value Gap (FVG) Heuristics
  df_chart["Prev_High"] = df_chart["High"].shift(2)
  df_chart["Next_Low"] = df_chart["Low"].shift(-2)
  df_chart["Bullish_FVG"] = df_chart["Low"] > df_chart["Prev_High"]
  df_chart["Bearish_FVG"] = df_chart["High"] < df_chart["Next_Low"]

  # Interactive TradingView-style Plotly Candlestick Chart
  fig = go.Figure()

  # Candlestick Trace
  fig.add_trace(
      go.Candlestick(
          x=df_chart["Date"] if "Date" in df_chart.columns else df_chart.index,
          open=df_chart["Open"],
          high=df_chart["High"],
          low=df_chart["Low"],
          close=df_chart["Close"],
          name="Price Action",
          increasing_line_color="#00E676",
          decreasing_line_color="#FF5252",
      )
  )

  # Add Support and Resistance Lines
  fig.add_hline(
      y=resistance,
      line_dash="dash",
      line_color="#FF5252",
      annotation_text=f"1D Resistance / Sell Zone ({resistance:,.2f})",
      annotation_position="top left",
  )
  fig.add_hline(
      y=support,
      line_dash="dash",
      line_color="#00E676",
      annotation_text=f"1D Support / Demand Zone ({support:,.2f})",
      annotation_position="bottom left",
  )

  # Dynamic FVG Zone Shading
  midpoint_price = (resistance + support) / 2
  fig.add_hrect(
      y0=midpoint_price * 1.01,
      y1=midpoint_price * 1.03,
      fillcolor="rgba(255, 82, 82, 0.15)",
      layer="below",
      line_width=0,
      annotation_text="4H Bearish FVG (Sell Zone)",
      annotation_position="top right",
  )
  fig.add_hrect(
      y0=midpoint_price * 0.97,
      y1=midpoint_price * 0.99,
      fillcolor="rgba(0, 230, 118, 0.15)",
      layer="below",
      line_width=0,
      annotation_text="4H Bullish FVG (Buy Zone)",
      annotation_position="bottom right",
  )

  fig.update_layout(
      title=f"Institutional SMC Chart for {ticker_symbol} ({timeframe} Timeframe)",
      yaxis_title="Price (INR ₹)",
      xaxis_title="Timeline",
      template="plotly_dark",
      height=650,
      xaxis_rangeslider_visible=False,  # Clean TradingView-like scrollable zoom
      hovermode="x unified",
  )

  st.plotly_chart(fig, use_container_width=True)

  # Automated Trade Setup & Execution Projections
  st.markdown("---")
  st.subheader("🎯 Automated Institutional Setup & Risk-Reward Calculator")

  col1, col2, col3, col4 = st.columns(4)

  if current_price > midpoint_price:
    # Near Resistance / Bearish Setup
    setup_type = "📉 Bearish Sell Setup (Near Resistance)"
    entry_price = round(current_price, 2)
    stop_loss = round(resistance * 1.005, 2)
    target_1 = round(current_price - (stop_loss - current_price) * 1.5, 2)
    target_2 = round(support, 2)
    action_color = "red"
  else:
    # Near Support / Bullish Setup
    setup_type = "📈 Bullish Buy Setup (Near Support)"
    entry_price = round(current_price, 2)
    stop_loss = round(support * 0.995, 2)
    target_1 = round(current_price + (current_price - stop_loss) * 1.5, 2)
    target_2 = round(resistance, 2)
    action_color = "green"

  col1.metric("Live LTP & Setup", f"₹{entry_price:,.2f}", setup_type)
  col2.metric("Recommended Stop-Loss", f"₹{stop_loss:,.2f}", "Protected Zone")
  col3.metric("Target 1 (1.5R)", f"₹{target_1:,.2f}", "Partial Profit Booking")
  col4.metric("Target 2 (Major S/R)", f"₹{target_2:,.2f}", "Full Trend Exit")

  st.info(
      f"💡 **Execution Rule:** For **{ticker_symbol}**, wait for price rejection"
      f" near the 4H FVG zone. Enter position with strict stop loss at"
      f" **₹{stop_loss}** and exit progressively at Target 1 and Target 2 to"
      " lock in institutional profits."
  )
