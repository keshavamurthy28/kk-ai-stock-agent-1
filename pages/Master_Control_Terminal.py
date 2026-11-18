from datetime import datetime
import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Alpha | Master Excel Sync & Performance Terminal",
    layout="wide",
)

st.title("🎯 Institutional Master Terminal: Cross-Page Data Sync & Excel Tracker")
st.markdown(
    "**Centralized Command Center:** Synchronizes signals, tracks live target"
    " status, calculates win/loss efficiency, and compiles multi-sheet Excel"
    " mastersheets for your intraday portfolio."
)

ist = pytz.timezone("Asia/Kolkata")

# ---------------------------------------------------------
# 1. SIMULATED LIVE SCANNER ENGINE (Pulls Long & Short Signals)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_master_market_signals():
  universe = [
      "SBIN.NS",
      "DEEPAKFERT.NS",
      "RELIANCE.NS",
      "TCS.NS",
      "HDFCBANK.NS",
      "ICICIBANK.NS",
      "INFY.NS",
      "ITC.NS",
      "AXISBANK.NS",
      "PNB.NS",
  ]
  scanned_data = []

  for symbol in universe:
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="2d", interval="15m", auto_adjust=True)
      if df is None or df.empty or len(df) < 10:
        continue

      ltp = float(df["Close"].iloc[-1])
      prev_close = float(df["Close"].iloc[0])
      change_pct = round(((ltp - prev_close) / prev_close) * 100, 2)

      # Classification based on momentum
      signal_type = "LONG (Bullish)" if change_pct > 0 else "SHORT (Bearish)"
      target_1 = (
          round(ltp * 1.025, 2)
          if "LONG" in signal_type
          else round(ltp * 0.975, 2)
      )
      target_2 = (
          round(ltp * 1.048, 2)
          if "LONG" in signal_type
          else round(ltp * 0.952, 2)
      )
      stop_loss = (
          round(ltp * 0.99, 2) if "LONG" in signal_type else round(ltp * 1.01, 2)
      )

      scanned_data.append({
          "Timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
          "Symbol": symbol.replace(".NS", ""),
          "Strategy_Source": (
              "Daily Top 2 Picks" if "LONG" in signal_type else "Bearish Short"
          ),
          "Signal_Type": signal_type,
          "LTP": round(ltp, 2),
          "Change_Pct": change_pct,
          "Target_1": target_1,
          "Target_2": target_2,
          "Stop_Loss": stop_loss,
          "Status": "ACTIVE MONITORING",
      })
    except Exception:
      continue

  return pd.DataFrame(scanned_data)


# ---------------------------------------------------------
# 2. SESSION STATE TRADE TRACKER (Simulating Execution & Target Status)
# ---------------------------------------------------------
if "trade_log" not in st.session_state:
  # Pre-populate with sample historical synchronized data for master sheet demonstration
  st.session_state["trade_log"] = pd.DataFrame([
      {
          "Trade_ID": "TRD-101",
          "Date": "2026-11-18",
          "Time": "09:30:15",
          "Symbol": "SBIN",
          "Type": "LONG (Bullish)",
          "Entry_Price": 1130.18,
          "Exit_Price": 1165.42,
          "Target_1": 1165.42,
          "Target_2": 1191.58,
          "Stop_Loss": 1111.68,
          "Quantity": 100,
          "Status": "TARGET 1 HIT",
          "P&L_INR": 3524.00,
          "Efficiency_%": 3.12,
      },
      {
          "Trade_ID": "TRD-102",
          "Date": "2026-11-18",
          "Time": "10:15:40",
          "Symbol": "DEEPAKFERT",
          "Type": "LONG (Bullish)",
          "Entry_Price": 1462.87,
          "Exit_Price": 1450.00,
          "Target_1": 1508.49,
          "Target_2": 1542.34,
          "Stop_Loss": 1434.87,
          "Quantity": 50,
          "Status": "MANUAL EXIT",
          "P&L_INR": -643.50,
          "Efficiency_%": -0.88,
      },
  ])

# ---------------------------------------------------------
# 3. DASHBOARD LAYOUT & METRICS
# ---------------------------------------------------------
df_signals = fetch_master_market_signals()
df_trades = st.session_state["trade_log"]

st.subheader("📊 Synchronized Live Signal Feed (All Scanners)")
if not df_signals.empty:
  st.dataframe(df_signals, use_container_width=True)
else:
  st.info("Scanning market tickers...")

st.markdown("---")
st.subheader("📈 Master Performance & Efficiency Tracker")

# Calculate metrics
total_trades = len(df_trades)
winning_trades = len(df_trades[df_trades["P&L_INR"] > 0])
win_rate = (
    round((winning_trades / total_trades) * 100, 2) if total_trades > 0 else 0
)
net_pnl = round(df_trades["P&L_INR"].sum(), 2)
avg_efficiency = round(df_trades["Efficiency_%"].mean(), 2)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Executed Trades", total_trades)
col_m2.metric(
    "Net Realized P&L",
    f"₹{net_pnl:,.2f}",
    delta=f"{win_rate}% Win Rate",
)
col_m3.metric("Win/Loss Efficiency", f"{avg_efficiency}% Avg")
col_m4.metric("Active Strategy Status", "SYNCED & ONLINE")

# Display Master Trade Log Table
st.markdown("### 📝 Master Trade Log Sheet")
st.dataframe(df_trades, use_container_width=True)


# ---------------------------------------------------------
# 4. MULTI-SHEET EXCEL EXPORT ENGINE
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📥 Export Master Excel Datasheet")
st.markdown(
    "Download a fully compiled `.xlsx` workbook containing multiple synchronized"
    " sheets: **Master Trade Log**, **Live Signals**, and **Overall Performance"
    " Summary**."
)


def create_master_excel_workbook(trades_df, signals_df):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    # Sheet 1: Master Trade Log
    trades_df.to_excel(writer, sheet_name="Master_Trade_Log", index=False)

    # Sheet 2: Live Market Signals
    signals_df.to_excel(writer, sheet_name="Live_Signals_Feed", index=False)

    # Sheet 3: Performance Summary Sheet
    summary_data = pd.DataFrame({
        "Metric": [
            "Total Trades",
            "Winning Trades",
            "Win Rate (%)",
            "Net P&L (INR)",
            "Average Efficiency (%)",
            "Export Timestamp",
        ],
        "Value": [
            len(trades_df),
            len(trades_df[trades_df["P&L_INR"] > 0]),
            win_rate,
            net_pnl,
            avg_efficiency,
            datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
        ],
    })
    summary_data.to_excel(
        writer, sheet_name="Overall_Performance_Summary", index=False
    )

  processed_data = output.getvalue()
  return processed_data


excel_file_bytes = create_master_excel_workbook(df_trades, df_signals)

st.download_button(
    label="📥 Download Master Excel Datasheet (.xlsx)",
    data=excel_file_bytes,
    file_name=f"Institutional_Alpha_Master_Sheet_{datetime.now(ist).strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
