from datetime import datetime, time as dt_time
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Live Intraday Super-Signal Terminal", layout="wide")

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

st.title("🎯 Live Intraday Super-Signal & Night-Before Trigger Engine")
st.markdown(
    "Cross-checks NSE breakouts against your **Night Before Prep Watchlist**. "
    "🟢 **Emerald Green** rows were lined up beforehand and have **triggered**; "
    "🔵 **Electric Blue** rows are **fresh breakouts**."
)

status_label = (
    "🟢 Live NSE Market Hours (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed — Treat as Watchlist & Prep Mode"
)
st.caption(f"{status_label} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Beginner Guide: How to Read Breakout Signals & Book Profit Safely", expanded=False):
    st.markdown(
        "- **🟢 Night-Before Triggered vs. 🔵 Fresh Breakout:** Night-before matched stocks had cleaner trend alignment beforehand; fresh breakouts are sudden momentum moves.\n"
        "- **When to Buy:** Only after market hours begin (**9:15 AM IST**) when price is holding above the breakout/open and volume (`RVOL`) is active—never chase blindly at the open.\n"
        "- **When to Book Profit:** Consider booking partial or full profit near **Target 1 (1.5R)** first rather than waiting blindly for **Target 2 (3.0R)**, and book early if momentum stalls.\n"
        "- **Strict Stop-Loss:** If price drops to **Stop-Loss**, exit and accept the small planned loss—never average down. Not financial advice."
    )

# Clean Stock-to-Sector Mapping Dictionary (no duplicate keys)
STOCK_SECTOR_MAP = {
    "BELRISE": "Automobiles",
    "DEEPAKFERT": "Chemicals",
    "ATHERENERG": "Automobiles",
    "ITC": "FMCG",
    "BHARTIARTL": "Telecommunications",
    "PNB": "Banking & Finance",
    "KALYANKJIL": "Consumer Durables",
    "SBIN": "Banking & Finance",
    "HDFCBANK": "Banking & Finance",
    "ICICIBANK": "Banking & Finance",
    "EICHERMOT": "Automobiles",
    "BSE": "Financial Services",
    "HINDALCO": "Metals & Mining",
    "TDPOWERSYS": "Capital Goods",
    "ABB": "General Industrials",
    "V2RETAIL": "Retailing",
    "KAYNES": "Hardware Technology",
    "RELIANCE": "Energy & Oil",
    "TCS": "Software & Services",
    "INFY": "Software & Services",
    "AXISBANK": "Banking & Finance",
    "BAJFINANCE": "Banking & Finance",
    "TATAMOTORS": "Automobiles",
    "SUNPHARMA": "Healthcare",
    "MARUTI": "Automobiles",
    "NTPC": "Energy & Oil",
    "POWERGRID": "Energy & Oil",
    "M&M": "Automobiles",
    "TATASTEEL": "Metals & Mining",
    "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace",
    "TRENT": "Retailing",
    "ZOMATO": "Retailing",
    "BANKBARODA": "Banking & Finance",
    "CANBK": "Banking & Finance",
    "JINDALPOLY": "Packaging",
    "FINCABLES": "Hardware Technology",
    "AMBER": "Consumer Durables",
    "MSTCLTD": "Commercial Services",
    "POWERINDIA": "Utilities",
    "HONASA": "FMCG",
    "GLAND": "Healthcare",
    "MANKIND": "Healthcare",
    "DIVISLAB": "Healthcare",
    "WOCKPHARMA": "Healthcare",
    "INDUSTOWER": "Telecom Services",
    "HINDCOPPER": "Metals & Mining",
    "DATAPATTNS": "Defense & Aerospace",
    "DIXON": "Consumer Durables",
    "POLYCAB": "Hardware Technology",
    "KEI": "Hardware Technology",
    "PFC": "Financial Services",
    "RECLTD": "Financial Services",
    "IRFC": "Financial Services",
    "RVNL": "Transportation",
    "MAZDOCK": "Defense & Aerospace",
    "COCHINSHIP": "Defense & Aerospace",
    "GRSE": "Defense & Aerospace",
    "BDL": "Defense & Aerospace",
    "SUZLON": "Utilities",
    "IREDA": "Utilities",
    "HUDCO": "Realty",
    "NBCC": "Cement & Construction",
    "SJVN": "Utilities",
    "NHPC": "Utilities",
    "BHEL": "Capital Goods",
    "SAIL": "Metals & Mining",
    "NMDC": "Metals & Mining",
    "VEDL": "Metals & Mining",
    "JSWSTEEL": "Metals & Mining",
    "JINDALSTEL": "Metals & Mining",
    "ADANIENT": "Diversified",
    "ADANIPORTS": "Transportation",
    "ADANIPOWER": "Utilities",
    "TATAPOWER": "Utilities",
    "JSWENERGY": "Utilities",
    "CGPOWER": "Capital Goods",
    "SIEMENS": "General Industrials",
    "CUMMINSIND": "General Industrials",
    "THERMAX": "Capital Goods",
    "TRITURBINE": "Capital Goods",
    "KPITTECH": "Software & Services",
    "PERSISTENT": "Software & Services",
    "COFORGE": "Software & Services",
    "LTIM": "Software & Services",
    "TECHM": "Software & Services",
    "WIPRO": "Software & Services",
    "HCLTECH": "Software & Services",
    "NAUKRI": "Software & Services",
    "PAYTM": "Financial Services",
    "POLICYBZR": "Financial Services",
    "ANGELONE": "Financial Services",
    "CDSL": "Financial Services",
    "MCX": "Financial Services",
    "IEX": "Financial Services",
    "TITAN": "Consumer Durables",
    "DMART": "Retailing",
    "VBL": "Food Beverages",
    "GODREJCP": "FMCG",
    "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG",
    "DABUR": "FMCG",
    "MARICO": "FMCG",
    "COLPAL": "FMCG",
    "PIDILITIND": "Chemicals",
    "ASIANPAINT": "Consumer Durables",
    "BERGEPAINT": "Chemicals",
    "ULTRACEMCO": "Cement & Construction",
    "AMBUJACEM": "Cement & Construction",
    "SHREECEM": "Cement & Construction",
    "DLF": "Realty",
    "GODREJPROP": "Realty",
    "OBEROIRLTY": "Realty",
    "PRESTIGE": "Realty",
    "LODHA": "Realty",
    "INDIGO": "Transportation",
    "IRCTC": "Transportation",
    "CONCOR": "Transportation",
    "APOLLOHOSP": "Healthcare",
    "MAXHEALTH": "Healthcare",
}

NSE_ACTIVE_UNIVERSE = list(STOCK_SECTOR_MAP.keys())


def get_rvol_scale():
    current_ist = datetime.now(ist)
    m_open = current_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    m_close = current_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if current_ist < m_open or current_ist >= m_close or current_ist.weekday() >= 5:
        return 1.0
    mins = max((current_ist - m_open).total_seconds() / 60.0, 5.0)
    return min(375.0 / mins, 25.0)


def _extract_ticker_df(raw_df, sym, total_tickers):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if total_tickers > 1 and isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=90)
def scan_matched_super_signals(tickers):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(
            symbols,
            period="3mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame(), []

    scale = get_rvol_scale()
    auto_night_before = []
    signals = []

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = _extract_ticker_df(raw, sym, len(tickers)).dropna(subset=["Close", "Open", "High", "Low"])
            if len(df) < 25:
                continue

            ltp = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1])
            high_p = float(df["High"].iloc[-1])
            low_p = float(df["Low"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])

            if prev_c <= 0 or any(np.isnan(x) for x in [ltp, open_p, high_p, low_p, prev_c]):
                continue

            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            vol_pace = float(vol_series.iloc[-1]) * scale if pd.notna(vol_series.iloc[-1]) else 0.0
            vol_avg = float(vol_series.iloc[-21:-1].mean()) if len(vol_series) >= 22 else 0.0
            rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 and vol_pace > 0 else 1.0

            ema20 = float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50, adjust=False).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())

            dist_prev = ((res_20d - prev_c) / prev_c) * 100
            if prev_c > ema20 > ema50 and -2.5 <= dist_prev <= 4.0:
                auto_night_before.append(t)

            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            if pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema20:
                broke_20d = ltp >= res_20d
                score = (
                    (pct_chg * 6)
                    + (min(rvol, 20.0) * 6)
                    + (20 if broke_20d else 0)
                    + (10 if near_day_high else 0)
                )

                sl = round(max(low_p, prev_c * 0.99) * 0.995, 2)
                risk = max(ltp - sl, ltp * 0.012)
                t1 = round(ltp + (risk * 1.5), 2)
                t2 = round(ltp + (risk * 3.0), 2)

                signals.append({
                    "Stock": t,
                    "Sector": STOCK_SECTOR_MAP.get(t, "General"),
                    "Action": "BUY",
                    "LTP": round(ltp, 2),
                    "Change_%": pct_chg,
                    "Volume_Surge": f"{rvol:.2f}x",
                    "Stop_Loss": sl,
                    "Target_1": t1,
                    "Target_2": t2,
                    "Catalyst_Reason": (
                        f"20D Breakout + {rvol}x RVOL"
                        if broke_20d
                        else f"Intraday Drive (+{pct_chg}%) + {rvol}x RVOL"
                    ),
                    "Score": score,
                })
        except Exception:
            continue

    if not signals:
        return pd.DataFrame(), auto_night_before
    return pd.DataFrame(signals), auto_night_before


if st.button("🔄 Force Refresh Live Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

df_live, computed_nb = scan_matched_super_signals(NSE_ACTIVE_UNIVERSE)

session_nb = st.session_state.get("night_before_watchlist", [])
nb_watchlist = set(session_nb) | set(computed_nb)

if df_live.empty:
    st.warning("No stocks currently meet the breakout + RVOL threshold. Try clicking **Force Refresh Live Data**.")
else:
    df_live["Night_Before_Match"] = df_live["Stock"].isin(nb_watchlist)
    df_live["Final_Score"] = df_live["Score"] + np.where(
        df_live["Night_Before_Match"], 40, 0
    )
    df_live["Signal_Source"] = np.where(
        df_live["Night_Before_Match"],
        "🟢 NIGHT-BEFORE TRIGGERED",
        "🔵 FRESH INTRADAY BREAKOUT",
    )

    df_live = df_live.sort_values(by="Final_Score", ascending=False).reset_index(drop=True)
    df_live.insert(0, "Rank", df_live.index + 1)

    st.session_state["super_signal_confirmed"] = df_live[
        df_live["Night_Before_Match"]
    ]["Stock"].tolist()

    source_filter = st.selectbox(
        "Filter Signals by Type:",
        ["All Signals", "🟢 Night-Before Triggered Only", "🔵 Fresh Breakouts Only"],
        index=0,
    )

    if source_filter == "🟢 Night-Before Triggered Only":
        df_shown = df_live[df_live["Night_Before_Match"]].reset_index(drop=True)
    elif source_filter == "🔵 Fresh Breakouts Only":
        df_shown = df_live[~df_live["Night_Before_Match"]].reset_index(drop=True)
    else:
        df_shown = df_live.copy()

    def highlight_signal_source(row):
        if "NIGHT-BEFORE TRIGGERED" in str(row["Signal_Source"]):
            return [
                "background-color: rgba(0, 230, 118, 0.22); color: #E8F5E9; font-weight: 600"
            ] * len(row)
        return ["background-color: rgba(41, 182, 246, 0.14); color: #E1F5FE"] * len(row)

    display_cols = [
        "Rank",
        "Stock",
        "Sector",
        "Signal_Source",
        "Action",
        "LTP",
        "Change_%",
        "Volume_Surge",
        "Stop_Loss",
        "Target_1",
        "Target_2",
        "Catalyst_Reason",
    ]
    styled_df = (
        df_shown[display_cols]
        .style.apply(highlight_signal_source, axis=1)
        .format({
            "LTP": "₹{:.2f}",
            "Change_%": "+{:.2f}%",
            "Stop_Loss": "₹{:.2f}",
            "Target_1": "₹{:.2f}",
            "Target_2": "₹{:.2f}",
        })
    )

    st.markdown(
        "🟢 **Emerald Green:** Night Before Prep Stock That Triggered  | "
        " 🔵 **Electric Blue:** Fresh Breakout"
    )
    st.subheader("🏆 Execution Ranking Table")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🎯 Top Confirmed Execution Cards")
    for _, row in df_shown.head(3).iterrows():
        st.markdown(
            f"### Rank #{row['Rank']}: {row['Stock']} ({row['Sector']}) — "
            f"+{row['Change_%']}% — {row['Signal_Source']}"
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reference Price", f"BUY @ ₹{row['LTP']:,.2f}")
        c2.metric("Strict Stop-Loss", f"₹{row['Stop_Loss']:,.2f}")
        c3.metric("Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}")
        c4.metric("Target 2 (3.0R)", f"₹{row['Target_2']:,.2f}")
        st.info(f"💡 **Catalyst:** {row['Catalyst_Reason']}")
