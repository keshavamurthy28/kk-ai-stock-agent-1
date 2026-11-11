import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Matched Super-Signal Watchlist", page_icon="🎯", layout="wide"
)

st.title("🎯 Matched Morning Super-Signal Watchlist")
st.markdown(
    "This page automatically compares your **Night-Before Homework Watchlist** "
    "with **Live Morning Volume Spurts**. If a stock was on your night-before radar *and* "
    "is flashing a live morning volume breakout (> 2x), it locks in as your **Super-Signal** "
    "for immediate trade execution."
)

st.sidebar.header("Super-Signal Filters")
min_vol_surge = st.sidebar.slider(
    "Live Volume Surge Threshold (x)", 1.2, 5.0, 2.0, 0.2
)

# Unified master universe combining your tracked breakout stocks
MASTER_UNIVERSE = [
    "JYOTISTRUC",
    "ASHOKA",
    "KALYANKJIL",
    "APOLLO",
    "PCJEWELLER",
    "IRFC",
    "RVNL",
    "RPOWER",
    "GTLINFRA",
    "SUZLON",
    "YESBANK",
    "IDEA",
    "BANKBARODA",
    "PNB",
    "CANBK",
    "HDFCBANK",
    "ICICIBANK",
    "RELIANCE",
    "TATASTEEL",
    "INFY",
    "WOCKPHARMA",
    "HONASA",
    "BEL",
    "BHEL",
    "M&M",
    "THERMAX",
    "LENSKART",
    "RAIN",
    "DATAPATTNS",
    "GLAND",
    "AARTIDRUGS",
]


@st.cache_data(ttl=30)
def fetch_super_signals(symbols, vol_threshold):
  matched_setups = []

  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="30d", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 25:
        continue

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      close = float(latest["Close"])
      prev_close = float(prev["Close"])
      day_chg = ((close - prev_close) / prev_close) * 100

      # Check Night-Before condition (Above 20 EMA & Positive close)
      df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
      ema_20 = float(df["EMA_20"].iloc[-1])

      is_night_homework_qualified = close > ema_20 and day_chg > 0

      # Check Live Morning Spurt condition
      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      if is_night_homework_qualified and vol_ratio >= vol_threshold:
        atr = close * 0.022
        stop_loss = round(close - (1.2 * atr), 2)
        target = round(close + (3.0 * atr), 2)

        matched_setups.append({
            "Stock": sym,
            "Live LTP (₹)": round(close, 2),
            "Change (%)": round(day_chg, 2),
            "Vol Surge (x)": round(vol_ratio, 2),
            "Match Status": "🌟 NIGHT + MORNING MATCH",
            "Stop-Loss (₹)": stop_loss,
            "Target (₹)": target,
        })
    except Exception:
      continue

  return pd.DataFrame(matched_setups)


if st.button("🚀 Run Super-Signal Match Scan", type="primary"):
  st.cache_data.clear()
  with st.spinner(
      "Cross-referencing night homework with live market volume flow..."
  ):
    df_matched = fetch_super_signals(MASTER_UNIVERSE, min_vol_surge)

  if df_matched.empty:
    st.warning(
        "No direct matches found right now. Either markets are flat or volume"
        " surges haven't triggered yet."
    )
  else:
    df_matched = df_matched.sort_values(by="Vol Surge (x)", ascending=False)
    st.success(
        f"🎯 Success! Found {len(df_matched)} stocks that matched BOTH your"
        " night homework and morning volume scan."
    )

    st.markdown("### 🔥 High-Conviction Super-Signal Trade Cards")
    cols = st.columns(3)
    for idx, row in df_matched.reset_index().iterrows():
      c_idx = idx % 3
      with cols[c_idx]:
        st.markdown(f"#### {row['Stock']} ({row['Change (%)']:+.2f}%)")
        st.metric(
            label="Live Price",
            value=f"₹{row['Live LTP (₹)]}",
            delta=f"Vol: {row['Vol Surge (x)']}x",
        )
        st.markdown(
            f"✅ **Status:** {row['Match Status']}\n\n"
            f"🛑 **Stop-Loss:** ₹{row['Stop-Loss (₹)']}\n\n"
            f"🎯 **Target:** **₹{row['Target (₹)']}**"
        )
        st.markdown("---")

    st.markdown("### 📋 Complete Matched Super-Signal Table")
    st.dataframe(df_matched, use_container_width=True)
else:
  st.info(
      "Click the scan button above during market hours to instantly reveal"
      " stocks that match your night homework and morning volume filter."
  )
