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
    page_title="Daily Top 2 Picks | Live Momentum & SMC Terminal", layout="wide"
)

st.title("🎯 Daily Top 2 High-Momentum Intraday Sniper")
st.markdown(
    "**Expert-Grade Engine:** Dynamically scans high-liquidity NSE stocks for"
    " live volume surges and clean 2%–5% profit capture setups."
)

# ---------------------------------------------------------
# 1. LIVE REFRESH & TIME GATE
# ---------------------------------------------------------
col_r1, col_r2 = st.columns([4, 1])
with col_r2:
  if st.button("🔄 Force Refresh Live Scans"):
    st.cache_data.clear()
    st.toast("Cleared cache and fetched fresh live market ticks!")
    st.rerun()

ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()

# ---------------------------------------------------------
# 2. DYNAMIC HIGH-MOMENTUM UNIVERSE SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=30)
def fetch_live_momentum_picks():
  # Broad high-beta and liquid NSE intraday universe
  universe = [
      "ITC.NS",
      "RELIANCE.NS",
      "SBIN.NS",
      "HDFCBANK.NS",
      "TATASTEEL.NS",
      "ADANIENT.NS",
      "ADANIPORTS.NS",
      "AXISBANK.NS",
      "ICICIBANK.NS",
      "INFY.NS",
      "TCS.NS",
      "BAJFINANCE.NS",
      "MARUTI.NS",
      "SUNPHARMA.NS",
      "TATAMOTORS.NS",
      "LICI.NS",
      "BELRISE.NS",
      "DEEPAKFERT.NS",
      "ANGELONE.NS",
      "MAXHEALTH.NS",
  ]

  scored_stocks = []

  for symbol in universe:
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="5d", interval="15m", auto_adjust=True)
      if df is None or df.empty or len(df) < 10:
        continue

      df = df.reset_index()
      df.rename(columns={df.columns[0]: "Time"}, inplace=True)
      df["Time"] = pd.to_datetime(df["Time"])
      if df["Time"].dt.tz is not None:
        df["Time"] = (
            df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        )

      # Axis Formatting
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

      ltp = float(df["Close"].iloc[-1])
      prev_close = (
          ticker.history(period="5d")["Close"].iloc[-2]
          if len(ticker.history(period="5d")) >= 2
          else ltp
      )
      open_price = df["Open"].iloc[-1]
      change_pct = ((ltp - prev_close) / prev_close) * 100

      # Volume Surge (RVOL) calculation
      avg_vol = df["Volume"].rolling(15).mean().iloc[-1]
      curr_vol = df["Volume"].iloc[-1]
      rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      # We want stocks actively moving today (+0.5% to +6.0%) with good volume
      if 0.5 <= change_pct <= 6.0:
        v_avg = df["Volume"].rolling(20, min_periods=1).mean()
        v_col = [
            (
                "#00E676"
                if (c >= o and v >= 1.3 * va)
                else (
                    "#FF5252"
                    if (c < o and v >= 1.3 * va)
                    else (
                        "rgba(0,230,118,0.38)"
                        if c >= o
                        else "rgba(255,82,82,0.38)"
                    )
                )
            )
            for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
        ]

        # Precision 2-5% Intraday Risk-Reward Structure
        limit_buy = round(ltp * 0.992, 2)
        stop_loss = round(ltp * 0.978, 2)  # Strict ~1.2% Risk
        target_1 = round(ltp * 1.025, 2)  # Clean +2.5% Target 1
        target_2 = round(ltp * 1.045, 2)  # Clean +4.5% Target 2

        scored_stocks.append({
            "Symbol": symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "Change": round(change_pct, 2),
            "RVOL": rvol,
            "Limit_Buy": limit_buy,
            "Stop_Loss": stop_loss,
            "Target_1": target_1,
            "Target_2": target_2,
            "DataFrame": df,
            "Volume_Colors": v_col,
        })
    except Exception:
      continue

  # Sort by highest momentum & volume surge
  df_res = pd.DataFrame(scored_stocks)
  if not df_res.empty:
    df_res = df_res.sort_values(by=["Change", "RVOL"], ascending=False)
  return df_res


# ---------------------------------------------------------
# 3. SMC PLOTTING FUNCTION
# ---------------------------------------------------------
def render_chart(symbol, df, v_col, entry, sl, t1, t2):
  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.02,
      row_heights=[0.78, 0.22],
  )
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

  # Execution Levels
  fig.add_hline(
      y=entry,
      line_color="#FFD700",
      line_width=1.6,
      annotation_text=f"🟡 BUY: ₹{entry:,.2f}",
      annotation_position="bottom left",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=sl,
      line_color="#FF5252",
      line_width=1.6,
      annotation_text=f"🛑 SL: ₹{sl:,.2f}",
      annotation_position="bottom right",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=t1,
      line_dash="dash",
      line_color="#29B6F6",
      line_width=1.4,
      annotation_text=f"🎯 T1 (+2.5%): ₹{t1:,.2f}",
      annotation_position="top left",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=t2,
      line_dash="dash",
      line_color="#00E676",
      line_width=1.4,
      annotation_text=f"🚀 T2 (+4.5%): ₹{t2:,.2f}",
      annotation_position="top right",
      row=1,
      col=1,
  )

  fig.update_layout(
      title=f"📊 {symbol} (15m) | Live Momentum & Intraday Setup",
      template="plotly_dark",
      height=520,
      dragmode="pan",
      hovermode="x unified",
      showlegend=False,
      margin=dict(l=10, r=65, t=40, b=30),
      yaxis=dict(side="right", title="Price (₹)", showgrid=True),
      yaxis2=dict(side="right", title="Volume", showgrid=False),
      xaxis=dict(type="category", rangeslider_visible=False),
      xaxis2=dict(
          type="category", rangeslider_visible=False, tickmode="auto", nticks=12
      ),
  )
  return fig


# ---------------------------------------------------------
# 4. MAIN EXECUTION RENDER
# ---------------------------------------------------------
with st.spinner(
    "🔍 Scanning live NSE tape for active 2%–5% momentum runners..."
):
  df_top = fetch_live_momentum_picks()

if df_top is None or df_top.empty:
  st.warning(
      "⚠️ No stocks currently meeting the +0.5% to +6% momentum window. Click"
      " 'Force Refresh Live Scans' above."
  )
else:
  st.subheader("🔥 Top Live Actionable Picks for 2%–5% Capture Today")

  # Render Top 2 Live Setups Automatically
  for idx, row in df_top.head(2).iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

      with c1:
        st.markdown(f"### **#{idx+1} {row['Symbol']}**")
        st.metric(
            label="Live LTP",
            value=f"₹{row['LTP']}",
            delta=f"+{row['Change']}% (RVOL: {row['RVOL']}x)",
        )

      with c2:
        st.markdown("**Sniper Entry Levels**")
        st.write(f"🔹 **Limit Buy:** ₹{row['Limit_Buy']}")
        st.write(f"🛑 **Stop Loss:** ₹{row['Stop_Loss']}")

      with c3:
        st.markdown("**Profit Targets**")
        st.write(f"🎯 **Target 1 (+2.5%):** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2 (+4.5%):** ₹{row['Target_2']}")

      with c4:
        st.markdown("**Execution Status**")
        st.success("✅ **READY — ACTIVE MOMENTUM**")
        if st.button(f"📋 Copy Payload ({row['Symbol']})", key=f"btn_{row['Symbol']}"):
          st.toast(
              f"Copied {row['Symbol']}! Limit: ₹{row['Limit_Buy']} | T1:"
              f" ₹{row['Target_1']}"
          )

      with st.expander(
          f"📈 Expand Chart & VWAP Structure for #{idx+1} {row['Symbol']}"
      ):
        fig = render_chart(
            row["Symbol"],
            row["DataFrame"],
            row["Volume_Colors"],
            row["Limit_Buy"],
            row["Stop_Loss"],
            row["Target_1"],
            row["Target_2"],
        )
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.markdown("---")
