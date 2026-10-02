import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import ta
import yfinance as yf
from google import genai

# Page Configuration
st.set_page_config(
    page_title="AI Stock Agent", page_icon="📈", layout="wide"
)

st.title("📈 AI Stock Analysis & Intraday Signals")

# Hardcoded API key from your setup (or enter in sidebar)
DEFAULT_API_KEY = (
    "AQ.Ab8RN6KQhnH16r3F8pm9E9yU5UzcLo1iQHi1xI5HhNge-sJptw"
)

# Sidebar Inputs
st.sidebar.header("Trading Controls")
api_key = st.sidebar.text_input(
    "Gemini API Key", value=DEFAULT_API_KEY, type="password"
)
symbol = st.sidebar.text_input(
    "Stock Ticker (e.g., INFY, RELIANCE, TCS)", "INFY"
)
timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["15m (Intraday)", "5m (Intraday)", "1d (Daily)"]
)

run_btn = st.sidebar.button("Run Technical Analysis")


def fetch_data_and_analyze(ticker_symbol, tf_option):
  # Set correct interval
  interval = "15m" if "15m" in tf_option else ("5m" if "5m" in tf_option else "1d")
  period = "5d" if interval in ["5m", "15m"] else "6mo"

  yf_ticker = (
      f"{ticker_symbol.upper()}.NS"
      if not ticker_symbol.endswith(".NS")
      else ticker_symbol
  )

  df = yf.Ticker(yf_ticker).history(period=period, interval=interval)
  if df.empty:
    st.error("Invalid ticker or no data returned.")
    return None, None

  # Indicators
  df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
  df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
  df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
  df["ATR"] = ta.volatility.average_true_range(
      df["High"], df["Low"], df["Close"], window=14
  )

  latest = df.iloc[-1]
  cmp = round(latest["Close"], 2)
  atr = round(latest["ATR"], 2)

  # Intraday Signals
  is_bullish = latest["EMA_9"] > latest["EMA_21"] and latest["RSI"] > 50
  signal = "BUY" if is_bullish else "SELL"
  entry = cmp
  stop_loss = (
      round(cmp - (1.5 * atr), 2) if is_bullish else round(cmp + (1.5 * atr), 2)
  )
  target_1 = (
      round(cmp + (1.5 * atr), 2) if is_bullish else round(cmp - (1.5 * atr), 2)
  )
  target_2 = (
      round(cmp + (3.0 * atr), 2) if is_bullish else round(cmp - (3.0 * atr), 2)
  )

  metrics = {
      "Symbol": ticker_symbol.upper(),
      "Timeframe": interval,
      "Signal": signal,
      "CMP": cmp,
      "Entry": entry,
      "Stop Loss": stop_loss,
      "Target 1": target_1,
      "Target 2": target_2,
      "RSI": round(latest["RSI"], 2),
  }

  # Plot Chart
  df_plot = df.tail(50)
  fig, (ax1, ax2) = plt.subplots(
      2,
      1,
      figsize=(10, 6),
      sharex=True,
      gridspec_kw={"height_ratios": [3, 1]},
  )

  ax1.plot(
      df_plot.index,
      df_plot["Close"],
      label="Price",
      color="black",
      linewidth=1.5,
  )
  ax1.plot(
      df_plot.index,
      df_plot["EMA_9"],
      label="9 EMA",
      color="blue",
      linestyle="--",
  )
  ax1.plot(
      df_plot.index,
      df_plot["EMA_21"],
      label="21 EMA",
      color="orange",
      linestyle="--",
  )

  # Level Lines
  ax1.axhline(
      y=entry,
      color="green" if is_bullish else "red",
      linewidth=2,
      label=f"ENTRY ({signal}): ₹{entry}",
  )
  ax1.axhline(
      y=stop_loss, color="crimson", linestyle="--", label=f"STOP LOSS: ₹{stop_loss}"
  )
  ax1.axhline(
      y=target_1, color="royalblue", linestyle=":", label=f"TARGET 1: ₹{target_1}"
  )
  ax1.axhline(
      y=target_2, color="darkblue", linestyle=":", label=f"TARGET 2: ₹{target_2}"
  )

  ax1.set_title(
      f"{ticker_symbol.upper()} ({interval}) - Trading Levels Chart",
      fontweight="bold",
  )
  ax1.legend(loc="upper left")
  ax1.grid(True, alpha=0.3)

  ax2.plot(df_plot.index, df_plot["RSI"], label="RSI (14)", color="purple")
  ax2.axhline(70, color="red", linestyle=":")
  ax2.axhline(30, color="green", linestyle=":")
  ax2.set_ylim(0, 100)
  ax2.grid(True, alpha=0.3)

  if interval in ["5m", "15m"]:
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M\n%d-%b"))

  plt.tight_layout()
  return metrics, fig


if run_btn:
  metrics, fig = fetch_data_and_analyze(symbol, timeframe)

  if metrics:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signal", metrics["Signal"])
    col2.metric("Entry Price", f"₹{metrics['Entry']}")
    col3.metric("Stop Loss", f"₹{metrics['Stop Loss']}")
    col4.metric("Target 1", f"₹{metrics['Target 1']}")

    st.pyplot(fig)

    st.subheader("🤖 AI Analysis")
    with st.spinner("Generating AI Analysis Report..."):
      client = genai.Client(api_key=api_key)
      prompt = f"""
            You are an expert Stock Technical Analyst. Analyze {metrics['Symbol']} on {metrics['Timeframe']} timeframe:
            - Signal: {metrics['Signal']}
            - Current Price / Entry: ₹{metrics['CMP']}
            - Stop Loss: ₹{metrics['Stop Loss']}
            - Target 1: ₹{metrics['Target 1']}
            - Target 2: ₹{metrics['Target 2']}
            - RSI: {metrics['RSI']}

            Provide a clear summary with Trend Alignment, Risk Management advice, and execution strategy.
            """
      response = client.models.generate_content(
          model="gemini-3.8-flash", contents=prompt
      )
      st.markdown(response.text)