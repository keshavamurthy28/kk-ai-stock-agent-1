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
        "Institutional Alpha & Quality Value Terminal | Indian Market"
    ),
    layout="wide",
)

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
  # Broad, high-liquidity NSE universe spanning Nifty 50, Nifty Next 50, and High-Volume Midcaps
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
      "TVSMOTOR.NS",
      "BOSCHLTD.NS",
      "MUTHOOTFIN.NS",
      "CHOLAFIN.NS",
  ]

  alpha_scored_stocks = []

  for symbol in market_universe:
    try:
      ticker = yf.Ticker(symbol)

      # --- FUNDAMENTAL FILTER (Anti-Trap Protection) ---
      # Fetch basic info/financials to ensure company is profitable & fundamentally sound
      info = ticker.info
      net_income = info.get("netIncomeToCommon", 1)
      trailing_pe = info.get("trailingPE", 0)
      profit_margins = info.get("profitMargins", 0)

      # Anti-Trap Criteria: Must have positive net income and positive profit margins (avoids burning cash traps)
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

      # Extract previous day close from dataframe dates cleanly (Eliminates extra API calls)
      df["Date"] = df["Time"].dt.date
      unique_dates = df["Date"].unique()
      if len(unique_dates) >= 2:
        prev_close = float(
            df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1]
        )
      else:
        prev_close = float(df["Open"].iloc[0])

      change_pct = ((ltp - prev_close) / prev_close) * 100

      # Relative Volume (RVOL) Surge Calculation (Using last completed candle to avoid live candle bias)
      avg_vol = df["Volume"].iloc[-20:-2].mean()
      curr_vol = df["Volume"].iloc[-2]
      rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      latest_vwap = float(df["VWAP"].iloc[-1])
      latest_ema = float(df["EMA20"].iloc[-1])

      # EXPERT ALPHA & MOMENTUM FILTER:
      # 1. Positive intraday momentum (+0.3% to +5.5%)
      # 2. Institutional validation: Price above VWAP & 20 EMA
      # 3. Active volume participation (RVOL >= 1.1x)
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

        # Precision Risk-Reward Calculation
        limit_buy = round(ltp * 0.994, 2)
        stop_loss = round(latest_vwap * 0.992, 2)
        target_1 = round(ltp * 1.025, 2)
        target_2 = round(ltp * 1.048, 2)

        # Composite Alpha Score
        alpha_score = round(change_pct * rvol * (ltp / latest_vwap), 2)

        alpha_scored_stocks.append({
            "Symbol": symbol.replace(".NS", ""),
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
      row=1
