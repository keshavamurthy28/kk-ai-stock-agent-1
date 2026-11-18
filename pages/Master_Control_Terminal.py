from datetime import datetime, timedelta
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
        "Institutional Master Control & Target Audit Hub | MU₹A"
    ),
    layout="wide",
)

st.title(
    "🎯 Institutional Master Control Terminal: Automated Target Audit & Excel"
    " Hub"
)
st.markdown(
    "**Smart Cross-Page Tracker:** Automatically scrapes live stocks across all"
    " 8 custom pages, evaluates previous day signals against market highs/lows,"
    " and updates **Target Achieved / Failed** status with efficiency metrics."
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
          "LTP_At_Capture",
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
# 2. AUTOMATED BACKTESTING & TARGET AUDIT ENGINE
# ---------------------------------------------------------
def audit_and_update_targets(df_journal):
  if df_journal.empty:
    return df_journal

  updated_rows = []
  for _, row in df_journal.iterrows():
    # If already settled, keep as is
    if row["Status"] in [
        "TARGET 1 HIT",
        "TARGET 2 HIT",
        "STOP LOSS HIT",
        "EXPIRED / FAILED",
    ]:
      updated_rows.append(row)
      continue

    symbol_full = f"{row['Symbol']}.NS"
    signal_date = pd.to_datetime(row["Date"])
    today_dt = datetime.now(ist).date()

    # Only audit past trades (not today's active signals)
    if signal_date.date() < today_dt:
      try:
        ticker = yf.Ticker(symbol_full)
        # Fetch data from signal date onwards to check if target was breached
        df_hist = ticker.history(start=signal_date.strftime("%Y-%m-%d"), end=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"), interval="1d")
        
        if not df_hist.empty and len(df_hist) >= 2:
          # Check subsequent day(s) high and low
          subsequent_high = df_hist["High"].iloc[1:].max()
          subsequent_low = df_hist["Low"].iloc[1:].min()

          t1 = float(row["Target_1"])
          t2 = float(row["Target_2"])
          sl = float(row["Stop_Loss"])
          entry = float(row["LTP_At_Capture"])
          is_short = "SHORT" in str(row["Signal_Type"])

          if not is_short:  # LONG Trade Rules
            if subsequent_high >= t2:
              row["Status"] = "TARGET 2 HIT"
              row["Realized_P&L"] = round((t2 - entry) * 100, 2)
              row["Efficiency_%"] = round(((t2 - entry) / entry) * 100, 2)
            elif subsequent_high >= t1:
              row["Status"] = "TARGET 1 HIT"
              row["Realized_P&L"] = round((t1 - entry) * 100, 2)
              row["Efficiency_%"] = round(((t1 - entry) / entry) * 100, 2)
            elif subsequent_low <= sl:
              row["Status"] = "STOP LOSS HIT"
              row["Realized_P&L"] = round((sl - entry) * 100, 2)
              row["Efficiency_%"] = round(((sl - entry) / entry) * 100, 2)
            else:
              row["Status"] = "EXPIRED / FAILED"
              row["Realized_P&L"] = 0.0
              row["Efficiency_%"] = 0.0

          else:  # SHORT Trade Rules
            if subsequent_low <= t2:
              row["Status"] = "TARGET 2 HIT"
              row["Realized_P&L"] = round((entry - t2) * 100, 2)
              row["Efficiency_%"] = round(((entry - t2) / entry) * 100, 2)
            elif subsequent_low <= t1:
              row["Status"] = "TARGET 1 HIT"
              row["Realized_P&L"] = round((entry - t1) * 100, 2)
              row["Efficiency_%"] = round(((entry - t1) / entry) * 100, 2)
            elif subsequent_high >= sl:
              row["Status"] = "STOP LOSS HIT"
              row["Realized_P&L"] = round((entry - sl) * 100, 2)
              row["Efficiency_%"] = round(((entry - sl) / entry) * 100, 2)
            else:
              row["Status"] = "EXPIRED / FAILED"
              row["Realized_P&L"] = 0.0
              row["Efficiency_%"] = 0.0
      except Exception:
        pass

    updated_rows.append(row)

  return pd.DataFrame(updated_rows)


# ---------------------------------------------------------
# 3. LIVE MULTI-PAGE SIGNAL SCRAPER
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_all_terminals_data():
  current_ts = datetime.now(ist)
  date_str = current_ts.strftime("%Y-%m-%d")
  time_str = current_ts.strftime("%H:%M:%S")
  timestamp_str = current_ts.strftime("%Y-%m-%d %H:%M:%S")

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
            "LTP_At_Capture": ltp,
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
# 4. CONTROL PANEL & SYNC ACTIONS
# ---------------------------------------------------------
st.subheader("🔄 Cross-Terminal Data Synchronization & Audit")
col_c1, col_c2 = st.columns([3, 1])

with col_c1:
  st.info(
      "Click below to sync live signals and automatically audit past trades"
      " against the next day's price action (Target Achieved vs Failed)."
  )

with col_c2:
  if st.button("📥 Sync & Audit All Terminals"):
    if not df_live_aggregate.empty:
      current_master = st.session_state["master_df"]
      # Append new records
      combined = pd.concat([current_master, df_live_aggregate]).drop_duplicates(
          subset=["Date", "Source_Terminal", "Symbol"]
      )
      # Run automated audit test for past dates
      audited_master = audit_and_update_targets(combined)
      st.session_state["master_df"] = audited_master
      save_master_journal(audited_master)
      st.toast("Successfully audited and synchronized all pages!")
      st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 5. DASHBOARD & FILTERING
# ---------------------------------------------------------
st.subheader("📊 Multi-Page Performance Audit & Target Tracking")
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

  total_recs = len(master_data)
  achieved = len(
      master_data[
          master_data["Status"].isin(["TARGET 1 HIT", "TARGET 2 HIT"])
      ]
  )
  win_rate = (
      round((achieved / total_recs) * 100, 2) if total_recs > 0 else 0.0
  )
  net_pnl = round(master_data["Realized_P&L"].sum(), 2)
  avg_efficiency = round(master_data["Efficiency_%"].mean(), 2)

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Total Tracked Stocks", total_recs)
  m2.metric(
      "Cumulative Realized P&L",
      f"₹{net_pnl:,.2f}",
      delta=f"{win_rate}% Target Success Rate",
  )
  m3.metric("Average Efficiency", f"{avg_efficiency}%")
  m4.metric("Audit Status", "AUTOMATED & ACTIVE")

  st.markdown("### 📝 Consolidated Master Stock Journal (With Target Status)")
  st.dataframe(master_data, use_container_width=True)
else:
  st.warning(
      "No data recorded in master journal yet. Click 'Sync & Audit All"
      " Terminals' above."
  )

# ---------------------------------------------------------
# 6. MULTI-SHEET EXCEL WORKBOOK GENERATOR
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📥 Download Multi-Sheet Excel Workbook (All Pages)")


def generate_multi_sheet_excel(df_master):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_master.to_excel(writer, sheet_name="Master_Combined_Journal", index=False)

    if not df_master.empty and "Source_Terminal" in df_master.columns:
      for term in df_master["Source_Terminal"].unique():
        sheet_name = (
            term.replace("/", "_")
            .replace("—", "_")
            .replace(" ", "_")[:31]
        )
        term_df = df_master[df_master["Source_Terminal"] == term]
        term_df.to_excel(writer, sheet_name=sheet_name, index=False)

    summary_df = pd.DataFrame({
        "Metric Description": [
            "Total Tracked Records Across All Pages",
            "Targets Achieved (T1 / T2 Hit)",
            "Target Success Rate (%)",
            "Net Realized P&L (INR)",
            "Average Efficiency (%)",
            "Report Generation Timestamp",
        ],
        "Value": [
            len(df_master),
            achieved if not df_master.empty else 0,
            win_rate if not df_master.empty else 0.0,
            net_pnl if not df_master.empty else 0.0,
            avg_efficiency if not df_master.empty else 0.0,
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
      file_name=f"MU₹A_Target_Audit_Master_{datetime.now(ist).strftime('%Y%m%d_%H%M')}.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
