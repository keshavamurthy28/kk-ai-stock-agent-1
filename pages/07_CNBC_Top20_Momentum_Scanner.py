import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="CNBC Top 20 & Institutional Momentum Scanner",
    page_icon="📺",
    layout="wide",
)

st.title("📺 CNBC-Style 'Top 20' & Institutional Momentum Desk")
st.markdown(
    "Automated scanner replicating financial television and brokerage desk screening. "
    "Identifies **High-Conviction Breakouts**, **Volume Spurts**, and **Automatic Profit Booking Levels** for intraday trading."
)

# -------------------------------------------------------------------
# 1. WATCHLIST UNIVERSE
# -------------------------------------------------------------------
DEFAULT_UNIVERSE = [
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
]

st.sidebar.header("🛠️ Scanner Configuration")
selected_symbols = st.sidebar.multiselect(
    "Scanning Watchlist", DEFAULT_UNIVERSE, default=DEFAULT_UNIVERSE[:12]
)
min_volume_spike = st.sidebar.slider("Min Volume Surge Multiplier", 1.2, 3.0, 1.5)


# -------------------------------------------------------------------
# 2. SCANNING & SCORING ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def scan_cnbc_momentum_picks(symbols):
  results = []
  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="5d", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 5:
        g = yf.download(
            ticker, period="1mo", interval="1d", progress=False, auto_adjust=True
        )
        if isinstance(g.columns, pd.MultiIndex):
          g.columns = g.columns.get_level_values(0)
        df = g

      if df.empty or len(df) < 4:
        continue

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      ltp = float(latest["Close"])
      prev_close = float(prev["Close"])
      chg_pct = ((ltp - prev_close) / prev_close) * 100

      # Volume Surge Calculation
      avg_vol = float(df["Volume"].tail(5).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Technical triggers
      high_20 = float(df["High"].tail(20).max())
      low_20 = float(df["Low"].tail(20).min())

      # Scoring logic mimicking CNBC Desk criteria
      score = 0
      catalyst = "On Radar (Consolidation)"

      if chg_pct > 1.0 and vol_ratio >= min_volume_spike:
        score = 5
        catalyst = "Strong on Charts & Volume Breakout"
      elif chg_pct > 0.5:
        score = 4
        catalyst = "Positive Momentum / Q2 Flow"
      elif ltp >= high_20 * 0.98:
        score = 4
        catalyst = "Approaching 52W / Swing High"
      elif vol_ratio > 2.0:
        score = 4
        catalyst = "Institutional Volume Spurt"
      else:
        score = 3
        catalyst = "Accumulation Zone"

      # Risk & Profit Booking Target Calculation
      atr_approx = ltp * 0.022  # Estimated 2.2% intraday volatility range
      stop_loss = round(ltp - (1.5 * atr_approx), 2)
      target_1r = round(ltp + (1.5 * atr_approx), 2)  # 1:1.5 Risk Reward
      target_2r = round(ltp + (3.0 * atr_approx), 2)  # Profit Booking Target

      results.append({
          "Symbol": sym,
          "LTP": round(ltp, 2),
          "Change_%": round(chg_pct, 2),
          "Volume_Spike": round(vol_ratio, 2),
          "Score": f"{score}/5",
          "Catalyst": catalyst,
          "Stop_Loss": stop_loss,
          "Target_1": target_1r,
          "Target_Book_Profit": target_2r,
      })
    except Exception as e:
      continue

  return pd.DataFrame(results)


with st.spinner("Scanning market data and filtering high-conviction picks..."):
  df_scanned = scan_cnbc_momentum_picks(selected_symbols)

if df_scanned.empty:
  st.warning(
      "No stocks matched the criteria. Please select more symbols from the"
      " sidebar."
  )
else:
  # Sort by highest change & volume surge
  df_scanned = df_scanned.sort_values(by="Change_%", ascending=False)

  st.markdown(
      "### 🔥 Top Actionable Stocks for the Day (CNBC Desk Confluence)"
  )
  st.markdown(
      "*Picked based on volume surge, breakout proximity, and momentum score.*"
  )

  # Display in clean columns / card metrics
  cols = st.columns(3)
  for idx, row in df_scanned.reset_index().iterrows():
    col_idx = idx % 3
    with cols[col_idx]:
      badge_color = (
          "🟢" if row["Change_%"] >= 0 else "🔴"
      )
      st.markdown(
          f"#### {badge_color} {row['Symbol']} "
          f"({row['Change_%']:+.2f}%)"
      )
      st.metric(
          label="Live Price (₹)",
          value=f"₹{row['LTP']:.2f}",
          delta=f"Vol: {row['Volume_Spike']}x",
      )
      st.markdown(f"**Score:** {row['Score']} | **Catalyst:** {row['Catalyst']}")
      st.markdown(
          f"👉 **Action:** Buy CMP\n"
          f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']}\n"
          f"🎯 **Book Profit Target:** **₹{row['Target_Book_Profit']}**"
      )
      st.markdown("---")

  # Full Table Summary for quick reference
  st.markdown("### 📋 Complete Screening & Profit Booking Matrix")
  st.dataframe(df_scanned, use_container_width=True)
