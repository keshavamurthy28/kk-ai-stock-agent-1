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
    "Scans institutional momentum leaders for **VWAP alignment**, **anti-chase entry zones**, "
    "and strict **profit-booking rules (T1 & T2)** before **3:30 PM IST**."
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

col_m1, col_m2 = st.columns([3, 1])
with col_m2:
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


@st.cache_data(ttl=60)
def fetch_mudra_scans():
    try:
        raw = yf.download(
            MUDRA_UNIVERSE, period="10d", interval="15m", group_by="ticker", progress=False, auto_adjust=True
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
            open_p = float(df["Open"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])

            if prev_c <= 0 or np.isnan(ltp):
                continue

            chg_pct = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            avg_vol = float(vol_series.tail(20).mean())
            cur_vol = float(vol_series.iloc[-1])
            rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            ema20 = float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
            
            # Require positive momentum, volume expansion, and price holding above EMA20
            if chg_pct >= 0.5 and rvol >= 1.2 and ltp >= ema20:
                watch_buy = round(ltp * 0.993, 2)
                sl = round(max(watch_buy * 0.985, ema20 * 0.995), 2)
                risk = max(watch_buy - sl, watch_buy * 0.008)
                t1 = round(watch_buy + (risk * 1.5), 2)
                t2 = round(watch_buy + (risk * 2.2), 2)
                score = round((chg_pct * 10) + (rvol * 15), 2)

                results.append({
                    "Stock": clean_sym,
                    "LTP": round(ltp, 2),
                    "Watch_Buy": watch_buy,
                    "Change_%": chg_pct,
                    "RVOL": f"{rvol:.2f}x",
                    "Stop_Loss": sl,
                    "Target_1": t1,
                    "Target_2": t2,
                    "Score": score,
                    "Status": "🟢 MUDRA Institutional Momentum Callout",
                })
        except Exception:
            continue

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_res


with st.spinner("Scanning MUDRA institutional setups..."):
    df_mudra = fetch_mudra_scans()

if df_mudra.empty:
    st.session_state.setdefault("live_scanner_picks", {})["MUDRA Top 5"] = []
    st.info("ℹ️ No MUDRA setups currently meet the strict trend & volume criteria.")
else:
    top5_mudra = df_mudra.head(5)
    mudra_payload = [
        {
            "symbol": r["Stock"],
            "side": "BUY",
            "entry": float(r["Watch_Buy"]),
            "sl": float(r["Stop_Loss"]),
            "t1": float(r["Target_1"]),
            "t2": float(r["Target_2"]),
            "notes": f"MUDRA Rank #{i+1} | RVOL {r['RVOL']} | +{r['Change_%']}%",
        }
        for i, (_, r) in enumerate(top5_mudra.iterrows())
    ]
    st.session_state.setdefault("live_scanner_picks", {})["MUDRA Top 5"] = mudra_payload

    if st.button("📌 Log Top 5 MUDRA Picks to History Ledger", type="primary"):
        saved = _save_mudra_picks_to_ledger(mudra_payload, "MUDRA Top 5")
        st.success(f"Recorded {saved} MUDRA pick(s) to history ledger.")

    st.subheader("🎯 Active MUDRA Signal Desk")
    st.dataframe(
        df_mudra.drop(columns=["Score"]).style.format({
            "LTP": "₹{:,.2f}", "Watch_Buy": "₹{:,.2f}", "Change_%": "{:+.2f}%",
            "Stop_Loss": "₹{:,.2f}", "Target_1": "₹{:,.2f}", "Target_2": "₹{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
