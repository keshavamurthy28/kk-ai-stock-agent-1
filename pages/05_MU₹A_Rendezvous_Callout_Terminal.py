import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MU$₹A Rendezvous Advance Callouts", layout="wide")
st.header("⚙️ Terminal Control Center")
  if st.button("🔄 Refresh Live Scans", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.success("Cache cleared! Fetching fresh data...")
    st.rerun()

  st.markdown("---")
  st.markdown("### 🤖 AI Agent Status")
  st.info(
      "Connected to GitHub: `keshavamurthy28/kk-ai-stock-agent-1`"
  )
  st.caption("Active Engine: Python yfinance + Plotly Multi-Timeframe Engine")

st.title("🎯 MU$₹A Rendezvous: Live Breakout & Advance Callout Terminal")
st.markdown(
    "🟢 **Night-Before Coil Triggered:** Multi-day tight consolidation"
    " breaking out  |  🔵 **Fresh Intraday Surge:** High-volume institutional"
    " momentum breakout"
)

# High-liquidity universe with Sector Classifications
UNIVERSE = {
    "LICHSGFIN": ("LIC Housing Finance", "Banking & Finance"),
    "MCX": ("Multi Commodity Exchange", "Financial Services"),
    "CDSL": ("Central Depository Services", "Financial Services"),
    "BELRISE": ("Belrise Industries", "Automobiles"),
    "ITC": ("ITC Limited", "Consumer & Retail"),
    "DEEPAKFERT": ("Deepak Fertilisers", "Healthcare & Pharma"),
    "MAXHEALTH": ("Max Healthcare", "Healthcare & Pharma"),
    "KALYANKJIL": ("Kalyan Jewellers", "Consumer & Retail"),
    "KARURVYSYA": ("Karur Vysya Bank", "Banking & Finance"),
    "BSE": ("BSE Limited", "Financial Services"),
    "APOLLOMICRO": ("Apollo Micro Systems", "Infrastructure & Industrials"),
    "AUROPHARMA": ("Aurobindo Pharma", "Healthcare & Pharma"),
    "SBIN": ("State Bank of India", "Banking & Finance"),
    "BANKBARODA": ("Bank of Baroda", "Banking & Finance"),
    "INDIANB": ("Indian Bank", "Banking & Finance"),
    "UNIONBANK": ("Union Bank of India", "Banking & Finance"),
    "CANBK": ("Canara Bank", "Banking & Finance"),
    "IDFCFIRSTB": ("IDFC First Bank", "Banking & Finance"),
    "ABCAPITAL": ("Aditya Birla Capital", "Financial Services"),
    "JIOFIN": ("Jio Financial Services", "Financial Services"),
    "ETERNAL": ("Eternal Limited", "Consumer & Retail"),
    "TITAN": ("Titan Company", "Consumer & Retail"),
    "DIVISLAB": ("Divi's Laboratories", "Healthcare & Pharma"),
    "GRASIM": ("Grasim Industries", "Infrastructure & Industrials"),
    "PRESTIGE": ("Prestige Estates", "Infrastructure & Industrials"),
    "INDHOTEL": ("Indian Hotels Co.", "Consumer & Retail"),
    "BEL": ("Bharat Electronics", "Infrastructure & Industrials"),
    "LT": ("Larsen & Toubro", "Infrastructure & Industrials"),
    "MUTHOOTFIN": ("Muthoot Finance", "Banking & Finance"),
    "MANKIND": ("Mankind Pharma", "Healthcare & Pharma"),
}


@st.cache_data(ttl=30)
def scan_live_universe(symbols_dict):
  tickers = [f"{s}.NS" for s in symbols_dict.keys()]
  raw = yf.download(
      tickers,
      period="1mo",
      interval="1d",
      group_by="ticker",
      progress=False,
      threads=True,
  )
  rows = []

  # Retrieve Night-Before watchlist from session state if available
  session_nb = st.session_state.get("night_before_watchlist", [])

  for sym, (name, sector) in symbols_dict.items():
    t_key = f"{sym}.NS"
    try:
      df_s = (
          raw[t_key].dropna(subset=["Close", "Volume"])
          if len(tickers) > 1
          else raw.dropna(subset=["Close", "Volume"])
      )
      if len(df_s) < 6:
        continue

      ltp = float(df_s["Close"].iloc[-1])
      prev_close = float(df_s["Close"].iloc[-2])
      chg_pct = ((ltp - prev_close) / prev_close) * 100.0

      cur_vol = float(df_s["Volume"].iloc[-1])
      avg_vol = (
          float(df_s["Volume"].iloc[-11:-1].mean())
          if len(df_s) >= 11
          else float(df_s["Volume"].iloc[:-1].mean())
      )
      rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

      high_15d = float(df_s["High"].iloc[-16:-1].max())
      low_5d = float(df_s["Low"].iloc[-5:].min())

      # Check if matched with Night Before Watchlist or meeting coil criteria
      is_night_matched = sym in session_nb

      if is_night_matched or (ltp >= high_15d * 0.995 and rvol >= 1.2):
        sig_source = "🟢 NIGHT-BEFORE TRIGGERED"
        reason = f"Night Coil Breakout + {rvol:.2f}x RVOL"
      else:
        sig_source = "🔵 FRESH INTRADAY BREAKOUT"
        reason = f"Momentum Drive ({chg_pct:+.2f}%) + {rvol:.2f}x RVOL"

      sl = round(max(low_5d * 0.992, ltp * 0.955), 2)
      risk = max(ltp - sl, ltp * 0.015)
      t1 = round(ltp + (risk * 1.5), 2)
      t2 = round(ltp + (risk * 2.5), 2)

      score = (
          (chg_pct * 2.0)
          + (min(rvol, 10.0) * 3.0)
          + (15.0 if "NIGHT-BEFORE" in sig_source else 0.0)
      )

      rows.append({
          "Score": score,
          "Stock": sym,
          "Company": name,
          "Sector": sector,
          "Signal_Source": sig_source,
          "Action": "BUY" if chg_pct > -1.0 else "WATCH",
          "LTP": round(ltp, 2),
          "Change_%": round(chg_pct, 2),
          "Volume_Surge": rvol,
          "Stop_Loss": sl,
          "Target_1": t1,
          "Target_2": t2,
          "Catalyst_Reason": reason,
      })
    except Exception:
      continue

  if not rows:
    return pd.DataFrame()

  res_df = (
      pd.DataFrame(rows)
      .sort_values(by="Score", ascending=False)
      .head(10)
      .reset_index(drop=True)
  )
  res_df.insert(0, "Rank", range(1, len(res_df) + 1))
  return res_df.drop(columns=["Score"])


with st.spinner("Scanning NSE live breakouts & sector flows..."):
  rank_df = scan_live_universe(UNIVERSE)

selected_sym = "MCX"

if not rank_df.empty:
  st.subheader("🏆 Live Intraday & Advance Execution Ranking Table")
  st.caption(
      "👇 **Click any row in the table below** to project its interactive"
      " chart, Limit Buy zone, Stop-Loss, and Targets."
  )


  def highlight_signal_rows(row):
    if "NIGHT-BEFORE" in str(row["Signal_Source"]):
      return ["background-color: rgba(0, 230, 118, 0.14)"] * len(row)
    return ["background-color: rgba(41, 182, 246, 0.10)"] * len(row)


  styled_df = (
      rank_df.drop(columns=["Company"])
      .style.apply(highlight_signal_rows, axis=1)
      .format({
          "LTP": "₹{:,.2f}",
          "Change_%": "{:+.2f}%",
          "Volume_Surge": "{:.2f}x",
          "Stop_Loss": "₹{:,.2f}",
          "Target_1": "₹{:,.2f}",
          "Target_2": "₹{:,.2f}",
      })
  )

  event = st.dataframe(
      styled_df,
      use_container_width=True,
      hide_index=True,
      on_select="rerun",
      selection_mode="single-row",
  )

  if event and event.selection and event.selection.rows:
    clicked_idx = event.selection.rows[0]
    selected_sym = rank_df.iloc[clicked_idx]["Stock"]
  else:
    selected_sym = rank_df.iloc[0]["Stock"]
else:
  st.warning("Live market scanner temporarily unavailable. Defaulting to MCX.")

st.markdown("---")

# Controls for projected chart below
c1, c2 = st.columns([1, 2])
all_syms = list(UNIVERSE.keys())
default_idx = (
    all_syms.index(selected_sym) if selected_sym in all_syms else 0
)
active_sym = c1.selectbox(
    "Active Projected Stock (Click table row above or pick here)",
    all_syms,
    index=default_idx,
)
tf_choice = c2.radio(
    "Candle Interval (TradingView / Kite Style)",
    ["5m", "15m", "1h", "4h", "1D"],
    index=1,
    horizontal=True,
)


@st.cache_data(ttl=15)
def fetch_chart_data(sym, tf):
  t_obj = yf.Ticker(f"{sym}.NS")
  p_map = {"5m": "5d", "15m": "15d", "1h": "60d", "4h": "60d", "1D": "6mo"}
  i_map = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "1h", "1D": "1d"}
  df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)

  if df is None or df.empty:
    return pd.DataFrame()

  df = df.reset_index()
  df.rename(columns={df.columns[0]: "Time"}, inplace=True)
  df["Time"] = pd.to_datetime(df["Time"])
  if df["Time"].dt.tz is not None:
    df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

  if tf == "4h":
    df = (
        df.set_index("Time")
        .resample("4h", offset="15min")
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
        .dropna()
        .reset_index()
    )
  return df


df = fetch_chart_data(active_sym, tf_choice)

if df.empty:
  st.error(f"Could not load chart data for {active_sym}.")
else:
  ltp = float(df["Close"].iloc[-1])
  company_name, sector_name = UNIVERSE.get(
      active_sym, (active_sym, "General")
  )

  if not rank_df.empty and active_sym in rank_df["Stock"].values:
    r_row = rank_df[rank_df["Stock"] == active_sym].iloc[0]
    initial_sl = float(r_row["Stop_Loss"])
    target_1 = float(r_row["Target_1"])
    target_2 = float(r_row["Target_2"])
    bias_label = r_row["Signal_Source"]
  else:
    initial_sl = round(ltp * 0.96, 2)
    risk_tmp = ltp - initial_sl
    target_1 = round(ltp + risk_tmp * 1.5, 2)
    target_2 = round(ltp + risk_tmp * 2.5, 2)
    bias_label = "Breakout Setup"

  suggested_entry = round(ltp * 0.994, 2)
  risk_amt = max(suggested_entry - initial_sl, suggested_entry * 0.01)
  zero_loss_trigger = round(suggested_entry + (risk_amt * 0.8), 2)

  st.subheader(
      f"📊 Projected Execution Blueprint: {company_name} ({active_sym})"
      f" — 📂 Sector: {sector_name}"
  )

  m1, m2, m3, m4, m5 = st.columns(5)
  m1.metric("Live LTP", f"₹{ltp:,.2f}", bias_label)
  m2.metric(
      "🟡 Kite Limit Buy",
      f"₹{suggested_entry:,.2f}",
      "Pullback / Breakout Entry",
  )
  m3.metric("🛑 Initial Stop-Loss", f"₹{initial_sl:,.2f}", "Hard Risk Protection")
  m4.metric("🎯 Target 1 (1.5R)", f"₹{target_1:,.2f}", "Book 50% Profit")
  m5.metric("🚀 Target 2 (2.5R)", f"₹{target_2:,.2f}", "Book Remaining 50%")

  st.info(
      f"**🛡️ Beginner Execution Plan for {active_sym} ({sector_name}):**  \n"
      f"1. **Buy Zone:** Place a Limit Buy on Zerodha Kite around"
      f" **₹{suggested_entry:,.2f}** (or buy on breakout above"
      f" **₹{ltp:,.2f}** with volume).  \n"
      f"2. **Protect Capital:** Immediately place a Stop-Loss order at"
      f" **₹{initial_sl:,.2f}**. Never hold below this line.  \n"
      f"3. **Zero-Loss Lock:** Once price crosses"
      f" **₹{zero_loss_trigger:,.2f}**, move your Stop-Loss up to"
      f" **₹{suggested_entry:,.2f}** so the trade becomes 100% risk-free."
  )

  # VWAP & EMA 20
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
                  "rgba(0,230,118,0.40)" if c >= o else "rgba(255,82,82,0.40)"
              )
          )
      )
      for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
  ]

  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=[0.78, 0.22],
  )

  fig.add_trace(
      go.Candlestick(
          x=df["Time"],
          open=df["Open"],
          high=df["High"],
          low=df["Low"],
          close=df["Close"],
          name=active_sym,
          increasing_line_color="#00E676",
          decreasing_line_color="#FF5252",
      ),
      row=1,
      col=1,
  )

  fig.add_trace(
      go.Scatter(
          x=df["Time"],
          y=df["VWAP"],
          mode="lines",
          name="VWAP",
          line=dict(color="#FFD700", width=1.3),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df["Time"],
          y=df["EMA20"],
          mode="lines",
          name="20 EMA",
          line=dict(color="#29B6F6", width=1.3),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Bar(
          x=df["Time"],
          y=df["Volume"],
          name="Volume",
          marker_color=v_col,
      ),
      row=2,
      col=1,
  )

  fig.add_hline(
      y=suggested_entry,
      line_dash="solid",
      line_color="#FFD700",
      line_width=1.6,
      annotation_text=f"🟡 BUY: ₹{suggested_entry:,.2f}",
      annotation_position="bottom left",
      annotation_font_color="#FFD700",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=initial_sl,
      line_dash="solid",
      line_color="#FF5252",
      line_width=1.6,
      annotation_text=f"🛑 SL: ₹{initial_sl:,.2f}",
      annotation_position="bottom right",
      annotation_font_color="#FF5252",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=target_1,
      line_dash="dash",
      line_color="#29B6F6",
      line_width=1.4,
      annotation_text=f"🎯 T1: ₹{target_1:,.2f}",
      annotation_position="top left",
      annotation_font_color="#29B6F6",
      row=1,
      col=1,
  )
  fig.add_hline(
      y=target_2,
      line_dash="dash",
      line_color="#00E676",
      line_width=1.4,
      annotation_text=f"🚀 T2: ₹{target_2:,.2f}",
      annotation_position="top right",
      annotation_font_color="#00E676",
      row=1,
      col=1,
  )

  rb = [dict(bounds=["sat", "mon"])]
  if tf_choice != "1D":
    rb.append(dict(bounds=[15.5, 9.25], pattern="hour"))

  tv_tickformats = [
      dict(dtickrange=[None, 86400000], value="%H:%M<br>%d %b"),
      dict(dtickrange=[86400000, "M1"], value="%d %b<br>%Y"),
      dict(dtickrange=["M1", None], value="%b '%y"),
  ]

  fig.update_layout(
      title=(
          f"{active_sym} ({sector_name}) ({tf_choice}) | LTP: ₹{ltp:,.2f} |"
          " Yellow: VWAP | Blue: 20 EMA"
      ),
      template="plotly_dark",
      height=640,
      dragmode="pan",
      hovermode="x unified",
      showlegend=False,
      margin=dict(l=10, r=65, t=45, b=35),
      yaxis=dict(
          side="right",
          title="Price (₹)",
          showgrid=True,
          gridcolor="rgba(255,255,255,0.06)",
      ),
      yaxis2=dict(side="right", title="Volume", showgrid=False),
      xaxis=dict(
          rangeslider_visible=False,
          rangebreaks=rb,
          tickformatstops=tv_tickformats,
          showgrid=True,
          gridcolor="rgba(255,255,255,0.06)",
      ),
      xaxis2=dict(
          rangeslider_visible=False,
          rangebreaks=rb,
          tickformatstops=tv_tickformats,
          showgrid=True,
          gridcolor="rgba(255,255,255,0.06)",
      ),
  )

  st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
