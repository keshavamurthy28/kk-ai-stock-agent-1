import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced SMC & FVG Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS to make the chart toolbar look clean & compact like Zerodha Kite
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
        div[data-testid="stHorizontalBlock"] { align-items: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- TOP BAR: SYMBOL INPUT & CANDLE INTERVALS (Like Kite Top Bar) ---
top_col1, top_col2, top_col3 = st.columns([2, 6, 2])

with top_col1:
  stock_input = (
      st.text_input(
          "NSE Symbol",
          value="RELIANCE",
          label_visibility="collapsed",
          placeholder="Enter Symbol (e.g., AMBER, RELIANCE)",
      )
      .upper()
      .strip()
  )

ticker_symbol = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

with top_col2:
  # Top Interval Selector: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1D, 1W
  interval_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"]
  selected_tf = st.radio(
      "Candle Interval",
      options=interval_options,
      index=2,  # Default to 15m for execution view
      horizontal=True,
      label_visibility="collapsed",
  )

with top_col3:
  show_mtf_zones = st.toggle("Show 1D & 4H Zones", value=True)


# --- DATA FETCHING & RESAMPLING ENGINE ---
@st.cache_data(ttl=60)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
  try:
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if df.empty:
      return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    # Normalize datetime column name
    dt_col = "Datetime" if "Datetime" in df.columns else "Date"
    df.rename(columns={dt_col: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
      df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df
  except Exception:
    return pd.DataFrame()


def get_timeframe_data(ticker: str, tf: str) -> pd.DataFrame:
  # Maps execution timeframe to optimal yfinance period & interval
  config = {
      "1m": ("5d", "1m"),
      "5m": ("15d", "5m"),
      "15m": ("30d", "15m"),
      "30m": ("30d", "30m"),
      "1h": ("60d", "1h"),
      "4h": ("60d", "1h"),  # Resampled below
      "1D": ("2y", "1d"),
      "1W": ("5y", "1wk"),
  }
  period, yf_int = config.get(tf, ("30d", "15m"))
  df = fetch_data(ticker, period, yf_int)

  if not df.empty and tf == "4h":
    df = (
        df.set_index("Time")
        .resample("4h")
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


# --- SMC DETECTION FUNCTIONS (FVG, SWINGS, CHoCH) ---
def detect_fvgs(df: pd.DataFrame, max_zones: int = 3):
  """Detects genuine 3-candle institutional Fair Value Gaps."""
  bull_fvgs, bear_fvgs = [], []
  for i in range(2, len(df)):
    # Bullish FVG: Candle[i].Low > Candle[i-2].High
    if df["Low"].iloc[i] > df["High"].iloc[i - 2]:
      bull_fvgs.append({
          "start": df["Time"].iloc[i - 2],
          "y0": float(df["High"].iloc[i - 2]),
          "y1": float(df["Low"].iloc[i]),
      })
    # Bearish FVG: Candle[i].High < Candle[i-2].Low
    if df["High"].iloc[i] < df["Low"].iloc[i - 2]:
      bear_fvgs.append({
          "start": df["Time"].iloc[i - 2],
          "y0": float(df["High"].iloc[i]),
          "y1": float(df["Low"].iloc[i - 2]),
      })
  return bull_fvgs[-max_zones:], bear_fvgs[-max_zones:]


def detect_structure_and_signals(df: pd.DataFrame, lookback: int = 5):
  """Detects Swing Highs/Lows, CHoCH (Change of Character), and Buy/Sell triggers."""
  df = df.copy()
  df["Swing_High"] = df["High"] == df["High"].rolling(
      2 * lookback + 1, center=True
  ).max()
  df["Swing_Low"] = df["Low"] == df["Low"].rolling(
      2 * lookback + 1, center=True
  ).min()

  signals = []
  last_sh = None
  last_sl = None
  trend = "neutral"  # 'bullish' or 'bearish'

  for i in range(lookback, len(df)):
    if df["Swing_High"].iloc[i - lookback]:
      last_sh = (
          df["Time"].iloc[i - lookback],
          float(df["High"].iloc[i - lookback]),
      )
    if df["Swing_Low"].iloc[i - lookback]:
      last_sl = (
          df["Time"].iloc[i - lookback],
          float(df["Low"].iloc[i - lookback]),
      )

    close_p = float(df["Close"].iloc[i])
    prev_close = float(df["Close"].iloc[i - 1])
    curr_time = df["Time"].iloc[i]

    # Bullish CHoCH: Price breaks above previous lower-high in a downtrend
    if last_sh and prev_close <= last_sh[1] and close_p > last_sh[1]:
      label = "Bullish CHoCH" if trend != "bullish" else "BOS"
      sl_price = (
          last_sl[1] * 0.998 if last_sl else float(df["Low"].iloc[i]) * 0.995
      )
      signals.append({
          "time": curr_time,
          "price": float(df["Low"].iloc[i]),
          "type": "BUY",
          "structure": label,
          "struct_x0": last_sh[0],
          "struct_y": last_sh[1],
          "sl": round(sl_price, 2),
      })
      trend = "bullish"
      last_sh = None  # Reset so it doesn't re-trigger on same swing

    # Bearish CHoCH: Price breaks below previous higher-low in an uptrend
    elif last_sl and prev_close >= last_sl[1] and close_p < last_sl[1]:
      label = "Bearish CHoCH" if trend != "bearish" else "BOS"
      sl_price = (
          last_sh[1] * 1.002 if last_sh else float(df["High"].iloc[i]) * 1.005
      )
      signals.append({
          "time": curr_time,
          "price": float(df["High"].iloc[i]),
          "type": "SELL",
          "structure": label,
          "struct_x0": last_sl[0],
          "struct_y": last_sl[1],
          "sl": round(sl_price, 2),
      })
      trend = "bearish"
      last_sl = None

  return signals


# --- LOAD MULTI-TIMEFRAME DATA ---
df_exec = get_timeframe_data(ticker_symbol, selected_tf)
df_daily = fetch_data(ticker_symbol, "6mo", "1d")
df_4h = get_timeframe_data(ticker_symbol, "4h")

if df_exec.empty or len(df_exec) < 15:
  st.warning(
      f"No data found for **{ticker_symbol}** on **{selected_tf}**. Try"
      " switching to `15m`, `1h`, or `1D`."
  )
else:
  # 1. Macro 1D Levels
  d1_res = (
      float(df_daily["High"].tail(60).max())
      if not df_daily.empty
      else float(df_exec["High"].max())
  )
  d1_sup = (
      float(df_daily["Low"].tail(60).min())
      if not df_daily.empty
      else float(df_exec["Low"].min())
  )
  ltp = float(df_exec["Close"].iloc[-1])

  # 2. 4H Institutional FVGs
  bull_fvgs_4h, bear_fvgs_4h = (
      detect_fvgs(df_4h, max_zones=2) if not df_4h.empty else ([], [])
  )

  # 3. Execution Timeframe Structure (CHoCH & Entry/SL Points)
  signals = detect_structure_and_signals(df_exec, lookback=4)

  # --- BUILD TRADINGVIEW / KITE STYLE CHART ---
  fig = go.Figure()

  # Candlestick Trace
  fig.add_trace(
      go.Candlestick(
          x=df_exec["Time"],
          open=df_exec["Open"],
          high=df_exec["High"],
          low=df_exec["Low"],
          close=df_exec["Close"],
          name=stock_input,
          increasing_line_color="#089981",
          increasing_fillcolor="#089981",
          decreasing_line_color="#F23645",
          decreasing_fillcolor="#F23645",
      )
  )

  x_end = df_exec["Time"].iloc[-1]
  x_start = df_exec["Time"].iloc[0]

  # Overlay 1D S/R & 4H FVGs
  if show_mtf_zones:
    fig.add_hline(
        y=d1_res,
        line_dash="dash",
        line_color="#F23645",
        line_width=1.5,
        annotation_text=f"1D Supply/Resistance: ₹{d1_res:,.2f}",
        annotation_position="top left",
    )
    fig.add_hline(
        y=d1_sup,
        line_dash="dash",
        line_color="#089981",
        line_width=1.5,
        annotation_text=f"1D Demand/Support: ₹{d1_sup:,.2f}",
        annotation_position="bottom left",
    )

    # Plot 4H Bullish FVGs
    for idx, fvg in enumerate(bull_fvgs_4h):
      fig.add_shape(
          type="rect",
          x0=max(fvg["start"], x_start),
          x1=x_end,
          y0=fvg["y0"],
          y1=fvg["y1"],
          fillcolor="rgba(8, 153, 129, 0.18)",
          line=dict(color="rgba(8, 153, 129, 0.5)", width=1),
          layer="below",
      )
      fig.add_annotation(
          x=x_end,
          y=(fvg["y0"] + fvg["y1"]) / 2,
          text=f"4H Bull FVG ({fvg['y0']:.0f}-{fvg['y1']:.0f})",
          showarrow=False,
          xanchor="right",
          font=dict(color="#089981", size=10),
      )

    # Plot 4H Bearish FVGs
    for idx, fvg in enumerate(bear_fvgs_4h):
      fig.add_shape(
          type="rect",
          x0=max(fvg["start"], x_start),
          x1=x_end,
          y0=fvg["y0"],
          y1=fvg["y1"],
          fillcolor="rgba(242, 54, 69, 0.18)",
          line=dict(color="rgba(242, 54, 69, 0.5)", width=1),
          layer="below",
      )
      fig.add_annotation(
          x=x_end,
          y=(fvg["y0"] + fvg["y1"]) / 2,
          text=f"4H Bear FVG ({fvg['y0']:.0f}-{fvg['y1']:.0f})",
          showarrow=False,
          xanchor="right",
          font=dict(color="#F23645", size=10),
      )

  # Plot CHoCH Lines + Buy/Sell Badges + Stop-Loss Markers
  buy_x, buy_y, buy_text = [], [], []
  sell_x, sell_y, sell_text = [], [], []

  for sig in signals[-8:]:  # Show recent 8 structure signals to prevent clutter
    line_col = "#089981" if sig["type"] == "BUY" else "#F23645"
    # Draw Horizontal CHoCH / BOS structural break line
    fig.add_shape(
        type="line",
        x0=sig["struct_x0"],
        x1=sig["time"],
        y0=sig["struct_y"],
        y1=sig["struct_y"],
        line=dict(color=line_col, width=1.2, dash="dot"),
    )
    fig.add_annotation(
        x=sig["time"],
        y=sig["struct_y"],
        text=sig["structure"],
        showarrow=False,
        yshift=8 if sig["type"] == "BUY" else -8,
        font=dict(size=9, color=line_col),
    )

    if sig["type"] == "BUY":
      buy_x.append(sig["time"])
      buy_y.append(sig["price"] * 0.997)
      buy_text.append(f"BUY @ ₹{sig['price']:.2f}<br>SL: ₹{sig['sl']:.2f}")
    else:
      sell_x.append(sig["time"])
      sell_y.append(sig["price"] * 1.003)
      sell_text.append(f"SELL @ ₹{sig['price']:.2f}<br>SL: ₹{sig['sl']:.2f}")

  if buy_x:
    fig.add_trace(
        go.Scatter(
            x=buy_x,
            y=buy_y,
            mode="markers+text",
            name="Buy Trigger",
            text=["▲ BUY"] * len(buy_x),
            textposition="bottom center",
            hovertext=buy_text,
            hoverinfo="text",
            marker=dict(symbol="triangle-up", size=12, color="#00E676"),
            textfont=dict(color="#00E676", size=11, family="Arial Black"),
        )
    )

  if sell_x:
    fig.add_trace(
        go.Scatter(
            x=sell_x,
            y=sell_y,
            mode="markers+text",
            name="Sell Trigger",
            text=["▼ SELL"] * len(sell_x),
            textposition="top center",
            hovertext=sell_text,
            hoverinfo="text",
            marker=dict(symbol="triangle-down", size=12, color="#FF5252"),
            textfont=dict(color="#FF5252", size=11, family="Arial Black"),
        )
    )

  # Highlight Latest Signal's Exact Entry & Stop-Loss Line on Chart
  latest_sig = signals[-1] if signals else None
  if latest_sig:
    fig.add_hline(
        y=latest_sig["sl"],
        line_dash="solid",
        line_color="#FF9800",
        line_width=1.5,
        annotation_text=f"🛑 Active Stop-Loss: ₹{latest_sig['sl']:,.2f}",
        annotation_position="bottom right",
        annotation_font_color="#FF9800",
    )

  # --- REMOVE WEEKEND / AFTER-HOURS GAPS FOR CLEAN INTRADAY CANDLES ---
  rangebreaks = [dict(bounds=["sat", "mon"])]
  if selected_tf in ["1m", "5m", "15m", "30m", "1h", "4h"]:
    rangebreaks.append(dict(bounds=[15.5, 9.25], pattern="hour"))

  # --- KITE-LIKE INTERACTIVE ZOOM & BOTTOM DATE RANGE BUTTONS ---
  fig.update_layout(
      title=dict(
          text=(
              f"<b>{stock_input} · {selected_tf} · NSE</b> | LTP:"
              f" ₹{ltp:,.2f}"
          ),
          font=dict(size=16),
      ),
      template="plotly_dark",
      height=680,
      dragmode="pan",  # Click & drag pans smoothly like TradingView
      hovermode="x unified",
      margin=dict(l=10, r=60, t=50, b=40),
      yaxis=dict(
          side="right",  # Price axis on the right like Kite/TradingView
          title="Price (₹)",
          fixedrange=False,
          gridcolor="rgba(255,255,255,0.06)",
      ),
      xaxis=dict(
          rangeslider=dict(visible=False),
          rangebreaks=rangebreaks,
          gridcolor="rgba(255,255,255,0.06)",
          # Bottom Quick-Zoom Buttons (1D, 5D, 1M, 3M, 6M, YTD, 1Y, All)
          rangeselector=dict(
              buttons=list([
                  dict(count=1, label="1D", step="day", stepmode="backward"),
                  dict(count=5, label="5D", step="day", stepmode="backward"),
                  dict(count=1, label="1M", step="month", stepmode="backward"),
                  dict(count=3, label="3M", step="month", stepmode="backward"),
                  dict(count=6, label="6M", step="month", stepmode="backward"),
                  dict(count=1, label="YTD", step="year", stepmode="todate"),
                  dict(count=1, label="1Y", step="year", stepmode="backward"),
                  dict(step="all", label="All"),
              ]),
              bgcolor="#1E222D",
              activecolor="#2962FF",
              font=dict(color="white", size=11),
              x=0.0,
              y=-0.12,  # Positioned cleanly at the bottom-left like Kite
          ),
      ),
      legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
  )

  # Enable Mouse Scroll Wheel Zoom
  st.plotly_chart(
      fig,
      use_container_width=True,
      config={
          "scrollZoom": True,
          "displayModeBar": True,
          "modeBarButtonsToRemove": ["lasso2d", "select2d"],
      },
  )

  # --- MULTI-TIMEFRAME TOP-DOWN WORKFLOW BREAKDOWN (1D -> 4H -> 15m) ---
  st.markdown("---")
  st.subheader("🧭 Top-Down Institutional Execution Plan (1D ➔ 4H ➔ 15m)")

  step1, step2, step3, step4 = st.columns(4)

  # Step 1: 1D Bias
  midpoint = (d1_res + d1_sup) / 2
  d1_bias = (
      "Bullish (Discount Zone)" if ltp < midpoint else "Bearish (Premium Zone)"
  )
  step1.metric(
      "1️⃣ 1D Macro Bias",
      d1_bias,
      f"Sup: ₹{d1_sup:,.0f} | Res: ₹{d1_res:,.0f}",
  )

  # Step 2: 4H FVG Zone
  if bull_fvgs_4h:
    latest_4h_zone = (
        f"₹{bull_fvgs_4h[-1]['y0']:,.0f} - ₹{bull_fvgs_4h[-1]['y1']:,.0f}"
    )
    fvg_label = "4H Bullish FVG"
  elif bear_fvgs_4h:
    latest_4h_zone = (
        f"₹{bear_fvgs_4h[-1]['y0']:,.0f} - ₹{bear_fvgs_4h[-1]['y1']:,.0f}"
    )
    fvg_label = "4H Bearish FVG"
  else:
    latest_4h_zone = "No Unfilled 4H Gap"
    fvg_label = "4H Liquidity"
  step2.metric("2️⃣ 4H POI / FVG Zone", latest_4h_zone, fvg_label)

  # Step 3 & 4: Execution Trigger & Stop-Loss / Target
  if latest_sig:
    action = latest_sig["type"]
    entry = round(latest_sig["price"], 2)
    sl = latest_sig["sl"]
    risk = abs(entry - sl)
    target = (
        round(entry + (risk * 2), 2)
        if action == "BUY"
        else round(entry - (risk * 2), 2)
    )

    step3.metric(
        f"3️⃣ {selected_tf} Trigger ({latest_sig['structure']})",
        f"{action} @ ₹{entry:,.2f}",
        f"Confirmed on {latest_sig['time'].strftime('%d %b %H:%M')}",
    )
    step4.metric(
        "4️⃣ Stop-Loss & 1:2 Target",
        f"SL: ₹{sl:,.2f}",
        f"Target: ₹{target:,.2f}",
    )
  else:
    step3.metric(f"3️⃣ {selected_tf} Trigger", "WAIT", "Awaiting CHoCH")
    step4.metric("4️⃣ Stop-Loss & Target", "Pending", "No active setup")
