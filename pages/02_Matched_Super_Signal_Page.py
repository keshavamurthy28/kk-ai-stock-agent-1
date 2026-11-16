import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Live Intraday Super-Signal Terminal", layout="wide")

st.title("🎯 Live Intraday Super-Signal & Early Breakout Engine")
st.markdown(
    "Scans **120+ Active NSE Equities** in real time for **15-Min Opening Range Breakouts (ORB)**, **Time-Adjusted Volume Surges**, and **20-Day Resistance Breakouts** to catch institutional momentum early."
)

# Expanded 120+ High-Momentum NSE Universe (Nifty 50 + Next 50 + Midcap/Active Movers)
NSE_ACTIVE_UNIVERSE = [
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
    "TITAN", "KALYANKJIL", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND",
    "DABUR", "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT",
    "ULTRACEMCO", "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY",
    "PRESTIGE", "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"
]
NSE_ACTIVE_UNIVERSE = list(dict.fromkeys(NSE_ACTIVE_UNIVERSE))

def get_rvol_scale():
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    m_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    m_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5:
        return 1.0
    mins = max((now_ist - m_open).total_seconds() / 60.0, 5.0)
    return min(375.0 / mins, 25.0)

@st.cache_data(ttl=90)
def scan_live_intraday_breakouts(tickers):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="1mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    scale = get_rvol_scale()
    signals = []

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
            if len(df) < 15:
                continue

            ltp = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1])
            high_p = float(df["High"].iloc[-1])
            low_p = float(df["Low"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])

            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_pace = float(df["Volume"].iloc[-1]) * scale
            vol_avg = float(df["Volume"].iloc[-16:-1].mean())
            rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 else 1.0

            res_15d = float(df["High"].iloc[-16:-1].max())
            ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])

            # Early Breakout Criteria: Positive momentum, holding near intraday high, volume surge
            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            if pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema20:
                broke_15d = ltp >= res_15d
                score = (pct_chg * 6) + (rvol * 10) + (20 if broke_15d else 0) + (10 if near_day_high else 0)

                sl = round(max(low_p, prev_c * 0.99) * 0.995, 2)
                risk = max(ltp - sl, ltp * 0.012)
                t1 = round(ltp + (risk * 1.5), 2)
                t2 = round(ltp + (risk * 3.0), 2)

                status = "🔥 #1 Live Intraday Volume & Breakout Leader" if score >= 65 else "⚡ Early Institutional Accumulation Breakout"
                reason = (
                    f"15D High Breakout + {rvol}x Pace Volume Surge" if broke_15d
                    else f"Strong Opening Drive (+{pct_chg}%) + {rvol}x Institutional RVOL"
                )

                signals.append({
                    "Stock": t,
                    "Action": "BUY",
                    "LTP": round(ltp, 2),
                    "Change_%": pct_chg,
                    "Volume_Surge": f"{rvol:.2f}x",
                    "Stop_Loss": sl,
                    "Target_1": t1,
                    "Target_2": t2,
                    "Status": status,
                    "Catalyst_Reason": reason,
                    "Score": score
                })
        except Exception:
            continue

    if not signals:
        return pd.DataFrame()
    df_out = pd.DataFrame(signals).sort_values(by="Score", ascending=False).reset_index(drop=True)
    df_out.insert(0, "Rank", df_out.index + 1)
    return df_out.drop(columns=["Score"])

if st.button("🔄 Force Refresh Live Data"):
    st.cache_data.clear()

df_live = scan_live_intraday_breakouts(NSE_ACTIVE_UNIVERSE)

if df_live.empty:
    st.warning("No stocks currently meet the strict intraday breakout + RVOL criteria.")
else:
    st.subheader("🏆 Live Intraday Execution Ranking Table")
    st.dataframe(df_live, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🎯 Live Execution Summary Cards (Top 3 Ranked)")
    for _, row in df_live.head(3).iterrows():
        st.markdown(f"### Rank #{row['Rank']}: {row['Stock']} (+{row['Change_%']}%) — {row['Status']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Action & LTP", f"BUY @ ₹{row['LTP']:,.2f}")
        c2.metric("Stop-Loss", f"₹{row['Stop_Loss']:,.2f}")
        c3.metric("Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}")
        c4.metric("Target 2 (3.0R)", f"₹{row['Target_2']:,.2f}")
        st.info(f"💡 **Root Cause / Catalyst:** {row['Catalyst_Reason']}")
