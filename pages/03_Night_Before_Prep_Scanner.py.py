from datetime import datetime, time as dt_time
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Advance Night-Before Institutional Prep Scanner", layout="wide"
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

st.title("🌙 Advance Night-Before Institutional Prep & Smart Money Coiling Watchlist")
st.markdown(
    "**Night-Before Prep Guide:** Scans daily candles for **tight price coiling** and "
    "**estimated volume-weighted flow** after market hours so you can build a focused "
    "watchlist for the next session."
)

# ---------------------------------------------------------
# 1. SCANNER CONTROLS & BEGINNER GUIDE
# ---------------------------------------------------------
col_c1, col_c2 = st.columns([3.5, 1.5])
with col_c1:
    session_note = (
        "🟢 Market is currently OPEN — treat as an intraday/next-session check."
        if is_market_open
        else "🌙 Pre-Market / After-Hours Mode — ideal for building tomorrow's watchlist."
    )
    st.caption(f"{session_note} • Last Check: **{now_ist.strftime('%d %b %Y, %I:%M %p IST')}**")
with col_c2:
    if st.button("🔄 Run Advance Smart Money Prep Scan", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Scanning Indian market for smart money accumulation & coiling...")
        st.rerun()

with st.expander("📘 Beginner Guide: How to Use Night-Before Prep Safely", expanded=False):
    st.markdown(
        "- **Tight Coiling (`Range_Ratio` ≤ 1.3x):** Price has been moving in a relatively narrow range compared to its recent 10-day average—often a sign of calm before a bigger move.\n"
        "- **Net Flow (Cr):** An **estimate** from price change and volume—not an official exchange institutional report.\n"
        "- **Advance Buy / SL / Targets:** Starter reference levels for learning and planning only. Always wait to see live price action after **9:15 AM IST**, start small, and use a stop-loss. Not financial advice."
    )

SECTOR_MAPPING = {
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "INDUSINDBK.NS",
        "PNB.NS",
        "CANBK.NS",
        "MUTHOOTFIN.NS",
    ],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["MARUTI.NS", "BAJAJFINSV.NS", "M&M.NS"],
    "Energy & Oil": [
        "RELIANCE.NS",
        "ONGC.NS",
        "NTPC.NS",
        "POWERGRID.NS",
        "COALINDIA.NS",
        "ATGL.NS",
    ],
    "Metals & Mining": ["TATASTEEL.NS", "ADANIENT.NS"],
    "Consumer & Retail": [
        "ITC.NS",
        "HINDUNILVR.NS",
        "TITAN.NS",
        "ASIANPAINT.NS",
        "ETERNAL.NS",
        "HONASA.NS",
    ],
    "Infrastructure & Industrials": [
        "LT.NS",
        "ADANIPORTS.NS",
        "GRASIM.NS",
        "SUPREMEIND.NS",
    ],
    "Healthcare & Pharma": ["SUNPHARMA.NS", "MAXHEALTH.NS", "DEEPAKFERT.NS"],
    "Financial Services": ["BAJFINANCE.NS", "LICI.NS", "ANGELONE.NS"],
}


def _extract_ticker_df(raw_df, ticker):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if ticker in raw_df.columns.get_level_values(0):
            return raw_df[ticker].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


# ---------------------------------------------------------
# 2. MARKET-WIDE PRE-BREAKOUT + SECTOR SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def run_advance_night_prep():
    watchlist_rows = []
    universe_map = {
        sym: sector for sector, symbols in SECTOR_MAPPING.items() for sym in symbols
    }
    all_symbols = sorted(list(universe_map.keys()))

    raw = yf.download(
        all_symbols, period="30d", interval="1d", group_by="ticker", progress=False
    )

    for symbol, sector in universe_map.items():
        try:
            df = _extract_ticker_df(raw, symbol).dropna(subset=["Close", "High", "Low"])
            if df is None or df.empty or len(df) < 20:
                continue

            df = df.copy()
            df["Range"] = df["High"] - df["Low"]
            avg_range = float(df["Range"].rolling(10).mean().iloc[-1])
            recent_range = float(df["Range"].iloc[-1])

            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            avg_vol = float(vol_series.rolling(15).mean().iloc[-1])
            recent_vol = float(vol_series.iloc[-1])

            close_price = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])

            if (
                prev_close == 0
                or avg_range <= 0
                or any(np.isnan(x) for x in [close_price, prev_close, avg_range, recent_range])
            ):
                continue

            change_pct = round(((close_price - prev_close) / prev_close) * 100, 2)
            vol_ratio = (recent_vol / avg_vol) if avg_vol > 0 and recent_vol > 0 else 1.0
            turnover_cr = round((close_price * recent_vol) / 10000000, 2)
            net_flow_cr = round(turnover_cr * (change_pct / 100) * vol_ratio, 2)

            range_ratio = round(recent_range / avg_range, 2)
            is_tight_coil = range_ratio <= 1.3
            is_volume_steady = vol_ratio >= 0.6

            if is_tight_coil and is_volume_steady:
                smart_signal = (
                    "🟢 Smart Inflow (Accumulation)"
                    if net_flow_cr > 0
                    else "🟡 Coiling / Neutral"
                )

                advance_buy = round(close_price * 0.995, 2)
                stop_loss = round(close_price * 0.978, 2)
                target_1 = round(close_price * 1.025, 2)
                target_2 = round(close_price * 1.050, 2)

                watchlist_rows.append({
                    "Symbol": symbol.replace(".NS", ""),
                    "Sector": sector,
                    "Close": round(close_price, 2),
                    "Change_%": change_pct,
                    "Net Flow (Cr)": net_flow_cr,
                    "Smart Signal": smart_signal,
                    "Advance_Buy": advance_buy,
                    "Stop_Loss": stop_loss,
                    "Target_1": target_1,
                    "Target_2": target_2,
                    "Range_Ratio": range_ratio,
                })
        except Exception:
            continue

    df_res = pd.DataFrame(watchlist_rows)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Net Flow (Cr)", ascending=False).reset_index(drop=True)
        df_res = df_res[[
            "Symbol",
            "Sector",
            "Close",
            "Change_%",
            "Net Flow (Cr)",
            "Smart Signal",
            "Advance_Buy",
            "Stop_Loss",
            "Target_1",
            "Target_2",
            "Range_Ratio",
        ]]
    return df_res


# ---------------------------------------------------------
# 3. RENDER ADVANCE PREP TABLE WITH SECTOR & SIGNAL FILTERS
# ---------------------------------------------------------
df_prep = run_advance_night_prep()

if df_prep is not None and not df_prep.empty:
    st.session_state["night_before_watchlist"] = df_prep["Symbol"].tolist()

if df_prep is None or df_prep.empty:
    st.warning("⚠️ No tight accumulation coils detected right now. Click **Run Advance Smart Money Prep Scan**.")
else:
    st.subheader("🎯 Smart Money Pre-Market Setups Connected with Sector Flows")

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        all_sectors = ["All Sectors"] + sorted(df_prep["Sector"].unique().tolist())
        selected_sector = st.selectbox("🔍 Filter Watchlist by Sector Connection:", all_sectors)
    with f_col2:
        signal_filter = st.selectbox(
            "📌 Filter by Signal Type:",
            ["All Setups", "🟢 Smart Inflow Only", "🟡 Coiling / Neutral Only"],
        )

    df_filtered = df_prep.copy()
    if selected_sector != "All Sectors":
        df_filtered = df_filtered[df_filtered["Sector"] == selected_sector]
    if signal_filter == "🟢 Smart Inflow Only":
        df_filtered = df_filtered[df_filtered["Net Flow (Cr)"] > 0]
    elif signal_filter == "🟡 Coiling / Neutral Only":
        df_filtered = df_filtered[df_filtered["Net Flow (Cr)"] <= 0]

    if df_filtered.empty:
        st.info("No matching stocks for this filter combination. Try switching back to **All Setups** or **All Sectors**.")
    else:
        st.dataframe(
            df_filtered.style.format({
                "Close": "₹{:,.2f}",
                "Change_%": "{:+.2f}%",
                "Net Flow (Cr)": "₹{:,.2f} Cr",
                "Advance_Buy": "₹{:,.2f}",
                "Stop_Loss": "₹{:,.2f}",
                "Target_1": "₹{:,.2f}",
                "Target_2": "₹{:,.2f}",
                "Range_Ratio": "{:.2f}x",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.subheader("📋 Detailed Sector-Connected Execution Blueprints (Top 5)")

        for _, row in df_filtered.head(5).iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

                with c1:
                    st.markdown(f"### **{row['Symbol']}**")
                    st.caption(f"📂 **Sector:** {row['Sector']}")
                    st.metric(
                        label="Last Close / Est. Flow",
                        value=f"₹{row['Close']:,.2f}",
                        delta=f"Net Flow: ₹{row['Net Flow (Cr)']:+.2f} Cr",
                    )

                with c2:
                    st.markdown("**Reference Entry & Risk**")
                    st.write(f"🔹 **Watch Buy Near:** ₹{row['Advance_Buy']:,.2f}")
                    st.write(f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']:,.2f}")

                with c3:
                    st.markdown("**Reference Targets**")
                    st.write(f"🎯 **Target 1 (+2.5%):** ₹{row['Target_1']:,.2f}")
                    st.write(f"🚀 **Target 2 (+5.0%):** ₹{row['Target_2']:,.2f}")

                with c4:
                    st.markdown("**Action Plan**")
                    st.success(f"✅ **{row['Smart Signal']}**")
                    if st.button(
                        f"📋 Copy Payload ({row['Symbol']})", key=f"adv_{row['Symbol']}"
                    ):
                        st.toast(
                            f"Copied {row['Symbol']} ({row['Sector']}) plan! Watch: "
                            f"₹{row['Advance_Buy']:,.2f} | SL: ₹{row['Stop_Loss']:,.2f} | T1: ₹{row['Target_1']:,.2f}"
                        )

            st.markdown("---")
