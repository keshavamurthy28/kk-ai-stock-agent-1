from datetime import datetime, time as dt_time
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Same-Day Intraday & Long-Term Watchlist",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

st.title("⚡ Pure Same-Day Intraday Setups + Separate Long-Term Table")
st.markdown(
    "**Same-Day Intraday Focus:** Designed for **buy today & exit today (before 3:30 PM IST)** "
    "with disciplined profit-booking targets and hard stop-losses—paired with a **separate table** "
    "for longer-term stocks so you don't mix timeframes."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Beginner Rulebook: Same-Day Profit Booking & Risk Guardrails", expanded=True):
    st.markdown(
        "- **No 'Pakka' Guarantee:** Even strong setups can reverse in live trading—never treat any scanner signal as guaranteed profit.\n"
        "- **Same-Day Exit Rule:** For **Intraday (Buy Today / Sell Today)**, look to book profit around **Target 1** first, honor your **Stop-Loss**, and exit before **3:30 PM IST**.\n"
        "- **Separate Long-Term Table:** Use the **Long-Term Watchlist** table below only for multi-day/positional study—not for same-day scalping. Not financial advice."
    )

UNIVERSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "SBIN.NS",
    "ITC.NS",
    "BHARTIARTL.NS",
    "AXISBANK.NS",
    "LT.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "TATASTEEL.NS",
    "NTPC.NS",
    "ONGC.NS",
    "VEDL.NS",
    "HINDALCO.NS",
]

col_f1, col_r1 = st.columns([3.5, 1.5])
with col_f1:
    intraday_bias = st.selectbox(
        "🎯 Same-Day Intraday Direction:",
        ["Bullish Intraday (Buy Today / Sell Today)", "Bearish Intraday (Weakness / Breakdown Watch)"],
        index=0,
    )
with col_r1:
    if st.button("🔄 Refresh Intraday & Long-Term", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Refreshing live 5m intraday & daily long-term tables...", icon="⚡")
        st.rerun()


def _extract_ticker_df(raw_df, sym):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=60)
def fetch_intraday_and_longterm_tables(direction_choice):
    bullish_mode = "Bullish Intraday" in direction_choice
    intraday_rows = []
    longterm_rows = []

    try:
        raw_5m = yf.download(
            UNIVERSE,
            period="5d",
            interval="5m",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
        raw_1d = yf.download(
            UNIVERSE,
            period="3mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    for symbol in UNIVERSE:
        clean_sym = symbol.replace(".NS", "")

        # --- 1. PURE SAME-DAY INTRADAY (5m + VWAP) ---
        try:
            df_5m = _extract_ticker_df(raw_5m, symbol).dropna(subset=["Open", "High", "Low", "Close"])
            if df_5m is not None and len(df_5m) >= 20:
                df_5m = df_5m.copy()
                df_5m.index = pd.to_datetime(df_5m.index)
                if df_5m.index.tz is not None:
                    df_5m.index = df_5m.index.tz_convert("Asia/Kolkata").tz_localize(None)

                today_dates = df_5m.index.date
                latest_date = today_dates[-1]
                df_today = df_5m[df_5m.index.date == latest_date]
                prev_days = df_5m[df_5m.index.date < latest_date]

                ltp_5m = float(df_5m["Close"].iloc[-1])
                prev_close_ref = (
                    float(prev_days["Close"].iloc[-1])
                    if not prev_days.empty
                    else float(df_today["Open"].iloc[0])
                )

                vol_s = df_today["Volume"] if "Volume" in df_today and df_today["Volume"].sum() > 0 else None
                if vol_s is not None:
                    tp = (df_today["High"] + df_today["Low"] + df_today["Close"]) / 3.0
                    vwap_val = float((tp * vol_s).cumsum().iloc[-1] / vol_s.cumsum().iloc[-1])
                    avg_bar_vol = float(df_5m["Volume"].tail(40).mean())
                    last_bar_vol = float(df_5m["Volume"].iloc[-1])
                    vol_ratio = round(last_bar_vol / avg_bar_vol, 2) if avg_bar_vol > 0 else 1.0
                else:
                    vwap_val = float(df_today["Close"].mean())
                    vol_ratio = 1.0

                if prev_close_ref > 0 and not np.isnan(ltp_5m):
                    intra_chg = round(((ltp_5m - prev_close_ref) / prev_close_ref) * 100, 2)

                    if bullish_mode and intra_chg > 0.25 and ltp_5m >= vwap_val * 0.998:
                        sl_intra = round(min(vwap_val * 0.994, ltp_5m * 0.990), 2)
                        t1_intra = round(ltp_5m * 1.012, 2)  # Quick same-day profit booking (+1.2%)
                        t2_intra = round(ltp_5m * 1.022, 2)  # Stretch intraday target (+2.2%)
                        score_intra = round(intra_chg * max(vol_ratio, 0.8), 2)
                        intraday_rows.append({
                            "Stock": clean_sym,
                            "Plan": "BUY & EXIT TODAY",
                            "LTP": round(ltp_5m, 2),
                            "Chg_%": intra_chg,
                            "VWAP": round(vwap_val, 2),
                            "Vol_Pace": f"{vol_ratio:.2f}x",
                            "Stop_Loss": sl_intra,
                            "Target_1_Book": t1_intra,
                            "Target_2_Stretch": t2_intra,
                            "Exit_Rule": "Sell before 3:30 PM IST",
                            "Score": score_intra,
                        })
                    elif (not bullish_mode) and intra_chg < -0.25 and ltp_5m <= vwap_val * 1.002:
                        sl_intra = round(max(vwap_val * 1.006, ltp_5m * 1.010), 2)
                        t1_intra = round(ltp_5m * 0.988, 2)
                        t2_intra = round(ltp_5m * 0.978, 2)
                        score_intra = round(abs(intra_chg) * max(vol_ratio, 0.8), 2)
                        intraday_rows.append({
                            "Stock": clean_sym,
                            "Plan": "SHORT / EXIT TODAY",
                            "LTP": round(ltp_5m, 2),
                            "Chg_%": intra_chg,
                            "VWAP": round(vwap_val, 2),
                            "Vol_Pace": f"{vol_ratio:.2f}x",
                            "Stop_Loss": sl_intra,
                            "Target_1_Book": t1_intra,
                            "Target_2_Stretch": t2_intra,
                            "Exit_Rule": "Cover before 3:30 PM IST",
                            "Score": score_intra,
                        })
        except Exception:
            pass

        # --- 2. SEPARATE LONG-TERM TREND TABLE (1d EMA20 & EMA50) ---
        try:
            df_1d = _extract_ticker_df(raw_1d, symbol).dropna(subset=["Close"])
            if df_1d is not None and len(df_1d) >= 50:
                close_1d = float(df_1d["Close"].iloc[-1])
                prev_1d = float(df_1d["Close"].iloc[-2])
                ema20_1d = float(df_1d["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
                ema50_1d = float(df_1d["Close"].ewm(span=50, adjust=False).mean().iloc[-1])

                if prev_1d > 0 and not np.isnan(close_1d):
                    day_chg_1d = round(((close_1d - prev_1d) / prev_1d) * 100, 2)
                    trend_tag = (
                        "🟢 Uptrend (Above 20 & 50 EMA)"
                        if close_1d > ema20_1d > ema50_1d
                        else ("🟡 Pullback / Mixed Trend" if close_1d >= ema50_1d else "🔴 Below 50 EMA")
                    )
                    lt_score = round(
                        ((close_1d - ema50_1d) / max(ema50_1d, 0.01)) * 100 + day_chg_1d,
                        2,
                    )
                    longterm_rows.append({
                        "Stock": clean_sym,
                        "Horizon": "Multi-Week / Long-Term",
                        "Close": round(close_1d, 2),
                        "Day_%": day_chg_1d,
                        "EMA_20": round(ema20_1d, 2),
                        "EMA_50": round(ema50_1d, 2),
                        "Long_Term_SL_Zone": round(ema50_1d * 0.97, 2),
                        "Trend_Status": trend_tag,
                        "Score": lt_score,
                    })
        except Exception:
            pass

    df_intra = (
        pd.DataFrame(intraday_rows)
        .sort_values(by="Score", ascending=False)
        .drop(columns=["Score"])
        .reset_index(drop=True)
        if intraday_rows
        else pd.DataFrame()
    )
    df_lt = (
        pd.DataFrame(longterm_rows)
        .sort_values(by="Score", ascending=False)
        .drop(columns=["Score"])
        .reset_index(drop=True)
        if longterm_rows
        else pd.DataFrame()
    )
    return df_intra, df_lt


with st.spinner("Scanning live 5m intraday setups & daily long-term trends..."):
    df_intraday, df_longterm = fetch_intraday_and_longterm_tables(intraday_bias)

# ---------------------------------------------------------
# TABLE 1: PURE SAME-DAY INTRADAY WATCHLIST
# ---------------------------------------------------------
st.subheader("🎯 Table 1: Same-Day Intraday Setups (Buy & Exit Today)")
if df_intraday.empty:
    st.info(
        "ℹ️ No stocks matched the same-day intraday filter right now. Click **Refresh Intraday & Long-Term** "
        "or switch direction above."
    )
else:
    st.dataframe(
        df_intraday.style.format({
            "LTP": "₹{:,.2f}",
            "Chg_%": "{:+.2f}%",
            "VWAP": "₹{:,.2f}",
            "Stop_Loss": "₹{:,.2f}",
            "Target_1_Book": "₹{:,.2f}",
            "Target_2_Stretch": "₹{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Quick Same-Day Execution Cards (Top 2)")
    for idx, row in df_intraday.head(2).iterrows():
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.metric(f"#{idx+1} {row['Stock']}", f"₹{row['LTP']:,.2f}", f"{row['Chg_%']:+.2f}% | VWAP ₹{row['VWAP']:,.2f}")
        c2.metric("🛑 Same-Day Stop-Loss", f"₹{row['Stop_Loss']:,.2f}", "Strict Intraday Exit")
        c3.metric("🎯 Target 1 (Book Profit)", f"₹{row['Target_1_Book']:,.2f}", "Lock Gains First")
        c4.metric("🚀 Target 2 (Stretch)", f"₹{row['Target_2_Stretch']:,.2f}", row["Exit_Rule"])

st.markdown("---")

# ---------------------------------------------------------
# TABLE 2: SEPARATE LONG-TERM WATCHLIST
# ---------------------------------------------------------
st.subheader("🏦 Table 2: Separate Long-Term Watchlist (Multi-Week / Positional Study)")
st.caption("Kept separate from same-day intraday trades so longer-term trend stocks aren't confused with intraday entries.")
if df_longterm.empty:
    st.info("ℹ️ Long-term daily trend data is currently unavailable.")
else:
    st.dataframe(
        df_longterm.style.format({
            "Close": "₹{:,.2f}",
            "Day_%": "{:+.2f}%",
            "EMA_20": "₹{:,.2f}",
            "EMA_50": "₹{:,.2f}",
            "Long_Term_SL_Zone": "₹{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
