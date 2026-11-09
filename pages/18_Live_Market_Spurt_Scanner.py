import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Live Market Spurt Scanner", page_icon="🚨", layout="wide"
)

st.title("Live Market Spurt & Sudden Breakout Detector")
st.markdown(
    "Dynamically scans for sudden volume surges and aggressive price breakouts"
    " across active NSE equities."
)

st.sidebar.header("Configuration")
min_change = st.sidebar.slider("Minimum % Gain Filter", 1.0, 10.0, 3.0, 0.5)
vol_multiplier = st.sidebar.slider(
    "Volume Surge Threshold (x)", 1.2, 5.0, 1.5, 0.1
)

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
def scan_spurts(symbols, min_chg, min_vol_mul):
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

      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      if chg_pct >= min_chg and vol_ratio >= min_vol_mul:
        atr = ltp * 0.02
        stop_loss = round(ltp - (1.2 * atr), 2)
        target = round(ltp + (3.0 * atr), 2)

        results.append({
            "Stock": sym,
            "LTP": round(ltp, 2),
            "Change_Pct": round(chg_pct, 2),
            "Vol_Surge": round(vol_ratio, 2),
            "Stop_Loss": stop_loss,
            "Target": target,
        })
    except:
      continue
  return pd.DataFrame(results)


if st.button("Run Live Spurt Scan", type="primary"):
  st.cache_data.clear()
  with st.spinner("Scanning live market order flow..."):
    df_res = scan_spurts(EXPANDED_NSE_UNIVERSE, min_change, vol_multiplier)

  if df_res.empty:
    st.warning("No stocks match the criteria right now.")
  else:
    df_res = df_res.sort_values(by="Vol_Surge", ascending=False)
    st.success(f"Found {len(df_res)} active breakout stocks.")

    cols = st.columns(3)
    for idx, row in df_res.reset_index().iterrows():
      c_idx = idx % 3
      with cols[c_idx]:
        st.markdown(f"### {row['Stock']} ({row['Change_Pct']:+.2f}%)")
        st.metric(
            label="Live Price",
            value=f"Rs {row['LTP']}",
            delta=f"Vol: {row['Vol_Surge']}x",
        )
        st.markdown(
            f"**Stop-Loss:** Rs {row['Stop_Loss']}\n\n"
            f"**Target:** **Rs {row['Target']}**"
        )
        st.markdown("---")

    st.dataframe(df_res, use_container_width=True)
else:
  st.info("Click the button above to begin live market scanning.")
