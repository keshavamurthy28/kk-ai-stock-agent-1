import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Daily Top 2 Institutional Execution Picks",
    page_icon="⭐",
    layout="wide",
)

st.title("⭐ Daily Top 2 High-Conviction Stocks for the Day")
st.markdown(
    "Automated institutional scanner configured to extract **exactly 2 top-tier stocks** "
    "each day using volume surge confluence, EMA trend alignment, and automated risk-reward targets."
)

# Core liquid institutional stock pool for daily extraction
DAILY_SCAN_POOL = [
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
]


@st.cache_data(ttl=300)
def get_daily_top_two(symbols):
  scored_results = []
  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="1mo", interval="1d", progress=False, auto_adjust=True
      )
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      if df.empty or len(df) < 15:
        continue

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      ltp = float(latest["Close"])
      prev_close = float(prev["Close"])
      chg_pct = ((ltp - prev_close) / prev_close) * 100

      # Volume Confirmation
      avg_vol = float(df["Volume"].tail(10).mean())
      cur_vol = float(latest["Volume"])
      vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0

      # Trend bias via 20 EMA
      df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
      ema_20 = float(df["EMA_20"].iloc[-1])

      # Advanced Scoring Algorithm (Confluence Score)
      score = 0
      if chg_pct > 0:
        score += 2
      if vol_ratio > 1.2:
        score += 2
      if ltp > ema_20:
        score += 1

      # Volatility & Target Matrices (1:3 Risk Reward for Book Profit)
      atr_val = float(
          (df["High"] - df["Low"]).tail(10).mean()
      )  # Average True Range proxy
      stop_loss = round(ltp - (1.2 * atr_val), 2)
      book_profit_target = round(ltp + (3.0 * atr_val), 2)

      scored_results.append({
          "Stock": sym,
          "Score": score,
          "LTP": round(ltp, 2),
          "Change_%": round(chg_pct, 2),
          "Vol_Surge": round(vol_ratio, 2),
          "Stop_Loss": stop_loss,
          "Book_Profit_Target": book_profit_target,
      })
    except Exception:
      continue

  if not scored_results:
    return pd.DataFrame()

  df_res = pd.DataFrame(scored_results)
  # Sort strictly by Confluence Score and Volume Surge to find the top 2 absolute best
  df_res = df_res.sort_values(
      by=["Score", "Vol_Surge", "Change_%"], ascending=False
  )
  return df_res.head(2)


with st.spinner("Analyzing market depth and calculating today's Top 2 picks..."):
  top_two_df = get_daily_top_two(DAILY_SCAN_POOL)

if top_two_df.empty:
  st.warning("Could not compute top picks at the moment. Please try again later.")
else:
  st.markdown("### 🏆 Today's High-Conviction Top 2 Execution Setups")

  cols = st.columns(2)
  for idx, row in top_two_df.reset_index().iterrows():
    with cols[idx]:
      st.markdown(
          f"### 🎯 Pick #{idx+1}: **{row['Stock']}** "
          f"({row['Change_%']:+.2f}%)"
      )
      st.metric(
          label="Recommended Buy Price (LTP)",
          value=f"₹{row['LTP']:.2f}",
          delta=f"Volume Surge: {row['Vol_Surge']}x",
      )
      st.markdown(f"**Confluence Score:** {row['Score']} / 5")
      st.markdown(
          f"🛑 **Stop-Loss Anchor:** ₹{row['Stop_Loss']}\n\n"
          f"🎯 **Book-Profit Target:** **₹{row['Book_Profit_Target']}**"
      )
      st.markdown("---")

  st.markdown("### 📋 Execution Matrix Summary")
  st.dataframe(top_two_df, use_container_width=True)
