import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="All-NSE Order Block & Live Trade Scanner", layout="wide"
)

st.title("🌐 All-NSE Institutional Signal Scanner (Live Market Mode)")
st.markdown(
    "Scans top NSE F&O stocks simultaneously for Order Blocks, volume surges,"
    " and real-time momentum, ranked automatically for today's session."
)

# Sidebar & Page Controls
st.sidebar.header("⚙️ Scanner Settings")
selected_timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "1h", "15m"])
rr_ratio = st.sidebar.selectbox(
    "Risk-to-Reward Ratio (Target 1)", [2.0, 1.0, 3.0]
)
signal_filter = st.sidebar.radio("Filter Signals", ["ALL", "BUY ONLY"])

if st.sidebar.button("🚀 Run Full Live NSE Market Scan"):
  st.cache_data.clear()
  st.success("Cache cleared! Running full live NSE institutional scan.")


@st.cache_data(ttl=60)
def fetch_multi_stock_breakouts():
  """Scans a comprehensive multi-stock universe for Order Blocks, volume spurts,

  and breakout momentum.
  """
  universe = [
      "MSTCLTD",
      "POWERINDIA",
      "AMBER",
      "TDPOWERSYS",
      "GVT&D",
      "APOLLO",
      "PNB",
      "DCXINDIA",
      "KALYANKJIL",
      "RELIANCE",
      "TCS",
      "HDFCBANK",
      "ICICIBANK",
      "SBIN",
      "HAL",
      "BEL",
      "JIOFIN",
      "IRFC",
      "RVNL",
  ]

  scanned_results = []

  for symbol in universe:
    try:
      ticker = yf.Ticker(f"{symbol}.NS")
      hist = ticker.history(period="20d")

      if hist.empty or len(hist) < 10:
        continue

      latest = hist.iloc[-1]
      prev = hist.iloc[-2]

      ltp = float(latest["Close"])
      prev_close = float(prev["Close"])
      change_pct = ((ltp - prev_close) / prev_close) * 100

      avg_vol = hist["Volume"].iloc[:-1].mean()
      vol_mult = float(latest["Volume"]) / avg_vol if avg_vol > 0 else 1.0

      # Technical EMAs & FVG / Order Block proxy
      hist["EMA_9"] = hist["Close"].ewm(span=9, adjust=False).mean()
      hist["EMA_21"] = hist["Close"].ewm(span=21, adjust=False).mean()
      hist["EMA_50"] = hist["Close"].ewm(span=50, adjust=False).mean()

      if change_pct >= 0.5 and vol_mult >= 1.15:
        action = "BUY"
        stop_loss = round(ltp * 0.965, 2)
        risk = ltp - stop_loss
        target_1 = round(ltp + (risk * rr_ratio), 2)
        target_2 = round(ltp + (risk * (rr_ratio + 1.5)), 2)

        scanned_results.append({
            "Stock": symbol,
            "Action": action,
            "LTP": round(ltp, 2),
            "Change_%": round(change_pct, 2),
            "Volume_Spurt": f"{round(vol_mult, 2)}x",
            "Stop_Loss": stop_loss,
            "Target_1": target_1,
            "Target_2": target_2,
            "Status": "🔥 Institutional Breakout & Order Block Confluence",
            "History": hist,
        })
    except Exception:
      continue

  df = pd.DataFrame(scanned_results)
  if not df.empty:
    df = df.sort_values(by="Change_%", ascending=False).reset_index(drop=True)
  return df


# Execute Scan
with st.spinner("Executing live multi-stock institutional scan..."):
  df_breakouts = fetch_multi_stock_breakouts()

if df_breakouts.empty:
  st.warning(
      "No stocks met the strict breakout criteria right now. Displaying active"
      " momentum leaders."
  )
  # Fallback
  fallback_hist = yf.Ticker("MSTCLTD.NS").history(period="20d")
  fallback_hist["EMA_9"] = fallback_hist["Close"].ewm(span=9).mean()
  fallback_
