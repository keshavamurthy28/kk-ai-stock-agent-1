import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Multi-Stock Breakout Scanner", layout="wide")

st.title("🚀 NSE Multi-Stock Breakout & Volume Screener")
st.markdown("Scans multiple F&O stocks simultaneously for volume surges, price displacement, and breakout zones.")

# Expanded stock universe
BROAD_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ITC.NS",
    "SUNPHARMA.NS", "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "TITAN.NS", "BAJFINANCE.NS", "NTPC.NS", "POWERGRID.NS"
]

timeframe = st.selectbox("Select Timeframe for Bulk Scan", ["1d", "1h"], index=0)

@st.cache_data(ttl=300)
def scan_market(tickers, tf):
    import yfinance as yf
    results = []
    period = "1mo" if tf == "1h" else "3mo"
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=tf, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            if len(df) < 15:
                continue
                
            # Basic Breakout & Volume criteria
            df['Volume_MA'] = df['Volume'].rolling(10).mean()
            df['Body'] = (df['Close'] - df['Open']).abs()
            df['ATR'] = df['Body'].rolling(14, min_periods=1).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            is_volume_surge = latest['Volume'] > (1.5 * latest['Volume_MA'])
            is_bullish_breakout = latest['Close'] > df['High'].iloc[-15:-1].max()
            
            if is_bullish_breakout or is_volume_surge:
                results.append({
                    'Stock': ticker.replace(".NS", ""),
                    'LTP': round(float(latest['Close']), 2),
                    'Volume Surge': "🔥 Yes" if is_volume_surge else "Normal",
                    'Breakout Status': "🚀 New High Breakout" if is_bullish_breakout else "Consolidating",
                    'Signal Strength': 'High' if (is_volume_surge and is_bullish_breakout) else 'Moderate'
                })
        except Exception:
            continue
    return pd.DataFrame(results)

if st.button("Run Bulk Market Scan"):
    with st.spinner("Scanning NSE F&O universe..."):
        scan_df = scan_market(BROAD_UNIVERSE, timeframe)
        
    if not scan_df.empty:
        st.success(f"Scan complete! Found {len(scan_df)} active breakout/volume candidates.")
        st.dataframe(scan_df, use_container_width=True)
    else:
        st.warning("No stocks met the strict breakout criteria on this timeframe. Try switching to 1h.")
else:
    st.info("Click 'Run Bulk Market Scan' above to scan across all loaded stocks.")
