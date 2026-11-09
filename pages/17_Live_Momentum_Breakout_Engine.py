import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Live Momentum Breakout & Profit Engine",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Live Momentum Breakout & Fresh Entry Engine")
st.markdown(
    "Click the button below to execute a live market scan across high-liquidity NSE stocks. "
    "This engine targets **fresh breakout setups** (moving green with high volume) so you can enter and book profit before the move peaks."
)

# Comprehensive liquid equity pool for instant real-time scanning
LIVE_SCAN_POOL = [
    "RELIANCE",
    "TATASTEEL",
    "SBIN",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "ONGC",
    "BEL",
    "HAL",
    "DIVISLAB",
    "WOCKPHARMA",
    "SUNPHARMA",
    "GLAND",
    "HONASA",
    "M&M",
    "BHEL",
    "NTPC",
    "HINDALCO",
    "BHARTIARTL",
    "TCS",
    "KALYANKJIL",
    "LAURUSLABS",
    "IOLCP",
    "DATAPATTNS",
    "SAILIFE",
    "MCX",
    "BSE",
    "BANKBARODA",
]


def scan_fresh_breakouts(symbols):
  valid_setups = []
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

      # Volume Confirmation
      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Fresh Breakout Filter: Must be moving green (+0.3% to +6%) but NOT exhausted (>6%)
      # and volume must be expanding (> 1.2x average)
      if 0.3 <= chg_pct <= 6.0 and vol_ratio >= 1.2:
        # Dynamic Risk-Reward Target Calculation (3R Profit Booking)
        atr_proxy = ltp * 0.02  # 2% volatility buffer
        stop_loss = round(ltp - (1.2 * atr_proxy), 2)
        book_profit_target = round(ltp + (3.0 * atr_proxy), 2)

        valid_setups.append({
            "Stock": sym,
            "LTP": round(ltp, 2),
            "Change_%": round(chg_pct, 2),
            "Vol_Surge": round(vol_ratio, 2),
            "Stop_Loss": stop_loss,
            "Book_Profit_Target": book_profit_target,
        })
    except Exception:
      continue

  if not valid_setups:
    return pd.DataFrame()

  df_res = pd.DataFrame(valid_setups)
  # Sort by highest volume expansion to get the top institutional momentum candidates
  df_res = df_res.sort_values(by="Vol_Surge", ascending=False)
  return df_res.head(2)  # Returns exactly the top 2 actionable fresh picks


# Interactive scan trigger button
if st.button("🚀 Run Live Scan & Get Top 2 Fresh Picks Now", type="primary"):
  with st.spinner(
      "Scanning live order flow and filtering out exhausted moves..."
  ):
    df_picks = scan_fresh_breakouts(LIVE_SCAN_POOL)

  if df_picks.empty:
    st.warning(
        "No fresh breakout stocks match the criteria right now. Market may be"
        " consolidating."
    )
  else:
    st.markdown(
        "### 🎯 Top 2 Fresh Actionable Setups (Ready for Entry & Profit Booking)"
    )

    cols = st.columns(2)
    for idx, row in df_picks.reset_index().iterrows():
      with cols[idx]:
        st.markdown(
            f"### 🟢 Pick #{idx+1}: **{row['Stock']}** "
            f"({row['Change_%']:+.2f}%)"
        )
        st.metric(
            label="Live Entry Price (LTP)",
            value=f"₹{row['LTP']:.2f}",
            delta=f"Volume Spurt: {row['Vol_Surge']}x",
        )
        st.markdown(
            f"🛑 **Stop-Loss Anchor:** ₹{row['Stop_Loss']}\n\n"
            f"🎯 **Book-Profit Target:** **₹{row['Book_Profit_Target']}**"
        )
        st.markdown("---")

    st.markdown("### 📋 Live Execution Summary Matrix")
    st.dataframe(df_picks, use_container_width=True)
else:
  st.info(
      "Click the button above anytime during market hours to fetch fresh"
      " real-time setups instantly."
  )
