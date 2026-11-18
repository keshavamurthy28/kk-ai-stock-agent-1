import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

st.title("🗺️ Sector Heatmap & Breadth Analysis (Over 31+ Sectors)")

if st.button("🔄 Refresh Live Data", type="primary"):
  st.cache_data.clear()
  st.rerun()

# Core Sectoral Indices Mapping
SECTOR_TICKERS = {
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "NIFTY INFRA": "^CNXINFRA",
    "NIFTY MEDIA": "^CNXMEDIA",
    "NIFTY FIN SERVICE": "NIFTY_FIN_SERVICE.NS",
}


@st.cache_data(ttl=300)
def fetch_sector_predictive_scores():
  # Fetch Benchmark Nifty 50
  nifty_df = yf.Ticker("^NSEI").history(period="5d", interval="1d")
  if nifty_df.empty or len(nifty_df) < 2:
    return None, 0.0

  nifty_chg = (
      (nifty_df["Close"].iloc[-1] - nifty_df["Close"].iloc[-2])
      / nifty_df["Close"].iloc[-2]
  ) * 100

  records = []
  for name, ticker in SECTOR_TICKERS.items():
    try:
      df = yf.Ticker(ticker).history(period="5d", interval="1d")
      if df.empty or len(df) < 2:
        continue

      close_today = float(df["Close"].iloc[-1])
      close_prev = float(df["Close"].iloc[-2])
      high_today = float(df["High"].iloc[-1])
      low_today = float(df["Low"].iloc[-1])
      vol_today = float(df["Volume"].iloc[-1])
      vol_avg = (
          float(df["Volume"].iloc[:-1].mean())
          if len(df) > 2
          else vol_today
      )

      day_chg = ((close_today - close_prev) / close_prev) * 100

      # 1. Relative Strength (RS) vs Nifty 50
      rel_strength = day_chg - nifty_chg

      # 2. Closing Range Position (0 to 100% — where did it close in today's candle?)
      candle_range = high_today - low_today
      close_pos = (
          ((close_today - low_today) / candle_range) * 100
          if candle_range > 0
          else 50.0
      )

      # 3. Relative Volume Multiplier
      rvol = round(vol_today / vol_avg, 2) if vol_avg > 0 else 1.0

      # Institutional Overnight Carry-Forward Score (0 to 100)
      # Weighs RS outperformance (45%), Strong High-Close (35%), and Volume Expansion (20%)
      rs_score = np.clip((rel_strength + 2.0) * 15, 0, 45)
      close_score = (close_pos / 100.0) * 35
      vol_score = np.clip(rvol * 10, 0, 20)
      total_score = round(rs_score + close_score + vol_score, 1)

      # Signal Classification
      if total_score >= 65 and rel_strength > 0:
        signal = "🔥 TOP LONG CANDIDATE (Strong Carry-Forward)"
      elif total_score >= 52 and rel_strength > 0:
        signal = "🟢 ACCUMULATION WATCH (Outperforming Nifty)"
      elif rel_strength < -1.0 and close_pos < 30:
        signal = "🔴 DISTRIBUTION / SHORT BIAS"
      else:
        signal = "⚪ NEUTRAL / RANGEBOUND"

      records.append({
          "Sector": name,
          "LTP": round(close_today, 2),
          "Day Change %": round(day_chg, 2),
          "RS vs Nifty %": round(rel_strength, 2),
          "Close Strength %": round(close_pos, 1),
          "RVOL": f"{rvol}x",
          "Momentum Score": total_score,
          "Tomorrow's Advance Setup": signal,
      })
    except Exception:
      continue

  df_res = pd.DataFrame(records)
  if not df_res.empty:
    df_res = df_res.sort_values(
        by="Momentum Score", ascending=False
    ).reset_index(drop=True)
  return df_res, round(nifty_chg, 2)


df_sectors, nifty_day_chg = fetch_sector_predictive_scores()

if df_sectors is not None and not df_sectors.empty:
  # ---------------------------------------------------------
  # NEW SECTION: TOMORROW'S ADVANCE SECTOR RADAR
  # ---------------------------------------------------------
  st.markdown("---")
  st.subheader("🔮 Tomorrow's Advance Sector Radar (EOD Institutional Carry-Forward)")
  st.caption(
      f"Evaluates Relative Strength against Nifty 50 ({nifty_day_chg:+.2f}%),"
      " final-hour closing range strength, and volume expansion to flag"
      " sectors primed for tomorrow's opening drive."
  )

  top_2 = df_sectors.head(2)
  col1, col2 = st.columns(2)

  with col1:
    s1 = top_2.iloc[0]
    st.success(
        f"**#1 PRIME SECTOR FOR TOMORROW: {s1['Sector']}**\n\n"
        f"• **Score:** {s1['Momentum Score']}/100 | **RS vs Nifty:** {s1['RS vs Nifty %']:+.2f}%\n"
        f"• **Closing Strength:** Closed in top {100 - s1['Close Strength %']:.0f}% of daily range ({s1['RVOL']} Vol)\n"
        f"• **Action:** Look for bullish continuation setups in top {s1['Sector']} leaders at 9:15 AM."
    )

  if len(top_2) > 1:
    with col2:
      s2 = top_2.iloc[1]
      st.info(
          f"**#2 SECONDARY WATCH SECTOR: {s2['Sector']}**\n\n"
          f"• **Score:** {s2['Momentum Score']}/100 | **RS vs Nifty:** {s2['RS vs Nifty %']:+.2f}%\n"
          f"• **Closing Strength:** Closed at {s2['Close Strength %']:.0f}% of daily range ({s2['RVOL']} Vol)\n"
          f"• **Action:** Track pre-open order flow for breakout confirmation above today's high."
      )

  st.markdown("---")

  # ---------------------------------------------------------
  # VISUAL SECTOR HEATMAP (TREEMAP)
  # ---------------------------------------------------------
  st.subheader("🗺️ Institutional Sector Heatmap")
  df_sectors["AbsSize"] = df_sectors["Momentum Score"].clip(lower=20)
  fig = px.treemap(
      df_sectors,
      path=["Sector"],
      values="AbsSize",
      color="Day Change %",
      color_continuous_scale=["#B71C1C", "#EF5350", "#ECEFF1", "#66BB6A", "#1B5E20"],
      color_continuous_midpoint=0,
      hover_data=["LTP", "RS vs Nifty %", "Close Strength %", "Momentum Score"],
  )
  fig.update_traces(
      texttemplate="<b>%{label}</b><br>%{customdata[1]:+.2f}% RS",
      textfont=dict(size=14),
  )
  fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
  st.plotly_chart(fig, use_container_width=True)

  # ---------------------------------------------------------
  # FULL SECTOR SCORING & RANKING TABLE
  # ---------------------------------------------------------
  st.subheader("📊 Sector Analysis and Scores Table (RS, Close Position & Momentum)")
  st.dataframe(
      df_sectors,
      use_container_width=True,
      hide_index=True,
      column_config={
          "Momentum Score": st.column_config.ProgressColumn(
              "Momentum Score",
              help="Composite score based on Relative Strength, Closing Range & RVOL",
              format="%.1f",
              min_value=0,
              max_value=100,
          ),
          "Day Change %": st.column_config.NumberColumn(format="%.2f%%"),
          "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
          "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
      },
  )
else:
  st.warning("⚠️ Unable to fetch live sectoral index data. Please click Refresh Live Data.")
