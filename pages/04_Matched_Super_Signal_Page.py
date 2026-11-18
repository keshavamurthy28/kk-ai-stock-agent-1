import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Live Intraday Super-Signal Terminal", layout="wide")
st.title("🎯 Live Intraday Super-Signal & Night-Before Trigger Engine")
st.markdown(
    "Cross-checks live NSE breakouts against your **Night Before Prep"
    " Watchlist**. 🟢 **Emerald Green** rows were predicted in **Night Before"
    " Prep** and have **actively triggered** today."
)

# Comprehensive Stock-to-Sector Mapping Dictionary
STOCK_SECTOR_MAP = {
    "BELRISE": "Automobiles",
    "DEEPAKFERT": "Chemicals",
    "ATHERENERG": "Automobiles",
    "ITC": "FMCG",
    "BHARTIARTL": "Telecommunications",
    "PNB": "Banking & Finance",
    "KALYANKJIL": "Consumer Durables",
    "SBIN": "Banking & Finance",
    "HDFCBANK": "Banking & Finance",
    "ICICIBANK": "Banking & Finance",
    "EICHERMOT": "Automobiles",
    "BSE": "Financial Services",
    "HINDALCO": "Metals & Mining",
    "TDPOWERSYS": "Capital Goods",
    "ABB": "General Industrials",
    "V2RETAIL": "Retailing",
    "KAYNES": "Hardware Technology",
    "RELIANCE": "Energy & Oil",
    "TCS": "Software & Services",
    "INFY": "Software & Services",
    "AXISBANK": "Banking & Finance",
    "BAJFINANCE": "Banking & Finance",
    "TATAMOTORS": "Automobiles",
    "SUNPHARMA": "Healthcare",
    "MARUTI": "Automobiles",
    "NTPC": "Energy & Oil",
    "POWERGRID": "Energy & Oil",
    "M&M": "Automobiles",
    "TATASTEEL": "Metals & Mining",
    "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace",
    "TRENT": "Retailing",
    "ZOMATO": "Retailing",
    "BANKBARODA": "Banking & Finance",
    "CANBK": "Banking & Finance",
    "JINDALPOLY": "Packaging",
    "FINCABLES": "Hardware Technology",
    "AMBER": "Consumer Durables",
    "MSTCLTD": "Commercial Services",
    "POWERINDIA": "Utilities",
    "HONASA": "FMCG",
    "GLAND": "Healthcare",
    "MANKIND": "Healthcare",
    "DIVISLAB": "Healthcare",
    "WOCKPHARMA": "Healthcare",
    "INDUSTOWER": "Telecom Services",
    "HINDCOPPER": "Metals & Mining",
    "DATAPATTNS": "Defense & Aerospace",
    "DIXON": "Consumer Durables",
    "POLYCAB": "Hardware Technology",
    "KEI": "Hardware Technology",
    "PFC": "Financial Services",
    "RECLTD": "Financial Services",
    "IRFC": "Financial Services",
    "RVNL": "Transportation",
    "MAZDOCK": "Defense & Aerospace",
    "COCHINSHIP": "Defense & Aerospace",
    "GRSE": "Defense & Aerospace",
    "BDL": "Defense & Aerospace",
    "SUZLON": "Utilities",
    "IREDA": "Utilities",
    "HUDCO": "Realty",
    "NBCC": "Cement & Construction",
    "SJVN": "Utilities",
    "NHPC": "Utilities",
    "BHEL": "Capital Goods",
    "SAIL": "Metals & Mining",
    "NMDC": "Metals & Mining",
    "VEDL": "Metals & Mining",
    "JSWSTEEL": "Metals & Mining",
    "JINDALSTEL": "Metals & Mining",
    "ADANIENT": "Diversified",
    "ADANIPORTS": "Transportation",
    "ADANIPOWER": "Utilities",
    "TATAPOWER": "Utilities",
    "JSWENERGY": "Utilities",
    "CGPOWER": "Capital Goods",
    "SIEMENS": "General Industrials",
    "CUMMINSIND": "General Industrials",
    "THERMAX": "Capital Goods",
    "TRITURBINE": "Capital Goods",
    "KPITTECH": "Software & Services",
    "PERSISTENT": "Software & Services",
    "COFORGE": "Software & Services",
    "LTIM": "Software & Services",
    "TECHM": "Software & Services",
    "WIPRO": "Software & Services",
    "HCLTECH": "Software & Services",
    "NAUKRI": "Software & Services",
    "PAYTM": "Financial Services",
    "POLICYBZR": "Financial Services",
    "ANGELONE": "Financial Services",
    "CDSL": "Financial Services",
    "MCX": "Financial Services",
    "IEX": "Financial Services",
    "TITAN": "Consumer Durables",
    "DMART": "Retailing",
    "VBL": "Food Beverages",
    "GODREJCP": "FMCG",
    "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG",
    "DABUR": "FMCG",
    "MARICO": "FMCG",
    "COLPAL": "FMCG",
    "PIDILITIND": "Chemicals",
    "ASIANPAINT": "Consumer Durables",
    "BERGEPAINT": "Chemicals",
    "ULTRACEMCO": "Cement & Construction",
    "AMBUJACEM": "Cement & Construction",
    "SHREECEM": "Cement & Construction",
    "DLF": "Realty",
    "GODREJPROP": "Realty",
    "OBEROIRLTY": "Realty",
    "PRESTIGE": "Realty",
    "LODHA": "Realty",
    "INDIGO": "Transportation",
    "IRCTC": "Transportation",
    "CONCOR": "Transportation",
    "APOLLOHOSP": "Healthcare",
    "MAXHEALTH": "Healthcare",
}

NSE_ACTIVE_UNIVERSE = list(STOCK_SECTOR_MAP.keys())


def get_rvol_scale():
  now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
  m_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
  m_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
  if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5:
    return 1.0
  mins = max((now_ist - m_open).total_seconds() / 60.0, 5.0)
  return min(375.0 / mins, 25.0)


@st.cache_data(ttl=90)
def scan_matched_super_signals(tickers):
  symbols = [f"{t}.NS" for t in tickers]
  try:
    raw = yf.download(
        symbols,
        period="3mo",
        interval="1d",
        group_by="ticker",
        progress=False,
        auto_adjust=True,
    )
  except Exception:
    return pd.DataFrame(), []

  scale = get_rvol_scale()
  auto_night_before = []
  signals = []

  for t in tickers:
    sym = f"{t}.NS"
    try:
      df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
      if len(df) < 25:
        continue

      ltp = float(df["Close"].iloc[-1])
      open_p = float(df["Open"].iloc[-1])
      high_p = float(df["High"].iloc[-1])
      low_p = float(df["Low"].iloc[-1])
      prev_c = float(df["Close"].iloc[-2])

      pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
      vol_pace = float(df["Volume"].iloc[-1]) * scale
      vol_avg = float(df["Volume"].iloc[-21:-1].mean())
      rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 else 1.0

      ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
      ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
      res_20d = float(df["High"].iloc[-21:-1].max())

      dist_prev = ((res_20d - prev_c) / prev_c) * 100
      if prev_c > ema20 > ema50 and -2.5 <= dist_prev <= 4.0:
        auto_night_before.append(t)

      near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
      if pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema20:
        broke_20d = ltp >= res_20d
        score = (
            (pct_chg * 6)
            + (min(rvol, 20.0) * 6)
            + (20 if broke_20d else 0)
            + (10 if near_day_high else 0)
        )

        sl = round(max(low_p, prev_c * 0.99) * 0.995, 2)
        risk = max(ltp - sl, ltp * 0.012)
        t1 = round(ltp + (risk * 1.5), 2)
        t2 = round(ltp + (risk * 3.0), 2)

        signals.append({
            "Stock": t,
            "Sector": STOCK_SECTOR_MAP.get(t, "General"),
            "Action": "BUY",
            "LTP": round(ltp, 2),
            "Change_%": pct_chg,
            "Volume_Surge": f"{rvol:.2f}x",
            "Stop_Loss": sl,
            "Target_1": t1,
            "Target_2": t2,
            "Catalyst_Reason": (
                f"20D Breakout + {rvol}x RVOL"
                if broke_20d
                else f"Intraday Drive (+{pct_chg}%) + {rvol}x RVOL"
            ),
            "Score": score,
        })
    except Exception:
      continue

  if not signals:
    return pd.DataFrame(), auto_night_before
  return pd.DataFrame(signals), auto_night_before


if st.button("🔄 Force Refresh Live Data"):
  st.cache_data.clear()

df_live, computed_nb = scan_matched_super_signals(NSE_ACTIVE_UNIVERSE)

# Pull Night-Before Watchlist directly from session state or computed fallback
session_nb = st.session_state.get("night_before_watchlist", [])
nb_watchlist = set(session_nb) | set(computed_nb)

if df_live.empty:
  st.warning(
      "No stocks currently meet the live intraday breakout + RVOL threshold."
  )
else:
  df_live["Night_Before_Match"] = df_live["Stock"].isin(nb_watchlist)
  df_live["Final_Score"] = df_live["Score"] + np.where(
      df_live["Night_Before_Match"], 40, 0
  )
  df_live["Signal_Source"] = np.where(
      df_live["Night_Before_Match"],
      "🟢 NIGHT-BEFORE TRIGGERED",
      "🔵 FRESH INTRADAY BREAKOUT",
  )

  df_live = df_live.sort_values(by="Final_Score", ascending=False).reset_index(
      drop=True
  )
  df_live.insert(0, "Rank", df_live.index + 1)

  st.session_state["super_signal_confirmed"] = df_live[
      df_live["Night_Before_Match"]
  ]["Stock"].tolist()


  def highlight_signal_source(row):
    if "NIGHT-BEFORE TRIGGERED" in str(row["Signal_Source"]):
      return [
          (
              "background-color: rgba(0, 230, 118, 0.22); color: #E8F5E9;"
              " font-weight: 600"
          )
      ] * len(row)
    return ["background-color: rgba(41, 182, 246, 0.14); color: #E1F5FE"] * len(
        row
    )


  display_cols = [
      "Rank",
      "Stock",
      "Sector",
      "Signal_Source",
      "Action",
      "LTP",
      "Change_%",
      "Volume_Surge",
      "Stop_Loss",
      "Target_1",
      "Target_2",
      "Catalyst_Reason",
  ]
  styled_df = (
      df_live[display_cols]
      .style.apply(highlight_signal_source, axis=1)
      .format({
          "LTP": "₹{:.2f}",
          "Change_%": "+{:.2f}%",
          "Stop_Loss": "₹{:.2f}",
          "Target_1": "₹{:.2f}",
          "Target_2": "₹{:.2f}",
      })
  )

  st.markdown(
      "🟢 **Emerald Green:** Night Before Prep Stock That Triggered Live  | "
      " 🔵 **Electric Blue:** Fresh Intraday Breakout"
  )
  st.subheader("🏆 Live Intraday Execution Ranking Table")
  st.dataframe(styled_df, use_container_width=True, hide_index=True)

  st.markdown("---")
  st.subheader("🎯 Top Confirmed Execution Cards")
  for _, row in df_live.head(3).iterrows():
    st.markdown(
        f"### Rank #{row['Rank']}: {row['Stock']} ({row['Sector']}) —"
        f" +{row['Change_%']}% — {row['Signal_Source']}"
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Action & LTP", f"BUY @ ₹{row['LTP']:,.2f}")
    c2.metric("Strict Stop-Loss", f"₹{row['Stop_Loss']:,.2f}")
    c3.metric("Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}")
    c4.metric("Target 2 (3.0R)", f"₹{row['Target_2']:,.2f}")
    st.info(f"💡 **Catalyst:** {row['Catalyst_Reason']}")
