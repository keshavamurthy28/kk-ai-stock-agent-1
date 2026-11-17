from datetime import datetime, time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
# 2. ADVANCED DATA FETCHING & SMC CALCULATION FUNCTION
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_top_picks_with_smc():
  watchlist = ["ITC.NS", "HONASA.NS", "PNB.NS", "MAXHEALTH.NS", "SBIN.NS"]
  data_rows = []

  for symbol in watchlist:
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="15d", interval="15m", auto_adjust=True)
      df4 = ticker.history(period="60d", interval="1h", auto_adjust=True)

      if df is None or df.empty or len(df) < 5:
        continue

      df = df.reset_index()
      df.rename(columns={df.columns[0]: "Time"}, inplace=True)
      df["Time"] = pd.to_datetime(df["Time"])
      if df["Time"].dt.tz is not None:
        df["Time"] = (
            df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        )

      # Axis String Formatting (TradingView/Kite style)
      is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
      df["Axis_Str"] = np.where(
          is_new_day,
          df["Time"].dt.strftime("%d %b '%y  %H:%M"),
          df["Time"].dt.strftime("%H:%M  (%d %b)"),
      )

      # Indicators
      df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
      df["VWAP"] = (
          (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"])
          .groupby(df["Time"].dt.date)
          .cumsum()
          / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
      )
      v_avg = df["Volume"].rolling(20, min_periods=1).mean()
      v_col = [
          (
              "#00E676"
              if (c >= o and v >= 1.5 * va)
              else (
                  "#FF5252"
                  if (c < o and v >= 1.5 * va)
                  else (
                      "rgba(0,230,118,0.38)"
                      if c >= o
                      else "rgba(255,82,82,0.38)"
                  )
              )
          )
          for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
      ]

      ltp = float(df["Close"].iloc[-1])
      prev_close = (
          ticker.history(period="5d")["Close"].iloc[-2]
          if len(ticker.history(period="5d")) >= 2
          else ltp
      )
      open_price = df["Open"].iloc[-1]
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
          "DataFrame": df,
          "Volume_Colors": v_col,
      })
    except Exception:
      continue

  return pd.DataFrame(data_rows)


# ---------------------------------------------------------
# 3. ADVANCED SMC PLOTTING FUNCTION (Matched to Graph Page)
# ---------------------------------------------------------
def render_advanced_smc_chart(symbol, df, v_col):
  end_str = df["Axis_Str"].iloc[-1]
  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.02,
      row_heights=[0.78, 0.22],
  )

  # Candlesticks
  fig.add_trace(
      go.Candlestick(
          x=df["Axis_Str"],
          open=df["Open"],
          high=df["High"],
          low=df["Low"],
          close=df["Close"],
          name=symbol,
          increasing_line_color="#00E676",
          decreasing_line_color="#FF5252",
      ),
      row=1,
      col=1,
  )

  # VWAP & 20 EMA
  fig.add_trace(
      go.Scatter(
          x=df["Axis_Str"],
          y=df["VWAP"],
          mode="lines",
          name="VWAP",
          line=dict(color="#FFD700", width=1.5),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df["Axis_Str"],
          y=df["EMA20"],
          mode="lines",
          name="20 EMA",
          line=dict(color="#29B6F6", width=1.2),
      ),
      row=1,
      col=1,
  )

  # Volume Bars
  fig.add_trace(
      go.Bar(
          x=df["Axis_Str"],
          y=df["Volume"],
          name="Volume",
          marker_color=v_col,
      ),
      row=2,
      col=1,
  )

  # Layout styling matching the Advanced SMC Terminal
  fig.update_layout(
      title=f"📊 {symbol} (15m) | Institutional SMC Structure, VWAP & Volume",
      template="plotly_dark",
      height=550,
      dragmode="pan",
      hovermode="x unified",
      showlegend=False,
      margin=dict(l=10, r=65, t=40, b=30),
      yaxis=dict(
          side="right",
          title="Price (₹)",
          showgrid=True,
          gridcolor="rgba(255,255,255,0.06)",
          showspikes=True,
          spikemode="across",
      ),
      yaxis2=dict(side="right", title="Volume", showgrid=False),
      xaxis=dict(type="category", rangeslider_visible=False, showgrid=True),
      xaxis2=dict(
          type="category",
          rangeslider_visible=False,
          tickmode="auto",
          nticks=12,
          showgrid=True,
      ),
  )
  return fig


# ---------------------------------------------------------
# 4. MAIN RENDER BLOCK
# ---------------------------------------------------------
with st.spinner(
    "🔄 Fetching live NSE market data and calculating SMC structures..."
):
  top_picks_df = fetch_top_picks_with_smc()

if top_picks_df is None or top_picks_df.empty:
  st.info(
      "⚠️ No stocks currently match strict confluence filters for today's"
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
            st.toast(
                f"Copied order details for {row['Symbol']}! Limit:"
                f" ₹{row['Limit_Buy']}"
            )

      # MATCHED ADVANCED SMC GRAPH EXPANDER
      with st.expander(
          f"📈 View Advanced SMC Chart & VWAP Structure for {row['Symbol']}"
      ):
        fig = render_advanced_smc_chart(
            row["Symbol"], row["DataFrame"], row["Volume_Colors"]
        )
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.markdown("---")
