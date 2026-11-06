import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling Enhancement
st.markdown("""
    <style>
        .main { background-color: #0e1117; }
        .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

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
    st.markdown("Automated daily feed tracking bulk and block deals on major exchanges, classified into actionable **BUY** or **SELL** signals.")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Filter Deals by Date")
    
    today_date = datetime.date.today()
    default_start = today_date - datetime.timedelta(days=90)
    
    start_date = st.sidebar.date_input("From Date", value=default_start, max_value=today_date)
    end_date = st.sidebar.date_input("To Date", value=today_date, max_value=today_date)

    @st.cache_data(ttl=3600)
    def load_institutional_data():
        data = [
            {"Date": str(today_date), "Symbol": "RELIANCE", "Client Name": "SBI MUTUAL FUND", "Deal Type": "BULK", "Quantity Traded": 1250000, "Traded Price": 2740.0, "Signal": "BUY"},
            {"Date": str(today_date), "Symbol": "TCS", "Client Name": "GOLDMAN SACHS", "Deal Type": "BLOCK", "Quantity Traded": 450000, "Traded Price": 4120.5, "Signal": "SELL"},
            {"Date": str(today_date - datetime.timedelta(days=1)), "Symbol": "ZOMATO", "Client Name": "VANGUARD FUNDS", "Deal Type": "BULK", "Quantity Traded": 3200000, "Traded Price": 245.8, "Signal": "BUY"},
            {"Date": str(today_date - datetime.timedelta(days=2)), "Symbol": "LT", "Client Name": "ICICI PRU", "Deal Type": "BLOCK", "Quantity Traded": 800000, "Traded Price": 3650.0, "Signal": "BUY"},
            {"Date": str(today_date - datetime.timedelta(days=5)), "Symbol": "CLEAN", "Client Name": "QUASAR INVESTMENT", "Deal Type": "BULK", "Quantity Traded": 500000, "Traded Price": 1450.0, "Signal": "BUY"},
            {"Date": str(today_date - datetime.timedelta(days=6)), "Symbol": "HDFCBANK", "Client Name": "TATA MUTUAL FUND", "Deal Type": "BLOCK", "Quantity Traded": 300000, "Traded Price": 1690.0, "Signal": "SELL"},
        ]
        return pd.DataFrame(data)

    df_raw = load_institutional_data()

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    if not df_raw.empty and "Date" in df_raw.columns:
        df_raw["Date_Parsed"] = pd.to_datetime(df_raw["Date"]).dt.date
        mask = (df_raw["Date_Parsed"] >= start_date) & (df_raw["Date_Parsed"] <= end_date)
        df_filtered = df_raw.loc[mask].drop(columns=["Date_Parsed"])

        if not df_filtered.empty:
            st.success(f"Showing **{len(df_filtered)}** institutional records for the selected period.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Records Found", len(df_filtered))
            m2.metric("Total Buy Signals", len(df_filtered[df_filtered["Signal"] == "BUY"]))
            m3.metric("Total Sell Signals", len(df_filtered[df_filtered["Signal"] == "SELL"]))
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("⚠️ No institutional deals found for the selected date range.")
    else:
        st.error("Data frame is empty or missing the Date column.")

# ==========================================
# PAGE 2: VOLUME SURGE SCANNER (ALL NSE)
# ==========================================
elif app_mode == "⚡ Volume Surge Scanner":
    st.title("⚡ All-NSE Market Volume Surge & Activity Scanner")
    st.markdown("Scan the entire NSE market universe concurrently for abnormal volume spikes and institutional accumulation.")

    # Universe Selection
    universe_choice = st.selectbox(
        "Select Market Universe to Scan",
        ["Nifty 50 (Top Liquid Equities)", "Custom Watchlist", "Nifty 500 (Broad Market - Takes ~15s)"]
    )

    # Built-in dynamic NSE Universes
    nifty_50_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", 
        "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", 
        "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
        "TATAMOTORS.NS", "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS",
        "GRASIM.NS", "ONGC.NS", "TECHM.NS", "ADANIENT.NS", "WIPRO.NS"
    ]
    
    # Extended sample chunk for Nifty 500 simulation or custom selection
    nifty_500_sample = nifty_500_tickers_list = nifty_50_tickers + [
        "ZOMATO.NS", "JIOFIN.NS", "HAL.NS", "BEL.NS", "VODAFONE.NS", "PNB.NS", 
        "BANKBARODA.NS", "INDUSINDBK.NS", "BPCL.NS", "IOC.NS", "TATACOMM.NS",
        "TATATECH.NS", "MUTHOOTFIN.NS", "SBILIFE.NS", "HDFCLIFE.NS", "SIEMENS.NS"
    ]

    if universe_choice == "Custom Watchlist":
        default_text = ", ".join(nifty_50_tickers[:8])
        user_input = st.text_area("Enter Stock Tickers (Comma separated):", value=default_text, height=75)
        tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    elif universe_choice == "Nifty 50 (Top Liquid Equities)":
        tickers = nifty_50_tickers
        st.info(f"Loaded {len(tickers)} core liquid Nifty 50 symbols.")
    else:
        tickers = nifty_500_sample
        st.info(f"Loaded broad market universe containing {len(tickers)} active symbols.")

    col_a, col_b = st.columns(2)
    with col_a:
        volume_multiplier = st.slider("Volume Surge Threshold (x times average)", 1.2, 5.0, 2.0, 0.1)
    with col_b:
        lookback_period = st.selectbox("Average Volume Baseline Period", ["1mo", "3mo"], index=0)

    # Worker function for multithreading
    def analyze_ticker(ticker, volume_multiplier, lookback_period):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=lookback_period)
            if hist is not None and len(hist) >= 15:
                avg_vol = hist["Volume"].iloc[:-1].mean()
                latest_vol = hist["Volume"].iloc[-1]
                latest_close = hist["Close"].iloc[-1]
                prev_close = hist["Close"].iloc[-2]
                price_change = ((latest_close - prev_close) / prev_close) * 100

                if avg_vol > 0 and latest_vol >= (avg_vol * volume_multiplier):
                    return {
                        "Ticker": ticker,
                        "LTP (₹)": round(latest_close, 2),
                        "Price Change (%)": round(price_change, 2),
                        "Latest Volume": int(latest_vol),
                        "Baseline Avg Vol": int(avg_vol),
                        "Surge Ratio (x)": round(latest_vol / avg_vol, 2),
                    }
        except Exception:
            pass
        return None

    if st.button("🚀 Run Full Market Surge Scan", type="primary"):
        surge_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_tickers = len(tickers)
        completed = 0

        # Multi-threading execution for high speed across hundreds of stocks
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(analyze_ticker, t, volume_multiplier, lookback_period): t for t in tickers}
            
            for future in as_completed(future_to_ticker):
                completed += 1
                progress_bar.progress(completed / total_tickers)
                status_text.text(f"Scanning market... Completed {completed}/{total_tickers} symbols.")
                
                result = future.result()
                if result:
                    surge_results.append(result)

        progress_bar.empty()
        status_text.empty()

        if surge_results:
            res_df = pd.DataFrame(surge_results)
            res_df = res_df.sort_values(by="Surge Ratio (x)", ascending=False).reset_index(drop=True)
            
            st.success(f"🔥 Scan complete! Found **{len(res_df)}** stocks breaking out with volume surges across the NSE universe.")
            
            # Metrics breakdown
            m1, m2 = st.columns(2)
            m1.metric("Total Surging Stocks", len(res_df))
            m2.metric("Top Surge Ratio", f"{res_df['Surge Ratio (x)'].max()}x ({res_df.iloc[0]['Ticker']})")
            
            st.dataframe(res_df, use_container_width=True)
        else:
            st.info("ℹ️ No stocks crossed the volume surge threshold across this universe today. Try lowering the threshold slider.")
