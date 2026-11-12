import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Matched Super-Signal Watchlist", layout="wide")

st.markdown("### 🎯 Matched Morning Super-Signal Watchlist")
st.markdown("Automatically scans live Indian market leaders, high-volume stocks, and cross-references your morning volume filters.")

st.sidebar.header("Filters")
min_vol_surge = st.sidebar.slider("Min Volume Surge (x)", 1.0, 5.0, 2.0, 0.1)

# Curated list of heavy-weight / active NSE momentum stocks to scan automatically
# You can expand this list or hook it to an NSE live index/scraper fetch
DEFAULT_NSE_UNIVERSE = [
    "HINDCOPPER", "STLTECH", "CUPID", "KALYANKJIL", "ITC", "SBIN", "ONGC",
    "RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "HDFCBANK", "NTPC", 
    "BHARTIARTL", "TATAPOWER", "ADANIPORTS", "BAJFINANCE", "M&M", "SUNPHARMA",
    "WOCKPHARMA", "GLAND", "BEL", "BHEL", "DIVISLAB", "HONASA", "ROTO", "V2RETAIL"
]

if st.button("Run Automated Market Scan"):
    results = []
    
    # Progress bar for smooth automatic fetching
    progress_bar = st.progress(0)
    total_stocks = len(DEFAULT_NSE_UNIVERSE)
    
    for idx, symbol in enumerate(DEFAULT_NSE_UNIVERSE):
        sym_query = f"{symbol}.NS"
        try:
            # Fetch recent price and volume history via yfinance
            df = yf.download(sym_query, period="5d", interval="1d", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) < 2:
                continue
            
            ltp = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            chg_pct = ((ltp - prev_close) / prev_close) * 100
            
            avg_vol = float(df["Volume"].tail(5).mean())
            cur_vol = float(df["Volume"].iloc[-1])
            vol_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Automatically evaluate if it crosses your volume breakout filter
            if vol_mult >= min_vol_surge:
                atr = ltp * 0.02
                results.append({
                    "Stock": symbol,
                    "LTP": round(ltp, 2),
                    "Change (%)": round(chg_pct, 2),
                    "Volume Multiplier": round(vol_mult, 2),
                    "Stop Loss": round(ltp - (1.5 * atr), 2),
                    "Profit Target": round(ltp + (3.0 * atr), 2)
                })
        except Exception:
            continue
            
        progress_bar.progress((idx + 1) / total_stocks)
        
    progress_bar.empty()
    
    if results:
        df_matched = pd.DataFrame(results).sort_values(by="Volume Multiplier", ascending=False)
        st.success(f"Successfully auto-scanned market and found {len(df_matched)} active breakout signals matching your volume criteria!")
        st.dataframe(df_matched, use_container_width=True)
    else:
        st.warning("Market scan completed, but no stocks met the current volume multiplier threshold. Try lowering the 'Min Volume Surge' slider on the sidebar to 1.1x or 1.2x.")
else:
    st.info("Click **'Run Automated Market Scan'** above to let the app automatically check active Indian stock market tickers for breakout and profit-booking setups.")
