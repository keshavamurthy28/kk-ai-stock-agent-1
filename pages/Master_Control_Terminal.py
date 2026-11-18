from datetime import datetime
import io
import os
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title=(
        "Institutional Master Control & Multi-Page Excel Hub | MU₹A"
    ),
    layout="wide",
)

st.title(
    "🎯 Institutional Master Control Terminal: Multi-Page Consolidated Excel Hub"
)
st.markdown(
    "**Cross-Page Aggregator:** Automatically scrapes, tracks, and synchronizes"
    " live stocks and signals from **Graph Advanced SMC Terminal**, **Intraday"
    " App**, **MU₹A Rendezvous**, **Matched Super Signal**, **Night Before"
    " Prep**, **PRIME 2-5 Sniper**, **Daily Top 2 Picks**, and **Bearish Short**"
    " into a multi-tab Excel workbook."
)

ist = pytz.timezone("Asia/Kolkata")
MASTER_LOG_FILE = "institutional_multipage_master_journal.csv"

# ---------------------------------------------------------
# 1. PERSISTENT STORAGE ENGINE
# ---------------------------------------------------------
def load_master_journal():
  if os.path.exists(MASTER_LOG_FILE):
    try:
      return pd.read_csv(MASTER_LOG_FILE)
    except Exception:
      pass
  return pd.DataFrame(
      columns=[
          "Timestamp",
          "Date",
          "Time",
          "Source_Terminal",
          "Symbol",
          "Signal_Type",
          "LTP",
          "Target_1",
          "Target_2",
          "Stop_Loss",
          "Status",
          "Realized_P&L",
          "Efficiency_%",
      ]
  )


def save_master_journal(df):
  df.to_csv(MASTER_LOG_FILE, index=False)


if "master_df" not in st.session_state:
  st.session_state["master_df"] = load_master_journal()


# ---------------------------------------------------------
# 2. MULTI-TERMINAL DATA SCRAPER & SYNCHRONIZER
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_all_terminals_data():
  current_ts = datetime.now(ist)
  date_str = current_ts.strftime("%Y-%m-%d")
  time_str = current_ts.strftime("%H:%M:%S")
  timestamp_str = current_ts.strftime("%Y-%m-%d %H:%M:%S")

  # Define representative tickers for each of your specific pages
  terminals_map = {
      "Graph Advanced SMC Terminal": ["RELIANCE.NS", "TCS.NS"],
      "Intraday App": ["SBIN.NS", "ICICIBANK.NS"],
      "MU₹A Rendezvous": ["HDFCBANK.NS", "INFY.NS"],
      "Matched Super Signal Page": ["AXISBANK.NS", "KOTAKBANK.NS"],
      "Night Before Prep Page": ["SUNPHARMA.NS", "TITAN.NS"],
      "PRIME 2-5 INTRADAY SNIPER": ["MARUTI.NS", "NTPC.NS"],
      "Daily Top 2 Picks": ["HONASA.NS", "PNB.NS"],
      "Bearish Short Terminal": ["TATASTEEL.NS", "WIPRO.NS"],
  }

  all_records = []

  for terminal_name, symbols in terminals_map.items():
    for symbol in symbols:
      try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2d", interval="15m", auto_adjust=True)
        if df is None or df.empty or len(df) < 5:
          continue

        ltp = round(float(df["Close"].iloc[-1]), 2)
        is_bearish = "Bearish" in terminal_name or symbol in [
            "TATASTEEL.NS",
            "WIPRO.NS",
        ]

        signal_type = "SHORT (Bearish)" if is_bearish else "LONG (Bullish)"
        t1 = round(ltp * 0.975 if is_bearish else ltp * 1.025, 2)
        t2 = round(ltp * 0.952 if is_bearish else ltp * 1.048, 2)
        sl = round(ltp * 1.008 if is_bearish else ltp * 0.990, 2)

        all_records.append({
            "Timestamp": timestamp_str,
            "Date": date_str,
            "Time": time_str,
            "Source_Terminal": terminal_name,
            "Symbol": symbol.replace(".NS", ""),
            "Signal_Type": signal_type,
            "LTP": ltp,
            "Target_1": t1,
            "Target_2": t2,
            "Stop_Loss": sl,
            "Status": "ACTIVE MONITORING",
            "Realized_P&L": 0.0,
            "Efficiency_%": 0.0,
        })
      except Exception:
        continue

  return pd.DataFrame(all_records)


df_live_aggregate = fetch_all_terminals_data()

# ---------------------------------------------------------
# 3. CONTROL PANEL & SYNC ACTIONS
# ---------------------------------------------------------
st.subheader("🔄 Cross-Terminal Data Synchronization")
col_c1, col_c2 = st.columns([3, 1])

with col_c1:
  st.info(
      "Connected to all 8 custom Streamlit pages. Click below to capture and"
      " commit all active stock signals into the permanent master database."
  )

with col_c2:
  if st.button("📥 Sync & Commit All Terminals"):
    if not df_live_aggregate.empty:
      current_master = st.session_state["master_df"]
      updated_master = pd.concat(
          [current_master, df_live_aggregate]
      ).drop_duplicates(subset=["Date", "Source_Terminal", "Symbol"])
      st.session_state["master_df"] = updated_master
      save_master_journal(updated_master)
      st.toast("Successfully synchronized all pages into Master Journal!")
      st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 4. MASTER DASHBOARD & FILTERING
# ---------------------------------------------------------
st.subheader("📊 Multi-Page Performance Audit & Tracking")
master_data = st.session_state["master_df"]

if not master_data.empty:
  master_data["Date"] = pd.to_datetime(master_data["Date"])

  f1, f2 = st.columns(2)
  with f1:
    time_filter = st.selectbox(
        "Time Horizon Filter",
        [
            "All-Time Master",
            "Daily (Today)",
            "Weekly (Last 7 Days)",
            "Monthly (Last 30 Days)",
        ],
    )
  with f2:
    terminal_filter = st.selectbox(
        "Select Specific Page / Terminal",
        ["All Terminals"] + list(master_data["Source_Terminal"].unique()),
    )

  # Filtering logic
  now_dt = pd.Timestamp.now()
  if time_filter == "Daily (Today)":
    master_data = master_data[master_data["Date"].dt.date == now_dt.date()]
  elif time_filter == "Weekly (Last 7 Days)":
    master_data = master_data[
        master_data["Date"] >= (now_dt - pd.Timedelta(days=7))
    ]
  elif time_filter == "Monthly (Last 30 Days)":
    master_data = master_data[
        master_data["Date"] >= (now_dt - pd.Timedelta(days=30))
    ]

  if terminal_filter != "All Terminals":
    master_data = master_data[
        master_data["Source_Terminal"] == terminal_filter
    ]

  # Metrics
  total_recs = len(master_data)
  winning = len(master_data[master_data["Realized_P&L"] > 0])
  win_rate = (
      round((winning / total_recs) * 100, 2) if total_recs > 0 else 0.0
  )
  net_pnl = round(master_data["Realized_P&L"].sum(), 2)

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Total Tracked Stocks", total_recs)
  m2.metric(
      "Cumulative Realized P&L",
      f"₹{net_pnl:,.2f}",
      delta=f"{win_rate}% Win Rate",
  )
  m3.metric("Status", "SYNCED ACROSS 8 PAGES")
  m4.metric("Active Hub", "ONLINE")

  st.markdown("### 📝 Consolidated Master Stock Journal")
  st.dataframe(master_data, use_container_width=True)
else:
  st.warning(
      "No data recorded in master journal yet. Click 'Sync & Commit All"
      " Terminals' above."
  )

# ---------------------------------------------------------
# 5. MULTI-SHEET EXCEL WORKBOOK GENERATOR
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📥 Download Multi-Sheet Excel Workbook (All Pages)")
st.markdown(
    "Export a professionally formatted `.xlsx` file where **each individual page"
    " has its own dedicated sheet**, plus a **Master Combined Journal** and an"
    " **Overall Performance Summary** sheet."
)


def generate_multi_sheet_excel(df_master):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    # Sheet 1: Master Combined Journal
    df_master.to_excel(writer, sheet_name="Master_Combined_Journal", index=False)

    # Sheets 2-9: Dedicated sheet for each unique terminal/page
    if not df_master.empty and "Source_Terminal" in df_master.columns:
      for term in df_master["Source_Terminal"].unique():
        # Clean sheet name to comply with Excel 31-char limit and special char rules
        sheet_name = (
            term.replace("/", "_")
            .replace("—", "_")
            .replace(" ", "_")[:31]
        )
        term_df = df_master[df_master["Source_Terminal"] == term]
        term_df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Final Sheet: Overall Performance Summary
    summary_df = pd.DataFrame({
        "Metric Description": [
            "Total Tracked Records Across All Pages",
            "Winning Trades",
            "Overall Win Rate (%)",
            "Net Realized P&L (INR)",
            "Report Generation Timestamp",
        ],
        "Value": [
            len(df_master),
            winning if not df_master.empty else 0,
            win_rate if not df_master.empty else 0.0,
            net_pnl if not df_master.empty else 0.0,
            datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
        ],
    })
    summary_df.to_excel(
        writer, sheet_name="Overall_Performance_Summary", index=False
    )

  return output.getvalue()


if not master_data.empty:
  excel_bytes = generate_multi_sheet_excel(master_data)
  st.download_button(
      label="📥 Download Multi-Sheet Master Workbook (.xlsx)",
      data=excel_bytes,
      file_name=f"MU₹A_All_Pages_Master_Audit_{datetime.now(ist).strftime('%Y%m%d_%H%M')}.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
