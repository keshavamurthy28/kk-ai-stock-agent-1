import io
import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Institutional Bulk & Block Intelligence", layout="wide")

st.title("📊 Institutional Bulk & Block Deals - Live NSE Integrator")
st.markdown(
    "Fetch data instantly via file upload or by pulling direct end-of-day archives from NSE India."
)

st.sidebar.header("⚙️ Data Source Selection")
fetch_mode = st.sidebar.radio(
    "Choose Data Source", 
    ["Upload Report (Recommended & Reliable)", "Fetch Live Directly from NSE"]
)

df_raw = pd.DataFrame()

@st.cache_data
def load_fallback_data():
    return pd.DataFrame([
        {"Date": "06-Nov-2026", "Symbol": "RELIANCE", "Security Name": "Reliance Industries Ltd", "Client Name": "SBI MUTUAL FUND", "Buy/Sell": "BUY", "Volume": 1500000, "Trade Price/Weighted. Avg. Price": 2740.0},
        {"Date": "06-Nov-2026", "Symbol": "ZOMATO", "Security Name": "Zomato Limited", "Client Name": "VANGUARD FUNDS", "Buy/Sell": "BUY", "Volume": 3500000, "Trade Price/Weighted. Avg. Price": 245.8},
        {"Date": "06-Nov-2026", "Symbol": "TCS", "Security Name": "Tata Consultancy Services", "Client Name": "GOLDMAN SACHS", "Buy/Sell": "SELL", "Volume": 800000, "Trade Price/Weighted. Avg. Price": 4120.0},
    ])

if fetch_mode == "Upload Report (Recommended & Reliable)":
    uploaded_file = st.sidebar.file_uploader("Upload Daily NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
            st.sidebar.success("✅ Report loaded successfully!")
        except Exception as e:
            st.sidebar.error(f"Error reading file: {e}")
            df_raw = load_fallback_data()
    else:
        df_raw = load_fallback_data()

else:
    st.sidebar.info("Attempting to connect directly to NSE India archives...")
    if st.sidebar.button("Download Today's Data from NSE"):
        try:
            # NSE requires proper headers to mimic a real browser request and bypass firewall blockades
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            session = requests.Session()
            # Hit homepage first to collect valid cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            
            # Direct endpoint for NSE bulk deals CSV archive
            bulk_url = "https://www.nseindia.com/api/historical/bulk-deals?from=true" # or daily static csv link
            response = session.get("https://archives.nseindia.com/content/equities/bulk.csv", headers=headers, timeout=10)
            
            if response.status_code == 200:
                df_raw = pd.read_csv(io.StringIO(response.text))
                st.success("Successfully fetched live Bulk Deals CSV directly from NSE!")
            else:
                st.warning("NSE server blocked direct automated download (common firewall policy). Falling back to sample data or manual upload.")
                df_raw = load_fallback_data()
        except Exception as ex:
            st.error(f"Connection failed: {ex}. Please use the file upload option.")
            df_raw = load_fallback_data()
    else:
        df_raw = load_fallback_data()

# Standardize column headers
df_raw.columns = [str(col).strip().title() for col in df_raw.columns]

# Identify columns flexibly
symbol_col = next((col for col in df_raw.columns if 'symbol' in col.lower() or 'security' in col.lower()), 'Symbol')
client_col = next((col for col in df_raw.columns if 'client' in col.lower() or 'name' in col.lower()), 'Client Name')
action_col = next((col for col in df_raw.columns if 'buy' in col.lower() or 'sell' in col.lower()), 'Buy/Sell')
vol_col = next((col for col in df_raw.columns if 'volume' in col.lower() or 'quantity' in col.lower()), 'Volume')
price_col = next((col for col in df_raw.columns if 'price' in col.lower() or 'avg' in col.lower()), 'Trade Price/Weighted. Avg. Price')

# Clean numeric data
if vol_col in df_raw.columns:
    df_raw[vol_col] = pd.to_numeric(df_raw[vol_col].astype(str).str.replace(',', ''), errors='coerce')
if price_col in df_raw.columns:
    df_raw[price_col] = pd.to_numeric(df_raw[price_col].astype(str).str.replace(',', ''), errors='coerce')

# --- TABS FOR INTELLIGENCE EXTRACTION ---
tab1, tab2, tab3 = st.tabs([
    "🏆 Top Institutional Accumulations (By Stock)", 
    "🔍 Smart Money Price Anchors", 
    "📄 Raw Verified Data Feed"
])

with tab1:
    st.subheader("🔥 Stocks with Highest Institutional Volume Accumulation")
    if not df_raw.empty and symbol_col in df_raw.columns and vol_col in df_raw.columns:
        pivot_df = df_raw.pivot_table(index=symbol_col, columns=action_col, values=vol_col, aggfunc='sum', fill_value=0)
        if 'BUY' in pivot_df.columns and 'SELL' in pivot_df.columns:
            pivot_df['NET_ACCUMULATION'] = pivot_df['BUY'] - pivot_df['SELL']
        elif 'BUY' in pivot_df.columns:
            pivot_df['NET_ACCUMULATION'] = pivot_df['BUY']
        else:
            pivot_df['NET_ACCUMULATION'] = pivot_df.iloc[:, 0]

        pivot_df = pivot_df.sort_values(by='NET_ACCUMULATION', ascending=False).reset_index()
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.warning("Insufficient data columns for aggregation.")

with tab2:
    st.subheader("⚓ Smart Money Price Anchors")
    if not df_raw.empty and price_col in df_raw.columns:
        display_cols = [c for c in [symbol_col, client_col, action_col, vol_col, price_col] if c in df_raw.columns]
        top_deals = df_raw.sort_values(by=vol_col, ascending=False) if vol_col in df_raw.columns else df_raw
        st.dataframe(top_deals[display_cols].head(15), use_container_width=True, hide_index=True)
    else:
        st.warning("Price data not available.")

with tab3:
    st.subheader("📄 Complete Filtered Report")
    st.dataframe(df_raw, use_container_width=True)
