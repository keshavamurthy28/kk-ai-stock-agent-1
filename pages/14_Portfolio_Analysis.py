import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Zerodha Portfolio & Technical Analysis Agent", layout="wide"
)

st.title("Zerodha Portfolio Trend & Action Agent")
st.markdown(
    "Upload your Zerodha Console portfolio holdings export file to evaluate"
    " asset performance, track P&L, and screen for technical breakout or"
    " dip-buying opportunities."
)

# Sidebar Controls & Technical Thresholds
st.sidebar.header("⚙️ Portfolio & Technical Rules")
uploaded_holdings = st.sidebar.file_uploader(
    "Upload Zerodha Holdings (.xlsx or .csv)", type=["xlsx", "csv"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Technical Signal Thresholds")
rsi_sell = st.sidebar.slider(
    "RSI Overbought (Sell Limit)", min_value=50, max_value=90, value=70
)
rsi_buy = st.sidebar.slider(
    "RSI Oversold (Dip Limit)", min_value=10, max_value=50, value=30
)

fast_ema = st.sidebar.selectbox("Fast EMA Period", [9, 20, 50], index=1)
slow_ema = st.sidebar.selectbox("Slow EMA Period", [21, 50, 200], index=1)

# Date Range Filter
st.sidebar.markdown("---")
date_col1, date_col2 = st.sidebar.columns(2)
start_date = date_col1.date_input(
    "Analysis Start Date", datetime.date(2025, 11, 13)
)
end_date = date_col2.date_input("Analysis End Date", datetime.date(2026, 11, 13))

st.markdown("---")


@st.cache_data(ttl=60)
def load_portfolio_data(file_obj):
  """Loads and standardizes Zerodha holdings export data."""
  if file_obj is not None:
    try:
      if file_obj.name.endswith(".csv"):
        df = pd.read_csv(file_obj)
      else:
        df = pd.read_excel(file_obj)
      return df
    except Exception as e:
      st.error(f"Error reading holdings file: {e}")
      return pd.DataFrame()

  # Default sample holdings dataset if no file is uploaded yet
  sample_data = [
      {
          "Instrument": "MPHASIS",
          "Qty.": 100,
          "Avg. cost": 2606.06,
          "LTP": 2425.20,
          "Invested": 260606.00,
          "Cur. val": 242520.00,
          "P&L": -18086.00,
          "Net chg.": "-6.94%",
      },
      {
          "Instrument": "DATAPATTNS",
          "Qty.": 21,
          "Avg. cost": 4211.60,
          "LTP": 4244.50,
          "Invested": 88443.60,
          "Cur. val": 89134.50,
          "P&L": 690.90,
          "Net chg.": "+0.78%",
      },
      {
          "Instrument": "KEI",
          "Qty.": 4,
          "Avg. cost": 5004.50,
          "LTP": 4121.75,
          "Invested": 20018.00,
          "Cur. val": 16487.00,
          "P&L": -3531.00,
          "Net chg.": "-17.64%",
      },
      {
          "Instrument": "HDFCBANK",
          "Qty.": 14,
          "Avg. cost": 761.34,
          "LTP": 800.30,
          "Invested": 10658.80,
          "Cur. val": 11204.20,
          "P&L": 545.40,
          "Net chg.": "+5.12%",
      },
      {
          "Instrument": "HINDALCO",
          "Qty.": 10,
          "Avg. cost": 1011.90,
          "LTP": 947.30,
          "Invested": 10119.05,
          "Cur. val": 9473.00,
          "P&L": -646.05,
          "Net chg.": "-6.38%",
      },
      {
          "Instrument": "SUNPHARMA",
          "Qty.": 4,
          "Avg. cost": 1670.80,
          "LTP": 1886.10,
          "Invested": 6683.20,
          "Cur. val": 7544.40,
          "P&L": 861.20,
          "Net chg.": "+12.89%",
      },
  ]
  return pd.DataFrame(sample_data)


df_holdings = load_portfolio_data(uploaded_holdings)

if not df_holdings.empty:
  # Summary Metrics
  total_invested = (
      df_holdings["Invested"].sum() if "Invested" in df_holdings.columns else 0.0
  )
  total_current = (
      df_holdings["Cur. val"].sum() if "Cur. val" in df_holdings.columns else 0.0
  )
  total_pnl = total_current - total_invested
  pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Total Investment", f"₹{total_invested:,.2f}")
  col2.metric("Current Value", f"₹{total_current:,.2f}")
  col3.metric("Total P&L", f"₹{total_pnl:,.2f}", f"{pnl_pct:.2f}%")
  col4.metric("Total Holdings", len(df_holdings))

  st.markdown("---")

  # Tabs for Portfolio Insights
  tab1, tab2, tab3 = st.tabs([
      "📋 Holdings & Performance",
      "📊 Asset Allocation & P&L Chart",
      "⚡ Technical Action Scanner",
  ])

  with tab1:
    st.subheader("Zerodha Portfolio Holdings Feed")
    st.dataframe(df_holdings, use_container_width=True)

  with tab2:
    st.subheader("Portfolio Allocation Breakdown")
    if "Instrument" in df_holdings.columns and "Cur. val" in df_holdings.columns:
      fig = px.pie(
          df_holdings,
          names="Instrument",
          values="Cur. val",
          title="Current Value Distribution by Stock",
          template="plotly_dark",
      )
      st.plotly_chart(fig, use_container_width=True)
    else:
      st.info("Allocation chart unavailable.")

  with tab3:
    st.subheader("Technical Action Signals (RSI & EMAs)")
    st.markdown(
        "Screening portfolio equities against configured Fast EMA ("
        f"{fast_ema}) and Slow EMA ({slow_ema}) thresholds."
    )

    signal_rows = []
    inst_col = (
        "Instrument"
        if "Instrument" in df_holdings.columns
        else "Symbol"
        if "Symbol" in df_holdings.columns
        else None
    )

    if inst_col:
      for _, row in df_holdings.iterrows():
        ticker = str(row[inst_col]).strip()
        try:
          hist = yf.Ticker(f"{ticker}.NS").history(period="30d")
          if not hist.empty:
            ltp = float(hist["Close"].iloc[-1])
            ema_fast = hist["Close"].ewm(span=fast_ema).mean().iloc[-1]
            ema_slow = hist["Close"].ewm(span=slow_ema).mean().iloc[-1]

            action = (
                "🚀 HOLD / BULLISH TREND"
                if ltp > ema_fast
                else "⚠️ WATCH / PULLBACK"
            )
            signal_rows.append({
                "Instrument": ticker,
                "LTP": round(ltp, 2),
                f"EMA_{fast_ema}": round(ema_fast, 2),
                f"EMA_{slow_ema}": round(ema_slow, 2),
                "Signal": action,
            })
        except Exception:
          continue

      if signal_rows:
        st.dataframe(pd.DataFrame(signal_rows), use_container_width=True)
      else:
        st.warning("Could not fetch technical indicators for holdings.")
else:
  st.warning("No portfolio data found. Please upload your Zerodha holdings.")
