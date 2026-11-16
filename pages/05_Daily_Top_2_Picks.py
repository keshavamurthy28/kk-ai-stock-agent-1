import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")

st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown(
    "Automatically computes **Exact Kite Limit Buy Zones** (so you never chase tops), **Strict Stop-Losses**, and **Intraday + Swing Targets** across **🟢 Master Confluence** stocks."
)

NSE_UNIVERSE = list(dict.fromkeys([
    "BELRISE", "DEEPAKFERT", "ATHERENERG", "ITC", "BHARTIARTL", "PNB", "KALYANKJIL",
    "SBIN", "HDFCBANK", "ICICIBANK", "EICHERMOT", "BSE", "HINDALCO", "TDPOWERSYS",
    "ABB", "V2RETAIL", "KAYNES", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE",
    "TATAMOTORS", "SUNPHARMA", "MARUTI", "NTPC", "POWERGRID", "M&M", "TATASTEEL",
    "HAL", "BEL", "TRENT", "ZOMATO", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES",
    "AMBER", "MSTCLTD", "POWERINDIA", "HONASA", "GLAND", "MANKIND", "DIVISLAB",
    "WOCKPHARMA", "INDUSTOWER", "HINDCOPPER", "DATAPATTNS", "DIXON", "POLYCAB", "KEI",
    "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL",
    "SUZLON", "IREDA", "HUDCO", "NBCC", "SJVN", "NHPC", "BHEL", "SAIL", "NMDC",
    "VEDL", "JSWSTEEL", "JINDALSTEL", "ADANIENT", "ADANIPORTS", "ADANIPOWER",
    "TATAPOWER", "JSWENERGY", "CGPOWER", "SIEMENS", "CUMMINSIND", "THERMAX",
    "TRITURBINE", "KPITTECH", "PERSISTENT", "COFORGE", "LTIM", "TECHM", "WIPRO",
    "HCLTECH", "NAUKRI", "PAYTM", "POLICYBZR", "ANGELONE", "CDSL", "MCX", "IEX",
    "TITAN", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND", "DABUR",
    "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT", "ULTRACEMCO",
    "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE",
    "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"
]))

def get_rvol_scale():
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    m_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    m_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5:
        return 1.0
    mins = max((now_ist - m_open).total_seconds() / 60.0, 5.0)
    return min(375.0 / mins, 25.0)

@st.cache_data(ttl=90)
def compute_top2_confluence(tickers, session_nb_list, session_ss_list):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    scale = get_rvol_scale()
    candidates = []

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
            if len(df) < 25:
                continue

            ltp = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1])
            high_p = float(df["High"].iloc[-1])
            low_p = float(df["Low"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])

            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_pace = float(df["Volume"].iloc[-1]) * scale
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 else 1.0

            ema21 = float(df["Close"].ewm(span=21).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())

            dist_prev = ((res_20d - prev_c) / prev_c) * 100
            is_nb_coil = (t in session_nb_list) or (prev_c > ema21 > ema50 and -2.5 <= dist_prev <= 4.0)
            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            is_ss_live = (t in session_ss_list) or (pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema21)

            if pct_chg < 0.8 or pct_chg > 9.5 or not is_ss_live:
                continue

            is_master = is_nb_coil and is_ss_live
            broke_20d = ltp >= res_20d
            score = (100 if is_master else 0) + (pct_chg * 5) + (min(rvol, 8.0) * 4) + (15 if broke_20d else 0) + (10 if near_day_high else 0)

            # Calculate Pullback Limit Buy Price (Retest of 20D breakout / 38.2% intraday retracement)
            intraday_retrace = high_p - ((high_p - low_p) * 0.382)
            ideal_buy = round(max(res_20d, intraday_retrace, open_p * 1.003), 2)
            if ideal_buy > ltp:
                ideal_buy = round(ltp, 2)

            extension_pct = round(((ltp - ideal_buy) / ideal_buy) * 100, 2)
            if extension_pct > 0.8:
                kite_instruction = f"⏳ WAIT FOR PULLBACK BUY @ ₹{ideal_buy:,.2f}"
                action_note = f"Extended +{extension_pct}% above retest. Place Kite Limit Order at ₹{ideal_buy:,.2f}."
            else:
                kite_instruction = f"✅ BUY NOW / LIMIT @ ₹{ideal_buy:,.2f}"
                action_note = f"Price is inside optimal entry zone! Execute Buy near ₹{ideal_buy:,.2f}."

            # Tight Intraday SL & Swing SL
            intraday_sl = round(min(low_p, ideal_buy * 0.988), 2)
            risk = max(ideal_buy - intraday_sl, ideal_buy * 0.008)
            target_intraday = round(ideal_buy + (risk * 1.5), 2)
            target_swing = round(ideal_buy + (risk * 3.0), 2)

            tags = (["Night-Before Coil"] if is_master else []) + ["Super-Signal Live"] + (["20D Breakout"] if broke_20d else [])
            candidates.append({
                "Stock": t,
                "LTP": round(ltp, 2),
                "Change_%": pct_chg,
                "Pace_RVOL": round(rvol, 2),
                "Kite_Action": kite_instruction,
                "Limit_Buy": ideal_buy,
                "Stop_Loss": intraday_sl,
                "Target_1": target_intraday,
                "Target_2": target_swing,
                "Action_Note": action_note,
                "Score": round(score, 1),
                "Confluence": " + ".join(tags),
                "Is_Master": is_master
            })
        except Exception:
            continue

    if not candidates
