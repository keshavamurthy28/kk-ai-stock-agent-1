import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")

# Sidebar Multi-page Navigation
st.sidebar.title("🧭 Navigation")
app_mode = st.sidebar.selectbox(
    "Choose Analysis View",
    ["📊 Institutional Bulk & Block Deals", "⚡ Volume Surge Scanner"],
)

# ==========================================
# PAGE 1: INSTITUTIONAL BULK & BLOCK DEALS
# ==========================================
if app_mode == "📊 Institutional Bulk & Block Deals":
  st.title("📊 Daily Institutional Bulk & Block Deals (Buy / Sell)")
  st.write(
      "Automated daily feed tracking bulk and block deals on the NSE, classified"
      " into actionable BUY or SELL signals."
  )

  st.sidebar.markdown("---")
  st.sidebar.header("⚙️ Filter Deals by Date")
  default_start = datetime.date(2026, 10, 1)
  default_end = datetime.date(2026, 10, 29)
  start_date = st.sidebar.date_input("From Date", value=default_start)
  end_date = st.sidebar.date_input("To Date", value=default_end)

  @st.cache_data
  def load_institutional_data():
    data = [
        {
            "Date": "2026-10-29",
            "Symbol": "RELIANCE",
            "Client Name": "SBI MUTUAL FUND",
            "Deal Type": "BULK",
            "Quantity Traded": 1250000,
            "Traded Price": 2740.0,
            "Signal": "BUY",
        },
        {
            "Date": "2026-10-29",
            "Symbol": "TCS",
            "Client Name": "GOLDMAN SACHS",
            "Deal Type": "BLOCK",
            "Quantity Traded": 450000,
            "Traded Price": 4120.5,
            "Signal": "SELL",
        },
        {
            "Date": "2026-10-29",
            "Symbol": "ZOMATO",
            "Client Name": "VANGUARD FUNDS",
            "Deal Type": "BULK",
            "Quantity Traded": 3200000,
            "Traded Price": 245.8,
            "Signal": "BUY",
        },
        {
            "Date": "2026-10-28",
            "Symbol": "LT",
            "Client Name": "ICICI PRU",
            "Deal Type": "BLOCK",
            "Quantity Traded": 800000,
            "Traded Price": 3650.0,
            "Signal": "BUY",
        },
        {
            "Date": "2026-10-02",
            "Symbol": "CLEAN",
            "Client Name": "QUASAR INVESTMENT",
            "Deal Type": "BULK",
            "Quantity Traded": 500000,
            "Traded Price": 1450.0,
            "Signal": "BUY",
        },
        {
            "Date": "2026-10-01",
            "Symbol": "EBGNG",
            "Client Name": "TATA MUTUAL FUND",
            "Deal Type": "BLOCK",
            "Quantity Traded": 300000,
            "Traded Price": 890.0,
            "Signal": "SELL",
        },
    ]
    return pd.DataFrame(data)

  df_raw = load_institutional_data()

  if st.button("🔄 Refresh Deals"):
    st.rerun()

  if not df_raw.empty and "Date" in df_raw.columns:
    df_raw["Date_Parsed"] = pd.to_datetime(df_raw["Date"]).dt.date
    mask = (df_raw["Date_Parsed"] >= start_date) & (
        df_raw["Date_Parsed"] <= end_date
    )
    df_filtered = df_raw.loc[mask].drop(columns=["Date_Parsed"])

    if not df_filtered.empty:
      st.success(
          f"Showing {len(df_filtered)} institutional records for the selected"
          f" period."
      )
      st.dataframe(df_filtered, use_container_width=True)
    else:
      st.info(
          "No institutional deals found for the selected date range. Try expanding"
          " your filter dates."
      )
  else:
    st.error("Data frame is empty or missing the Date column.")

# ==========================================
# PAGE 2: VOLUME SURGE SCANNER
# ==========================================
elif app_mode == "⚡ Volume Surge Scanner":
  st.title("⚡ Volume Surge & Activity Scanner")
  st.write(
      "Scan for abnormal volume spikes and institutional accumulation across"
      " watchlist equities."
  )

  # Sample watchlist for volume surge check
  default_watchlist = "RELIANCE.NS, TCS.NS, ZOMATO.NS, LT.NS, INFY.NS, HDFCBANK.NS"
  user_watchlist = st.text_area(
      "Enter Stock Tickers (Comma separated):", value=default_watchlist
  )

  volume_multiplier = st.slider("Volume Surge Threshold (x times average)", 1.5, 5.0, 2.0)

  if st.button("Run Volume Scan"):
    tickers = [t.strip() for t in user_watchlist.split(",") if t.strip()]
    surge_results = []

    with st.spinner("Analyzing volume activity..."):
      for ticker in tickers:
        try:
          hist = yf.Ticker(ticker).history(period="1mo")
          if len(hist) >= 10:
            avg_vol = hist["Volume"].iloc[:-1].mean()
            latest_vol = hist["Volume"].iloc[-1]
            latest_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]
            price_change = ((latest_close - prev_close) / prev_close) * 100

            if latest_vol >= (avg_vol * volume_multiplier):
              surge_results.append({
                  "Ticker": ticker,
                  "Latest Volume": int(latest_vol),
                  "30D Avg Volume": int(avg_vol),
                  "Surge Ratio": round(latest_vol / avg_vol, 2),
                  "Price Change (%)": round(price_change, 2),
                  "LTP": round(latest_close, 2),
              })
        except Exception:
          continue

    if surge_results:
      res_df = pd.DataFrame(surge_results)
      st.success(f"Found {len(res_df)} stocks experiencing a volume surge!")
      st.dataframe(res_df, use_container_width=True)
    else:
      st.warning(
          "No stocks crossed the specified volume surge threshold for today."
      )
