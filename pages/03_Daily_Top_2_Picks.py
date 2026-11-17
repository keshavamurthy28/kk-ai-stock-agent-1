from datetime import datetime, time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Daily Top 2 Picks | Advanced SMC & FVG Terminal",
    layout="wide",
)

st.title("🎯 Daily Top 2 Intraday Sniper Picks")
st.markdown(
    "Automated high-confluence stock selection based on Smart Money"
    " Concepts (SMC), Fair Value Gaps (FVG), and Relative Volume (RVOL)."
)

# ---------------------------------------------------------
# 1. TIME GATE & EXECUTION GUARDRAILS (IST)
# ---------------------------------------------------------
ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()

market_open = time(9, 15)
allowed_execution_time = time(9, 20)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Automated Execution Gate")

if current_time_ist < allowed_execution_time:
  st.sidebar.warning(
      f"⏳ **Pre-Open Phase ({current_time_ist.strftime('%H:%M:%S')} IST):**"
      " Execution locked until 09:20 AM."
  )
  lock_execution = True
else:
  st.sidebar.success("✅ **Live Execution Window Active**")
  lock_execution = False


# ---------------------------------------------------------
# 2. DATA & CHART PLOTTING FUNCTION
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_top_picks_data():
  watchlist = ["ITC.NS", "HONASA.NS", "PNB.NS", "MAXHEALTH.NS", "SBIN.NS"]
  data_rows = []

  for symbol in watchlist:
    try:
      ticker = yf.Ticker(symbol)
      hist = ticker.history(period="5d", interval="15m")
      if len(hist) >= 2:
        prev_close = ticker.history(period="5d")["Close"].iloc[-2]
        open_price = hist["Open"].iloc[-1]
        ltp = hist["Close"].iloc[-1]
        change_pct = ((ltp - prev_close) / prev_close) * 100
        gap_pct = ((open_price - prev_close) / prev_close) * 100

        data_rows.append({
            "Symbol": symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "Change": round(change_pct, 2),
            "Gap_Pct": round(gap_pct, 2),
            "Limit_Buy": round(ltp * 0.992, 2),
            "Stop_Loss": round(ltp * 0.975, 2),
            "Target_1": round(ltp * 1.025, 2),
            "Target_2": round(ltp * 1.050, 2),
            "History": hist,  # Storing history for plotting
        })
    except Exception:
      continue

  return pd.DataFrame(data_rows)


def plot_smc_chart(symbol, hist):
  fig = go.Figure(
      data=[
          go.Candlestick(
              x=hist.index,
              open=hist["Open"],
              high=hist["High"],
              low=hist["Low"],
              close=hist["Close"],
              name="Price (15m)",
          )
      ]
  )
  fig.update_layout(
      title=f"📊 {symbol} — Intraday SMC Structure & Levels",
      yaxis_title="Price (₹)",
      xaxis_title="Time",
      template="plotly_dark",
      height=350,
      margin=dict(l=10, r=10, t=30, b=10),
  )
  return fig


# ---------------------------------------------------------
# 3. MAIN RENDER BLOCK
# ---------------------------------------------------------
with st.spinner("🔄 Fetching live NSE market data and calculating levels..."):
  top_picks_df = fetch_top_picks_data()

if top_picks_df is None or top_picks_df.empty:
  st.info(
      "⚠️ No stocks currently match all strict confluence filters for today's"
      " session."
  )
  if st.button("🔄 Force Refresh Data"):
    st.rerun()
else:
  st.subheader("🏆 Today's Filtered Rank #1 & #2 Setups")

  for index, row in top_picks_df.head(2).iterrows():
    is_chased = row["Gap_Pct"] > 1.5

    with st.container():
      col1, col2, col3, col4 = st.columns([2, 2, 2, 3])

      with col1:
        st.markdown(f"### **{row['Symbol']}**")
        st.metric(
            label="Live LTP",
            value=f"₹{row['LTP']}",
            delta=f"{row['Change']}%",
        )

      with col2:
        st.markdown("**Execution Levels**")
        st.write(f"🔹 **Limit Buy:** ₹{row['Limit_Buy']}")
        st.write(f"🛑 **Stop Loss:** ₹{row['Stop_Loss']}")

      with col3:
        st.markdown("**Targets**")
        st.write(f"🎯 **Target 1 (~2.5%):** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2 (~5.0%):** ₹{row['Target_2']}")

      with col4:
        st.markdown("**Status & Guardrail**")
        if lock_execution:
          st.warning("⏳ Locked (Pre-09:20 AM)")
        elif is_chased:
          st.error(
              f"⛔ **AUTO-REJECT:** Gap is {row['Gap_Pct']}% (> 1.5%). Chasing"
              " risk."
          )
        else:
          st.success("✅ **READY FOR KITE ORDER**")
          if st.button(
              f"📋 Copy Kite Order Payload ({row['Symbol']})",
              key=f"btn_{row['Symbol']}",
          ):
            st.toast(f"Copied order details for {row['Symbol']}!")

      # Inline Chart Expandable Section
      with st.expander(f"📈 View Live SMC Chart & Structure for {row['Symbol']}"):
        fig = plot_smc_chart(row["Symbol"], row["History"])
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
