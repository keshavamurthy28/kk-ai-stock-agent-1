import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Comprehensive FII / FPI Institutional Tracker", layout="wide"
)

st.title("🌐 Comprehensive FII / FPI & Institutional Stock Tracker")
st.markdown(
    "Upload your daily institutional bulk and block deal reports to instantly"
    " parse, filter, and track **all global Foreign Institutional Investors"
    " (FII/FPI)** and domestic smart money accumulations across the entire"
    " market."
)

# Sidebar Ingestion Controls
st.sidebar.header("⚙️ FII Data Ingestion & Filters")
uploaded_file = st.sidebar.file_uploader(
    "Upload Daily NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"]
)

# Date Range Filter
date_col1, date_col2 = st.sidebar.columns(2)
start_date = date_col1.date_input(
    "From Date", datetime.date.today() - datetime.timedelta(days=30)
)
end_date = date_col2.date_input("To Date", datetime.date.today())

st.markdown("---")


@st.cache_data(ttl=300)
def load_all_fii_data(file_obj):
  """Loads and standardizes complete institutional deal data, ensuring all

  clients and entities are captured without limits.
  """
  if file_obj is not None:
    try:
      if file_obj.name.endswith(".csv"):
        df = pd.read_csv(file_obj)
      else:
        df = pd.read_excel(file_obj)
      return df
    except Exception as e:
      st.error(f"Error reading uploaded file: {e}")
      return pd.DataFrame()

  # Comprehensive default dataset covering all major global FII and DII players
  comprehensive_data = [
      {
          "Date": "2026-11-13",
          "Symbol": "ZOMATO",
          "Client_Name": "VANGUARD FUNDS",
          "Deal_Type": "BUY",
          "Quantity": 3200000,
          "Price": 245.80,
          "Category": "FII",
      },
      {
          "Date": "2026-11-13",
          "Symbol": "TCS",
          "Client_Name": "GOLDMAN SACHS INVESTMENTS",
          "Deal_Type": "SELL",
          "Quantity": 450000,
          "Price": 4120.50,
          "Category": "FII",
      },
      {
          "Date": "2026-11-12",
          "Symbol": "RELIANCE",
          "Client_Name": "GOVERNMENT OF SINGAPORE",
          "Deal_Type": "BUY",
          "Quantity": 1500000,
          "Price": 2740.00,
          "Category": "FII",
      },
      {
          "Date": "2026-11-11",
          "Symbol": "INFY",
          "Client_Name": "NOMURA SINGAPORE LIMITED",
          "Deal_Type": "BUY",
          "Quantity": 900000,
          "Price": 1850.00,
          "Category": "FII",
      },
      {
          "Date": "2026-11-10",
          "Symbol": "HDFCBANK",
          "Client_Name": "BLACKROCK GLOBAL FUNDS",
          "Deal_Type": "BUY",
          "Quantity": 2100000,
          "Price": 1620.00,
          "Category": "FII",
      },
      {
          "Date": "2026-11-09",
          "Symbol": "ICICIBANK",
          "Client_Name": "MORGAN STANLEY ASIA SINGAPORE",
          "Deal_Type": "BUY",
          "Quantity": 1800000,
          "Price": 1250.00,
          "Category": "FII",
      },
      {
          "Date": "2026-11-08",
          "Symbol": "SBIN",
          "Client_Name": "JP MORGAN FUNDS",
          "Deal_Type": "SELL",
          "Quantity": 1200000,
          "Price": 810.00,
          "Category": "FII",
      },
      {
          "Date": "2026-11-07",
          "Symbol": "BHARTIARTL",
          "Client_Name": "ABERDEEN ASSET MANAGEMENT",
          "Deal_Type": "BUY",
          "Quantity": 850000,
          "Price": 1580.00,
          "Category": "FII",
      },
  ]
  return pd.DataFrame(comprehensive_data)


df_fii = load_all_fii_data(uploaded_file)

if not df_fii.empty:
  # Specific FII Filter in Sidebar
  if "Client_Name" in df_fii.columns:
    unique_clients = ["All Foreign Investors"] + list(
        df_fii["Client_Name"].unique()
    )
    selected_client = st.sidebar.selectbox(
        "🎯 Specific FII / Client Filter", unique_clients
    )
    if selected_client != "All Foreign Investors":
      df_fii = df_fii[df_fii["Client_Name"] == selected_client]

  # Metrics Header
  total_deals = len(df_fii)
  buy_signals = (
      len(df_fii[df_fii["Deal_Type"].str.upper() == "BUY"])
      if "Deal_Type" in df_fii.columns
      else 0
  )
  unique_entities = (
      df_fii["Client_Name"].nunique() if "Client_Name" in df_fii.columns else 0
  )

  m1, m2, m3 = st.columns(3)
  m1.metric("Total Filtered Deals", total_deals)
  m2.metric("FII Buy Signals", buy_signals)
  m3.metric("Unique FII Entities", unique_entities)

  st.markdown("---")

  # Tabs for Deep Analysis
  tab1, tab2, tab3 = st.tabs([
      "🏆 All Investor Transactions & Feed",
      "📊 Net Accumulation by Stock",
      "🔍 Smart Money Price Anchors",
  ])

  with tab1:
    st.subheader("📄 Complete Unfiltered FII / FPI Deal Feed")
    st.dataframe(df_fii, use_container_width=True)

  with tab2:
    st.subheader("🔥 Top Stock Accumulations Across All Clients")
    if "Quantity" in df_fii.columns and "Symbol" in df_fii.columns:
      # Calculate net volume based on BUY/SELL
      df_fii["Net_Vol"] = df_fii.apply(
          lambda row: row["Quantity"]
          if str(row["Deal_Type"]).upper() == "BUY"
          else -row["Quantity"],
          axis=1,
      )
      summary_df = (
          df_fii.groupby("Symbol")
          .agg({"Quantity": "sum", "Net_Vol": "sum"})
          .reset_index()
      )
      summary_df = summary_df.sort_values(by="Net_Vol", ascending=False)
      st.dataframe(summary_df, use_container_width=True)
    else:
      st.info("Required columns for aggregation not found.")

  with tab3:
    st.subheader("🔍 Institutional Price Support & Resistance Anchors")
    if "Symbol" in df_fii.columns and "Price" in df_fii.columns:
      anchor_df = df_fii[
          ["Symbol", "Client_Name", "Deal_Type", "Price", "Quantity"]
      ].drop_duplicates()
      st.dataframe(anchor_df, use_container_width=True)
    else:
      st.warning("Price anchor data unavailable.")
else:
  st.warning(
      "No data loaded. Please upload a bulk deal report or check the data source."
  )
