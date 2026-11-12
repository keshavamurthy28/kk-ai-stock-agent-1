import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Matched Super-Signal Watchlist", layout="wide")

st.markdown("### 🎯 Matched Morning Super-Signal Watchlist")
st.markdown("Automatically cross-references your Night-Before Homework with Live Morning Volume Spurts.")

# 1. Create a unified session state so lists from Night Before Prep flow here automatically
if "universal_watchlist" not in st.session_state:
    st.session_state.universal_watchlist = [
        "HINDCOPPER", "STLTECH", "CUPID", "KALYANKJIL", "ITC", "SBIN", "ONGC"
    ]

st.sidebar.header("Filters")
min_vol_surge = st.sidebar.slider("Min Volume Surge (x)", 1.0, 5.0, 2.0, 0.1)

# Allow manual override or addition of your scanned stocks
user_tickers = st.sidebar.text_area(
    "Active Homework Watchlist (Comma separated)", 
    value=", ".join(st.session_state.universal_watchlist)
)
watchlist = [t.strip().upper() for t in user_tickers.split(",") if t.strip()]

if st.button("Run Super-Signal Match Scan"):
    results = []
    for symbol in watchlist:
        sym_query = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        try:
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
            
            # Relaxed filter or exact match
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
            
    if results:
        df_matched = pd.DataFrame(results).sort_values(by="Volume Multiplier", ascending=False)
        st.success(f"Found {len(df_matched)} active breakout signals matching your criteria!")
        st.dataframe(df_matched, use_container_width=True)
    else:
        st.warning("No matched super-signals found right now based on your volume filter threshold. Try lowering the Min Volume Surge slider to 1.1x or 1.2x.")
