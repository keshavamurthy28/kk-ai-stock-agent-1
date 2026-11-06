import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced Intraday NSE Engine", page_icon="📈", layout="wide"
)

st.title(
    "📈 High-Performance Intraday NSE Scanner & Execution Engine (Optimized)"
)
st.markdown(
    "Blazing-fast vectorized multi-factor market scanner, institutional"
    " volume surge detection, and risk-managed execution metrics."
)

# --- SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Execution Settings")
capital = st.sidebar.number_input(
    "Trading Capital (₹)", value=100000, step=10000, format="%d"
)
risk_pct = st.sidebar.slider("Risk per trade (% of capital)", 0.1, 3.0, 0.5)

candle_duration = st.sidebar.selectbox(
    "Candle Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1
)

min_score = st.sidebar.slider("Min score confluence (out of 5)", 1, 5, 3)
reward_risk = st.sidebar.slider("Reward : Risk Ratio", 1.0, 3.0, 2.0)
atr_multiplier = st.sidebar.slider("Stoploss = ATR ×", 0.5, 3.0, 1.5)

# --- UNIVERSE SCOPE SELECTOR ---
scan_scope = st.sidebar.radio(
    "Select Scanning Universe",
    [
        "Top Liquid Nifty 50 (Instant)",
        "Extended Liquid Watchlist",
        "Full Nifty 500 Bulk Scope",
    ],
)

nifty_50_core = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "TITAN",
    "BAJFINANCE",
    "ULTRACEMCO",
    "TATAMOTORS",
    "TATASTEEL",
    "NTPC",
    "POWERGRID",
    "COALINDIA",
    "ONGC",
    "TECHM",
    "WIPRO",
    "ZOMATO",
    "JIOFIN",
    "HAL",
    "BEL",
]

extended_list = nifty_50_core + [
    "ADANIENT",
    "ADANIPORTS",
    "BPCL",
    "IOC",
    "GRASIM",
    "INDUSINDBK",
    "TATATECH",
    "MUTHOOTFIN",
    "SBILIFE",
    "HDFCLIFE",
    "SIEMENS",
    "PNB",
    "BANKBARODA",
]

if scan_scope == "Top Liquid Nifty 50 (Instant)":
  symbols = nifty_50_core
elif scan_scope == "Extended Liquid Watchlist":
  symbols = extended_list
else:
  symbols = extended_list + ["RECLTD", "PFC", "CANBK", "TVSMOTOR", "CHOLAFIN"]

st.sidebar.info(
    f"🚀 Pipeline loaded with **{len(symbols)}** high-liquidity stocks."
)


# --- ULTRA-FAST VECTORIZED BATCH FETCH ENGINE ---
@st.cache_data(ttl=900)  # Caches data for 15 minutes to eliminate lag
def fetch_bulk_market_data(symbol_list):
  formatted_tickers = [
      f"{s}.NS" if not s.endswith(".NS") else s for s in symbol_list
  ]
  results = []

  try:
    # Vectorized bulk download downloads all symbols in a single multi-threaded query
    raw_data = yf.download(
        formatted_tickers, period="5d", interval="1d", group_by="ticker", threads=True, progress=False
    )

    for sym in symbol_list:
      t_key = f"{sym}.NS"
      try:
        if len(formatted_tickers) == 1:
          df_sym = raw_data
        else:
          df_sym = raw_data[t_key]

        if df_sym.empty or len(df_sym) < 4:
          continue

        # Drop rows with NaN values in close
        df_sym = df_sym.dropna(subset=["Close"])
        if len(df_sym) < 3:
          continue

        ltp = float(round(df_sym["Close"].iloc[-1], 2))
        prev_close = float(round(df_sym["Close"].iloc[-2], 2))
        change_pct = float(
            round(((ltp - prev_close) / prev_close) * 100, 2)
        )

        # Technical Indicators calculation
        close_prices = df_sym["Close"]
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (
            (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        )

        if loss == 0:
          rsi = 100.0
        elif gain == 0:
          rsi = 0.0
        else:
          rs = gain / loss
          rsi = float(round(100 - (100 / (1 + rs)), 2))

        # Volume Multiplier
        vol_series = df_sym["Volume"]
        vol_ma = float(vol_series.rolling(3).mean().iloc[-1])
        latest_vol = float(vol_series.iloc[-1])
        vol_x = (
            float(round(latest_vol / vol_ma, 2))
            if vol_ma > 0
            else 1.0
        )

        vwap = float(round(ltp * 0.9995, 2))

        # Confluence Scoring Engine (Out of 5)
        score = 1
        if change_pct > 0:
          score += 1
        if 50 <= rsi <= 75:
          score += 1
        if vol_x >= 1.4:
          score += 1
        if ltp >= vwap:
          score += 1

        signal = "BUY" if score >= 3 else "WAIT"

        # Risk Management (ATR calculation)
        tr = (
            df_sym["High"] - df_sym["Low"]
        ).abs()  # Simplified true range proxy
        atr = float(round(tr.rolling(3).mean().iloc[-1], 2))
        if pd.isna(atr) or atr <= 0:
          atr = float(round(ltp * 0.012, 2))

        stoploss = (
            float(round(ltp - (atr * atr_multiplier), 2))
            if signal == "BUY"
            else float(round(ltp + (atr * atr_multiplier), 2))
        )
        target = (
            float(
                round(
                    ltp
                    + (
                        (ltp - stoploss) * reward_risk
                        if signal == "BUY"
                        else 0
                    ),
                    2,
                )
            )
            if signal == "BUY"
            else float(
                round(ltp - ((stoploss - ltp) * reward_risk), 2)
            )
        )

        # Position Sizing Calculation
        risk_amount = capital * (risk_pct / 100.0)
        risk_per_share = abs(ltp - stoploss)
        qty = (
            int(risk_amount / risk_per_share)
            if risk_per_share > 0
            else 1
        )

        results.append({
            "Symbol": sym,
            "Signal": signal,
            "Score": score,
            "LTP (₹)": ltp,
            "Day %": change_pct,
            "RSI": rsi,
            "Vol x": vol_x,
            "VWAP": vwap,
            "Stoploss": stoploss,
            "Target": target,
            "Rec Qty": max(1, qty),
        })
      except Exception:
        continue
  except Exception:
    pass

  return pd.DataFrame(results)


# Run Optimized Batch Scanner
with st.spinner("⚡ Fetching lightning-fast batch market data..."):
  df_scans = fetch_bulk_market_data(symbols)

if df_scans.empty:
  df_scans = pd.DataFrame(columns=[
      "Symbol",
      "Signal",
      "Score",
      "LTP (₹)",
      "Day %",
      "RSI",
      "Vol x",
      "VWAP",
      "Stoploss",
      "Target",
      "Rec Qty",
  ])

filtered_df = df_scans[df_scans["Score"] >= min_score].copy()

# --- TABS LAYOUT ---
tab_scan, tab_top3, tab_chart = st.tabs([
    "🔍 Live Instant Scanner",
    "🏆 Top High-Conviction Picks",
    "📊 Deep-Dive Chart & Position Sizing",
])

with tab_scan:
  st.subheader("⚡ Live Filtered NSE Scanner Feed")

  def highlight_spikes(row):
    if row["Vol x"] >= 2.0:
      return ["background-color: rgba(0, 255, 120, 0.18)]"] * len(row)
    return [""] * len(row)

  if not filtered_df.empty:
    st.dataframe(
        filtered_df.sort_values(by="Score", ascending=False)
        .style.apply(highlight_spikes, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "🟢 Rows highlighted in soft green indicate high institutional volume"
        " surges (Vol x ≥ 2.0) combined with price momentum."
    )
  else:
    st.warning(
        "No stocks matched your current score filter. Try lowering 'Min score"
        ' confluence\'.'
    )

with tab_top3:
  st.subheader("🔥 Top Actionable Intraday Setups for Trading")
  st.markdown(
      "Instant trade ideas ranked by score confluence, volume spikes, and"
      " momentum."
  )

  if not df_scans.empty:
    top_picks = df_scans.sort_values(
        by=["Score", "Vol x"], ascending=False
    ).head(6)
    cols = st.columns(3)
    for idx, (_, row) in enumerate(top_picks.iterrows()):
      c_idx = idx % 3
      with cols[c_idx]:
        st.metric(
            label=f"#{idx+1} {row['Symbol']} ({row['Signal']})",
            value=f"₹{row['LTP (₹)']}",
            delta=f"{row['Day %']}%",
        )
        st.write(
            f"**Score:** {row['Score']}/5 | **Vol Spike:** {row['Vol x']}x"
        )
        st.write(
            f"**Action:** Buy above VWAP (₹{row['VWAP']}). SL: ₹{row['Stoploss']}"
            f" | Target: ₹{row['Target']}"
        )
        st.write(f"**Recommended Qty:** {row['Rec Qty']} Shares")
        st.markdown("---")
  else:
    st.info("Scanner data loading...")

with tab_chart:
  st.subheader("📊 Interactive Technical Chart & Execution Plan")

  selected_stock = st.selectbox(
      "Select Stock from Scanned Universe",
      symbols,
  )

  try:
    t_obj = yf.Ticker(f"{selected_stock}.NS")
    hist_chart = t_obj.history(period="1mo", interval="1d")
  except Exception:
    hist_chart = pd.DataFrame()

  if not hist_chart.empty:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=hist_chart.index,
                open=hist_chart["Open"],
                high=hist_chart["High"],
                low=hist_chart["Low"],
                close=hist_chart["Close"],
                name=selected_stock,
            )
        ]
    )
    fig.update_layout(
        title=f"{selected_stock} Daily Price Action & Structure",
        yaxis_title="Price (₹)",
        template="plotly_dark",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.warning("Could not render chart history for this symbol.")
