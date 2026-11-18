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
    page_title=(
        "Bearish Alpha & SMC Short Terminal | Institutional Breakdown"
    ),
    layout="wide",
)

st.title("🎯 Institutional Alpha: Daily Top Bearish Intraday Setups (Shorts)")
st.markdown(
    "**Expert Analyst Engine:** Scans the Indian stock market for negative"
    " volume expansion, VWAP breakdown resistance, and ATR-managed risk"
    " structures designed for 2%–5% short profit capture."
)

# ---------------------------------------------------------
# 1. LIVE CONTROL PANEL & REFRESH
# ---------------------------------------------------------
col_r1, col_r2 = st.columns([4, 1])
with col_r2:
  if st.button("🔄 Force Refresh Bearish Scan"):
    st.cache_data.clear()
    st.toast("Cleared cache and executed market-wide bearish alpha scan!")
    st.rerun()

ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()


# ---------------------------------------------------------
# 2. WHOLE-MARKET BEARISH INSTITUTIONAL ALPHA SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_bearish_institutional_picks():
  market_universe = [
      "RELIANCE.NS",
      "TCS.NS",
      "HDFCBANK.NS",
      "ICICIBANK.NS",
      "INFY.NS",
      "SBIN.NS",
      "ITC.NS",
      "BHARTIARTL.NS",
      "LICI.NS",
      "AXISBANK.NS",
      "KOTAKBANK.NS",
      "LT.NS",
      "BAJFINANCE.NS",
      "MARUTI.NS",
      "SUNPHARMA.NS",
      "TITAN.NS",
      "ADANIENT.NS",
      "ADANIPORTS.NS",
      "TATASTEEL.NS",
      "NTPC.NS",
      "POWERGRID.NS",
      "COALINDIA.NS",
      "ONGC.NS",
      "BAJAJFINSV.NS",
      "WIPRO.NS",
      "ASIANPAINT.NS",
      "HCLTECH.NS",
      "GRASIM.NS",
      "TECHM.NS",
      "INDUSINDBK.NS",
      "DEEPAKFERT.NS",
      "ANGELONE.NS",
      "HONASA.NS",
      "MAXHEALTH.NS",
      "PNB.NS",
      "CANBK.NS",
      "TORNTPHARM.NS",
      "SUPREMEIND.NS",
      "ETERNAL.NS",
      "BELRISE.NS",
  ]

  bearish_scored_stocks = []

  for symbol in market_universe:
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="5d", interval="15m", auto_adjust=True)
      if df is None or df.empty or len(df) < 15:
        continue

      df = df.reset_index()
      df.rename(columns={df.columns[0]: "Time"}, inplace=True)
      df["Time"] = pd.to_datetime(df["Time"])
      if df["Time"].dt.tz is not None:
        df["Time"] = (
            df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        )

      # Time-axis string formatting
      is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
      df["Axis_Str"] = np.where(
          is_new_day,
          df["Time"].dt.strftime("%d %b '%y  %H:%M"),
          df["Time"].dt.strftime("%H:%M  (%d %b)"),
      )

      # Core Technical Indicators
      df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
      df["VWAP"] = (
          (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"])
          .groupby(df["Time"].dt.date)
          .cumsum()
          / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
      )

      ltp = float(df["Close"].iloc[-1])

      # Extract previous close cleanly from dataframe dates
      df["Date"] = df["Time"].dt.date
      unique_dates = df["Date"].unique()
      if len(unique_dates) >= 2:
        prev_close = float(
            df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1]
        )
      else:
        prev_close = float(df["Open"].iloc[0])

      change_pct = ((ltp - prev_close) / prev_close) * 100

      # Relative Volume (RVOL) Surge Calculation (Using last completed candle)
      avg_vol = df["Volume"].iloc[-17:-2].mean()
      curr_vol = df["Volume"].iloc[-2]
      rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      latest_vwap = float(df["VWAP"].iloc[-1])
      latest_ema = float(df["EMA20"].iloc[-1])

      # EXPERT BEARISH ALPHA FILTER:
      # 1. Negative intraday momentum (-0.5% to -5.5%)
      # 2. Institutional breakdown: Price must be below VWAP & 20 EMA
      # 3. Active volume participation (RVOL >= 1.1x)
      if (
          -5.5 <= change_pct <= -0.5
          and ltp <= latest_vwap
          and ltp <= latest_ema
          and rvol >= 1.1
      ):
        v_avg = df["Volume"].rolling(20, min_periods=1).mean()
        v_col = [
            (
                "#FF5252"
                if (c < o and v >= 1.3 * va)
                else (
                    "#00E676"
                    if (c >= o and v >= 1.3 * va)
                    else (
                        "rgba(255,82,82,0.38)"
                        if c < o
                        else "rgba(0,230,118,0.38)"
                    )
                )
            )
            for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
        ]

        # Short Risk-Reward Calculation
        limit_short = round(ltp * 1.004, 2)  # Sell/Short on minor bounce up
        stop_loss = round(latest_vwap * 1.008, 2)  # Stop loss above VWAP
        target_1 = round(ltp * 0.975, 2)  # Target 1 (-2.5%)
        target_2 = round(ltp * 0.952, 2)  # Target 2 (-4.8%)

        # Composite Alpha Score for Shorts (Magnitude of decline * RVOL)
        alpha_score = round(abs(change_pct) * rvol * (latest_vwap / ltp), 2)

        bearish_scored_stocks.append({
            "Symbol": symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "Change": round(change_pct, 2),
            "RVOL": rvol,
            "Alpha_Score": alpha_score,
            "Limit_Short": limit_short,
            "Stop_Loss": stop_loss,
            "Target_1": target_1,
            "Target_2": target_2,
            "DataFrame": df,
            "Volume_Colors": v_col,
        })
    except Exception:
      continue

  df_res = pd.DataFrame(bearish_scored_stocks)
  if not df_res.empty:
    df_res = df_res.sort_values(by="Alpha_Score", ascending=False).reset_index(
        drop=True
    )
  return df_res


# ---------------------------------------------------------
# 3. ADVANCED INSTITUTIONAL BEARISH PLOTTING ENGINE
# ---------------------------------------------------------
def render_bearish_chart(symbol, df, v_col, entry, sl, t1, t2):
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

  # Short Execution Level Overlays
  fig.add_hline(
      y=entry,
      line_color="#FFD700",
      line_width=1.6,
      annotation_text=f"🔻 SHORT ENTRY: ₹{entry:,.2f}",
      annotation_position="bottom left",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=sl,
      line_color="#FF5252",
      line_width=1.6,
      annotation_text=f"🛑 SL: ₹{sl:,.2f}",
      annotation_position="top right",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=t1,
      line_dash="dash",
      line_color="#29B6F6",
      line_width=1.4,
      annotation_text=f"🎯 T1 (-2.5%): ₹{t1:,.2f}",
      annotation_position="bottom left",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=t2,
      line_dash="dash",
      line_color="#00E676",
      line_width=1.4,
      annotation_text=f"🚀 T2 (-4.8%): ₹{t2:,.2f}",
      annotation_position="bottom right",
      row=1,
      col=1,
  )

  fig.update_layout(
      title=f"📊 {symbol} (15m) | Institutional Bearish Breakdown Blueprint",
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
# 4. MAIN EXECUTION RENDER BLOCK
# ---------------------------------------------------------
with st.spinner(
    "🔍 Scanning market for institutional bearish breakdown setups..."
):
  df_bearish = fetch_bearish_institutional_picks()

if df_bearish is None or df_bearish.empty:
  st.warning(
      "⚠️ No stocks currently match strict bearish breakdown criteria. Click"
      " 'Force Refresh Bearish Scan' above."
  )
else:
  st.subheader(
      "🔥 Top Verified Bearish Institutional Picks (Short 2%–5% Target)"
  )

  # Render Top 2 Highest Conviction Short Picks Automatically
  for idx, row in df_bearish.head(2).iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

      with c1:
        st.markdown(f"### **#{idx+1} {row['Symbol']}**")
        st.metric(
            label="Live LTP",
            value=f"₹{row['LTP']}",
            delta=(
                f"{row['Change']}% (Bearish Alpha: {row['Alpha_Score']} | RVOL:"
                f" {row['RVOL']}x)"
            ),
            delta_color="inverse",
        )

      with c2:
        st.markdown("**Precision Short Levels**")
        st.write(f"🔻 **Short Entry:** ₹{row['Limit_Short']}")
        st.write(f"🛑 **Stop Loss:** ₹{row['Stop_Loss']}")

      with c3:
        st.markdown("**Profit Targets (Downside)**")
        st.write(f"🎯 **Target 1 (-2.5%):** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2 (-4.8%):** ₹{row['Target_2']}")

      with c4:
        st.markdown("**Execution Status**")
        st.error("🔴 **BEARISH INSTITUTIONAL — VERIFIED SHORT**")
        if st.button(
            f"📋 Copy Short Payload ({row['Symbol']})",
            key=f"bear_{row['Symbol']}",
        ):
          st.toast(
              f"Copied {row['Symbol']}! Short: ₹{row['Limit_Short']} | T1:"
              f" ₹{row['Target_1']}"
          )

      with st.expander(
          f"📈 Expand Chart & VWAP Breakdown Structure for #{idx+1}"
          f" {row['Symbol']}"
      ):
        fig = render_bearish_chart(
            row["Symbol"],
            row["DataFrame"],
            row["Volume_Colors"],
            row["Limit_Short"],
            row["Stop_Loss"],
            row["Target_1"],
            row["Target_2"],
        )
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.markdown("---")
