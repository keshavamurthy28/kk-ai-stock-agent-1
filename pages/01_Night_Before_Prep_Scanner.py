import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Predictive Institutional Breakout Scanner", layout="wide")

st.title("🎯 Predictive Institutional Pre-Breakout & Accumulation Scanner")
st.markdown(
    "Identifies stocks in **tight institutional accumulation** (VCP compression, rising RVOL, and 20D resistance coil) **before** the breakout—filtering out overextended traps."
)

NSE_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL",
    "ITC", "LT", "AXISBANK", "BAJFINANCE", "TATAMOTORS", "SUNPHARMA", "MARUTI",
    "NTPC", "POWERGRID", "M&M", "TATASTEEL", "HAL", "BEL", "TRENT", "ZOMATO",
    "PNB", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES", "AMBER", "MSTCLTD",
    "POWERINDIA", "TDPOWERSYS", "HONASA", "GLAND", "MANKIND", "DIVISLAB",
    "WOCKPHARMA", "KALYANKJIL", "EICHERMOT", "INDUSTOWER", "ABB", "HINDCOPPER",
    "DATAPATTNS", "DIXON", "POLYCAB", "KEI", "PFC", "RECLTD", "IRFC", "RVNL"
]

def get_intraday_volume_multiplier():
    """Adjusts partial intraday volume based on NSE market hours (9:15 AM - 3:30 PM IST)."""
    now_utc = datetime.datetime.utcnow()
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)

    if now_ist < market_open or now_ist >= market_close or now_ist.weekday() >= 5:
        return 1.0  # Full day completed
    mins_elapsed = max((now_ist - market_open).total_seconds() / 60.0, 5.0)
    return min(375.0 / mins_elapsed, 25.0)  # Scale partial volume to full-day pace

@st.cache_data(ttl=120)
def scan_predictive_setups(tickers):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    vol_scale = get_intraday_volume_multiplier()
    rows = []

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
            if len(df) < 25:
                continue

            close_now = float(df["Close"].iloc[-1])
            open_now = float(df["Open"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            pct_chg = round(((close_now - close_prev) / close_prev) * 100, 2)

            # Time-adjusted Relative Volume (fixes the 0.16x morning bug)
            vol_now = float(df["Volume"].iloc[-1]) * vol_scale
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round(vol_now / vol_avg, 2) if vol_avg > 0 else 1.0

            # Trend & Moving Averages
            ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
            above_emas = close_now > ema20 > ema50

            # Volatility Contraction (VCP): Last 5d range vs prior 15d range
            atr5 = float((df["High"] - df["Low"]).tail(5).mean())
            atr20 = float((df["High"] - df["Low"]).tail(20).mean())
            is_coiling = atr5 < (atr20 * 0.90)

            # Proximity to 20-Day Breakout High (excluding today)
            res_20d = float(df["High"].iloc[-21:-1].max())
            dist_to_bo = round(((res_20d - close_now) / close_now) * 100, 2)

            # Filter out crashing stocks or already-exhausted >7% spikes
            if pct_chg < -0.5 or pct_chg > 7.5:
                continue

            # Institutional Pre-Breakout Conviction Score (0 - 100)
            score = 0
            reasons = []
            if above_emas:
                score += 30
                reasons.append("Above 20/50 EMA")
            if -1.5 <= dist_to_bo <= 3.5:
                score += 30
                reasons.append(f"Coiling {dist_to_bo}% from 20D High")
            if rvol >= 1.3:
                score += 25
                reasons.append(f"Pace RVOL {rvol}x")
            if is_coiling:
                score += 15
                reasons.append("VCP Tight Range")
            if close_now >= open_now and pct_chg > 0:
                score += 10

            if score >= 55:
                sl = round(min(float(df["Low"].tail(3).min()), ema20) * 0.995, 2)
                risk = max(close_now - sl, close_now * 0.01)
                t1 = round(close_now + (risk * 1.5), 2)
                t2 = round(close_now + (risk * 3.0), 2)

                tier = "Early Breakout" if dist_to_bo <= 0.5 and pct_chg >= 1.0 else "Pre-Breakout Coil"
                rows.append({
                    "Stock": t,
                    "LTP (₹)": round(close_now, 2),
                    "Change_%": pct_chg,
                    "Pace_RVOL": f"{rvol:.2f}x",
                    "Setup_Stage": tier,
                    "Score": score,
                    "Entry_Zone": f"₹{round(close_now*0.998,2)} - ₹{round(close_now*1.003,2)}",
                    "Stop_Loss": sl,
                    "Target_1": t1,
                    "Target_2": t2,
                    "Institutional_Signal": " + ".join(reasons)
                })
        except Exception:
            continue

    return pd.DataFrame(rows)

if st.button("🔄 Scan Live Pre-Breakout Setups"):
    st.cache_data.clear()

df_picks = scan_predictive_setups(NSE_UNIVERSE)

if df_picks.empty:
    st.warning("No high-probability pre-breakout coils detected right now. Market may be in broad distribution.")
else:
    df_picks = df_picks.sort_values(by=["Score", "Change_%"], ascending=False).reset_index(drop=True)

    breakout_now = df_picks[df_picks["Setup_Stage"] == "Early Breakout"]
    coil_watch = df_picks[df_picks["Setup_Stage"] == "Pre-Breakout Coil"]

    st.subheader(f"🚀 Early Breakout Triggers ({len(breakout_now)} Stocks — Entering Momentum Now)")
    if not breakout_now.empty:
        st.dataframe(breakout_now, use_container_width=True, hide_index=True)
    else:
        st.info("No stocks crossing 20D resistance right this minute—monitor the Pre-Breakout Coils below.")

    st.subheader(f"🧲 Pre-Breakout Accumulation Coils ({len(coil_watch)} Stocks — Buy Before Expansion)")
    if not coil_watch.empty:
        st.dataframe(coil_watch, use_container_width=True, hide_index=True)
