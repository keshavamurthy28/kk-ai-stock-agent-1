import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Night-Before Homework & Prep Scanner",
    page_icon="🌙",
    layout="wide",
)

st.title("🌙 Night-Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Run this scan **after market hours or the night before** to generate your "
    "pre-market watchlist. These are stocks showing strong daily closes, 20 EMA support, "
    "and accumulation patterns ready for tomorrow's morning volume spurt."
)

# Comprehensive watchlist covering large-caps, mid-caps, and active breakouts
HOMEWORK_UNIVERSE = [
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


@st.cache_data(ttl=3600)
def run_nightly_prep(symbols):
  prep_list = []
  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="3mo", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 30:
        continue

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      close = float(latest["Close"])
      prev_close = float(prev["Close"])
      day_chg = ((close - prev_close) / prev_close) * 100

      # Technical indicators for night homework
      df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
      ema_20 = float(df["EMA_20"].iloc[-1])

      # 20-day high breakout check
      high_20 = float(df["High"].tail(20).max())

      # Homework criteria: Closed positive, trading above 20 EMA, or testing 20-day high
      if close > ema_20 and day_chg > 0:
        prep_list.append({
            "Stock": sym,
            "Close Price (₹)": round(close, 2),
            "Daily Change (%)": round(day_chg, 2),
            "Proximity to 20D High": (
                "Breakout Watch" if close >= (high_20 * 0.98) else "Accumulation"
            ),
            "Trend Status": "Bullish (Above 20 EMA)",
        })
    except Exception:
      continue

  return pd.DataFrame(prep_list)


if st.button("🌙 Run Evening Homework Scan", type="primary"):
  st.cache_data.clear()
  with st.spinner(
      "Analyzing daily candles, moving averages, and breakout zones..."
  ):
    df_homework = run_nightly_prep(HOMEWORK_UNIVERSE)

  if df_homework.empty:
    st.warning("No setups found for tomorrow.")
  else:
    df_homework = df_homework.sort_values(by="Daily Change (%)", ascending=False)
    st.success(
        f"✅ Homework Complete! Generated watchlist of {len(df_homework)}"
        " potential stocks for tomorrow."
    )

    st.markdown("### 📋 Tomorrow's Pre-Market Homework Watchlist")
    st.dataframe(df_homework, use_container_width=True)
else:
  st.info(
      "Click the button above in the evening or night before market open to build"
      " your custom watchlist."
  )
