import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="CNBC Morning Desk & Profit Booking Terminal",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 CNBC Morning Desk & Expert Panel Live 'Stock of the Day' Terminal")
st.markdown(
    "Designed specifically for **today's session**. Track morning panel picks, live volume "
    "momentum, breakout status, and automated profit-booking target matrices."
)

# -------------------------------------------------------------------
# 1. SIDEBAR CONFIGURATION & WATCHLIST INPUT
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Morning Desk Setup")
default_picks = "MANKIND, DIVISLAB, HONASA, WOCKPHARMA, GLAND, BANKBARODA, SBIN, UNIONBANK, SMSPHARMA"
user_input_tickers = st.sidebar.text_area(
    "Enter Today's Panel Picks (Comma Separated)", value=default_picks
)

watchlist = [
    t.strip().upper() for t in user_input_tickers.split(",") if t.strip()
]
min_vol = st.sidebar.slider("Min Volume Surge Multiplier", 1.0, 3.0, 1.2)

# -------------------------------------------------------------------
# 2. LIVE DESK SCANNING & PROFIT TARGET ENGINE
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

      # Volume Surge vs 5-day average
      avg_vol = float(df["Volume"].tail(5).mean())
      cur_vol = float(latest["Volume"])
      vol_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Intraday Volatility & Profit Booking Target Levels
      atr_est = ltp * 0.022  # Estimated 2.2% intraday range
      stop_loss = round(ltp - (1.2 * atr_est), 2)
      target_1 = round(ltp + (1.5 * atr_est), 2)
      target_book_profit = round(
          ltp + (3.0 * atr_est), 2
      )  # Main Profit Booking Target

      # Status Determination
      if chg_pct > 0.5 and vol_mult >= min_vol:
        status = "🟢 MOVING GREEN / BREAKOUT"
      elif chg_pct > 0:
        status = "🟢 POSITIVE"
      else:
        status = "🔴 DIP / ACCUMULATION"

      results.append({
          "Stock": sym,
          "LTP (₹)": round(ltp, 2),
          "Change (%)": round(chg_pct, 2),
          "Volume Mult": round(vol_mult, 2),
          "Status": status,
          "Stop-Loss (₹)": stop_loss,
          "Book-Profit Target (₹)": target_book_profit,
      })
    except Exception as e:
      continue
  return pd.DataFrame(results)


with st.spinner("Scanning morning desk picks and calculating profit targets..."):
  df_desk = fetch_desk_picks(watchlist)

if df_desk.empty:
  st.warning(
      "Could not retrieve ticker data. Please check the symbols in the"
      " sidebar."
  )
else:
  # Sort by highest momentum change
  df_desk = df_desk.sort_values(by="Change (%)", ascending=False)

  st.markdown("### 🔥 Today's Actionable Desk Picks & Profit Booking Matrix")

  # Render card metrics for quick reading
  cols = st.columns(3)
  for idx, row in df_desk.reset_index().iterrows():
    c_idx = idx % 3
    with cols[c_idx]:
      st.markdown(f"#### {row['Stock']} ({row['Change (%)']:+.2f}%)")
      st.metric(
          label="Live Price",
          value=f"₹{row['LTP (₹)]:.2f}",
          delta=f"Vol: {row['Volume Mult']}x",
      )
      st.markdown(f"**Zone:** {row['Status']}")
      st.markdown(
          f"🛑 **Stop-Loss:** ₹{row['Stop-Loss (₹)]}\n"
          f"🎯 **Book-Profit Target:** **₹{row['Book-Profit Target (₹)]}**"
      )
      st.markdown("---")

  st.markdown("### 📋 Detailed Desk Summary Table")
  st.dataframe(df_desk, use_container_width=True)
