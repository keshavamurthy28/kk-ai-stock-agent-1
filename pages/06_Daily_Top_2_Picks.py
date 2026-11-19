from datetime import datetime, time as dt_time
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Master Pipeline Top 2 Picks | Adaptive Market Posture",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

st.title(
    "🔥 Master Pipeline Top 2 Picks: Adaptive Bullish Long / Bearish Short Terminal"
)
st.markdown(
    "**Beginner-Friendly Pipeline View:** Checks Nifty 50 posture and scans large-cap stocks "
    "for momentum setups—helping you focus on **at most 2 setups at a time** rather than "
    "chasing dozens of tickers."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Beginner Guide: How to Read Top 2 Setups & Book Profit Safely", expanded=False):
    st.markdown(
        "- **Market Posture:** **BULLISH** when Nifty is up (`>+0.4%`), **BEARISH** when Nifty is down (`<-0.4%`), and **NEUTRAL / MIXED** in between so red Nifty days aren't mislabeled bullish.\n"
        "- **When to Buy / Act:** Only during live market hours (**9:15 AM IST**) after checking price action and volume—never treat a scanner card as a guaranteed profit.\n"
        "- **When to Book Profit:** Consider booking partial or full profit around **Target 1** first rather than waiting blindly for **Target 2**, and honor your **Stop-Loss** if price moves against you. Not financial advice."
    )

# ---------------------------------------------------------
# 1. LIVE MARKET PULSE & PIPELINE SYNC
# ---------------------------------------------------------
col_r1, col_r2 = st.columns([4, 1])
with col_r2:
    if st.button("🔄 Force Refresh Pipeline Execution", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cleared cache and re-evaluated pipeline data stream!", icon="⚡")
        st.rerun()


def _extract_ticker_df(raw_df, sym):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=120)
def evaluate_market_posture_and_picks():
    universe = [
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
    all_symbols = ["^NSEI"] + universe

    try:
        raw = yf.download(
            all_symbols,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return "NEUTRAL", 0.0, pd.DataFrame()

    df_nifty = _extract_ticker_df(raw, "^NSEI").dropna(subset=["Close"])
    market_bias = "NEUTRAL"
    nifty_chg = 0.0

    if not df_nifty.empty and len(df_nifty) >= 2:
        nifty_close = float(df_nifty["Close"].iloc[-1])
        nifty_prev = float(df_nifty["Close"].iloc[-2])
        if nifty_prev > 0 and not np.isnan(nifty_close) and not np.isnan(nifty_prev):
            nifty_chg = round(((nifty_close - nifty_prev) / nifty_prev) * 100, 2)
            if nifty_chg > 0.4:
                market_bias = "BULLISH"
            elif nifty_chg < -0.4:
                market_bias = "BEARISH"
            else:
                market_bias = "NEUTRAL"

    scored_rows = []

    for symbol in universe:
        try:
            df = _extract_ticker_df(raw, symbol).dropna(subset=["Close"])
            if df is None or df.empty or len(df) < 2:
                continue

            ltp = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            if prev_close <= 0 or np.isnan(ltp) or np.isnan(prev_close):
                continue

            change_pct = round(((ltp - prev_close) / prev_close) * 100, 2)

            if market_bias == "BULLISH" and change_pct > 0.3:
                score = change_pct
                action = "BUY (LONG)"
                sl = round(ltp * 0.985, 2)
                t1 = round(ltp * 1.025, 2)
                t2 = round(ltp * 1.050, 2)
            elif market_bias == "BEARISH" and change_pct < -0.3:
                score = abs(change_pct)
                action = "SELL / SHORT WATCH"
                sl = round(ltp * 1.015, 2)
                t1 = round(ltp * 0.975, 2)
                t2 = round(ltp * 0.950, 2)
            elif market_bias == "NEUTRAL" and abs(change_pct) >= 0.8:
                score = abs(change_pct)
                if change_pct > 0:
                    action = "BUY (LONG WATCH)"
                    sl = round(ltp * 0.985, 2)
                    t1 = round(ltp * 1.025, 2)
                    t2 = round(ltp * 1.050, 2)
                else:
                    action = "WEAK / SHORT WATCH"
                    sl = round(ltp * 1.015, 2)
                    t1 = round(ltp * 0.975, 2)
                    t2 = round(ltp * 0.950, 2)
            else:
                continue

            scored_rows.append({
                "Symbol": symbol.replace(".NS", ""),
                "Action": action,
                "LTP": round(ltp, 2),
                "Change_%": change_pct,
                "Score": score,
                "Stop_Loss": sl,
                "Target_1": t1,
                "Target_2": t2,
            })
        except Exception:
            continue

    df_res = pd.DataFrame(scored_rows)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return market_bias, nifty_chg, df_res


market_bias, nifty_chg, df_picks = evaluate_market_posture_and_picks()

# Display Market Posture Banner based on Nifty Change
if market_bias == "BULLISH":
    st.success(
        f"🟢 **Market Posture: BULLISH (Nifty Change: {nifty_chg:+.2f}%)** — "
        "Highlighting top positive large-cap setups for watchlist review."
    )
elif market_bias == "BEARISH":
    st.error(
        f"🔴 **Market Posture: BEARISH / DISTRIBUTION (Nifty Change: {nifty_chg:+.2f}%)** — "
        "Highlighting top weak large-cap setups for watchlist / profit-booking review."
    )
else:
    st.warning(
        f"🟡 **Market Posture: NEUTRAL / MIXED (Nifty Change: {nifty_chg:+.2f}%)** — "
        "Nifty is flat/range-bound; showing notable movers (`±0.8%+`) with extra caution."
    )

st.markdown("---")

if df_picks is None or df_picks.empty:
    st.info(
        "ℹ️ No immediate setups matched the current threshold. Click **Force Refresh Pipeline Execution** "
        "or check back once live market movement picks up after **9:15 AM IST**."
    )
else:
    st.subheader(f"🎯 Top 2 Watchlist Setups ({market_bias} Mode)")

    for idx, row in df_picks.head(2).iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

            with c1:
                st.markdown(f"### **#{idx+1} {row['Symbol']}**")
                st.metric(
                    label="Last Price & Stance",
                    value=f"₹{row['LTP']:,.2f}",
                    delta=f"{row['Change_%']:+.2f}% | {row['Action']}",
                )

            with c2:
                st.markdown("**Reference Levels**")
                st.write(f"🔹 **Stance:** {row['Action']}")
                st.write(f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']:,.2f}")

            with c3:
                st.markdown("**Target Objectives**")
                st.write(f"🎯 **Target 1:** ₹{row['Target_1']:,.2f}")
                st.write(f"🚀 **Target 2:** ₹{row['Target_2']:,.2f}")

            with c4:
                st.markdown("**Beginner Check**")
                if "BUY" in row["Action"]:
                    st.success("✅ **POSITIVE MOMENTUM WATCH**")
                else:
                    st.warning("⚠️ **WEAKNESS / CAUTION WATCH**")

                if st.button(
                    f"📋 Copy Directive Payload ({row['Symbol']})",
                    key=f"directive_{row['Symbol']}",
                ):
                    st.toast(
                        f"Copied {row['Symbol']} ({row['Action']})! SL: ₹{row['Stop_Loss']:,.2f}"
                        f" | T1: ₹{row['Target_1']:,.2f}"
                    )

        st.markdown("---")
