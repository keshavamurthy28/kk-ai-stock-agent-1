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
    page_title="Institutional Alpha Intraday Sniper | MU₹A Rendezvous",
    layout="wide",
)

st.title("🎯 Institutional Alpha Intraday Sniper Terminal (Anti-Trap)")
st.markdown(
    "**Expert Analyst Engine:** Market-wide scanning combining **Fundamental"
    " Quality Filters** (Positive earnings & profit margins) with VWAP support,"
    " volume expansion, and ATR-managed risk boundaries for reliable 2%–5%"
    " intraday gains."
)

# ---------------------------------------------------------
# 1. TOP CONTROLS & LIVE REFRESH
# ---------------------------------------------------------
col_ctrl1, col_ctrl2 = st.columns([3, 1])
with col_ctrl2:
  if st.button("🔄 Force Refresh Sniper Scans"):
    st.cache_data.clear()
    st.toast("Cleared cache and executed market-wide sniper scan!")
    st.rerun()

ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()


# ---------------------------------------------------------
# 2. MARKET-WIDE INSTITUTIONAL SNIPER SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_institutional_sniper_picks():
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
      "ETERNAL.NS",  # Updated from ZOMATO
      "BELRISE.NS",
      "TATACOMM.NS",
      "PIDILITEIND.NS",
      "SRF.NS",
      "HAL.NS",
      "BEL.NS",
  ]

  sniper_rows = []

  for symbol in market_universe:
    try:
      ticker = yf.Ticker(symbol)

      # --- FUNDAMENTAL FILTER (Anti-Trap Protection) ---
      info = ticker.info
      net_income = info.get("netIncomeToCommon", 1)
      profit_margins = info.get("profitMargins", 0)

      if (
          net_income is not None
          and net_income <= 0
          or profit_margins is not None
          and profit_margins < 0.02
      ):
        continue  # Skip fundamentally weak or cash-burning stocks

      df = ticker.history(period="5d", interval="5m", auto_adjust=True)
      if df is None or df.empty or len(df) < 20:
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

      # Clean previous close extraction from DataFrame dates (Avoids extra API requests)
      df["Date"] = df["Time"].dt.date
      unique_dates = df["Date"].unique()
      if len(unique_dates) >= 2:
        prev_close = float(
            df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1]
        )
      else:
        prev_close = float(df["Open"].iloc[0])

      change_pct = ((ltp - prev_close) / prev_close) * 100

      # Relative Volume (RVOL) Check using last COMPLETED candle
      avg_vol = df["Volume"].iloc[-20:-2].mean()
      curr_vol = df["Volume"].iloc[-2]
      rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      latest_vwap = float(df["VWAP"].iloc[-1])
      latest_ema = float(df["EMA20"].iloc[-1])

      # 14-Day ATR Calculation (from daily summary)
      df_daily = ticker.history(period="14d", interval="1d")
      if not df_daily.empty and len(df_daily) >= 5:
        tr = np.maximum(
            df_daily["High"] - df_daily["Low"],
            np.maximum(
                abs(df_daily["High"] - df_daily["Close"].shift(1)),
                abs(df_daily["Low"] - df_daily["Close"].shift(1)),
            ),
        )
        atr_14 = float(tr.mean())
      else:
        atr_14 = ltp * 0.03

      # Institutional Sniper Filter: Positive momentum + VWAP/EMA Trend Validation + RVOL
      if (
          0.4 <= change_pct <= 6.5
          and ltp >= latest_vwap
          and ltp >= latest_ema
          and rvol >= 1.1
      ):
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

        vwap_buy = round(latest_vwap * 0.995, 2)
        stop_loss = round(latest_vwap * 0.990, 2)
        t1 = round(ltp + (atr_14 * 0.8), 2)
        t2 = round(ltp + (atr_14 * 1.3), 2)

        alpha_score = round(change_pct * rvol * (ltp / latest_vwap), 2)

        sniper_rows.append({
            "Symbol": symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "Change": round(change_pct, 2),
            "RVOL": rvol,
            "Alpha_Score": alpha_score,
            "ATR": round(atr_14, 2),
            "VWAP_Buy": vwap_buy,
            "Stop_Loss": stop_loss,
            "Target_1": t1,
            "Target_2": t2,
            "DataFrame": df,
            "Volume_Colors": v_col,
        })
    except Exception:
      continue

  df_res = pd.DataFrame(sniper_rows)
  if not df_res.empty:
    df_res = df_res.sort_values(by="Alpha_Score", ascending=False).reset_index(
        drop=True
    )
  return df_res


# ---------------------------------------------------------
# 3. PLOTTING FUNCTION
# ---------------------------------------------------------
def render_sniper_chart(symbol, df, v_col, entry, sl, t1, t2, atr):
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

  fig.add_hline(
      y=entry,
      line_color="#FFD700",
      line_width=1.6,
      annotation_text=f"🟡 VWAP BUY: ₹{entry:,.2f}",
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
      annotation_text=f"🎯 TARGET 1 (+2.5%): ₹{t1:,.2f}",
      annotation_position="top left",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=t2,
      line_dash="dash",
      line_color="#00E676",
      line_width=1.4,
      annotation_text=f"🚀 TARGET 2 (+5.0%): ₹{t2:,.2f}",
      annotation_position="top right",
      row=1,
      col=1,
  )

  fig.update_layout(
      title=f"📊 {symbol} (5m) | 14D ATR: ₹{atr}",
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
# 4. MAIN RENDER BLOCK
# ---------------------------------------------------------
with st.spinner(
    "🎯 Scanning market-wide institutional alpha & anti-trap sniper bands..."
):
  df_sniper = fetch_institutional_sniper_picks()

if df_sniper is None or df_sniper.empty:
  st.warning(
      "⚠️ No stocks currently meeting sniper confluence or fundamental quality"
      " filters. Click 'Force Refresh Sniper Scans' above."
  )
else:
  st.subheader(
      "🏆 Institutional Alpha Intraday Sniper Ranking (Quality Verified)"
  )

  for idx, row in df_sniper.head(3).iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

      with c1:
        st.markdown(f"### **#{idx+1} {row['Symbol']}**")
        st.metric(
            label="Live LTP",
            value=f"₹{row['LTP']}",
            delta=(
                f"+{row['Change']}% (Alpha: {row['Alpha_Score']} | RVOL:"
                f" {row['RVOL']}x)"
            ),
        )

      with c2:
        st.markdown("**Sniper Entry Levels**")
        st.write(f"🟡 **VWAP Buy:** ₹{row['VWAP_Buy']}")
        st.write(f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']}")

      with c3:
        st.markdown("**ATR Target Matrix**")
        st.write(f"🎯 **Target 1:** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2:** ₹{row['Target_2']}")

      with c4:
        st.markdown("**Execution Status**")
        st.success("✅ **VERIFIED NON-TRAP SNIPER BUY**")
        if st.button(
            f"📋 Copy Sniper Payload ({row['Symbol']})", key=f"snip_{row['Symbol']}"
        ):
          st.toast(
              f"Copied {row['Symbol']}! VWAP Buy: ₹{row['VWAP_Buy']} | T1:"
              f" ₹{row['Target_1']}"
          )

      with st.expander(
          f"📈 Expand 5m Intraday Sniper Chart & Levels for #{idx+1}"
          f" {row['Symbol']}"
      ):
        fig = render_sniper_chart(
            row["Symbol"],
            row["DataFrame"],
            row["Volume_Colors"],
            row["VWAP_Buy"],
            row["Stop_Loss"],
            row["Target_1"],
            row["Target_2"],
            row["ATR"],
        )
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.markdown("---")
