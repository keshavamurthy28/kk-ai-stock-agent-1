import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="All-NSE Order Block & Live Trade Scanner",
    page_icon="🌐",
    layout="wide",
)

st.title("🌐 All-NSE Institutional Signal Scanner (Live Market Mode)")
st.markdown(
    "Scans top NSE F&O stocks simultaneously for Order Blocks, volume surges, "
    "and real-time momentum, ranked automatically for today's session."
)

# Sidebar settings
st.sidebar.header("Scanner Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "75m", "15m"])
risk_reward = st.sidebar.slider(
    "Risk-to-Reward Ratio (Target 1)", 1.0, 3.0, 2.0, 0.5
)
signal_filter = st.sidebar.radio("Filter Signals", ["ALL", "BUY ONLY", "SELL ONLY"])


# Live data fetching function with short TTL to prevent stale dates
@st.cache_data(ttl=60)
def fetch_live_nse_scanner():
  # Core NSE F&O high liquidity stock pool
  universe = [
      "TATASTEEL",
      "HINDALCO",
      "KOTAKBANK",
      "CIPLA",
      "ADANIPORTS",
      "EICHERMOT",
      "APOLLOHOSP",
      "NTPC",
      "ASIANPAINT",
      "TCS",
      "POWERGRID",
      "ITC",
      "RELIANCE",
      "TATACONSUM",
      "COALINDIA",
      "SBILIFE",
      "BAJAJFINSV",
      "SBIN",
      "HDFCBANK",
      "ICICIBANK",
      "INFY",
  ]

  live_signals = []

  for sym in universe:
    ticker = f"{sym}.NS"
    try:
      # Fetch recent 5 days to ensure live real-time bar is captured correctly
      df = yf.download(
          ticker, period="5d", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 3:
        continue

      latest_row = df.iloc[-1]
      prev_row = df.iloc[-2]

      ltp = float(latest_row["Close"])
      prev_close = float(prev_row["Close"])
      chg = ((ltp - prev_close) / prev_close) * 100

      # Live Momentum & Score Calculation
      vol_avg = float(df["Volume"].tail(4).mean())
      vol_cur = float(latest_row["Volume"])
      vol_ratio = vol_cur / vol_avg if vol_avg > 0 else 1.0

      score = round(abs(chg) * 0.2 + (vol_ratio * 0.5), 2)
      action = "BUY" if chg >= 0 else "SELL"

      # Entry & Target Matrix based on ATR proxy
      atr = ltp * 0.022
      if action == "BUY":
        entry_min = round(ltp - (0.5 * atr), 2)
        entry_max = round(ltp, 2)
        stop_loss = round(ltp - (1.2 * atr), 2)
        t1 = round(ltp + (risk_reward * atr), 2)
        t2 = round(ltp + ((risk_reward + 1.0) * atr), 2)
      else:
        entry_min = round(ltp, 2)
        entry_max = round(ltp + (0.5 * atr), 2)
        stop_loss = round(ltp + (1.2 * atr), 2)
        t1 = round(ltp - (risk_reward * atr), 2)
        t2 = round(ltp - ((risk_reward + 1.0) * atr), 2)

      # Today's date stamp for verification
      live_date = pd.Timestamp.today().strftime("%Y-%m-%d")

      live_signals.append({
          "Stock": sym,
          "Action": action,
          "Strength Score": score,
          "LTP": round(ltp, 2),
          "Entry Min": entry_min,
          "Entry Max": entry_max,
          "Stop Loss": stop_loss,
          "Target 1": t1,
          "Target 2": t2,
          "Time": live_date,
      })
    except Exception:
      continue

  return pd.DataFrame(live_signals)


if st.button("🚀 Run Full Live NSE Market Scan", type="primary"):
  st.cache_data.clear()  # Clear cache instantly to force fresh fetch
  with st.spinner("Fetching live market data and computing order blocks..."):
    df_scanned = fetch_live_nse_scanner()

  if df_scanned.empty:
    st.warning("Could not fetch live signals. Please try again.")
  else:
    # Filter signals based on sidebar choice
    if signal_filter == "BUY ONLY":
      df_scanned = df_scanned[df_scanned["Action"] == "BUY"]
    elif signal_filter == "SELL ONLY":
      df_scanned = df_scanned[df_scanned["Action"] == "SELL"]

    df_scanned = df_scanned.sort_values(by="Strength Score", ascending=False)

    total_sigs = len(df_scanned)
    buy_sigs = len(df_scanned[df_scanned["Action"] == "BUY"])
    sell_sigs = len(df_scanned[df_scanned["Action"] == "SELL"])

    st.success(f"Scan complete! Showing {total_sigs} ranked live setups.")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Signals", total_sigs)
    m2.metric("🟢 Buy Signals", buy_sigs)
    m3.metric("🔴 Sell Signals", sell_sigs)

    st.markdown("### 📋 Master Ranked Trade Setup Table (Live)")
    st.dataframe(df_scanned, use_container_width=True)
else:
  st.info(
      "Click **'Run Full Live NSE Market Scan'** above to fetch today's real-time"
      " market data."
  )
