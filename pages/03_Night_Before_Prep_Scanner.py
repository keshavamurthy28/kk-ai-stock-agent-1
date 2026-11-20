from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advance Night-Before Institutional Prep Scanner", layout="wide"
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_morning_picks_to_ledger(picks: list[dict], module_label: str = "Night Before -> Morning Top 2") -> int:
    if not picks:
        return 0
    if callable(_ledger_record_picks):
        try:
            return int(_ledger_record_picks(module_label, picks))
        except Exception:
            pass

    ledger_dir = REPO_ROOT / "data_ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_file = ledger_dir / "pick_click_ledger.csv"
    cols = [
        "pick_id", "logged_at_ist", "session_date", "iso_week", "module",
        "symbol", "side", "entry_price", "stop_loss", "target_1", "target_2", "notes",
    ]
    ts_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    s_date = now_ist.strftime("%Y-%m-%d")
    i_week = f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}"
    bucket = now_ist.strftime("%Y-%m-%d %H:%M")

    existing = pd.read_csv(ledger_file) if ledger_file.exists() else pd.DataFrame(columns=cols)
    seen = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()
    new_rows = []
    for p in picks:
        sym = str(p["symbol"]).strip().upper()
        if not sym.endswith(".NS"):
            sym = f"{sym}.NS"
        side = str(p.get("side", "BUY")).upper()
        entry = float(p["entry"])
        pid = hashlib.sha1(f"{bucket}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)
        new_rows.append({
            "pick_id": pid, "logged_at_ist": ts_str, "session_date": s_date, "iso_week": i_week,
            "module": module_label, "symbol": sym, "side": side, "entry_price": round(entry, 2),
            "stop_loss": round(float(p["sl"]), 2), "target_1": round(float(p["t1"]), 2),
            "target_2": round(float(p["t2"]), 2), "notes": str(p.get("notes", "")),
        })
    if not new_rows:
        return 0
    out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True).drop_duplicates(
        subset=["pick_id"], keep="first"
    )
    out.to_csv(ledger_file, index=False)
    return len(new_rows)


st.title("🌙 Advance Night-Before Institutional Prep & Smart Money Coiling Watchlist")
st.markdown(
    "**Night-Before Prep Guide:** Scans daily candles for **trend-aligned price coiling** "
    "(above 20 & 50 EMA) and **estimated volume-weighted flow** after market hours."
)

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
        st.toast("Scanning Indian market for smart money accumulation & coiling...", icon="⚡")
        st.rerun()

with st.expander("📘 Advisor Guide: Using Night-Before Prep Without Over-Expectation", expanded=False):
    st.markdown(
        "- **No 100% Guarantee:** Coiling setups help you prepare a clean list, not predict guaranteed wins.\n"
        "- **Trend Filter:** In Strict mode, stocks must hold above their **20 EMA** and **50 EMA** with tight range coiling (`≤ 1.15x`).\n"
        "- **Profit Booking:** Treat **Target 1 (+1.8%)** as your primary profit-booking milestone after live market confirmation."
    )

SECTOR_MAPPING = {
    "Banking & Finance": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
        "INDUSINDBK.NS", "PNB.NS", "CANBK.NS", "MUTHOOTFIN.NS",
    ],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["MARUTI.NS", "BAJAJFINSV.NS", "M&M.NS"],
    "Energy & Oil": [
        "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS", "ATGL.NS",
    ],
    "Metals & Mining": ["TATASTEEL.NS", "ADANIENT.NS"],
    "Consumer & Retail": [
        "ITC.NS", "HINDUNILVR.NS", "TITAN.NS", "ASIANPAINT.NS", "ETERNAL.NS", "HONASA.NS",
    ],
    "Infrastructure & Industrials": [
        "LT.NS", "ADANIPORTS.NS", "GRASIM.NS", "SUPREMEIND.NS",
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


@st.cache_data(ttl=3600)
def run_advance_night_prep(strict_coil_mode=True):
    watchlist_rows = []
    universe_map = {
        sym: sector for sector, symbols in SECTOR_MAPPING.items() for sym in symbols
    }
    all_symbols = sorted(list(universe_map.keys()))

    raw = yf.download(
        all_symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True
    )

    max_coil = 1.15 if strict_coil_mode else 1.30
    min_vol_ratio = 0.85 if strict_coil_mode else 0.60

    for symbol, sector in universe_map.items():
        try:
            df = _extract_ticker_df(raw, symbol).dropna(subset=["Close", "High", "Low"])
            if df is None or df.empty or len(df) < 50:
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
            ema20 = float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50, adjust=False).mean().iloc[-1])

            if (
                prev_close == 0
                or avg_range <= 0
                or any(np.isnan(x) for x in [close_price, prev_close, avg_range, recent_range, ema20, ema50])
            ):
                continue

            change_pct = round(((close_price - prev_close) / prev_close) * 100, 2)
            vol_ratio = (recent_vol / avg_vol) if avg_vol > 0 and recent_vol > 0 else 1.0
            turnover_cr = round((close_price * recent_vol) / 10000000, 2)
            net_flow_cr = round(turnover_cr * (change_pct / 100) * vol_ratio, 2)

            range_ratio = round(recent_range / avg_range, 2)
            trend_ok = (close_price > ema20 > ema50) if strict_coil_mode else (close_price >= ema50 * 0.98)
            is_tight_coil = range_ratio <= max_coil
            is_volume_steady = vol_ratio >= min_vol_ratio
            flow_ok = (net_flow_cr > 0) if strict_coil_mode else True

            if is_tight_coil and is_volume_steady and flow_ok and trend_ok:
                smart_signal = (
                    "🟢 Smart Inflow + Trend Aligned"
                    if net_flow_cr > 0
                    else "🟡 Coiling / Neutral"
                )

                advance_buy = round(close_price * 0.994, 2)
                stop_loss = round(close_price * 0.982, 2)
                target_1 = round(close_price * 1.018, 2)
                target_2 = round(close_price * 1.035, 2)

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
            "Symbol", "Sector", "Close", "Change_%", "Net Flow (Cr)",
            "Smart Signal", "Advance_Buy", "Stop_Loss", "Target_1", "Target_2", "Range_Ratio",
        ]]
    return df_res


f_col1, f_col2, f_col3 = st.columns([1.4, 1.3, 1.3])
with f_col1:
    prep_mode = st.selectbox(
        "🛡️ Coil Quality Mode:",
        ["Strict (EMA Stack, Coil ≤ 1.15x & +Flow)", "Standard (Coil ≤ 1.30x)"],
        index=0,
    )

df_prep = run_advance_night_prep(strict_coil_mode=prep_mode.startswith("Strict"))

if df_prep is not None and not df_prep.empty:
    st.session_state["night_before_watchlist"] = df_prep["Symbol"].tolist()

if df_prep is None or df_prep.empty:
    st.session_state.setdefault("live_scanner_picks", {})["Night Before -> Morning Top 2"] = []
    st.warning("⚠️ No trend-aligned accumulation coils detected under current mode. Try **Standard** or click **Run Advance Smart Money Prep Scan**.")
else:
    with f_col2:
        all_sectors = ["All Sectors"] + sorted(df_prep["Sector"].unique().tolist())
        selected_sector = st.selectbox("🔍 Filter Watchlist by Sector Connection:", all_sectors)
    with f_col3:
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
        st.session_state.setdefault("live_scanner_picks", {})["Night Before -> Morning Top 2"] = []
    else:
        st.subheader("🌅 Top 2 Morning Picks (Highlighted Separately for Next Session)")
        top2_morning = df_filtered.head(2)
        m_cols = st.columns(len(top2_morning))
        morning_payload = []
        for idx_m, m_row in top2_morning.iterrows():
            with m_cols[idx_m]:
                st.metric(
                    label=f"Morning Pick #{idx_m + 1}: {m_row['Symbol']} ({m_row['Sector']})",
                    value=f"Watch ₹{m_row['Advance_Buy']:,.2f}",
                    delta=f"T1 ₹{m_row['Target_1']:,.2f} | SL ₹{m_row['Stop_Loss']:,.2f}",
                )
                st.caption(f"Flow: ₹{m_row['Net Flow (Cr)']:+.2f} Cr • Coil: {m_row['Range_Ratio']:.2f}x")
            morning_payload.append({
                "symbol": m_row["Symbol"],
                "side": "BUY",
                "entry": float(m_row["Advance_Buy"]),
                "sl": float(m_row["Stop_Loss"]),
                "t1": float(m_row["Target_1"]),
                "t2": float(m_row["Target_2"]),
                "notes": f"{m_row['Smart Signal']} | Coil {m_row['Range_Ratio']:.2f}x | Flow ₹{m_row['Net Flow (Cr)']:+.2f} Cr",
            })

        st.session_state.setdefault("live_scanner_picks", {})["Night Before -> Morning Top 2"] = morning_payload

        if st.button("📌 Log Top 2 Morning Picks to History Ledger", type="primary"):
            saved_m = _save_morning_picks_to_ledger(morning_payload, "Night Before -> Morning Top 2")
            st.success(f"Recorded {saved_m} Top 2 morning pick(s) to history ledger.")

        st.markdown("---")
        st.subheader("🎯 Smart Money Pre-Market Setups Connected with Sector Flows")
        st.dataframe(
            df_filtered.style.format({
                "Close": "₹{:,.2f}", "Change_%": "{:+.2f}%", "Net Flow (Cr)": "₹{:,.2f} Cr",
                "Advance_Buy": "₹{:,.2f}", "Stop_Loss": "₹{:,.2f}", "Target_1": "₹{:,.2f}",
                "Target_2": "₹{:,.2f}", "Range_Ratio": "{:.2f}x",
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
                    st.write(f"🎯 **Target 1 (+1.8%):** ₹{row['Target_1']:,.2f}")
                    st.write(f"🚀 **Target 2 (+3.5%):** ₹{row['Target_2']:,.2f}")
                with c4:
                    st.markdown("**Action Plan**")
                    st.success(f"✅ **{row['Smart Signal']}**")
                    if st.button(f"📋 Copy Payload ({row['Symbol']})", key=f"adv_{row['Symbol']}"):
                        st.toast(
                            f"Copied {row['Symbol']} ({row['Sector']}) plan! Watch: "
                            f"₹{row['Advance_Buy']:,.2f} | SL: ₹{row['Stop_Loss']:,.2f} | T1: ₹{row['Target_1']:,.2f}"
                        )
            st.markdown("---")
