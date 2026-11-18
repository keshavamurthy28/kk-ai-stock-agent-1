import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

st.title("🗺️ Sector Heatmap & Breadth Analysis (Interactive Color-Filter & Drill-Down)")

if st.button("🔄 Refresh Live Data", type="primary"):
  st.cache_data.clear()
  st.rerun()

# Core Sectoral Indices + Top Constituent Stocks for Drill-Down & Real Volume
SECTOR_CONSTITUENTS = {
    "NIFTY PSU BANK": {
        "index": "^CNXPSUBANK",
        "stocks": ["SBIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS", "INDIANB.NS"],
    },
    "NIFTY BANK": {
        "index": "^NSEBANK",
        "stocks": ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS", "AUBANK.NS"],
    },
    "NIFTY IT": {
        "index": "^CNXIT",
        "stocks": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "MPHASIS.NS"],
    },
    "NIFTY PHARMA": {
        "index": "^CNXPHARMA",
        "stocks": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "AUROPHARMA.NS"],
    },
    "NIFTY AUTO": {
        "index": "^CNXAUTO",
        "stocks": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "TVSMOTOR.NS"],
    },
    "NIFTY FMCG": {
        "index": "^CNXFMCG",
        "stocks": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", "VBL.NS"],
    },
    "NIFTY METAL": {
        "index": "^CNXMETAL",
        "stocks": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "VEDL.NS", "NMDC.NS", "NATIONALUM.NS"],
    },
    "NIFTY ENERGY": {
        "index": "^CNXENERGY",
        "stocks": ["RELIANCE.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS", "COALINDIA.NS", "TATAPOWER.NS"],
    },
    "NIFTY REALTY": {
        "index": "^CNXREALTY",
        "stocks": ["DLF.NS", "MACROTECH.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "PHOENIXLTD.NS"],
    },
    "NIFTY INFRA": {
        "index": "^CNXINFRA",
        "stocks": ["LT.NS", "BHARTIARTL.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "GRASIM.NS", "SIEMENS.NS"],
    },
    "NIFTY FIN SERVICE": {
        "index": "NIFTY_FIN_SERVICE.NS",
        "stocks": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "JIOFIN.NS", "CHOLAFIN.NS", "SHRIRAMFIN.NS", "PFC.NS"],
    },
}


@st.cache_data(ttl=300)
def fetch_drilldown_sector_data():
  all_tickers = ["^NSEI"]
  for info in SECTOR_CONSTITUENTS.values():
    all_tickers.append(info["index"])
    all_tickers.extend(info["stocks"])
  all_tickers = list(set(all_tickers))

  raw = yf.download(
      all_tickers, period="5d", interval="1d", group_by="ticker", progress=False
  )
  if raw.empty or "^NSEI" not in raw:
    return None, None, 0.0

  nifty_df = raw["^NSEI"].dropna()
  if len(nifty_df) < 2:
    return None, None, 0.0

  nifty_chg = (
      (nifty_df["Close"].iloc[-1] - nifty_df["Close"].iloc[-2])
      / nifty_df["Close"].iloc[-2]
  ) * 100

  sector_records = []
  stock_records = []

  for sector_name, info in SECTOR_CONSTITUENTS.items():
    idx_ticker = info["index"]
    if idx_ticker not in raw:
      continue

    df_idx = raw[idx_ticker].dropna()
    if len(df_idx) < 2:
      continue

    close_today = float(df_idx["Close"].iloc[-1])
    close_prev = float(df_idx["Close"].iloc[-2])
    high_today = float(df_idx["High"].iloc[-1])
    low_today = float(df_idx["Low"].iloc[-1])

    day_chg = ((close_today - close_prev) / close_prev) * 100
    rel_strength = day_chg - nifty_chg
    candle_range = high_today - low_today
    close_pos = (
        ((close_today - low_today) / candle_range) * 100
        if candle_range > 0
        else 50.0
    )

    sector_rvols = []
    for sym in info["stocks"]:
      if sym not in raw:
        continue
      df_s = raw[sym].dropna()
      if len(df_s) < 2:
        continue

      s_close = float(df_s["Close"].iloc[-1])
      s_prev = float(df_s["Close"].iloc[-2])
      s_high = float(df_s["High"].iloc[-1])
      s_low = float(df_s["Low"].iloc[-1])
      s_vol = float(df_s["Volume"].iloc[-1])
      s_vol_avg = (
          float(df_s["Volume"].iloc[:-1].mean()) if len(df_s) > 2 else s_vol
      )

      s_chg = ((s_close - s_prev) / s_prev) * 100
      s_rs = s_chg - nifty_chg
      s_range = s_high - s_low
      s_close_pos = (
          ((s_close - s_low) / s_range) * 100 if s_range > 0 else 50.0
      )
      s_rvol = round(s_vol / s_vol_avg, 2) if s_vol_avg > 0 else 1.0
      sector_rvols.append(s_rvol)

      s_score = round(
          np.clip((s_rs + 2.5) * 12, 0, 45)
          + (s_close_pos / 100.0) * 35
          + np.clip(s_rvol * 10, 0, 20),
          1,
      )

      stock_records.append({
          "Sector": sector_name,
          "Stock": sym.replace(".NS", ""),
          "LTP": round(s_close, 2),
          "Day Change %": round(s_chg, 2),
          "RS vs Nifty %": round(s_rs, 2),
          "Close Strength %": round(s_close_pos, 1),
          "RVOL": s_rvol,
          "Stock Score": s_score,
          "BoxSize": max(s_score, 15.0),
      })

    avg_sector_rvol = round(np.mean(sector_rvols), 2) if sector_rvols else 1.0

    rs_score = np.clip((rel_strength + 2.0) * 15, 0, 45)
    close_score = (close_pos / 100.0) * 35
    vol_score = np.clip(avg_sector_rvol * 10, 0, 20)
    total_score = round(rs_score + close_score + vol_score, 1)

    if total_score >= 65 and rel_strength > 0:
      signal = "🔥 TOP LONG CANDIDATE (Strong Carry-Forward)"
    elif total_score >= 52 and rel_strength > 0:
      signal = "🟢 ACCUMULATION WATCH (Outperforming Nifty)"
    elif rel_strength < -1.0 and close_pos < 30:
      signal = "🔴 DISTRIBUTION / SHORT BIAS"
    else:
      signal = "⚪ NEUTRAL / RANGEBOUND"

    sector_records.append({
        "Sector": sector_name,
        "LTP": round(close_today, 2),
        "Day Change %": round(day_chg, 2),
        "RS vs Nifty %": round(rel_strength, 2),
        "Close Strength %": round(close_pos, 1),
        "RVOL": f"{avg_sector_rvol}x",
        "Momentum Score": total_score,
        "Tomorrow's Advance Setup": signal,
    })

  df_sec = (
      pd.DataFrame(sector_records)
      .sort_values(by="Momentum Score", ascending=False)
      .reset_index(drop=True)
  )
  df_stk = (
      pd.DataFrame(stock_records)
      .sort_values(by="Stock Score", ascending=False)
      .reset_index(drop=True)
  )
  return df_sec, df_stk, round(nifty_chg, 2)


df_sectors, df_stocks, nifty_day_chg = fetch_drilldown_sector_data()

if df_sectors is not None and not df_sectors.empty:
  # ---------------------------------------------------------
  # 1. TOMORROW'S ADVANCE SECTOR RADAR
  # ---------------------------------------------------------
  st.markdown("---")
  st.subheader("🔮 Tomorrow's Advance Sector Radar (EOD Institutional Carry-Forward)")
  st.caption(
      f"Evaluates Relative Strength against Nifty 50 ({nifty_day_chg:+.2f}%),"
      " final-hour closing range strength, and constituent stock volume"
      " expansion."
  )

  top_2 = df_sectors.head(2)
  col1, col2 = st.columns(2)

  with col1:
    s1 = top_2.iloc[0]
    top_s1_stocks = ", ".join(
        df_stocks[df_stocks["Sector"] == s1["Sector"]].head(3)["Stock"].tolist()
    )
    st.success(
        f"**#1 PRIME SECTOR FOR TOMORROW: {s1['Sector']}**\n\n"
        f"• **Score:** {s1['Momentum Score']}/100 | **RS vs Nifty:** {s1['RS vs Nifty %']:+.2f}%\n"
        f"• **Closing Strength:** Closed in top {100 - s1['Close Strength %']:.0f}% of daily range ({s1['RVOL']} Vol)\n"
        f"• **Top Leaders Inside:** **{top_s1_stocks}**"
    )

  if len(top_2) > 1:
    with col2:
      s2 = top_2.iloc[1]
      top_s2_stocks = ", ".join(
          df_stocks[df_stocks["Sector"] == s2["Sector"]].head(3)["Stock"].tolist()
      )
      st.info(
          f"**#2 SECONDARY WATCH SECTOR: {s2['Sector']}**\n\n"
          f"• **Score:** {s2['Momentum Score']}/100 | **RS vs Nifty:** {s2['RS vs Nifty %']:+.2f}%\n"
          f"• **Closing Strength:** Closed at {s2['Close Strength %']:.0f}% of daily range ({s2['RVOL']} Vol)\n"
          f"• **Top Leaders Inside:** **{top_s2_stocks}**"
      )

  st.markdown("---")

  # ---------------------------------------------------------
  # 2. INTERACTIVE COLOR-BAND SLIDER & QUICK COLOR PICKER
  # ---------------------------------------------------------
  st.subheader("🎨 Interactive Color-Band & Momentum Filter")
  st.caption(
      "Click a Color Zone button OR drag the scrollable Day Change % range"
      " slider below to immediately isolate matching sectors & stocks:"
  )

  col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
  if "chg_range" not in st.session_state:
    st.session_state.chg_range = (-5.0, 5.0)

  with col_btn1:
    if st.button("🟩 Dark Green (+1% to +5%)", use_container_width=True):
      st.session_state.chg_range = (1.0, 5.0)
  with col_btn2:
    if st.button("🟢 Light Green (0% to +1%)", use_container_width=True):
      st.session_state.chg_range = (0.0, 1.0)
  with col_btn3:
    if st.button("🟥 Deep Red (-5% to -1%)", use_container_width=True):
      st.session_state.chg_range = (-5.0, -1.0)
  with col_btn4:
    if st.button("🔄 Show All Colors (-5% to +5%)", use_container_width=True):
      st.session_state.chg_range = (-5.0, 5.0)

  min_c, max_c = st.slider(
      "🎚️ Scrollable Day Change % Color Spectrum (-5% Red ◀━━━ 0% ━━━▶ +5% Green):",
      min_value=-5.0,
      max_value=5.0,
      value=st.session_state.chg_range,
      step=0.25,
      format="%+.2f%%",
  )

  # Filter stocks matching the chosen color band
  filtered_stocks = df_stocks[
      (df_stocks["Day Change %"] >= min_c) & (df_stocks["Day Change %"] <= max_c)
  ].copy()

  # ---------------------------------------------------------
  # 3. INTERACTIVE DRILL-DOWN SECTOR -> STOCK HEATMAP
  # ---------------------------------------------------------
  st.subheader("🗺️ Interactive Sector → Stock Drill-Down Heatmap")
  st.caption(
      "💡 Shows nested stocks inside every sector. Click any Sector box to"
      " zoom inside; click the top bar to zoom out."
  )

  if not filtered_stocks.empty:
    fig = px.treemap(
        filtered_stocks,
        path=[px.Constant("ALL NSE SECTORS"), "Sector", "Stock"],
        values="BoxSize",
        color="Day Change %",
        color_continuous_scale=["#B71C1C", "#EF5350", "#263238", "#66BB6A", "#1B5E20"],
        color_continuous_midpoint=0,
        range_color=[-3.0, 3.0],
        hover_data=["LTP", "RS vs Nifty %", "Close Strength %", "RVOL", "Stock Score"],
    )
    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>%{color:+.2f}%",
        textfont=dict(size=13),
        maxdepth=3,
    )
    fig.update_layout(
        template="plotly_dark",
        height=580,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Display instant matching stocks table for the selected color band
    st.subheader(
        f"📋 Matching Sectors & Stocks in Selected Color Range ({min_c:+.2f}% to {max_c:+.2f}%) — {len(filtered_stocks)} Stocks"
    )
    st.dataframe(
        filtered_stocks.drop(columns=["BoxSize"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stock Score": st.column_config.ProgressColumn(
                "Stock Score", format="%.1f", min_value=0, max_value=100
            ),
            "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
            "RVOL": st.column_config.NumberColumn(format="%.2fx"),
        },
    )
  else:
    st.info(
        f"No stocks currently fall between {min_c:+.2f}% and {max_c:+.2f}%."
        " Widen the slider or click 'Show All Colors'."
    )

  st.markdown("---")

  # ---------------------------------------------------------
  # 4. INTERACTIVE SECTOR INSPECTOR & FULL RANKING
  # ---------------------------------------------------------
  st.subheader("🔍 Inspect Constituent Stocks Inside Any Sector")
  selected_sector = st.selectbox(
      "Choose a Sector to view all constituent stocks & tomorrow's breakout setups:",
      df_sectors["Sector"].tolist(),
      index=0,
  )

  sector_stocks_view = df_stocks[df_stocks["Sector"] == selected_sector].drop(
      columns=["Sector", "BoxSize"]
  )
  st.dataframe(
      sector_stocks_view,
      use_container_width=True,
      hide_index=True,
      column_config={
          "Stock Score": st.column_config.ProgressColumn(
              "Stock Score", format="%.1f", min_value=0, max_value=100
          ),
          "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
          "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
          "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
          "RVOL": st.column_config.NumberColumn(format="%.2fx"),
      },
  )

  st.markdown("---")
  st.subheader("📊 Full Sector Ranking Table")
  st.dataframe(
      df_sectors,
      use_container_width=True,
      hide_index=True,
      column_config={
          "Momentum Score": st.column_config.ProgressColumn(
              "Momentum Score", format="%.1f", min_value=0, max_value=100
          ),
          "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
          "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
          "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
      },
  )
else:
  st.warning("⚠️ Unable to fetch live sectoral index data. Please click Refresh Live Data.")
