import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Live Market Spurt & Volume Breakout Scanner",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 Live Market Spurt & Sudden Breakout Detector")
st.markdown(
    "This scanner dynamically filters for sudden volume surges and aggressive price "
    "breakouts (like **Aarti Drugs** style momentum spikes) across active NSE equities."
)

st.sidebar.header("Scanner Configuration")
min_change = st.sidebar.slider("Minimum % Gain Filter", 1.0, 10.0, 3.0, 0.5)
vol_multiplier = st.sidebar.slider(
    "Volume Surge Threshold (x times average)", 1.2, 5.0, 1.5, 0.1
)

# Broad high-liquidity and mid-cap momentum stock universe prone to sudden institutional spurts
EXPANDED_NSE_UNIVERSE = [
    "AARTIDRUGS",
    "DATAPATTNS",
    "GLAND",
    "SAILIFE",
    "DIVISLAB",
    "LAURUSLABS",
    "KALYANKJIL",
    "SBIN",
    "HINDALCO",
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
    "NYKAA",
    "THERMAX",
    "LENSKART",
    "RAIN",
    "FINCABLES",
    "MCX",
    "BSE",
    "BANKBARODA",
]


@st.cache_data(ttl=30)
def scan_sudden_spurts(symbols, min_chg, min_vol_mul):
  triggered_stocks = []
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

      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      if chg_pct >= min_chg and vol_ratio >= min_vol_mul:
        atr = ltp * 0.02
        stop_loss = round(ltp - (1.2 * atr), 2)
        book_profit_target = round(ltp + (3.0 * atr), 2)

        triggered_stocks.append({
            "Stock": sym,
            "LTP (₹)": round(ltp, 2),
            "Change (%)": round(chg_pct, 2),
            "Volume Surge (x)": round(vol_ratio, 2),
            "Stop-Loss (₹)": stop_loss,
            "Book-Profit Target (₹)": book_profit_target,
        })
    except Exception:
      continue

  return pd.DataFrame(triggered_stocks)


if st.button("⚡ Scan for Live Sudden Breakouts & Spurts", type="primary"):
  st.cache_data.clear()
  with st.spinner(
      "Scanning live order flow for sudden volume and price spikes..."
  ):
    df_spurts = scan_sudden_spurts(
        EXPANDED_NSE_UNIVERSE, min_change, vol_multiplier
    )

  if df_spurts.empty:
    st.warning(
        "No stocks currently match the sudden spurt threshold. Lower the"
        " filters in the sidebar if markets are flat."
    )
  else:
    df_spurts = df_spurts.sort_values(by="Volume Surge (x)", ascending=False)
    st.success(
        f"🚨 Trigger Successful! Found {len(df_spurts)} active sudden breakout"
        " stocks."
    )

    st.markdown("### 🔥 Instant Actionable Spurt Setups")
    cols = st.columns(3)
    for idx, row in df_spurts.reset_index().iterrows():
      c_idx = idx % 3
      with cols[c_idx]:
        st.markdown(f"#### {row['Stock']} ({row['Change (%)']:+.2f}%)")
        st.metric(
            label="Live Price",
            value=f"₹{row['LTP (₹)]}",
            delta=f"Vol Spurt: {row['Volume Surge (x)']}x",
        )
        st.markdown(
            f"🛑 **Stop-Loss:** ₹{row['Stop-Loss (₹)']}\n\n"
            f"🎯 **Book-Profit Target:** **₹{row['Book-Profit Target (₹)]}**"
        )
        st.markdown("---")

    st.markdown("### 📋 Detailed Spurt Data Matrix")
    st.dataframe(df_spurts, use_container_width=True)
else:
  st.info(
      "Click the scan button above anytime to detect sudden volume spurts and"
      " mid-cap breakouts as they happen."
  )
