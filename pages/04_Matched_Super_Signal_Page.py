from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
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

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_super_picks_to_ledger(
    picks: list[dict], module_label: str = "Matched Super Signal (Top 2)"
) -> int:
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
        "pick_id",
        "logged_at_ist",
        "session_date",
        "iso_week",
        "module",
        "symbol",
        "side",
        "entry_price",
        "stop_loss",
        "target_1",
        "target_2",
        "notes",
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
        pid = hashlib.sha1(
            f"{bucket}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")
        ).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)
        new_rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_str,
            "session_date": s_date,
            "iso_week": i_week,
            "module": module_label,
            "symbol": sym,
            "side": side,
            "entry_price": round(entry, 2),
            "stop_loss": round(float(p["sl"]), 2),
            "target_1": round(float(p["t1"]), 2),
            "target_2": round(float(p["t2"]), 2),
            "notes": str(p.get("notes", "")),
        })
    if not new_rows:
        return 0
    out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True).drop_duplicates(
        subset=["pick_id"], keep="first"
    )
    out.to_csv(ledger_file, index=False)
    return len(new_rows)


st.title("🎯 Live Intraday Super-Signal & Night-Before Trigger Engine")
st.markdown(
    "Filters NSE momentum setups for **trend alignment**, **anti-chase entry zones**, "
    "and **realistic profit-booking targets (T1 & T2)**—plus cross-checks your **Night Before Prep Watchlist**."
)

status_label = (
    "🟢 Live NSE Market Hours (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed — Treat as Watchlist & Prep Mode"
)
st.caption(f"{status_label} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Advisor Profit-Booking & Risk Discipline", expanded=False):
    st.markdown(
        "- **No 100% Guarantee:** Even high-score breakouts can fail; treat every signal as a probability setup with a defined exit.\n"
        "- **Avoid Chasing:** `Watch_Buy` sits slightly below/near LTP (`~0.8%` pullback buffer) and filters out stocks already extended > 4.5%.\n"
        "- **Profit Booking Plan:** Book **50%–70% at Target 1 (1.5R)** to lock gains, move SL to breakeven/cost once 1.0R is cleared, and trail the rest toward **Target 2 (2.2R)**."
    )

STOCK_SECTOR_MAP = {
    "BELRISE": "Automobiles", "DEEPAKFERT": "Chemicals", "ATHERENERG": "Automobiles",
    "ITC": "FMCG", "BHARTIARTL": "Telecommunications", "PNB": "Banking & Finance",
    "KALYANKJIL": "Consumer Durables", "SBIN": "Banking & Finance", "HDFCBANK": "Banking & Finance",
    "ICICIBANK": "Banking & Finance", "EICHERMOT": "Automobiles", "BSE": "Financial Services",
    "HINDALCO": "Metals & Mining", "TDPOWERSYS": "Capital Goods", "ABB": "General Industrials",
    "V2RETAIL": "Retailing", "KAYNES": "Hardware Technology", "RELIANCE": "Energy & Oil",
    "TCS": "Software & Services", "INFY": "Software & Services", "AXISBANK": "Banking & Finance",
    "BAJFINANCE": "Banking & Finance", "TATAMOTORS": "Automobiles", "SUNPHARMA": "Healthcare",
    "MARUTI": "Automobiles", "NTPC": "Energy & Oil", "POWERGRID": "Energy & Oil",
    "M&M": "Automobiles", "TATASTEEL": "Metals & Mining", "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace", "TRENT": "Retailing", "ZOMATO": "Retailing",
    "BANKBARODA": "Banking & Finance", "CANBK": "Banking & Finance", "JINDALPOLY": "Packaging",
    "FINCABLES": "Hardware Technology", "AMBER": "Consumer Durables", "MSTCLTD": "Commercial Services",
    "POWERINDIA": "Utilities", "HONASA": "FMCG", "GLAND": "Healthcare", "MANKIND": "Healthcare",
    "DIVISLAB": "Healthcare", "WOCKPHARMA": "Healthcare", "INDUSTOWER": "Telecom Services",
    "HINDCOPPER": "Metals & Mining", "DATAPATTNS": "Defense & Aerospace", "DIXON": "Consumer Durables",
    "POLYCAB": "Hardware Technology", "KEI": "Hardware Technology", "PFC": "Financial Services",
    "RECLTD": "Financial Services", "IRFC": "Financial Services", "RVNL": "Transportation",
    "MAZDOCK": "Defense & Aerospace", "COCHINSHIP": "Defense & Aerospace", "GRSE": "Defense & Aerospace",
    "BDL": "Defense & Aerospace", "SUZLON": "Utilities", "IREDA": "Utilities", "HUDCO": "Realty",
    "NBCC": "Cement & Construction", "SJVN": "Utilities", "NHPC": "Utilities", "BHEL": "Capital Goods",
    "SAIL": "Metals & Mining", "NMDC": "Metals & Mining", "VEDL": "Metals & Mining",
    "JSWSTEEL": "Metals & Mining", "JINDALSTEL": "Metals & Mining", "ADANIENT": "Diversified",
    "ADANIPORTS": "Transportation", "ADANIPOWER": "Utilities", "TATAPOWER": "Utilities",
    "JSWENERGY": "Utilities", "CGPOWER": "Capital Goods", "SIEMENS": "General Industrials",
    "CUMMINSIND": "General Industrials", "THERMAX": "Capital Goods", "TRITURBINE": "Capital Goods",
    "KPITTECH": "Software & Services", "PERSISTENT": "Software & Services", "COFORGE": "Software & Services",
    "LTIM": "Software & Services", "TECHM": "Software & Services", "WIPRO": "Software & Services",
    "HCLTECH": "Software & Services", "NAUKRI": "Software & Services", "PAYTM": "Financial Services",
    "POLICYBZR": "Financial Services", "ANGELONE": "Financial Services", "CDSL": "Financial Services",
    "MCX": "Financial Services", "IEX": "Financial Services", "TITAN": "Consumer Durables",
    "DMART": "Retailing", "VBL": "Food Beverages", "GODREJCP": "FMCG", "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG", "COLPAL": "FMCG",
    "PIDILITIND": "Chemicals", "ASIANPAINT": "Consumer Durables", "BERGEPAINT": "Chemicals",
    "ULTRACEMCO": "Cement & Construction", "AMBUJACEM": "Cement & Construction",
    "SHREECEM": "Cement & Construction", "DLF": "Realty", "GODREJPROP": "Realty",
    "OBEROIRLTY": "Realty", "PRESTIGE": "Realty", "LODHA": "Realty", "INDIGO": "Transportation",
    "IRCTC": "Transportation", "CONCOR": "Transportation", "APOLLOHOSP": "Healthcare",
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
def scan_matched_super_signals(tickers, strict_mode=True):
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
            if len(df) < 50:
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

            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.38
            trend_aligned = (ema20 >= ema50 * 0.995) if strict_mode else True
            min_pct = 1.2 if strict_mode else 0.8
            max_pct_cap = 4.5 if strict_mode else 12.0
            min_rvol = 1.4 if strict_mode else 1.1

            if (
                min_pct <= pct_chg <= max_pct_cap
                and rvol >= min_rvol
                and ltp > open_p
                and ltp > ema20
                and trend_aligned
                and (not strict_mode or near_day_high)
            ):
                broke_20d = ltp >= res_20d
                score = (
                    (pct_chg * 6)
                    + (min(rvol, 20.0) * 6)
                    + (20 if broke_20d else 0)
                    + (12 if trend_aligned else 0)
                    + (10 if near_day_high else 0)
                )

                # Pullback-aware Watch Buy (avoids chasing top-of-candle spikes)
                watch_buy = round(ltp * 0.992, 2)
                sl = round(max(watch_buy * 0.978, min(watch_buy * 0.988, ema20 * 0.994)), 2)
                risk = max(watch_buy - sl, watch_buy * 0.01)
                t1 = round(watch_buy + (risk * 1.5), 2)
                t2 = round(watch_buy + (risk * 2.2), 2)

                signals.append({
                    "Stock": t,
                    "Sector": STOCK_SECTOR_MAP.get(t, "General"),
                    "Action": "BUY",
                    "LTP": round(ltp, 2),
                    "Watch_Buy": watch_buy,
                    "Change_%": pct_chg,
                    "Volume_Surge": f"{rvol:.2f}x",
                    "Stop_Loss": sl,
                    "Target_1": t1,
                    "Target_2": t2,
                    "Catalyst_Reason": (
                        f"20D Breakout + EMA20/50 Stack + {rvol}x RVOL"
                        if broke_20d
                        else f"Controlled Momentum (+{pct_chg}%) + {rvol}x RVOL"
                    ),
                    "Score": score,
                })
        except Exception:
            continue

    if not signals:
        return pd.DataFrame(), auto_night_before
    return pd.DataFrame(signals), auto_night_before


ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.9, 1.8, 1.2, 1.3])
with ctrl1:
    filter_quality = st.selectbox(
        "🛡️ Signal Quality Mode:",
        ["Strict (EMA Stack, RVOL ≥ 1.4x, ≤4.5% Move)", "Standard Breakout"],
        index=0,
    )
with ctrl2:
    source_filter = st.selectbox(
        "Filter Signals by Type:",
        ["All Signals", "🟢 Night-Before Triggered Only", "🔵 Fresh Breakouts Only"],
        index=0,
    )
with ctrl3:
    st.write("")
    auto_log_top2 = st.toggle("Auto-Log Top 2", value=False)
with ctrl4:
    st.write("")
    if st.button("🔄 Force Refresh Live Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

df_live, computed_nb = scan_matched_super_signals(
    NSE_ACTIVE_UNIVERSE,
    strict_mode=filter_quality.startswith("Strict"),
)

session_nb = st.session_state.get("night_before_watchlist", [])
nb_watchlist = set(session_nb) | set(computed_nb)

if df_live.empty:
    st.session_state.setdefault("live_scanner_picks", {})["Matched Super Signal (Top 2)"] = []
    st.warning("No stocks currently meet the refined trend + anti-chase threshold. Try **Standard Breakout** or click **Force Refresh Live Data**.")
else:
    df_live["Night_Before_Match"] = df_live["Stock"].isin(nb_watchlist)
    df_live["Final_Score"] = df_live["Score"] + np.where(df_live["Night_Before_Match"], 40, 0)
    df_live["Signal_Source"] = np.where(
        df_live["Night_Before_Match"],
        "🟢 NIGHT-BEFORE TRIGGERED",
        "🔵 FRESH INTRADAY BREAKOUT",
    )

    df_live = df_live.sort_values(by="Final_Score", ascending=False).reset_index(drop=True)
    df_live.insert(0, "Rank", df_live.index + 1)
    st.session_state["super_signal_confirmed"] = df_live[df_live["Night_Before_Match"]]["Stock"].tolist()

    if source_filter == "🟢 Night-Before Triggered Only":
        df_shown = df_live[df_live["Night_Before_Match"]].reset_index(drop=True)
    elif source_filter == "🔵 Fresh Breakouts Only":
        df_shown = df_live[~df_live["Night_Before_Match"]].reset_index(drop=True)
    else:
        df_shown = df_live.copy()

    st.subheader("⭐ Top 2 Highlighted Super Signals")
    top2_df = df_shown.head(2)
    if top2_df.empty:
        st.info("No signals in this filter slice.")
        st.session_state.setdefault("live_scanner_picks", {})["Matched Super Signal (Top 2)"] = []
    else:
        st.session_state["matched_super_top2"] = top2_df["Stock"].tolist()
        t2_cols = st.columns(len(top2_df))
        for idx_t2, r2 in top2_df.iterrows():
            with t2_cols[idx_t2]:
                st.metric(
                    label=f"#{r2['Rank']} {r2['Stock']} ({r2['Sector']})",
                    value=f"Watch ₹{r2['Watch_Buy']:,.2f}",
                    delta=f"LTP ₹{r2['LTP']:,.2f} (+{r2['Change_%']:.2f}%) | T1 ₹{r2['Target_1']:,.2f}",
                )
                st.caption(f"{r2['Signal_Source']} • SL ₹{r2['Stop_Loss']:,.2f} • Vol {r2['Volume_Surge']}")

        top2_payload = [
            {
                "symbol": r["Stock"],
                "side": "BUY",
                "entry": float(r["Watch_Buy"]),
                "sl": float(r["Stop_Loss"]),
                "t1": float(r["Target_1"]),
                "t2": float(r["Target_2"]),
                "notes": f"{r['Signal_Source']} | {r['Catalyst_Reason']}",
            }
            for _, r in top2_df.iterrows()
        ]
        st.session_state.setdefault("live_scanner_picks", {})["Matched Super Signal (Top 2)"] = top2_payload

        if auto_log_top2:
            auto_saved = _save_super_picks_to_ledger(top2_payload, "Matched Super Signal (Top 2)")
            if auto_saved > 0:
                st.toast(f"Auto-logged {auto_saved} Top 2 Super Signal(s) to ledger!", icon="📌")

        if st.button("📌 Log Top 2 Super Signals to History Ledger", type="primary"):
            saved_n = _save_super_picks_to_ledger(top2_payload, "Matched Super Signal (Top 2)")
            st.success(f"Recorded {saved_n} Top 2 signal(s) to history ledger.")

    def highlight_signal_source(row):
        if "NIGHT-BEFORE TRIGGERED" in str(row["Signal_Source"]):
            return ["background-color: rgba(0, 230, 118, 0.22); color: #E8F5E9; font-weight: 600"] * len(row)
        return ["background-color: rgba(41, 182, 246, 0.14); color: #E1F5FE"] * len(row)

    display_cols = [
        "Rank", "Stock", "Sector", "Signal_Source", "Action", "LTP",
        "Watch_Buy", "Change_%", "Volume_Surge", "Stop_Loss", "Target_1",
        "Target_2", "Catalyst_Reason",
    ]
    styled_df = (
        df_shown[display_cols]
        .style.apply(highlight_signal_source, axis=1)
        .format({
            "LTP": "₹{:.2f}", "Watch_Buy": "₹{:.2f}", "Change_%": "+{:.2f}%",
            "Stop_Loss": "₹{:.2f}", "Target_1": "₹{:.2f}", "Target_2": "₹{:.2f}",
        })
    )

    st.markdown("🟢 **Emerald Green:** Night Before Prep Stock That Triggered  |  🔵 **Electric Blue:** Fresh Breakout")
    st.subheader("🏆 Execution Ranking Table")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🎯 Top Confirmed Execution Cards")
    for _, row in df_shown.head(3).iterrows():
        st.markdown(
            f"### Rank #{row['Rank']}: {row['Stock']} ({row['Sector']}) — "
            f"+{row['Change_%']}% — {row['Signal_Source']}"
        )
        c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 1.5, 1.2])
        c1.metric("Watch Buy", f"₹{row['Watch_Buy']:,.2f}", f"LTP ₹{row['LTP']:,.2f}")
        c2.metric("Strict Stop-Loss", f"₹{row['Stop_Loss']:,.2f}")
        c3.metric("Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}")
        c4.metric("Target 2 (2.2R)", f"₹{row['Target_2']:,.2f}")
        with c5:
            st.write("")
            if st.button(f"📋 Copy {row['Stock']}", key=f"copy_ms_{row['Stock']}", use_container_width=True):
                st.toast(
                    f"{row['Stock']} ({row['Sector']}) | Buy: ₹{row['Watch_Buy']:,.2f} | "
                    f"SL: ₹{row['Stop_Loss']:,.2f} | T1: ₹{row['Target_1']:,.2f} | T2: ₹{row['Target_2']:,.2f}"
                )
        st.info(f"💡 **Catalyst:** {row['Catalyst_Reason']}")
