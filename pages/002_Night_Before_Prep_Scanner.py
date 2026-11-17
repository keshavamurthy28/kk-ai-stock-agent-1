import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Night Before Institutional Prep Scanner", layout="wide")

st.title("🌙 Night Before Institutional Prep & Watchlist Generator")
st.markdown(
    "Scans **120+ NSE Stocks** for tight pre-breakout accumulation coils and sends the watchlist automatically to **Matched Super Signal Page** & **Daily Top 2 Picks**."
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

@st.cache_data(ttl=120)
def build_night_before_watchlist(tickers):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    scale = get_rvol_scale()
    rows = []

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
            if len(df) < 25:
                continue

            close_now = float(df["Close"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            pct_chg = round(((close_now - close_prev) / close_prev) * 100, 2)

            vol_pace = float(df["Volume"].iloc[-1]) * scale
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 else 1.0

            ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())
            dist_20d = round(((res_20d - close_now) / close_now) * 100, 2)

            atr5 = float((df["High"] - df["Low"]).tail(5).mean())
            atr20 = float((df["High"] - df["Low"]).tail(20).mean())

            # Pre-breakout accumulation coil criteria
            if close_now > ema20 > ema50 and -2.5 <= dist_20d <= 4.0 and pct_chg >= -0.5:
                is_vcp = atr5 < (atr20 * 0.92)
                tier = "Aggressive Coil" if (dist_20d <= 1.5 and rvol >= 1.2) else "Conservative Swing"
                catalyst = (
                    f"VCP Tight Coil ({dist_20d}% below 20D High) + {rvol}x RVOL"
                    if is_vcp else f"Accumulating {dist_20d}% from 20D Breakout ({rvol}x RVOL)"
                )
                rows.append({
                    "Stock": t,
                    "Close": round(close_now, 2),
                    "Change_%": pct_chg,
                    "Pace_RVOL": f"{rvol:.2f}x",
                    "Dist_to_Breakout_%": dist_20d,
                    "Tier": tier,
                    "Catalyst_Driver": catalyst
                })
        except Exception:
            continue

    return pd.DataFrame(rows)

if st.button("🔄 Refresh Night Before Prep Scan"):
    st.cache_data.clear()

df_nb = build_night_before_watchlist(NSE_UNIVERSE)

if df_nb.empty:
    st.warning("No pre-breakout accumulation coils found right now.")
    st.session_state["night_before_watchlist"] = []
else:
    df_nb = df_nb.sort_values(by=["Dist_to_Breakout_%", "Change_%"], ascending=[True, False]).reset_index(drop=True)
    # Save watchlist to session state for Matched Super Signal Page
    st.session_state["night_before_watchlist"] = df_nb["Stock"].tolist()

    st.success(f"✅ **{len(df_nb)} Pre-Breakout Stocks** queued and synced with **Matched Super Signal Page**.")

    agg_df = df_nb[df_nb["Tier"] == "Aggressive Coil"]
    con_df = df_nb[df_nb["Tier"] == "Conservative Swing"]

    st.subheader(f"⚡ Aggressive Pre-Breakout Coils ({len(agg_df)} Stocks)")
    st.dataframe(agg_df, use_container_width=True, hide_index=True)

    st.subheader(f"🛡️ Conservative Swing Watchlist ({len(con_df)} Stocks)")
    st.dataframe(con_df, use_container_width=True, hide_index=True)
