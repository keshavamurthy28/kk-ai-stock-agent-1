import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Morning Desk & CNBC Panel Live Picks",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Morning Desk & CNBC Panel Live 'Stock of the Day' Terminal")
st.markdown(
    "Curated specifically for **today's session**. Enter the fresh morning panel picks or select "
    "from high-conviction catalyst stocks to track real-time momentum, volume confirmation, and automated profit-booking targets."
)

# -------------------------------------------------------------------
# 1. MORNING PANEL & DESK WATCHLIST INPUT
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Today's Panel Picks Input")
default_picks = "MANKIND, DIVISLAB, HONASA, WOCKPHARMA, GLAND, BANKBARODA, SBIN"
user_input_tickers = st.sidebar.text_area(
    "Enter Today's Morning Picks (Comma Separated)", value=default_picks
)

watchlist = [
    t.strip().upper() for t in user_input_tickers.split(",") if t.strip()
]

# -------------------------------------------------------------------
# 2. LIVE DESK SCANNING & TARGET CALCULATION ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=120)
def fetch_desk_picks(symbols):
  results = []
  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="5d", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 3:
        continue

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      ltp = float(latest["Close"])
      prev_close = float(prev["Close"])
      chg_pct = ((ltp - prev_close) / prev_close) * 100

      # Volume Check vs 5-day average
      avg_vol = float(df["Volume"].tail(5).mean())
      cur_vol = float(latest["Volume"])
      vol_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Intraday Volatility & Profit Booking Targets
      atr_est = ltp * 0.02  # 2% intraday average range
      stop_loss = round(ltp - (1.2 * atr_est), 2)
      target_book_profit = round(ltp + (2.5 * atr_est), 2)  # Book profit target

      # Status Determination
      if chg_pct > 0.5:
        status = "🟢 GREEN / MOMENTUM"
      elif chg_pct < -0.5:
        status = "🔴 DIP / ACCUMULATION"
      else:
        status = "⚪ CONSOLIDATING"

      results.append({
          "Stock": sym,
          "LTP (₹)": round(ltp, 2),
          "Today Change (%)": round(chg_pct, 2),
          "Volume Multiplier": round(vol_mult, 2),
          "Status": status,
          "Stop-Loss (₹)": stop_loss,
          "Book-Profit Target (₹)": target_book_profit,
      })
    except Exception as e:
      continue
  return pd.DataFrame(results)


with st.spinner("Fetching live prices and calculating today's booking targets..."):
  df_desk = fetch_desk_picks(watchlist)

if df_desk.empty:
  st.warning(
      "Could not fetch data for the entered tickers. Please verify the symbols."
  )
else:
  st.markdown("### 🔥 Today's Actionable Panel Picks & Profit Booking Matrix")

  # Render visual card metrics for quick reading
  cols = st.columns(3)
  for idx, row in df_desk.reset_index().iterrows():
    c_idx = idx % 3
    with cols[c_idx]:
      st.markdown(f"#### {row['Stock']} ({row['Today Change (%)']:+.2f}%)")
      st.metric(
          label="Live Price",
          value=f"₹{row['LTP (₹)]:.2f}",
          delta=f"Vol: {row['Volume_Multiplier']}x",
      )
      st.markdown(f"**Zone:** {row['Status']}")
      st.markdown(
          f"🛑 **Stop-Loss:** ₹{row['Stop-Loss (₹)]}\n"
          f"🎯 **Book Profit Target:** **₹{row['Book-Profit Target (₹)]}**"
      )
      st.markdown("---")

  st.markdown("### 📋 Detailed Desk Summary Table")
  st.dataframe(df_desk, use_container_width=True)
