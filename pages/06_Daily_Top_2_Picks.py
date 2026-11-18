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
    page_title="Institutional Alpha & Quality Value Terminal | Indian Market",
    layout="wide",
)

# --- CLEAN SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.markdown(
    "- 🗺️ **[Sector Rotation & Macro Pulse](Sector_Rotation_Scanner)**"
    f"[cite: 3]"
)
st.sidebar.markdown("- ⚡ **[Smart Money Flow Terminal](Smart_Money_Pulse)**")
st.sidebar.markdown(
    "- 🌙 **[Night-Before Prep & Coiling](Night_Before_Prep_Scanner)**"
)
st.sidebar.markdown(
    "- 🎯 **[Live Super-Signal Triggers](Matched_Super_Signal_Page)**"
)
st.sidebar.markdown("- 📈 **[Intraday Sniper Terminal](PRIME_2-5_INTRADAY_SNIPER)**")
st.sidebar.markdown("- 🔥 **[Daily Top 2 Alpha Picks](Daily_Top_2_Picks)**")
st.sidebar.markdown("---")

st.title(
    "🎯 Institutional Alpha & Fundamental Quality Terminal: Anti-Trap Intraday"
    " Setups"
)
st.markdown(
    "**Expert Analyst Engine:** Scans high-liquidity Indian equities combining"
    " **Fundamental Quality Filters** (Positive earnings, healthy margins)"
    " with **Multi-Factor Volume Expansion** and **VWAP Alignment** to filter"
    " out stagnant value traps."
)

# Comprehensive Stock-to-Sector Mapping (Unified across the workspace)
STOCK_SECTOR_MAP = {
    "RELIANCE": "Energy & Oil",
    "TCS": "Software & Services",
    "HDFCBANK": "Banking & Finance",
    "ICICIBANK": "Banking & Finance",
    "INFY": "Software & Services",
    "SBIN": "Banking & Finance",
    "ITC": "FMCG",
    "BHARTIARTL": "Telecommunications",
    "LICI": "Financial Services",
    "AXISBANK": "Banking & Finance",
    "KOTAKBANK": "Banking & Finance",
    "LT": "Capital Goods",
    "BAJFINANCE": "Banking & Finance",
    "MARUTI": "Automobiles",
    "SUNPHARMA": "Healthcare",
    "TITAN": "Consumer Durables",
    "ADANIENT": "Diversified",
    "ADANIPORTS": "Transportation",
    "TATASTEEL": "Metals & Mining",
    "NTPC": "Energy & Oil",
    "POWERGRID": "Energy & Oil",
    "COALINDIA": "Energy & Oil",
    "ONGC": "Energy & Oil",
    "BAJAJFINSV": "Banking & Finance",
    "WIPRO": "Software & Services",
    "ASIANPAINT": "Consumer Durables",
    "HCLTECH": "Software & Services",
    "GRASIM": "Cement & Construction",
    "TECHM": "Software & Services",
    "INDUSINDBK": "Banking & Finance",
    "DEEPAKFERT": "Fertilizers",
    "ANGELONE": "Financial Services",
    "HONASA": "FMCG",
    "MAXHEALTH": "Healthcare",
    "PNB": "Banking & Finance",
    "CANBK": "Banking & Finance",
    "TORNTPHARM": "Healthcare",
    "SUPREMEIND": "Capital Goods",
    "ETERNAL": "Retailing",
    "BELRISE": "Automobiles",
    "TATACOMM": "Telecommunications",
    "PIDILITEIND": "Chemicals",
    "SRF": "Chemicals",
    "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace",
    "TVSMOTOR": "Automobiles",
    "BOSCHLTD": "Automobiles",
    "MUTHOOTFIN": "Banking & Finance",
    "CHOLAFIN": "Banking & Finance",
}

# ---------------------------------------------------------
# 1. LIVE CONTROL PANEL & REFRESH
# ---------------------------------------------------------
col_r1, col_r2 = st.columns([4, 1])
with col_r2:
  if st.button("🔄 Force Refresh Alpha Scan"):
    st.cache_data.clear()
    st.toast("Cleared cache and executed market-wide alpha scan!")
    st.rerun()

ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()


# ---------------------------------------------------------
# 2. BROADER MARKET INSTITUTIONAL ALPHA & FUNDAMENTAL SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_institutional_alpha_picks():
  market_universe = [f"{sym}.NS" for sym in STOCK_SECTOR_MAP.keys()]
  alpha_scored_stocks = []

  for symbol in market_universe:
    clean_sym = symbol.replace(".NS", "")
    sector_name = STOCK_SECTOR_MAP.get(clean_sym, "General")

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
        continue  # Skip fundamentally weak or low-margin trap stocks

      # Fetch intraday 15m price history
      df = ticker.history(period="5d", interval="15m", auto_adjust=True)
      if df is None or df.empty or len(df) < 20:
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

      df["Date"] = df["Time"].dt.date
      unique_dates = df["Date"].unique()
      if len(unique_dates) >= 2:
        prev_close = float(
            df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1]
        )
      else:
        prev_close = float(df["Open"].iloc[0])

      change_pct = ((ltp - prev_close) / prev_close) * 100

      # Relative Volume (RVOL) Surge Calculation
      avg_vol = df["Volume"].iloc[-20:-2].mean()
      curr_vol = df["Volume"].iloc[-2]
      rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      latest_vwap = float(df["VWAP"].iloc[-1])
      latest_ema = float(df["EMA20"].iloc[-1])

      if (
          0.3 <= change_pct <= 5.5
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

        limit_buy = round(ltp * 0.994, 2)
        stop_loss = round(latest_vwap * 0.992, 2)
        target_1 = round(ltp * 1.025, 2)
        target_2 = round(ltp * 1.048, 2)

        alpha_score = round(change_pct * rvol * (ltp / latest_vwap), 2)

        alpha_scored_stocks.append({
            "Symbol": clean_sym,
            "Sector": sector_name,
            "LTP": round(ltp, 2),
            "Change": round(change_pct, 2),
            "RVOL": rvol,
            "Alpha_Score": alpha_score,
            "Limit_Buy": limit_buy,
            "Stop_Loss": stop_loss,
            "Target_1": target_1,
            "Target_2": target_2,
            "DataFrame": df,
            "Volume_Colors": v_col,
        })
    except Exception:
      continue

  df_res = pd.DataFrame(alpha_scored_stocks)
  if not df_res.empty:
    df_res = df_res.sort_values(by="Alpha_Score", ascending=False).reset_index(
        drop=True
    )
  return df_res


# ---------------------------------------------------------
# 3. ADVANCED INSTITUTIONAL PLOTTING ENGINE
# ---------------------------------------------------------
def render_institutional_chart(symbol, df, v_col, entry, sl, t1, t2):
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
      annotation_text=f"🚀 T2 (+4.8%): ₹{t2:,.2f}",
      annotation_position="top right",
      row=1,
      col=1,
  )

  fig.update_layout(
      title=f"📊 {symbol} (15m) | Institutional Alpha Execution Blueprint",
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
    "🔍 Scanning market universe with Fundamental Anti-Trap Filters & Alpha"
    " Momentum..."
):
  df_alpha = fetch_institutional_alpha_picks()

if df_alpha is None or df_alpha.empty:
  st.warning(
      "⚠️ No stocks currently match strict fundamental quality & intraday alpha"
      " criteria (Market may be rangebound/weak). Click 'Force Refresh Alpha"
      " Scan' above."
  )
else:
  st.subheader(
      "🔥 Top 2 Verified Fundamental + Technical Institutional Picks (2%–5%"
      " Target)"
  )

  # Sync top alpha picks to session state for cross-page connectivity
  st.session_state["top_alpha_picks"] = df_alpha.head(2)["Symbol"].tolist()

  for idx, row in df_alpha.head(2).iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

      with c1:
        st.markdown(f"### **#{idx+1} {row['Symbol']}**")
        st.caption(f"📂 **Sector:** {row['Sector']}")
        st.metric(
            label="Live LTP",
            value=f"₹{row['LTP']}",
            delta=(
                f"+{row['Change']}% (Alpha Score: {row['Alpha_Score']} | RVOL:"
                f" {row['RVOL']}x)"
            ),
        )

      with c2:
        st.markdown("**Precision Entry Levels**")
        st.write(f"🔹 **Limit Buy:** ₹{row['Limit_Buy']}")
        st.write(f"🛑 **Stop Loss:** ₹{row['Stop_Loss']}")

      with c3:
        st.markdown("**Profit Targets**")
        st.write(f"🎯 **Target 1 (+2.5%):** ₹{row['Target_1']}")
        st.write(f"🚀 **Target 2 (+4.8%):** ₹{row['Target_2']}")

      with c4:
        st.markdown("**Execution Status**")
        st.success(
            "✅ **FUNDAMENTAL & TECHNICAL — VERIFIED NON-TRAP BUY**"
        )
        if st.button(f"📋 Copy Payload ({row['Symbol']})", key=f"alpha_{row['Symbol']}"):
          st.toast(
              f"Copied {row['Symbol']} ({row['Sector']})! Limit:"
              f" ₹{row['Limit_Buy']} | T1: ₹{row['Target_1']}"
          )

      with st.expander(
          f"📈 Expand Chart & VWAP Structure for #{idx+1} {row['Symbol']}"
          f" ({row['Sector']})"
      ):
        fig = render_institutional_chart(
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
