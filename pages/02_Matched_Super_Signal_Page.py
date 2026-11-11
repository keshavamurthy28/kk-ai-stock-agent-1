import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Matched Super-Signal Watchlist", page_icon="🎯", layout="wide"
)

st.title("🎯 Matched Morning Super-Signal Watchlist")
st.markdown(
    "Automatically cross-references your Night-Before Homework with Live Morning"
    " Volume Spurts."
)

st.sidebar.header("Filters")
min_vol_surge = st.sidebar.slider("Min Volume Surge (x)", 1.2, 5.0, 2.0, 0.2)

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

      df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
      ema_20 = float(df["EMA_20"].iloc[-1])

      is_night_qualified = close > ema_20 and day_chg > 0

      avg_vol = float(df["Volume"].tail(4).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      if is_night_qualified and vol_ratio >= vol_threshold:
        atr = close * 0.022
        stop_loss = round(close - (1.2 * atr), 2)
        target = round(close + (3.0 * atr), 2)

        matched_setups.append({
            "Stock": sym,
            "LTP": round(close, 2),
            "Change_Pct": round(day_chg, 2),
            "Vol_Surge": round(vol_ratio, 2),
            "Status": "NIGHT + MORNING MATCH",
            "Stop_Loss": stop_loss,
            "Target": target,
        })
    except:
      continue

  return pd.DataFrame(matched_setups)


if st.button("Run Super-Signal Match Scan", type="primary"):
  st.cache_data.clear()
  with st.spinner("Matching night homework with live volume flow..."):
    df_matched = fetch_super_signals(MASTER_UNIVERSE, min_vol_surge)

  if df_matched.empty:
    st.warning("No matched super-signals found right now.")
  else:
    df_matched = df_matched.sort_values(by="Vol_Surge", ascending=False)
    st.success(f"Found {len(df_matched)} matched breakout stocks.")

    cols = st.columns(3)
    for idx, row in df_matched.reset_index().iterrows():
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

    st.dataframe(df_matched, use_container_width=True)
else:
  st.info("Click the button above to run the super-signal match scan.")
