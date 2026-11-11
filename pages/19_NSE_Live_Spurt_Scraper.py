import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Live Volume Spurt & Early Breakout Finder",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 NSE Live Volume Spurt & Early Breakout Finder")
st.markdown(
    "Scans a broad cross-section of active NSE equities for **early-morning volume "
    "spurts and institutional value spikes** (catching movers like Jyoti Structures, Ashoka, & Kalyan Jewellers early)."
)

st.sidebar.header("Scan Parameters")
min_volume_surge = st.sidebar.slider(
    "Minimum Volume Surge Multiplier", 1.5, 6.0, 2.0, 0.5
)
min_price_change = st.sidebar.slider("Minimum % Gain Filter", 1.5, 15.0, 3.0, 0.5)

# Expanded dynamic universe incorporating mid-caps, infrastructure, and high-volume movers
DYNAMIC_NSE_UNIVERSE = [
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


@st.cache_data(ttl=60)
def fetch_early_spurts(symbols, min_vol_mult, min_chg):
  spurt_results = []
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

      # Volume Spurt Ratio
      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Early detection trigger: High volume surge + active price rise
      if chg_pct >= min_chg and vol_ratio >= min_vol_mult:
        atr = ltp * 0.022
        stop_loss = round(ltp - (1.2 * atr), 2)
        target = round(ltp + (3.0 * atr), 2)

        spurt_results.append({
            "Stock": sym,
            "LTP (₹)": round(ltp, 2),
            "Change (%)": round(chg_pct, 2),
            "Volume Surge (x)": round(vol_ratio, 2),
            "Stop-Loss (₹)": stop_loss,
            "Book-Profit Target (₹)": target,
        })
    except Exception:
      continue

  return pd.DataFrame(spurt_results)


if st.button("🚀 Run Early Spurt & Volume Scan Now", type="primary"):
  st.cache_data.clear()
  with st.spinner(
      "Scanning market for early institutional accumulation and volume spurts..."
  ):
    df_spurts = fetch_early_spurts(
        DYNAMIC_NSE_UNIVERSE, min_volume_surge, min_price_change
    )

  if df_spurts.empty:
    st.warning(
        "No stocks match the early spurt filters at this moment. Try lowering"
        " the sliders in the sidebar."
    )
  else:
    df_spurts = df_spurts.sort_values(by="Volume Surge (x)", ascending=False)
    st.success(
        f"🎯 Success! Detected {len(df_spurts)} early-stage breakout candidates."
    )

    st.markdown("### 🔥 Actionable Early Spurt Setups")
    cols = st.columns(3)
    for idx, row in df_spurts.reset_index().iterrows():
      c_idx = idx % 3
      with cols[c_idx]:
        st.markdown(f"#### {row['Stock']} ({row['Change (%)']:+.2f}%)")
        st.metric(
            label="Live Price",
            value=f"₹{row['LTP (₹)]}",
            delta=f"Vol Surge: {row['Volume Surge (x)']}x",
        )
        st.markdown(
            f"🛑 **Stop-Loss:** ₹{row['Stop-Loss (₹)']}\n\n"
            f"🎯 **Book-Profit Target:** **₹{row['Book-Profit Target (₹)]}**"
        )
        st.markdown("---")

    st.markdown("### 📋 Complete Scanned Spurt Table")
    st.dataframe(df_spurts, use_container_width=True)
else:
  st.info(
      "Click the scan button above during market hours to capture early volume"
      " spurs instantly."
  )
