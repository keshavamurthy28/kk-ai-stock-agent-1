import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market-Wide Volume Surge & Action Agent", layout="wide")

st.title("⚡ Market-Wide Volume Surge & Institutional Action Scanner")
st.write(
    "Automatically scans the NSE universe for abnormal volume spikes, calculates"
    " actionable Buy/Sell levels, sets stop-losses, and analyzes the "
    "catalyst/reason behind the surge."
)

# Sidebar Configuration for Market Universe & Thresholds
st.sidebar.header("⚙️ Scanner Controls")
universe_choice = st.sidebar.selectbox(
    "Select Stock Universe", ["Nifty 50 Core", "Nifty 500 (Extended Universe)"]
)
volume_multiplier = st.sidebar.slider(
    "Volume Surge Threshold (x times 30D average)", 1.5, 5.0, 2.0
)


@st.cache_data(ttl=86400)
def get_stock_universe(universe_type):
  if universe_type == "Nifty 50 Core":
    return [
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "LTIM.NS",
        "LT.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "HINDUNILVR.NS",
        "BAJFINANCE.NS",
        "ASIANPAINT.NS",
        "MARUTI.NS",
        "SUNPHARMA.NS",
        "TITAN.NS",
        "TATAMOTORS.NS",
        "NTPC.NS",
    ]
  else:
    # Expanded Nifty sample / top high-liquidity stocks
    return [
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "LT.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "ZOMATO.NS",
        "PAYTM.NS",
        "NYKAA.NS",
        "POLICYBZR.NS",
        "TATAMOTORS.NS",
        "MARUTI.NS",
        "SUNPHARMA.NS",
        "TITAN.NS",
        "BAJFINANCE.NS",
        "ADANIENT.NS",
        "ADANIPORTS.NS",
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "GRASIM.NS",
        "POWERGRID.NS",
        "NTPC.NS",
        "COALINDIA.NS",
        "ONGC.NS",
        "BPCL.NS",
        "HEROMOTOCO.NS",
        "EICHERMOT.NS",
        "BAJAJ-AUTO.NS",
        "M&M.NS",
    ]


if st.button("🚀 Run Market-Wide Volume Scan"):
  tickers = get_stock_universe(universe_choice)
  surge_results = []

  progress_bar = st.progress(0)
  status_text = st.empty()

  total_stocks = len(tickers)
  for idx, ticker in enumerate(tickers):
    status_text.text(
        f"Scanning {ticker} ({idx + 1}/{total_stocks})..."
    )
    progress_bar.progress((idx + 1) / total_stocks)

    try:
      # Fetch 2 months of historical data to compute 30D average volume & ATR
      hist = yf.Ticker(ticker).history(period="2mo")
      if len(hist) >= 30:
        # Exclude today to calculate baseline 30-day average volume
        avg_vol_30d = hist["Volume"].iloc[-30:-1].mean()
        latest_vol = hist["Volume"].iloc[-1]
        latest_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        price_change_pct = ((latest_close - prev_close) / prev_close) * 100

        # Calculate Average True Range (ATR) or volatility for stop-loss
        high_low = hist["High"] - hist["Low"]
        high_close = abs(hist["High"] - hist["Close"].shift())
        low_close = abs(hist["Low"] - hist["Close"].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(
            axis=1
        )
        atr = true_range.iloc[-14:].mean()

        # Check if volume crosses the surge threshold
        if latest_vol >= (avg_vol_30d * volume_multiplier):
          surge_ratio = round(latest_vol / avg_vol_30d, 2)

          # Determine Signal, Stop-Loss, Target, and Why it surged
          if price_change_pct >= 1.5:
            signal = "BUY / MOMENTUM BREAKOUT"
            stop_loss = round(latest_close - (1.5 * atr), 2)
            target = round(latest_close + (3.0 * atr), 2)
            catalyst = (
                f"Heavy institutional buying pressure. Volume is {surge_ratio}x"
                f" above normal with a strong price rally (+{round(price_change_pct, 2)}%)."
            )
          elif price_change_pct <= -1.5:
            signal = "SELL / DISTRIBUTION TRAP"
            stop_loss = round(latest_close + (1.5 * atr), 2)
            target = round(latest_close - (3.0 * atr), 2)
            catalyst = (
                f"Heavy institutional selling/dumping. Volume is {surge_ratio}x"
                f" normal amid sharp price correction ({round(price_change_pct, 2)}%)."
            )
          else:
            signal = "ACCUMULATION / CONSOLIDATION"
            stop_loss = round(latest_close - (1.2 * atr), 2)
            target = round(latest_close + (2.0 * atr), 2)
            catalyst = (
                f"Unusual volume spike ({surge_ratio}x average) with tight price"
                " range. Indicates block accumulation or institutional positioning"
                " before a breakout."
            )

          surge_results.append({
              "Ticker": ticker.replace(".NS", ""),
              "LTP (₹)": round(latest_close, 2),
              "Price Change (%)": round(price_change_pct, 2),
              "Surge Ratio": f"{surge_ratio}x",
              "Action Signal": signal,
              "Stop-Loss (₹)": stop_loss,
              "Target (₹)": target,
              "Why Volume Surged (Catalyst)": catalyst,
          })
    except Exception:
      continue

  progress_bar.empty()
  status_text.empty()

  if surge_results:
    res_df = pd.DataFrame(surge_results)
    st.success(
        f"Scan Complete! Found {len(res_df)} stocks experiencing a major volume"
        " surge."
    )
    st.dataframe(res_df, use_container_width=True)
  else:
    st.warning(
        "No stocks crossed the volume surge threshold today matching your"
        " criteria. Try lowering the threshold slider."
    )
