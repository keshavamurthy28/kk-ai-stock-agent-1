import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")
st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown("Prioritizes **🟢 Master Confluence** stocks (predicted in **Night Before Prep** + confirmed in **Matched Super Signal**) with **Exact Kite Limit Buy Zones** and **SMC Past ➔ Present ➔ Future** charts.")

NSE_UNIVERSE = list(dict.fromkeys(["BELRISE", "DEEPAKFERT", "ATHERENERG", "ITC", "BHARTIARTL", "PNB", "KALYANKJIL", "SBIN", "HDFCBANK", "ICICIBANK", "EICHERMOT", "BSE", "HINDALCO", "TDPOWERSYS", "ABB", "V2RETAIL", "KAYNES", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE", "SUNPHARMA", "MARUTI", "NTPC", "POWERGRID", "M&M", "TATASTEEL", "HAL", "BEL", "TRENT", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES", "AMBER", "MSTCLTD", "POWERINDIA", "HONASA", "GLAND", "MANKIND", "DIVISLAB", "WOCKPHARMA", "INDUSTOWER", "HINDCOPPER", "DATAPATTNS", "DIXON", "POLYCAB", "KEI", "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "SUZLON", "IREDA", "HUDCO", "NBCC", "SJVN", "NHPC", "BHEL", "SAIL", "NMDC", "VEDL", "JSWSTEEL", "JINDALSTEL", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "TATAPOWER", "JSWENERGY", "CGPOWER", "SIEMENS", "CUMMINSIND", "THERMAX", "TRITURBINE", "KPITTECH", "PERSISTENT", "COFORGE", "TECHM", "WIPRO", "HCLTECH", "NAUKRI", "PAYTM", "POLICYBZR", "ANGELONE", "CDSL", "MCX", "IEX", "TITAN", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND", "DABUR", "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT", "ULTRACEMCO", "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"]))

def get_rvol_scale():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    m_open, m_close = now_ist.replace(hour=9, minute=15, second=0, microsecond=0), now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5: return 1.0
    return min(375.0 / max((now_ist - m_open).total_seconds() / 60.0, 5.0), 25.0)

@st.cache_data(ttl=90)
def compute_top2_confluence(tickers, nb_list, ss_list):
    try: raw = yf.download([f"{t}.NS" for t in tickers], period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception: return pd.DataFrame()
    scale, rows = get_rvol_scale(), []
    for t in tickers:
        try:
            df = raw[f"{t}.NS"].dropna()
            if len(df) < 25: continue
            ltp, open_p, high_p, low_p, prev_c = float(df["Close"].iloc[-1]), float(df["Open"].iloc[-1]), float(df["High"].iloc[-1]), float(df["Low"].iloc[-1]), float(df["Close"].iloc[-2])
            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round((float(df["Volume"].iloc[-1]) * scale) / vol_avg, 2) if vol_avg > 0 else 1.0
            ema21, ema50 = float(df["Close"].ewm(span=21).mean().iloc[-1]), float(df["Close"].ewm(span=50).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())
            is_nb = (t in nb_list) or (prev_c > ema21 > ema50 and -2.5 <= ((res_20d - prev_c) / prev_c) * 100 <= 4.0)
            is_ss = (t in ss_list) or (pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema21)
            if pct_chg < 0.8 or pct_chg > 9.5 or not is_ss: continue
            is_master, broke_20d = (is_nb and is_ss), (ltp >= res_20d)
            near_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            score = (100 if is_master else 0) + (pct_chg * 5) + (min(rvol, 8.0) * 4) + (15 if broke_20d else 0) + (10 if
