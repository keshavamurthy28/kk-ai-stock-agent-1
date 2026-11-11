import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Live Spurt Scraper", page_icon="🔍", layout="wide"
)

st.title("NSE Live Volume Spurt & Early Breakout Finder")
st.markdown(
    "Scans active NSE equities for early volume spurts and price momentum."
)

st.sidebar.header("Scan Parameters")
min_volume_surge = st.sidebar.slider("Min Volume Surge (x)", 1.5, 6.0, 2.0, 0.5)
min_price_change = st.sidebar.slider("Min % Gain", 1.5, 15.0, 3.0, 0.5)

UNIVERSE = [
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
def fetch_spurts(symbols, min_vol_mult, min_chg):
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

      if chg_pct >= min_chg and vol_ratio >= min_vol_mult:
        atr = ltp * 0.022
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


if st.button("Run Early Spurt Scan", type="primary"):
  st.cache_data.clear()
  with st.spinner("Scanning market for early volume spurts..."):
    df_res = fetch_spurts(UNIVERSE, min_volume_surge, min_price_change)

  if df_res.empty:
    st.warning("No stocks match the criteria right now.")
  else:
    df_res = df_res.sort_values(by="Vol_Surge", ascending=False)
    st.success(f"Found {len(df_res)} early breakout candidates.")

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
  st.info("Click the button above to run the scan.")
