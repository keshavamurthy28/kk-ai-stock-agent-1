import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Matched Super-Signal Watchlist", layout="wide")

st.markdown("### 🎯 Expert Desk: Automated Breakout & Profit-Booking Terminal")
st.markdown("Instantly scans the Indian market universe, filters high-volume institutional momentum, and generates ready-to-execute Buy, Stop-Loss, and Target setups.")

st.sidebar.header("Terminal Controls")
min_vol_surge = st.sidebar.slider("Min Volume Multiplier (x)", 1.0, 5.0, 1.5, 0.1)
risk_reward = st.sidebar.selectbox("Target Strategy", ["Aggressive (3:1)", "Balanced (2:1)"], index=0)

# Broad institutional and momentum stock pool
DEFAULT_NSE_UNIVERSE = [
    "HINDCOPPER", "STLTECH", "CUPID", "KALYANKJIL", "ITC", "SBIN", "ONGC",
    "RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "HDFCBANK", "NTPC", 
    "BHARTIARTL", "TATAPOWER", "ADANIPORTS", "BAJFINANCE", "M&M", "SUNPHARMA",
    "WOCKPHARMA", "GLAND", "BEL", "BHEL", "DIVISLAB", "HONASA", "ROTO", 
    "V2RETAIL", "IDEA", "YESBANK", "JPPOWER", "SUZLON", "ZOMATO", "NYKAA",
    "IRFC", "RVNL", "IREDA", "COCHINSHIP", "MAZDOCK", "BDL", "MANKIND"
]

if st.button("🚀 Run Instant Expert Scan & Generate Trades", type="primary"):
    results = []
    progress_bar = st.progress(0)
    total_stocks = len(DEFAULT_NSE_UNIVERSE)
    
    for idx, symbol in enumerate(DEFAULT_NSE_UNIVERSE):
        sym_query = f"{symbol}.NS"
        try:
            df = yf.download(sym_query, period="10d", interval="1d", progress=False, auto_adjust=True)
            
            if df is None or df.empty or len(df) < 5:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            if "Close" not in df.columns or "Volume" not in df.columns:
                continue
            
            ltp = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            chg_pct = ((ltp - prev_close) / prev_close) * 100
            
            # Calculate volume metrics
            avg_vol = float(df["Volume"].tail(5).mean())
            cur_vol = float(df["Volume"].iloc[-1])
            vol_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Calculate Average True Range (ATR) approximation for volatility-based risk management
            high_low = df["High"] - df["Low"]
            high_close = abs(df["High"] - df["Close"].shift())
            low_close = abs(df["Low"] - df["Close"].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = float(true_range.tail(5).mean())
            if pd.isna(atr) or atr == 0:
                atr = ltp * 0.02  # Fallback 2%
            
            # Filter criteria: Must be moving green (positive momentum) and meet volume surge
            if chg_pct > 0 and vol_mult >= min_vol_surge:
                stop_loss = round(ltp - (1.2 * atr), 2)
                
                if "Aggressive" in risk_reward:
                    target_1 = round(ltp + (2.0 * atr), 2)
                    target_2 = round(ltp + (3.5 * atr), 2)
                else:
                    target_1 = round(ltp + (1.5 * atr), 2)
                    target_2 = round(ltp + (2.5 * atr), 2)
                
                results.append({
                    "Stock": symbol,
                    "Action": "BUY",
                    "LTP (₹)": round(ltp, 2),
                    "Change (%)": round(chg_pct, 2),
                    "Volume Spike": f"{round(vol_mult, 2)}x",
                    "Stop Loss (₹)": stop_loss,
                    "Target 1 (₹)": target_1,
                    "Target 2 (₹)": target_2
                })
        except Exception:
            continue
            
        progress_bar.progress((idx + 1) / total_stocks)
        
    progress_bar.empty()
    
    if results:
        df_matched = pd.DataFrame(results).sort_values(by="Change (%)", ascending=False)
        st.success(f"🎯 Execution Matrix Ready! Found {len(df_matched)} high-conviction breakout setups.")
        
        # Display professional expert table
        st.dataframe(df_matched, use_container_width=True)
        
        st.markdown("### 📋 Quick-Execution Summary Cards")
        cols = st.columns(3)
        for i, row in df_matched.reset_index().iterrows():
            with cols[i % 3]:
                st.markdown(f"""
### 🟢 {row['Stock']} ({row['Change (%)']:+.2f}%)
* **Action:** **{row['Action']}** at ₹{row['LTP (₹)']}
* **Volume Surge:** {row['Volume Spike']}
* 🛑 **Stop-Loss:** **₹{row['Stop Loss (₹)']}**
* 🎯 **Target 1:** **₹{row['Target 1 (₹)']}**
* 🎯 **Target 2:** **₹{row['Target 2 (₹)']}**
---
""")
    else:
        st.warning("No stocks matched the strict volume/momentum criteria right now. Try lowering the 'Min Volume Multiplier' slider to 1.1x in the sidebar.")
else:
    st.info("Click **'🚀 Run Instant Expert Scan & Generate Trades'** above to let the automated desk compile your trade execution table.")
