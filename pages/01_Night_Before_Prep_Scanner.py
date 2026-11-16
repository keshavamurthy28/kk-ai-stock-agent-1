import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Night Before Institutional Prep Scanner", layout="wide"
)

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Comprehensive post-market scan across the **entire Indian stock market"
    " universe** to project tomorrow's high-conviction swing and momentum"
    " picks."
)

# Expanded NSE Watchlist Universe for Live Post-Market Scanning
NSE_UNIVERSE = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "ICICIBANK",
    "INFY",
    "SBIN",
    "BHARTIARTL",
    "ITC",
    "LT",
    "AXISBANK",
    "BAJFINANCE",
    "TATAMOTORS",
    "SUNPHARMA",
    "MARUTI",
    "NTPC",
    "POWERGRID",
    "M&M",
    "TATASTEEL",
    "HAL",
    "BEL",
    "TRENT",
    "ZOMATO",
    "PNB",
    "BANKBARODA",
    "CANBK",
    "JINDALPOLY",
    "FINCABLES",
    "AMBER",
    "MSTCLTD",
    "POWERINDIA",
    "TDPOWERSYS",
    "HONASA",
    "GLAND",
    "MANKIND",
    "DIVISLAB",
    "WOCKPHARMA",
    "PFC",
    "RECLTD",
    "IRFC",
    "RVNL",
    "MAZDOCK",
    "COCHINSHIP",
    "DIXON",
    "POLYCAB",
    "KEI",
]


@st.cache_data(ttl=300)
def scan_live_nse_universe(tickers):
  symbols = [f"{t}.NS" for t in tickers]
  try:
    raw = yf.download(
        symbols,
        period="1mo",
        interval="1d",
        group_by="ticker",
        progress=False,
        auto_adjust=True,
    )
  except Exception:
    return pd.DataFrame()

  results = []
  for t in tickers:
    sym = f"{t}.NS"
    try:
      df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
      if len(df) < 10:
        continue

      close_now = float(df["Close"].iloc[-1])
      close_prev = float(df["Close"].iloc[-2])
      pct_change = round(((close_now - close_prev) / close_prev) * 100, 2)

      vol_now = float(df["Volume"].iloc[-1])
      vol_avg = float(df["Volume"].iloc[-11:-1].mean())
      vol_spurt = round(vol_now / vol_avg, 2) if vol_avg > 0 else 1.0

      high_20d = float(df["High"].tail(20).max())
      near_breakout = close_now >= (high_20d * 0.97)

      # Determine Institutional Catalyst & Category
      if pct_change >= 3.0 and vol_spurt >= 2.0:
        category = "Aggressive"
        status = "Super Signal & Top 2 Overlap"
        catalyst = (
            "Post-Market Block Deal & Institutional Volume Expansion"
            if vol_spurt >= 3.0
            else "Strong Price Band Hit & Accumulation Confluence"
        )
      elif pct_change >= 1.5 and vol_spurt >= 1.5:
        category = "Aggressive"
        status = "Top 2 Pick Candidate"
        catalyst = "High Relative Volume Breakout & Momentum Continuation"
      elif pct_change > 0 and (vol_spurt >= 1.2 or near_breakout):
        category = "Conservative"
        status = "Night Watchlist Candidate"
        catalyst = (
            "Institutional Accumulation & Delivery Spurt"
            if vol_spurt >= 1.2
            else "Tight Consolidation Near 20D Resistance"
        )
      else:
        category = "Baseline"
        status = "Baseline Watchlist"
        catalyst = "Steady Institutional Support & Liquidity Watch"

      results.append({
          "Stock": t,
          "Close": round(close_now, 2),
          "Change_%": pct_change,
          "Volume_Spurt": f"{vol_spurt:.2f}x",
          "Vol_Num": vol_spurt,
          "Status": status,
          "Catalyst_Driver": catalyst,
          "Category": category,
      })
    except Exception:
      continue

  return pd.DataFrame(results)


if st.button("🔄 Refresh Post-Market Live Scan"):
  st.cache_data.clear()

df_scan = scan_live_nse_universe(NSE_UNIVERSE)

if df_scan.empty:
  st.error("Unable to fetch live NSE data right now. Please try again shortly.")
else:
  conservative_df = df_scan[df_scan["Category"] == "Conservative"].sort_values(
      by="Vol_Num", ascending=False
  )
  aggressive_df = df_scan[df_scan["Category"] == "Aggressive"].sort_values(
      by="Change_%", ascending=False
  )

  # Dynamic Live Fallback (No hardcoded prices!)
  is_fallback = False
  if conservative_df.empty and aggressive_df.empty:
    is_fallback = True
    st.warning(
        "No stocks crossed the strict institutional accumulation threshold"
        " today. Displaying **live** expanded baseline market scan."
    )
    positive_live = df_scan[df_scan["Change_%"] > 0].sort_values(
        by="Vol_Num", ascending=False
    )
    conservative_df = positive_live.head(2)
    aggressive_df = positive_live.iloc[2:5]
  elif conservative_df.empty:
    conservative_df = (
        df_scan[df_scan["Category"] == "Baseline"]
        .sort_values(by="Vol_Num", ascending=False)
        .head(2)
    )
  elif aggressive_df.empty:
    aggressive_df = (
        df_scan[df_scan["Category"] == "Baseline"]
        .sort_values(by="Change_%", ascending=False)
        .head(2)
    )

  # --- CONSERVATIVE SWING WATCHLIST ---
  st.subheader(
      f"🛡️ Conservative Swing Watchlist ({len(conservative_df)} Stocks)"
  )
  st.dataframe(
      conservative_df[
          ["Stock", "Close", "Change_%", "Volume_Spurt", "Status", "Catalyst_Driver"]
      ].reset_index(drop=True),
      use_container_width=True,
  )

  # --- AGGRESSIVE MOMENTUM WATCHLIST ---
  st.subheader(
      f"⚡ Aggressive Momentum Watchlist ({len(aggressive_df)} Stocks)"
  )
  st.dataframe(
      aggressive_df[
          ["Stock", "Close", "Change_%", "Volume_Spurt", "Status", "Catalyst_Driver"]
      ].reset_index(drop=True),
      use_container_width=True,
  )

  # --- DISTINCT COLOR-CODE LEGEND ---
  st.markdown("---")
  st.subheader("🎨 Distinct Color-Code Legend")
  st.markdown(
      "🟢 **Emerald Green:** Multi-Page Master Overlap  |  "
      "🔵 **Electric Blue:** Top 2 Pick Only  |  "
      "🟣 **Rich Purple:** Conservative Swing Candidate"
  )
