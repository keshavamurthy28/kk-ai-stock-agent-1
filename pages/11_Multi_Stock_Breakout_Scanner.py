import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# 1. Page Configuration
st.set_page_config(
    page_title="All-NSE Order Block & Trade Scanner",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🌐 All-NSE Institutional Signal Scanner")
st.markdown("Scans top NSE F&O stocks simultaneously for Order Blocks, generating automated Buy/Sell signals with SL & Targets.")

# Comprehensive Universe of Top Liquid NSE F&O Stocks
NSE_FO_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ITC.NS",
    "SUNPHARMA.NS", "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "TITAN.NS", "BAJFINANCE.NS", "NTPC.NS", "POWERGRID.NS",
    "TATASTEEL.NS", "WIPRO.NS", "ONGC.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "GRASIM.NS", "CIPLA.NS", "TECHM.NS", "BAJAJFINSV.NS",
    "HINDALCO.NS", "COALINDIA.NS", "DRREDDY.NS", "BRITANNIA.NS", "EICHERMOT.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "TATACONSUM.NS"
]

# Sidebar Controls
st.sidebar.header("Scanner Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1d", "1h"], index=0)
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (Target 1)", 1.5, 3.0, 2.0, 0.5)
signal_filter = st.sidebar.radio("Filter Signals", ["ALL", "BUY ONLY", "SELL ONLY"])

@st.cache_data(ttl=600)
def scan_all_stocks(tickers, tf):
    master_signals = []
    period = "3mo" if tf == "1d" else "1mo"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)
    
    for idx, ticker in enumerate(tickers):
        status_text.text(f"Scanning ({idx+1}/{total}): {ticker.replace('.NS', '')}...")
        progress_bar.progress((idx + 1) / total)
        
        try:
            df = yf.download(ticker, period=period, interval=tf, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            
            if len(df) < 20:
                continue
                
            # Order Block & Displacement Logic
            df['Body'] = (df['Close'] - df['Open']).abs()
            df['ATR'] = df['Body'].rolling(14, min_periods=1).mean()
            df['Displacement'] = df['Body'] > (1.2 * df['ATR'])
            df['Bullish_Impulse'] = (df['Close'] > df['Open']) & df['Displacement']
            df['Bearish_Impulse'] = (df['Close'] < df['Open']) & df['Displacement']

            # Check latest candles for active OB
            for i in range(len(df)-3, len(df)):
                if i < 2: 
                    continue
                
                # Bullish OB (BUY)
                if df['Bullish_Impulse'].iloc[i] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
                    entry_min = round(float(df['Low'].iloc[i-1]), 2)
                    entry_max = round(float(df['High'].iloc[i-1]), 2)
                    sl = round(entry_min * 0.992, 2)
                    risk = entry_max - sl
                    t1 = round(entry_max + (risk * rr_ratio), 2)
                    t2 = round(entry_max + (risk * (rr_ratio + 1.0)), 2)
                    
                    master_signals.append({
                        'Stock': ticker.replace(".NS", ""),
                        'Action': 'BUY',
                        'LTP': round(float(df['Close'].iloc[-1]), 2),
                        'Entry Min': entry_min,
                        'Entry Max': entry_max,
                        'Stop Loss': sl,
                        'Target 1': t1,
                        'Target 2': t2,
                        'Time': str(df.index[i-1])[:16]
                    })
                    break # Grab latest valid signal per stock
                    
                # Bearish OB (SELL)
                elif df['Bearish_Impulse'].iloc[i] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
                    entry_min = round(float(df['Low'].iloc[i-1]), 2)
                    entry_max = round(float(df['High'].iloc[i-1], 2), 2) if hasattr(df['High'], 'iloc') else round(float(df['High'].iloc[i-1]), 2)
                    sl = round(entry_max * 1.008, 2)
                    risk = sl - entry_min
                    t1 = round(entry_min - (risk * rr_ratio), 2)
                    t2 = round(entry_min - (risk * (rr_ratio + 1.0)), 2)
                    
                    master_signals.append({
                        'Stock': ticker.replace(".NS", ""),
                        'Action': 'SELL',
                        'LTP': round(float(df['Close'].iloc[-1]), 2),
                        'Entry Min': entry_min,
                        'Entry Max': entry_max,
                        'Stop Loss': sl,
                        'Target 1': t1,
                        'Target 2': t2,
                        'Time': str(df.index[i-1])[:16]
                    })
                    break
        except Exception:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(master_signals)

# Run Scanner Button
if st.button("🚀 Run Full NSE Market Scan", type="primary"):
    df_signals = scan_all_stocks(NSE_FO_UNIVERSE, timeframe)
    st.session_state['scan_results'] = df_signals

# Display Results if available in session
if 'scan_results' in st.session_state:
    res_df = st.session_state['scan_results']
    
    if not res_df.empty:
        # Apply Sidebar Filter
        if signal_filter == "BUY ONLY":
            res_df = res_df[res_df['Action'] == 'BUY']
        elif signal_filter == "SELL ONLY":
            res_df = res_df[res_df['Action'] == 'SELL']
            
        st.success(f"Scan complete! Found {len(res_df)} active institutional setups.")
        
        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        buy_count = len(res_df[res_df['Action'] == 'BUY'])
        sell_count = len(res_df[res_df['Action'] == 'SELL'])
        col1.metric("Total Signals", len(res_df))
        col2.metric("🟢 Buy Signals", buy_count)
        col3.metric("🔴 Sell Signals", sell_count)
        
        st.markdown("---")
        st.subheader("📋 Master Trade Setup Table")
        st.dataframe(res_df, use_container_width=True)
        
        # Mobile Card View for easier viewing on phone screens
        st.subheader("📱 Mobile Signal Cards")
        for idx, row in res_df.iterrows():
            is_buy = row['Action'] == 'BUY'
            card_bg = "#132a1c" if is_buy else "#3a1518"
            border_color = "#00c853" if is_buy else "#ff3d00"
            badge_bg = "#00c853" if is_buy else "#ff3d00"
            
            st.markdown(f"""
            <div style="background-color: {card_bg}; border-left: 5px solid {border_color}; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="font-size: 16px;">{row['Stock']}</b>
                    <span style="background-color: {badge_bg}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{row['Action']}</span>
                </div>
                <div style="margin-top: 6px; font-size: 13px;">
                    <b>LTP:</b> ₹{row['LTP']} | <b>Entry:</b> ₹{row['Entry Min']} - ₹{row['Entry Max']}
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #ddd;">
                    <div>🛑 <b>SL:</b> ₹{row['Stop Loss']}</div>
                    <div>🎯 <b>T1:</b> ₹{row['Target 1']}</div>
                    <div>🚀 <b>T2:</b> ₹{row['Target 2']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No signals found matching current criteria.")
else:
    st.info("Click the **'Run Full NSE Market Scan'** button above to scan all listed stocks.")
