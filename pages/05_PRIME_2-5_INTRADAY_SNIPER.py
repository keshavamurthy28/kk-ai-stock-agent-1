from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Prime 2-5 Intraday Sniper", layout="wide")

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


def _save_prime_picks_to_ledger(picks: list[dict], module_label: str = "Prime 2-5 Sniper Top 3") -> int:
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


st.title("🎯 Prime 2–5% Intraday Sniper Desk")
st.markdown(
    "Targeting high-probability **2% to 5% intraday expansion setups** with "
    "strict risk-reward bounds and anti-chase pullback entries."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

PRIME_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "BHARTIARTL.NS", "LT.NS", "BAJFINANCE.NS", "SUNPHARMA.NS",
    "TATAMOTORS.NS", "NTPC.NS", "AXISBANK.NS", "KALYANKJIL.NS", "HAL.NS",
    "BEL.NS", "AMBER.NS", "TDPOWERSYS.NS", "MSTCLTD.NS", "POWERINDIA.NS",
]

col_p1, col_p2 = st.columns([3, 1])
with col_p2:
    if st.button("🔄 Refresh Prime Sniper", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Refreshing live Prime Intraday Sniper data...", icon="⚡")
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
def fetch_prime_sniper_scans():
    try:
        raw = yf.download(
            PRIME_UNIVERSE, period="5d", interval="5m", group_by="ticker", progress=False, auto_adjust=True
        )
    except Exception:
        return pd.DataFrame()

    results = []
    for sym in PRIME_UNIVERSE:
        clean_sym = sym.replace(".NS", "")
        try:
            df = _extract_ticker_df(raw, sym).dropna(subset=["Open", "High", "Low", "Close"])
            if len(df) < 20:
                continue

            ltp = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[0])
            if open_p <= 0 or np.isnan(ltp):
                continue

            day_chg = round(((ltp - open_p) / open_p) * 100, 2)
            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            avg_vol = float(vol_series.tail(30).mean())
            cur_vol = float(vol_series.iloc[-1])
            rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            ema20 = float(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1])

            # Target sweet spot moves (1.2% to 4.5%) with volume support
            if 1.2 <= day_chg <= 4.5 and rvol >= 1.25 and ltp >= ema20:
                watch_buy = round(ltp * 0.992, 2)
                sl = round(max(watch_buy * 0.985, ema20 * 0.994), 2)
                risk = max(watch_buy - sl, watch_buy * 0.007)
                t1 = round(watch_buy + (risk * 1.5), 2)
                t2 = round(watch_buy + (risk * 2.5), 2)
                rr_t1 = round((t1 - watch_buy) / risk, 2)

                if rr_t1 >= 1.4:
                    results.append({
                        "Stock": clean_sym,
                        "LTP": round(ltp, 2),
                        "Watch_Buy": watch_buy,
                        "Move_%": day_chg,
                        "RVOL": f"{rvol:.2f}x",
                        "Stop_Loss": sl,
                        "Target_1": t1,
                        "Target_2": t2,
                        "R:R": f"{rr_t1:.2f}x",
                        "Status": "⚡ Prime 2-5% Sniper Breakout",
                    })
        except Exception:
            continue

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Move_%", ascending=False).reset_index(drop=True)
    return df_res


with st.spinner("Scanning Prime 2–5% Sniper setups..."):
    df_prime = fetch_prime_sniper_scans()

if df_prime.empty:
    st.session_state.setdefault("live_scanner_picks", {})["Prime 2-5 Sniper Top 3"] = []
    st.info("ℹ️ No Prime 2–5% setups currently match the anti-chase R:R filter.")
else:
    top3_prime = df_prime.head(3)
    prime_payload = [
        {
            "symbol": r["Stock"],
            "side": "BUY",
            "entry": float(r["Watch_Buy"]),
            "sl": float(r["Stop_Loss"]),
            "t1": float(r["Target_1"]),
            "t2": float(r["Target_2"]),
            "notes": f"Prime Sniper | Move +{r['Move_%']}% | RVOL {r['RVOL']} | R:R {r['R:R']}",
        }
        for _, r in top3_prime.iterrows()
    ]
    st.session_state.setdefault("live_scanner_picks", {})["Prime 2-5 Sniper Top 3"] = prime_payload

    if st.button("📌 Log Top 3 Prime Sniper Picks to History Ledger", type="primary"):
        saved = _save_prime_picks_to_ledger(prime_payload, "Prime 2-5 Sniper Top 3")
        st.success(f"Recorded {saved} Prime Sniper pick(s) to history ledger.")

    st.subheader("🚀 Prime Sniper Watchlist")
    st.dataframe(
        df_prime.style.format({
            "LTP": "₹{:,.2f}", "Watch_Buy": "₹{:,.2f}", "Move_%": "{:+.2f}%",
            "Stop_Loss": "₹{:,.2f}", "Target_1": "₹{:,.2f}", "Target_2": "₹{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
