import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FII & Foreign Investor Stock Picker", layout="wide")

st.title("🌐 Foreign Institutional Investor (FII / FPI) Daily Stock Picker")
st.markdown(
    "Isolate and track exact stock accumulation, block deals, and buying/selling patterns "
    "specifically driven by global **Foreign Institutional Investors (FII)** and **Foreign Portfolio Investors (FPI)**."
)

# 1. Sidebar Configuration & File Ingestion
st.sidebar.header("⚙️ FII Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Daily NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"])

today_date = datetime.date.today()
default_start = today_date - datetime.timedelta(days=30)

start_date = st.sidebar.date_input("From Date", value=default_start, max_value=today_date)
end_date = st.sidebar.date_input("To Date", value=today_date, max_value=today_date)

# 2. Intelligent FII Keyword Recognizer
# This automatically scans client names for known foreign institutional keywords
FII_KEYWORDS = [
    "VANGUARD", "GOLDMAN", "MORGAN STANLEY", "GIC", "SINGAPORE", "NOMURA", 
    "ABU DHABI", "BLACKROCK", "JPMORGAN", "JPM MORGAN", "CITIGROUP", "HSBC", 
    "UBS", "MAQUARIE", "BARCLAYS", "BNP PARIBAS", "MERRILL LYNCH", "CREDIT SUISSE",
    "FMR", "FIDELITY", "TROWES", "INVESCO", "SCHRODERS", "AMP", "STATE STREET"
]

@st.cache_data
def load_default_fii_data():
    current_day = datetime.date.today()
    data = [
        {"Date": str(current_day), "Symbol": "ZOMATO", "Client Name": "VANGUARD FUNDS", "Deal Type": "BULK", "Quantity Traded": 3200000, "Traded Price": 245.8, "Signal": "BUY"},
        {"Date": str(current_day), "Symbol": "TCS", "Client Name": "GOLDMAN SACHS INVESTMENTS", "Deal Type": "BLOCK", "Quantity Traded": 450000, "Traded Price": 4120.5, "Signal": "SELL"},
        {"Date": str(current_day - datetime.timedelta(days=1)), "Symbol": "RELIANCE", "Client Name": "GOVERNMENT OF SINGAPORE", "Deal Type": "BULK", "Quantity Traded": 1500000, "Traded Price": 2740.0, "Signal": "BUY"},
        {"Date": str(current_day - datetime.timedelta(days=2)), "Symbol": "INFY", "Client Name": "NOMURA SINGAPORE LIMITED", "Deal Type": "BLOCK", "Quantity Traded": 900000, "Traded Price": 1850.0, "Signal": "BUY"},
        {"Date": str(current_day - datetime.timedelta(days=3)), "Symbol": "SBIN", "Client Name": "SBI MUTUAL FUND", "Deal Type": "BULK", "Quantity Traded": 2000000, "Traded Price": 810.0, "Signal": "BUY"}, # Domestic (should be filtered out)
    ]
    return pd.DataFrame(data)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        st.sidebar.success("✅ Report uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {e}")
        df_raw = load_default_fii_data()
else:
    df_raw = load_default_fii_data()

# Standardize columns
df_raw.columns = [str(col).strip().title() for col in df_raw.columns]
date_col = next((col for col in df_raw.columns if 'date' in col.lower()), None)
client_col = next((col for col in df_raw.columns if 'client' in col.lower() or 'name' in col.lower()), 'Client Name')

# 3. Advanced Filtering for FII/FPI Entities Only
if not df_raw.empty and client_col in df_raw.columns:
    # Create pattern string for regex matching
    pattern = '|'.join(FII_KEYWORDS)
    
    # Filter rows where client name contains any FII keyword
    fii_mask = df_raw[client_col].str.upper().str.contains(pattern, na=False)
    df_fii = df_raw[fii_mask].copy()
    
    # Date Filtering
    if date_col:
        df_fii["Date_Parsed"] = pd.to_datetime(df_fii[date_col], errors='coerce').dt.date
        date_mask = (df_fii["Date_Parsed"] >= start_date) & (df_fii["Date_Parsed"] <= end_date)
        df_filtered = df_fii.loc[date_mask].drop(columns=["Date_Parsed"])
    else:
        df_filtered = df_fii

    # Sidebar Specific FII Dropdown Selector
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Specific FII Filter")
    unique_fiis = ["All Foreign Investors"] + sorted(df_filtered[client_col].dropna().unique().tolist())
    selected_fii = st.sidebar.selectbox("Choose Foreign Institution", unique_fiis)

    if selected_fii != "All Foreign Investors":
        df_filtered = df_filtered[df_filtered[client_col] == selected_fii]

    # Display Dashboard Results
    if not df_filtered.empty:
        st.success(f"🔍 Successfully isolated **{len(df_filtered)}** institutional trades executed by **Foreign Investors (FII/FPI)**.")
        
        # High-level Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total FII Deals", len(df_filtered))
        m2.metric("FII Buy Signals", len(df_filtered[df_filtered.get('Signal', '').str.upper() == 'BUY']))
        m3.metric("Unique FII Entities", df_filtered[client_col].nunique())

        # Styling function for institutional buy/sell actions
        def fii_color_coding(val):
            if "BUY" in str(val).upper():
                return 'background-color: rgba(46, 160, 67, 0.2); color: #3fb950;'
            elif "SELL" in str(val).upper():
                return 'background-color: rgba(248, 81, 73, 0.2); color: #f85149;'
            return ''

        # Display Dataframe
        if 'Signal' in df_filtered.columns:
            styled_df = df_filtered.style.map(fii_color_coding, subset=['Signal'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.dataframe(df_filtered, use_container_width=True)
            
        st.info("💡 **Trading Insight:** When a major global FII like Vanguard, Nomura, or the Government of Singapore initiates a massive bulk buy in an NSE stock, it signals strong medium-term foreign capital allocation. Consider aligning your swing trading direction with these heavy weights.")
    else:
        st.warning("⚠️ No foreign institutional trades found matching the selected date range or FII filter. Try expanding your date range or uploading an updated NSE report.")
else:
    st.error("Uploaded dataset is empty or missing client identification headers.")
