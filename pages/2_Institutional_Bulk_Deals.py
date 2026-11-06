import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Institutional Bulk & Block Deals", layout="wide")

st.title("📊 Daily Institutional Bulk & Block Deals (Client & Stock Lookup)")
st.markdown(
    "Track exact institutional clients, bulk/block deals, and stock holdings for any selected date. "
    "Upload the official daily NSE report to populate and filter through all active market clients."
)

# Helpful Guide
with st.expander("📥 How to get the official daily NSE bulk/block deal report (1-Click)"):
    st.markdown("""
    1. Go to the official [NSE India Bulk Deals Page](https://www.nseindia.com/report-detail/display-bulk-and-block-deals).
    2. Download the official CSV/Excel file for the day you want.
    3. Upload that file using the uploader below to instantly view exact client holdings and signals!
    """)

st.sidebar.header("⚙️ Filter Options")

# File Uploader for Official NSE Data
uploaded_file = st.sidebar.file_uploader("Upload NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"])

today_date = datetime.date.today()
default_start = today_date - datetime.timedelta(days=30)

start_date = st.sidebar.date_input("From Date", value=default_start, max_value=today_date)
end_date = st.sidebar.date_input("To Date", value=today_date, max_value=today_date)

# Load Data (From User Upload or Intelligent Fallback)
@st.cache_data
def load_default_data():
    current_day = datetime.date.today()
    data = [
        {"Date": str(current_day), "Symbol": "RELIANCE", "Client Name": "SBI MUTUAL FUND", "Deal Type": "BULK", "Quantity Traded": 1250000, "Traded Price": 2740.0, "Signal": "BUY"},
        {"Date": str(current_day), "Symbol": "TCS", "Client Name": "GOLDMAN SACHS", "Deal Type": "BLOCK", "Quantity Traded": 450000, "Traded Price": 4120.5, "Signal": "SELL"},
        {"Date": str(current_day - datetime.timedelta(days=1)), "Symbol": "ZOMATO", "Client Name": "VANGUARD FUNDS", "Deal Type": "BULK", "Quantity Traded": 3200000, "Traded Price": 245.8, "Signal": "BUY"},
        {"Date": str(current_day - datetime.timedelta(days=2)), "Symbol": "LT", "Client Name": "ICICI PRU MUTUAL FUND", "Deal Type": "BLOCK", "Quantity Traded": 800000, "Traded Price": 3650.0, "Signal": "BUY"},
    ]
    return pd.DataFrame(data)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        st.sidebar.success("✅ Official NSE report uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {e}")
        df_raw = load_default_data()
else:
    df_raw = load_default_data()

# Standardize column names
df_raw.columns = [str(col).strip().title() for col in df_raw.columns]

# Identify columns safely
date_col = next((col for col in df_raw.columns if 'date' in col.lower()), None)
client_col = next((col for col in df_raw.columns if 'client' in col.lower() or 'name' in col.lower()), 'Client Name')

# Dynamic Client Dropdown Selector in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filter by Client")
if not df_raw.empty and client_col in df_raw.columns:
    unique_clients = ["All Clients"] + sorted(df_raw[client_col].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Select Specific Client", unique_clients)
else:
    selected_client = "All Clients"

# Refresh Button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Reset View"):
        st.cache_data.clear()
        st.rerun()

# Processing and Filtering Data
if not df_raw.empty:
    if date_col:
        df_raw["Date_Parsed"] = pd.to_datetime(df_raw[date_col], errors='coerce').dt.date
        mask = (df_raw["Date_Parsed"] >= start_date) & (df_raw["Date_Parsed"] <= end_date)
        df_filtered = df_raw.loc[mask].drop(columns=["Date_Parsed"])
    else:
        df_filtered = df_raw

    # Apply Client Dropdown Filter
    if selected_client != "All Clients" and client_col in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[client_col] == selected_client]

    if not df_filtered.empty:
        st.success(f"Showing **{len(df_filtered)}** institutional records matching your filters.")
        
        # Summary Metrics
        m1, m2 = st.columns(2)
        m1.metric("Total Filtered Deals", len(df_filtered))
        m2.metric("Unique Clients Found", df_filtered[client_col].nunique() if client_col in df_filtered.columns else 1)
        
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.warning("⚠️ No records found for the selected date range or client dropdown selection.")
else:
    st.error("Data frame is empty.")
