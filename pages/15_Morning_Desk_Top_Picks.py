import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Morning Desk Picks", page_icon="🎯", layout="wide")

st.title("🎯 CNBC Morning Desk & Expert Panel Live Terminal")
st.markdown("Track morning panel picks, volume momentum, and profit-booking targets.")

st.sidebar.header("Settings")
tickers_input = st.sidebar.text_area("Tickers (comma separated)", value="MANKIND, DIVISLAB, HONASA, WOCKPHARMA, GLAND, SBIN")
watchlist = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

@st.cache_data(ttl=120)
def get_data(symbols):
    data = []
    for s in symbols:
        sym = f"{s}.NS" if not s.endswith(".NS") else s
        try:
            df = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 3:
                continue
            
            ltp = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            chg = ((ltp - prev) / prev) * 100
            
            avg_vol = float(df['Volume'].tail(5).mean())
            cur_vol = float(df['Volume'].iloc[-1])
            v_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0
            
            atr = ltp * 0.02
            sl = round(ltp - (1.2 * atr), 2)
            tgt = round(ltp + (3.0 * atr), 2)
            
            status = "🟢 BREAKOUT" if chg > 0.5 else "🔴 ACCUMULATION"
            
            data.append({
                "Stock": s,
                "LTP": round(ltp, 2),
                "Change_%": round(chg, 2),
                "Vol_Mult": round(v_mult, 2),
                "Status": status,
                "Stop_Loss": sl,
                "Book_Profit_Target": tgt
            })
        except:
            continue
    return pd.DataFrame(data)

df_res = get_data(watchlist)

if df_res.empty:
    st.warning("Please check your ticker symbols.")
else:
    df_res = df_res.sort_values(by="Change_%", ascending=False)
    st.markdown("### 🔥 Live Actionable Table")
    st.dataframe(df_res, use_container_width=True)
