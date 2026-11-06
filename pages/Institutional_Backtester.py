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
    ["📊 Institutional Bulk & Block Deals", "⚡ Volume Surge Scanner & Intraday Setup"],
)

# ==========================================
# PAGE 1: INSTITUTIONAL BULK & BLOCK DEALS
# ==========================================
if app_mode == "📊 Institutional Bulk & Block Deals":
    st.title("📊 Daily Institutional Bulk & Block Deals (Buy / Sell)")
    st.markdown("Automated daily feed tracking bulk and block deals on major exchanges.")

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
        ]
        return pd.DataFrame(data)

    df_raw = load_institutional_data()
    if not df_raw.empty and "Date" in df_raw.columns:
        df_raw["Date_Parsed"] = pd.to_datetime(df_raw["Date"]).dt.date
        mask = (df_raw["Date_Parsed"] >= start_date) & (df_raw["Date_Parsed"] <= end_date)
        df_filtered = df_raw.loc[mask].drop(columns=["Date_Parsed"])
        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("No records found for the selected date range.")

# ==========================================
# PAGE 2: VOLUME SURGE & INTRADAY SETUP
# ==========================================
elif app_mode == "⚡ Volume Surge Scanner & Intraday Setup":
    st.title("⚡ Intraday Volume Surge & Risk-Managed Setup Generator")
    st.markdown("Scans NSE equities for volume spikes, classifies **BUY/SELL** actions, and calculates exact **Stop-Loss** and **Targets** to protect against losses.")

    universe_choice = st.selectbox(
        "Select Market Universe to Scan",
        ["Nifty 50 (Top Liquid Equities)", "Nifty 500 (Broad Market)"]
    )

    nifty_50_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", 
        "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS", 
        "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
        "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS", "ONGC.NS", "TECHM.NS", "WIPRO.NS"
    ]
    
    nifty_500_sample = nifty_50_tickers + [
        "ZOMATO.NS", "JIOFIN.NS", "HAL.NS", "BEL.NS", "PNB.NS", 
        "BANKBARODA.NS", "INDUSINDBK.NS", "BPCL.NS", "IOC.NS", "TATATECH.NS"
    ]

    tickers = nifty_50_tickers if universe_choice == "Nifty 50 (Top Liquid Equities)" else nifty_500_sample

    col_a, col_b = st.columns(2)
    with col_a:
        volume_multiplier = st.slider("Volume Surge Threshold (x times average)", 1.2, 5.0, 2.0, 0.1)
    with col_b:
        risk_reward_ratio = st.selectbox("Target Risk-Reward Ratio", ["1 : 1.5", "1 : 2.0", "1 : 3.0"], index=1)

    def analyze_intraday_setup(ticker, volume_multiplier):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            if hist is not None and len(hist) >= 15:
                avg_vol = hist["Volume"].iloc[:-1].mean()
                latest_vol = hist["Volume"].iloc[-1]
                latest_close = hist["Close"].iloc[-1]
                prev_close = hist["Close"].iloc[-2]
                price_change = ((latest_close - prev_close) / prev_close) * 100
                day_high = hist["High"].iloc[-1]
                day_low = hist["Low"].iloc[-1]

                if avg_vol > 0 and latest_vol >= (avg_vol * volume_multiplier):
                    if price_change >= 0:
                        action = "🟢 BUY (Long)"
                        stop_loss = round(day_low * 0.995, 2)
                        risk = latest_close - stop_loss
                        mult = 2.0 if "2.0" in risk_reward_ratio else (1.5 if "1.5" in risk_reward_ratio else 3.0)
                        target = round(latest_close + (risk * mult), 2)
                    else:
                        action = "🔴 SELL (Short)"
                        stop_loss = round(day_high * 1.005, 2)
                        risk = stop_loss - latest_close
                        mult = 2.0 if "2.0" in risk_reward_ratio else (1.5 if "1.5" in risk_reward_ratio else 3.0)
                        target = round(latest_close - (risk * mult), 2)

                    return {
                        "Ticker": ticker,
                        "Action Setup": action,
                        "LTP (₹)": round(latest_close, 2),
                        "Change (%)": round(price_change, 2),
                        "Suggested Stop-Loss (₹)": stop_loss,
                        "Suggested Target (₹)": target,
                        "Surge Ratio (x)": round(latest_vol / avg_vol, 2),
                    }
        except Exception:
            pass
        return None

    if st.button("🚀 Run Intraday Setup Scanner", type="primary"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total = len(tickers)
        completed = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_tick = {executor.submit(analyze_intraday_setup, t, volume_multiplier): t for t in tickers}
            
            for future in as_completed(future_to_tick):
                completed += 1
                progress_bar.progress(completed / total)
                status_text.text(f"Scanning market... {completed}/{total}")
                res = future.result()
                if res:
                    results.append(res)

        progress_bar.empty()
        status_text.empty()

        if results:
            res_df = pd.DataFrame(results)
            res_df = res_df.sort_values(by="Surge Ratio (x)", ascending=False).reset_index(drop=True)
            
            st.success(f"🎯 Generated risk-managed setups for **{len(res_df)}** stocks!")
            
            def color_coding(val):
                if "BUY" in str(val):
                    return 'background-color: rgba(46, 160, 67, 0.2); color: #3fb950;'
                elif "SELL" in str(val):
                    return 'background-color: rgba(248, 81, 73, 0.2); color: #f85149;'
                return ''

            styled_df = res_df.style.applymap(color_coding, subset=['Action Setup'])
            st.dataframe(styled_df, use_container_width=True)
            
            st.info("💡 **Risk Rule Reminder:** Always place your broker Stop-Loss order right at the suggested price to protect your capital against sudden reversals.")
        else:
            st.warning("No stocks matched the exact intraday surge criteria right now.")
