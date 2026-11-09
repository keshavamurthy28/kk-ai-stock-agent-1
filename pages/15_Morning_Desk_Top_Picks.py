import pandas as pd
import streamlit as st
import yfinance as yf

# Expand watchlist to include Mid Cap, Small Cap & TV Momentum Stars
EXPANDED_NSE_UNIVERSE = [
    # CNBC Top Panel Picks & Small Caps
    "MANKIND",
    "DIVISLAB",
    "HONASA",
    "WOCKPHARMA",
    "GLAND",
    "RAIN",
    "ANUPAM",
    "DYNAMATECH",
    "TDPOWERSYS",
    "FINCABLES",
    "KALYANKJIL",
    "LAURUSLABS",
    "IOLCP",
    "DATAPATTNS",
    "SAILIFE",
    "MCX",
    "BSE",
    "BEL",
    "BHEL",
    "HAL",
    # Large & Mid Caps
    "SBIN",
    "RELIANCE",
    "TATASTEEL",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
    "M&M",
    "NTPC",
    "ONGC",
    "BHARTIARTL",
]


@st.cache_data(ttl=120)
def scan_any_indian_stock(symbols):
  data = []
  for s in symbols:
    # Append .NS for Indian National Stock Exchange listings
    sym = f"{s}.NS" if not s.endswith(".NS") else s
    try:
      df = yf.download(
          sym, period="5d", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 2:
        continue

      ltp = float(df["Close"].iloc[-1])
      prev = float(df["Close"].iloc[-2])
      chg = ((ltp - prev) / prev) * 100

      avg_vol = float(df["Volume"].tail(5).mean())
      cur_vol = float(df["Volume"].iloc[-1])
      vol_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Intraday 2.5% ATR target
      atr = ltp * 0.025
      sl = round(ltp - (1.2 * atr), 2)
      tgt = round(ltp + (3.0 * atr), 2)

      status = "🟢 BREAKOUT" if chg > 1.0 else "⚪ SIDEWAYS"

      data.append({
          "Stock": s,
          "LTP": round(ltp, 2),
          "Change_%": round(chg, 2),
          "Vol_Mult": round(vol_mult, 2),
          "Status": status,
          "Stop_Loss": sl,
          "Book_Profit_Target": tgt,
      })
    except:
      continue
  return pd.DataFrame(data)
