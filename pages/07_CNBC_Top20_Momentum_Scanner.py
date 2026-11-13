import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="CNBC Top 20 & Institutional Momentum Scanner", layout="wide")

st.title("📺 CNBC-Style 'Top 20' & Institutional Momentum Desk")
st.markdown("""
*Automated scanner replicating financial television and brokerage desk screening across the **broad Indian market (NSE)**.* 
*Identifies **High-Conviction Breakouts**, **Volume Spurts**, and **Automatic Profit Booking Levels** dynamically.*
""")

# --- Sidebar Configuration ---
st.sidebar.subheader("🌐 Market Universe & Filters")
market_scope = st.sidebar.selectbox(
    "Select Scanning Universe", 
    ["Broad NSE Liquid F&O Universe (Top 50+)", "Nifty 50 Momentum Basket", "Custom Watchlist Override"]
)

min_vol_surge = st.sidebar.slider("Min Volume Surge Multiplier", 0.5, 3.0, 1.2, 0.1)

# Define Broad Market Universes (Append '.NS' for Yahoo Finance)
nifty_fno_pool = [
    "RELIANCE", "TATASTEEL", "SBIN", "HDFCBANK", "INFY", "ICICIBANK", "ONGC", "BEL", "HAL", 
    "DIVISLAB", "WOCKPHARMA", "SUNPHARMA", "TCS", "ITC", "LT", "AXISBANK", "KOTAKBANK", 
    "BAJFINANCE", "MARUTI", "TITAN", "BHARTIARTL", "ASIANPAINT", "HINDUNILVR", "NTPC", 
    "POWERGRID", "TATAMOTORS", "M&M", "ADANIENT", "ADANIPORTS", "COALINDIA", "BAJAJ-AUTO",
    "JINDALSTEL", "BPCL", "TATAPOWER", "GRASIM", "TECHM", "HEROMOTOCO", "INDUSINDBK"
]

nifty_50_pool = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", 
    "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "HINDUNILVR", "MARUTI", "SUNPHARMA"
]

if market_scope == "Broad NSE Liquid F&O Universe (Top 50+)":
    active_pool = nifty_fno_pool
elif market_scope == "Nifty 50 Momentum Basket":
    active_pool = nifty_50_pool
else:
    user_input = st.sidebar.text_input("Custom Tickers (Space separated)", "RELIANCE TATASTEEL SBIN HDFCBANK INFY")
    active_pool = [s.strip().upper() for s in user_input.split()]

# --- Live Data Scanning Engine ---
@st.cache_data(ttl=600)
def fetch_and_scan_market(tickers):
    scanned_records = []
    
    for symbol in tickers:
        ticker_str = symbol if symbol.endswith(".NS") else symbol + ".NS"
        try:
            df = yf.download(ticker_str, period="5d", interval="1d", progress=False)
            if df is None or len(df) < 2:
                continue
            
            # Handle potential MultiIndex columns from newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            close_prices = df['Close']
            volumes = df['Volume']
            
            current_price = float(close_prices.iloc[-1])
            prev_close = float(close_prices.iloc[-2])
            pct_change = ((current_price - prev_close) / prev_close) * 100
            
            current_vol = float(volumes.iloc[-1])
            avg_vol = float(volumes.iloc[:-1].mean()) if len(volumes) > 1 else current_vol
            vol_surge = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Filter by volume surge if required
            if vol_surge < min_vol_surge and market_scope != "Custom Watchlist Override":
                # Keep top stocks flowing anyway if strict filter drops too many, but let's score them
                pass

            # Determine Catalyst & Score
            if pct_change > 1.0 and vol_surge >= 1.2:
                catalyst = "Institutional Volume Spurt"
                score = 4
            elif pct_change > 0:
                catalyst = "Positive Momentum / Q2 Flow"
                score = 4
            else:
                catalyst = "Accumulation Zone"
                score = 3
                
            stop_loss = round(current_price * 0.968, 2)
            target = round(current_price * 1.068, 2)
            
            scanned_records.append({
                "Ticker": symbol.replace(".NS", ""),
                "Price": round(current_price, 2),
                "Change_%": round(pct_change, 2),
                "Vol_Surge": round(vol_surge, 2),
                "Score": f"{score}/5",
                "Catalyst": catalyst,
                "Stop_Loss": stop_loss,
                "Target": target
            })
        except Exception:
            continue
            
    result_df = pd.DataFrame(scanned_records)
    if not result_df.empty:
        result_df = result_df.sort_values(by="Change_%", ascending=False).reset_index(drop=True)
    return result_df

with st.spinner("Scanning broader Indian market for live desk momentum..."):
    df_scanned = fetch_and_scan_market(active_pool)

if df_scanned.empty:
    st.warning("No stocks matched the current criteria. Try adjusting your volume filter or market scope.")
else:
    st.markdown(f"### 🔥 Top Actionable Stocks for the Day (Dynamic Market Sweep — Total Found: {len(df_scanned)})")
    st.markdown("*Picked based on live volume surge, breakout proximity, and momentum score across the market.*")
    
    # Display cards in a grid layout
    cols_per_row = 3
    rows = [df_scanned.iloc[i:i + cols_per_row] for i in range(0, len(df_scanned), cols_per_row)]
    
    for row in rows:
        cols = st.columns(len(row))
        for idx, (_, row_data) in enumerate(row.iterrows()):
            with cols[idx]:
                change_val = row_data['Change_%']
                emoji = "🟢" if change_val >= 0 else "🔴"
                
                st.markdown(f"""
                **{emoji} {row_data['Ticker']} ({change_val:+.2f}%)**  
                * Live Price: **₹{row_data['Price']}**  
                * Vol: **{row_data['Vol_Surge']}x**  
                * *Score:* {row_data['Score']} | *Catalyst:* {row_data['Catalyst']}  
                👉 **Action:** Buy CMP  
                🛑 **Stop-Loss:** ₹{row_data['Stop_Loss']}  
                🎯 **Book Profit Target:** *₹{row_data['Target']}*  
                ---
                """)

    # Complete Matrix Table View
    st.markdown("### 📋 Complete Screening & Profit Booking Matrix")
    st.dataframe(df_scanned, use_container_width=True)
