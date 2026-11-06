import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Institutional Bulk & Block Intelligence", layout="wide")

st.title("📊 Institutional Bulk & Block Deals - Smart Intelligence Extractor")
st.markdown(
    "Go beyond raw rows! This page extracts hidden institutional intelligence, "
    "tracking volume accumulation, smart money price anchors, and high-conviction buy/sell clusters."
)

st.sidebar.header("⚙️ Data Ingestion & Filters")
uploaded_file = st.sidebar.file_uploader("Upload Daily NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"])

# Default fallback data if no file is uploaded yet
@st.cache_data
def load_fallback_data():
    return pd.DataFrame([
        {"Date": "06-Nov-2026", "Symbol": "RELIANCE", "Security Name": "Reliance Industries Ltd", "Client Name": "SBI MUTUAL FUND", "Buy/Sell": "BUY", "Volume": 1500000, "Trade Price/Weighted. Avg. Price": 2740.0},
        {"Date": "06-Nov-2026", "Symbol": "ZOMATO", "Security Name": "Zomato Limited", "Client Name": "VANGUARD FUNDS", "Buy/Sell": "BUY", "Volume": 3500000, "Trade Price/Weighted. Avg. Price": 245.8},
        {"Date": "06-Nov-2026", "Symbol": "TCS", "Security Name": "Tata Consultancy Services", "Client Name": "GOLDMAN SACHS", "Buy/Sell": "SELL", "Volume": 800000, "Trade Price/Weighted. Avg. Price": 4120.0},
    ])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        st.sidebar.success("✅ Official NSE report loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {e}")
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

# Clean numeric columns
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
    st.markdown("Aggregates total shares bought vs sold across all institutional clients to show where heavy capital is flowing.")

    if not df_raw.empty and symbol_col in df_raw.columns and vol_col in df_raw.columns:
        # Group by Symbol and Action to find net accumulation
        grouped = df_raw.groupby([symbol_col, action_col])[vol_col].sum().reset_index()
        
        # Pivot table for clean view
        pivot_df = df_raw.pivot_table(index=symbol_col, columns=action_col, values=vol_col, aggfunc='sum', fill_value=0)
        
        if 'BUY' in pivot_df.columns and 'SELL' not in pivot_df.columns:
            pivot_df['NET_ACCUMULATION'] = pivot_df['BUY']
        elif 'BUY' in pivot_df.columns and 'SELL' in pivot_df.columns:
            pivot_df['NET_ACCUMULATION'] = pivot_df['BUY'] - pivot_df['SELL']
        else:
            pivot_df['NET_ACCUMULATION'] = pivot_df.iloc[:, 0]

        pivot_df = pivot_df.sort_values(by='NET_ACCUMULATION', ascending=False).reset_index()
        
        st.dataframe(pivot_df, use_container_width=True)
        st.info("💡 **Trading Insight:** Focus your intraday or swing trading on stocks at the very top of this Net Accumulation list where institutions are heavily buying.")
    else:
        st.warning("Insufficient data columns for aggregation.")

with tab2:
    st.subheader("⚓ Smart Money Price Anchors (Institutional Entry Zones)")
    st.markdown("Tracks the exact weighted average price where bulk deals occurred. Use these levels as major support/resistance.")

    if not df_raw.empty and price_col in df_raw.columns:
        display_cols = [c for c in [symbol_col, client_col, action_col, vol_col, price_col] if c in df_raw.columns]
        # Sort by largest volume traded
        top_deals = df_raw.sort_values(by=vol_col, ascending=False) if vol_col in df_raw.columns else df_raw
        st.dataframe(top_deals[display_cols].head(15), use_container_width=True, hide_index=True)
    else:
        st.warning("Price data not available.")

with tab3:
    st.subheader("📄 Complete Filtered Report")
    selected_client = st.selectbox("Filter Specific Client", ["All Clients"] + sorted(df_raw[client_col].dropna().unique().tolist()))
    
    if selected_client != "All Clients":
        filtered_view = df_raw[df_raw[client_col] == selected_client]
    else:
        filtered_view = df_raw
        
    st.dataframe(filtered_view, use_container_width=True)
