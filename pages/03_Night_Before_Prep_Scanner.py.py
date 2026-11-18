from datetime import datetime, time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Advance Night-Before Institutional Prep Scanner", layout="wide"
)
st.title(
    "🌙 Advance Night-Before Institutional Prep & Smart Money Coiling Watchlist"
)
st.markdown(
    "**Expert Advance Engine:** Pre-scans the Indian equity market by"
    " connecting tight multi-day accumulation coils with **Smart Money"
    " Institutional Flows** and **Sector Classifications** *before* the market"
    " opens."
)

# ---------------------------------------------------------
# 1. ADVANCED SCANNER CONTROLS
# ---------------------------------------------------------
col_c1, col_c2 = st.columns([4, 1])
with col_c2:
  if st.button("🔄 Run Advance Smart Money Prep Scan"):
    st.cache_data.clear()
    st.toast(
        "Scanning Indian market for smart money accumulation & coiling..."
    )
    st.rerun()

# Sector Mapping Dictionary (Consistent with Smart Money Pulse & Global Taxonomy)
SECTOR_MAPPING = {
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "INDUSINDBK.NS",
        "PNB.NS",
        "CANBK.NS",
        "MUTHOOTFIN.NS",
    ],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["MARUTI.NS", "BAJAJFINSV.NS", "M&M.NS"],
    "Energy & Oil": [
        "RELIANCE.NS",
        "ONGC.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "COALINDIA.NS",
        "ATGL.NS",
    ],
    "Metals & Mining": ["TATASTEEL.NS", "ADANIENT.NS"],
    "Consumer & Retail": [
        "ITC.NS",
        "HINDUNILVR.NS",
        "TITAN.NS",
        "ASIANPAINT.NS",
        "ETERNAL.NS",
        "HONASA.NS",
    ],
    "Infrastructure & Industrials": [
        "LT.NS",
        "ADANIPORTS.NS",
        "GRASIM.NS",
        "SUPREMEIND.NS",
    ],
    "Healthcare & Pharma": ["SUNPHARMA.NS", "MAXHEALTH.NS", "DEEPAKFERT.NS"],
    "Financial Services": ["BAJFINANCE.NS", "LICI.NS", "ANGELONE.NS"],
}


# ---------------------------------------------------------
# 2. ADVANCED MARKET-WIDE PRE-BREAKOUT + SECTOR SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def run_advance_night_prep():
  watchlist_rows = []

  universe_map = {
      sym: sector for sector, symbols in SECTOR_MAPPING.items() for sym in symbols
  }

  for symbol, sector in universe_map.items():
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="30d", interval="1d", auto_adjust=True)
      if df is None or df.empty or len(df) < 20:
        continue

      df["Range"] = df["High"] - df["Low"]
      avg_range = df["Range"].rolling(10).mean().iloc[-1]
      recent_range = df["Range"].iloc[-1]

      avg_vol = df["Volume"].rolling(15).mean().iloc[-1]
      recent_vol = df["Volume"].iloc[-1]

      close_price = float(df["Close"].iloc[-1])
      ltp = (
          float(ticker.history(period="1d")["Close"].iloc[-1])
          if not ticker.history(period="1d").empty
          else close_price
      )

      prev_close = float(df["Close"].iloc[-2])
      change_pct = round(((close_price - prev_close) / prev_close) * 100, 2)

      turnover_cr = round((close_price * recent_vol) / 10000000, 2)
      net_flow_cr = round(
          turnover_cr * (change_pct / 100) * (recent_vol / avg_vol), 2
      )

      is_tight_coil = recent_range <= (1.3 * avg_range)
      is_volume_steady = recent_vol >= (0.6 * avg_vol)

      if is_tight_coil and is_volume_steady:
        smart_signal = (
            "🟢 Smart Inflow (Accumulation)"
            if net_flow_cr > 0
            else "🟡 Coiling / Neutral"
        )

        advance_buy = round(close_price * 0.995, 2)
        stop_loss = round(close_price * 0.978, 2)
        target_1 = round(close_price * 1.025, 2)
        target_2 = round(close_price * 1.050, 2)

        watchlist_rows.append({
            "Symbol": symbol.replace(".NS", ""),
            "Sector": sector,
            "LTP": round(ltp, 2),
            "Close": round(close_price, 2),
            "Change_%": change_pct,
            "Net Flow (Cr)": net_flow_cr,
            "Smart Signal": smart_signal,
            "Advance_Buy": advance_buy,
            "Stop_Loss": stop_loss,
            "Target_1": target_1,
            "Target_2": target_2,
            "Range_Ratio": round(recent_range / avg_range, 2),
        })
    except Exception:
      continue

  df_res = pd.DataFrame(watchlist_rows)
  if not df_res.empty:
    df_res = df_res.sort_values(by="Net Flow (Cr)", ascending=False)
    df_res = df_res[
        [
            "Symbol",
            "Sector",
            "LTP",
            "Close",
            "Change_%",
            "Net Flow (Cr)",
            "Smart Signal",
            "Advance_Buy",
            "Stop_Loss",
            "Target_1",
            "Target_2",
            "Range_Ratio",
        ]
    ]
  return df_res


# ---------------------------------------------------------
# 3. RENDER ADVANCE PREP TABLE WITH SECTOR FILTER
# ---------------------------------------------------------
df_prep = run_advance_night_prep()

# Sync computed watchlist to session state for cross-page matching
if not df_prep.empty:
  st.session_state["night_before_watchlist"] = df_prep["Symbol"].tolist()

if df_prep is None or df_prep.empty:
  st.warning("⚠️ No tight accumulation coils detected. Run advance scan above.")
else:
  st.subheader(
      "🎯 Smart Money Pre-Market Setups Connected with Sector Flows"
  )

  all_sectors = ["All Sectors"] + sorted(df_prep["Sector"].unique().tolist())
  selected_sector = st.selectbox(
      "🔍 Filter Watchlist by Sector Connection:", all_sectors
  )

  if selected_sector != "All Sectors":
    df_filtered = df_prep[df_prep["Sector"] == selected_sector]
  else:
    df_filtered = df_prep

  st.dataframe(
      df_filtered.style.format({
          "LTP": "₹{:,.2f}",
          "Close": "₹{:,.2f}",
          "Change_%": "{:+.2f}%",
          "Net Flow (Cr)": "₹{:,.2f} Cr",
          "Advance_Buy": "₹{:,.2f}",
          "Stop_Loss": "₹{:,.2f}",
          "Target_1": "₹{:,.2f}",
          "Target_2": "₹{:,.2f}",
      }),
      use_container_width=True,
  )

  st.markdown("---")
  st.subheader("📋 Detailed Sector-Connected Execution Blueprints")

  for idx, row in df_filtered.head(5).iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

      with c1:
        st.markdown(f"### **{row['Symbol']}**")
        st.caption(f"📂 **Sector:** {row['Sector']}")
        st.metric(
            label="Live LTP / Flow",
            value=f"₹{row['LTP']}",
            delta=f"Net Flow: ₹{row['Net Flow (Cr)']} Cr",
        )

      with c2:
        st.markdown("**Advance Entry Levels**")
        st.write(f"🔹 **Advance Buy:** ₹{row['Advance_Buy']}")
        st.write(f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']}")

      with c3:
        st.markdown("**Target Objectives**")
        st.write(f"🎯 **Target 1 (+2.5%):** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2 (+5.0%):** ₹{row['Target_2']}")

      with c4:
        st.markdown("**Action Plan**")
        st.success(f"✅ **{row['Smart Signal']}**")
        if st.button(
            f"📋 Copy Payload ({row['Symbol']})", key=f"adv_{row['Symbol']}"
        ):
          st.toast(
              f"Copied {row['Symbol']} ({row['Sector']}) blueprint! Buy:"
              f" ₹{row['Advance_Buy']} | T1: ₹{row['Target_1']}"
          )

    st.markdown("---")
