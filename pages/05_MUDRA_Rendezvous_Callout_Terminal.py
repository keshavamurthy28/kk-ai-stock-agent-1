from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MUDRA Rendezvous Callout Terminal", layout="wide")

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


def _save_mudra_picks_to_ledger(picks: list[dict], module_label: str = "MUDRA Top 5") -> int:
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


st.title("🏛️ MUDRA Rendezvous Callout Terminal")
st.markdown(
    "Identifies institutional momentum & early pullback setups with **anti-chase entry zones**, "
    "**advance profit-booking levels (T1 & T2)**, and **strict stop-losses** before **3:30 PM IST**."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

MUDRA_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "AXISBANK.NS", "LT.NS",
    "BAJFINANCE.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS",
    "HAL.NS", "BEL.NS", "COALINDIA.NS", "APOLLOHOSP.NS", "TDPOWERSYS.NS",
]

col_f1, col_f2, col_f3 = st.columns([2, 1.5, 1])
with col_f1:
    mode_filter = st.selectbox(
        "🎯 Setup Mode",
        [
            "All Ranked Setups (Active + Early Watch)",
            "Strict Momentum Callouts Only",
            "Advance Profit-Booking & Pullback Watch",
        ],
        index=0,
    )
with col_f2:
    min_score = st.slider("Minimum MUDRA Score", min_value=0, max_value=80, value=25, step=5)
with col_f3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh MUDRA Signals", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Refreshing live MUDRA market signals...", icon="⚡")
        st.rerun()


def _extract_ticker_df(raw_df, sym):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


def _compute_session_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    if "Volume" in df and float(df["Volume"].sum()) > 0:
        vol_by_day = df["Volume"].groupby(df.index.date).cumsum().replace(0, np.nan)
        pv_by_day = (typical * df["Volume"]).groupby(df.index.date).cumsum()
        return (pv_by_day / vol_by_day).bfill().ffill()
    return typical.rolling(20, min_periods=1).mean()


@st.cache_data(ttl=60)
def fetch_mudra_scans():
    try:
        raw = yf.download(
            MUDRA_UNIVERSE,
            period="10d",
            interval="15m",
            group_by="ticker",
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    results = []
    for sym in MUDRA_UNIVERSE:
        clean_sym = sym.replace(".NS", "")
        try:
            df = _extract_ticker_df(raw, sym).dropna(subset=["Open", "High", "Low", "Close"])
            if len(df) < 20:
                continue

            ltp = float(df["Close"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])
            if prev_c <= 0 or np.isnan(ltp):
                continue

            # Latest bar change and multi-bar (4-bar / 1-hour) swing change
            bar_chg_pct = round(((ltp - prev_c) / prev_c) * 100, 2)
            lookback_idx = -5 if len(df) >= 5 else 0
            ref_c = float(df["Close"].iloc[lookback_idx])
            swing_1h_pct = round(((ltp - ref_c) / ref_c) * 100, 2) if ref_c > 0 else bar_chg_pct

            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            avg_vol = float(vol_series.tail(20).mean())
            cur_vol = float(vol_series.iloc[-1])
            rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            ema20_series = df["Close"].ewm(span=20, adjust=False).mean()
            ema20 = float(ema20_series.iloc[-1])
            vwap_series = _compute_session_vwap(df)
            vwap = float(vwap_series.iloc[-1])

            recent_high = float(df["High"].tail(24).max())
            recent_low = float(df["Low"].tail(24).min())
            upside_room_pct = round(((recent_high - ltp) / ltp) * 100, 2) if ltp > 0 else 0.0

            # Anti-chase entry zone & advance profit targets (T1 & T2)
            above_ema = ltp >= ema20
            above_vwap = ltp >= vwap
            watch_buy = round(min(ltp * 0.995, ema20 * 1.002), 2) if above_ema else round(ltp * 0.993, 2)
            sl = round(min(watch_buy * 0.986, recent_low * 0.997), 2)
            risk = max(watch_buy - sl, watch_buy * 0.008)

            # Advance profit-booking targets anchored to risk multiple & nearby resistance
            t1_risk = watch_buy + (risk * 1.5)
            t1 = round(min(t1_risk, recent_high) if recent_high > watch_buy * 1.004 else t1_risk, 2)
            t2 = round(max(t1 * 1.008, watch_buy + (risk * 2.3)), 2)

            # Composite MUDRA Score (0 - 100)
            score = 0.0
            score += max(-15.0, min(30.0, swing_1h_pct * 15.0))
            score += max(0.0, min(25.0, (rvol - 0.6) * 20.0))
            if above_ema:
                score += 15.0
            if above_vwap:
                score += 15.0
            if upside_room_pct >= 0.6:
                score += 15.0
            score = round(max(0.0, min(100.0, score)), 1)

            strict_callout = (bar_chg_pct >= 0.35 or swing_1h_pct >= 0.60) and rvol >= 1.1 and above_ema
            if strict_callout and score >= 55:
                tier = "Strict Callout"
                status = "🟢 MUDRA Active Momentum Callout"
            elif score >= 35 or (above_vwap and upside_room_pct >= 0.5):
                tier = "Advance Watch"
                status = "🟡 Advance Profit-Booking / Pullback Setup"
            else:
                tier = "Early Watch"
                status = "⚪ Early Radar (Wait for Confirmation)"

            results.append({
                "Stock": clean_sym,
                "LTP": round(ltp, 2),
                "Watch_Buy": watch_buy,
                "15m_%": bar_chg_pct,
                "1h_%": swing_1h_pct,
                "RVOL": f"{rvol:.2f}x",
                "Stop_Loss": sl,
                "Target_1": t1,
                "Target_2": t2,
                "Room_%": upside_room_pct,
                "Score": score,
                "Tier": tier,
                "Status": status,
            })
        except Exception:
            continue

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_res


with st.spinner("Scanning MUDRA institutional & advance profit-booking setups..."):
    df_all = fetch_mudra_scans()

if df_all.empty:
    st.session_state.setdefault("live_scanner_picks", {})["MUDRA Top 5"] = []
    st.warning("⚠️ Market data is temporarily unavailable. Click **Refresh MUDRA Signals** to retry.")
else:
    filtered = df_all[df_all["Score"] >= min_score].copy()
    if mode_filter == "Strict Momentum Callouts Only":
        filtered = filtered[filtered["Tier"] == "Strict Callout"]
    elif mode_filter == "Advance Profit-Booking & Pullback Watch":
        filtered = filtered[filtered["Tier"].isin(["Advance Watch", "Strict Callout"])]

    # Always keep a fallback list so the desk never goes completely empty when filters are tight
    using_fallback = False
    if filtered.empty:
        filtered = df_all.head(8).copy()
        using_fallback = True

    top5_mudra = filtered.head(5)
    mudra_payload = [
        {
            "symbol": r["Stock"],
            "side": "BUY",
            "entry": float(r["Watch_Buy"]),
            "sl": float(r["Stop_Loss"]),
            "t1": float(r["Target_1"]),
            "t2": float(r["Target_2"]),
            "notes": f"MUDRA #{i+1} | Score {r['Score']} | RVOL {r['RVOL']} | Room +{r['Room_%']}%",
        }
        for i, (_, r) in enumerate(top5_mudra.iterrows())
    ]
    st.session_state.setdefault("live_scanner_picks", {})["MUDRA Top 5"] = mudra_payload

    if using_fallback:
        st.info(
            "ℹ️ No stocks met your strict filter/score threshold right now—showing the **Top 8 highest-scoring MUDRA stocks** below for advance watch & profit-booking planning."
        )

    if st.button("📌 Log Top 5 MUDRA Picks to History Ledger", type="primary"):
        saved = _save_mudra_picks_to_ledger(mudra_payload, "MUDRA Top 5")
        st.success(f"Recorded {saved} MUDRA pick(s) to history ledger.")

    st.subheader("🎯 Active & Advance MUDRA Signal Desk")
    display_cols = [
        "Stock", "LTP", "Watch_Buy", "15m_%", "1h_%", "RVOL",
        "Stop_Loss", "Target_1", "Target_2", "Room_%", "Score", "Status",
    ]
    st.dataframe(
        filtered[display_cols].style.format({
            "LTP": "₹{:,.2f}",
            "Watch_Buy": "₹{:,.2f}",
            "15m_%": "{:+.2f}%",
            "1h_%": "{:+.2f}%",
            "Stop_Loss": "₹{:,.2f}",
            "Target_1": "₹{:,.2f}",
            "Target_2": "₹{:,.2f}",
            "Room_%": "+{:.2f}%",
            "Score": "{:.1f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
