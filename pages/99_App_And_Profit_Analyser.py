import ast
from datetime import datetime
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

ist = pytz.timezone("Asia/Kolkata")
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import (
        import_historical_csv,
        load_ledger,
        record_picks,
        top_n_picks,
    )
except Exception:
    LEDGER_COLS = [
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
    LEDGER_FILE = REPO_ROOT / "data_ledger" / "pick_click_ledger.csv"

    def top_n_picks(picks: list[dict], n: int) -> list[dict]:
        return list(picks[:n]) if picks else []

    def load_ledger() -> pd.DataFrame:
        if LEDGER_FILE.exists():
            return pd.read_csv(LEDGER_FILE)
        return pd.DataFrame(columns=LEDGER_COLS)

    def record_picks(module_label: str, picks: list[dict]) -> int:
        if not picks:
            return 0
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        now_i = datetime.now(ist)
        ts_str = now_i.strftime("%Y-%m-%d %H:%M:%S IST")
        s_date = now_i.strftime("%Y-%m-%d")
        i_week = f"{now_i.isocalendar().year}-W{now_i.isocalendar().week:02d}"
        bucket = now_i.strftime("%Y-%m-%d %H:%M")

        existing = load_ledger()
        seen = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()
        rows = []
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
            rows.append({
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
        if not rows:
            return 0
        out = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
            subset=["pick_id"], keep="first"
        )
        out.to_csv(LEDGER_FILE, index=False)
        return len(rows)

    def import_historical_csv(uploaded_file) -> tuple[int, int]:
        incoming = pd.read_csv(uploaded_file)
        existing = load_ledger()
        before = len(existing)
        merged = pd.concat([existing, incoming], ignore_index=True)
        if "pick_id" in merged.columns:
            merged = merged.drop_duplicates(subset=["pick_id"], keep="first")
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(LEDGER_FILE, index=False)
        return max(0, len(merged) - before), len(merged)


st.set_page_config(page_title="App, Risk Guardrail & Profit Analyser", layout="wide")
st.title("🧪 App, Risk Guardrail & Net Profit-Booking Analyser")
st.caption(
    "Tracks every logged pick forever, deducts realistic NSE brokerage/STT/slippage costs, enforces daily drawdown & "
    "position-sizing limits, and flags underperforming modules automatically. Not financial advice."
)

AUDIT_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "AXISBANK.NS", "LT.NS",
    "BAJFINANCE.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS",
]

MODULE_PICKS = {
    "Macro Radar Top Picks": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "Macro Green Top #1"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Macro Green Top #2"},
    ],
    "Night Before -> Morning Top 2": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "Morning Top #1"},
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "Morning Top #2"},
    ],
    "Matched Super Signal (Top 2)": [
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Matched Super #1"},
        {"symbol": "BHARTIARTL.NS", "side": "BUY", "entry": 2149.8, "sl": 2130.0, "t1": 2175.0, "t2": 2196.0, "notes": "Matched Super #2"},
    ],
    "MUDRA Top 5": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "MUDRA #1"},
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "MUDRA #2"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "MUDRA #3"},
        {"symbol": "LT.NS", "side": "BUY", "entry": 4205.7, "sl": 4170.0, "t1": 4252.0, "t2": 4290.0, "notes": "MUDRA #4"},
        {"symbol": "AXISBANK.NS", "side": "BUY", "entry": 1377.5, "sl": 1365.0, "t1": 1394.0, "t2": 1408.0, "notes": "MUDRA #5"},
    ],
    "PRIME Top 3": [
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "PRIME #1"},
        {"symbol": "LT.NS", "side": "BUY", "entry": 4205.7, "sl": 4170.0, "t1": 4252.0, "t2": 4290.0, "notes": "PRIME #2"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "PRIME #3"},
    ],
    "Bearish Top 2": [
        {"symbol": "TCS.NS", "side": "SHORT", "entry": 2347.5, "sl": 2368.0, "t1": 2320.0, "t2": 2298.0, "notes": "Bearish Top #1"},
        {"symbol": "HDFCBANK.NS", "side": "SHORT", "entry": 821.0, "sl": 828.5, "t1": 811.0, "t2": 803.0, "notes": "Bearish Top #2"},
    ],
    "Smart Money Top 2 Green & Red": [
        {"symbol": "BHARTIARTL.NS", "side": "BUY", "entry": 2149.8, "sl": 2130.0, "t1": 2175.0, "t2": 2196.0, "notes": "Smart Money Green #1"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Smart Money Green #2"},
        {"symbol": "TCS.NS", "side": "SHORT", "entry": 2347.5, "sl": 2368.0, "t1": 2320.0, "t2": 2298.0, "notes": "Smart Money Red #1"},
        {"symbol": "HDFCBANK.NS", "side": "SHORT", "entry": 821.0, "sl": 828.5, "t1": 811.0, "t2": 803.0, "notes": "Smart Money Red #2"},
    ],
    "Sector Rotation Top 2 Green & Red": [
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Sector Green #1"},
        {"symbol": "LT.NS", "side": "BUY", "entry": 4205.7, "sl": 4170.0, "t1": 4252.0, "t2": 4290.0, "notes": "Sector Green #2"},
        {"symbol": "TCS.NS", "side": "SHORT", "entry": 2347.5, "sl": 2368.0, "t1": 2320.0, "t2": 2298.0, "notes": "Sector Red #1"},
        {"symbol": "INFY.NS", "side": "SHORT", "entry": 1090.6, "sl": 1102.0, "t1": 1076.0, "t2": 1064.0, "notes": "Sector Red #2"},
    ],
}

CAP_BY_MODULE = {
    "Macro Radar Top Picks": 2,
    "Night Before -> Morning Top 2": 2,
    "Matched Super Signal (Top 2)": 2,
    "MUDRA Top 5": 5,
    "PRIME Top 3": 3,
    "Bearish Top 2": 2,
    "Smart Money Top 2 Green & Red": 4,
    "Sector Rotation Top 2 Green & Red": 4,
}


def _color_outcome_row(row):
    outcome = str(row.get("Outcome", row.get("status", "")))
    if "Target_1_Hit" in outcome or "Target 1 Reached" in outcome or "Target 2 Reached" in outcome:
        return ["background-color: rgba(0, 200, 83, 0.22); color: #A5F3C5"] * len(row)
    if "Stop_Loss_Hit" in outcome or "Stop-Loss Touched" in outcome:
        return ["background-color: rgba(255, 82, 82, 0.24); color: #FFB4B4"] * len(row)
    return ["background-color: rgba(255, 193, 7, 0.14); color: #FFE599"] * len(row)


def _parse_logged_ts_ist(ts_val) -> pd.Timestamp | None:
    if pd.isna(ts_val):
        return None
    s = str(ts_val).replace(" IST", "").strip()
    dt_parsed = pd.to_datetime(s, errors="coerce")
    if pd.isna(dt_parsed):
        return None
    if dt_parsed.tzinfo is None:
        return dt_parsed.tz_localize("Asia/Kolkata")
    return dt_parsed.tz_convert("Asia/Kolkata")


def audit_repo_files() -> pd.DataFrame:
    py_files = sorted(
        [p for p in REPO_ROOT.rglob("*.py") if ".git" not in p.parts and "__pycache__" not in p.parts]
    )
    findings = []
    for fpath in py_files:
        rel_name = str(fpath.relative_to(REPO_ROOT))
        try:
            src = fpath.read_text(encoding="utf-8", errors="replace")
            ast.parse(src)
            syntax_ok = True
        except SyntaxError as exc:
            findings.append({
                "File": rel_name,
                "Syntax": "❌ Error",
                "Lines": 0,
                "Cached": "N/A",
                "Uses_yfinance": "Unknown",
                "NSE_Direct_Call": "Check",
                "Audit_Notes": f"SyntaxError line {exc.lineno}: {exc.msg}",
            })
            continue

        uses_yf = "yfinance" in src or "yf." in src
        has_cache = "@st.cache_data" in src or "@st.cache_resource" in src
        has_try = "try:" in src and "except" in src
        nse_direct = "nseindia.com" in src.lower()

        notes = []
        if uses_yf and not has_cache:
            notes.append("No @st.cache_data found")
        if uses_yf and not has_try:
            notes.append("Missing try/except around data fetch")
        if nse_direct:
            notes.append("Direct NSE endpoint call (may block/fallback on cloud)")
        if not notes:
            notes.append("Clean structure & guarded data handling")

        findings.append({
            "File": rel_name,
            "Syntax": "✅ OK" if syntax_ok else "❌",
            "Lines": len(src.splitlines()),
            "Cached": "✅ Yes" if has_cache else "⚠️ No",
            "Uses_yfinance": "✅ Yes" if uses_yf else "No",
            "NSE_Direct_Call": "⚠️ Yes" if nse_direct else "No",
            "Audit_Notes": " | ".join(notes),
        })
    return pd.DataFrame(findings)


@st.cache_data(ttl=120)
def run_completeness_and_target_audit(t1_p: float, sl_p: float, min_move_p: float, friction_pct: float):
    completeness_rows = []
    sim_trades = []

    raw_5m = yf.download(
        AUDIT_UNIVERSE,
        period="5d",
        interval="5m",
        group_by="ticker",
        progress=False,
        threads=True,
        auto_adjust=True,
    )

    for sym in AUDIT_UNIVERSE:
        clean = sym.replace(".NS", "")
        try:
            if isinstance(raw_5m.columns, pd.MultiIndex):
                lvl0 = raw_5m.columns.get_level_values(0)
                lvl1 = raw_5m.columns.get_level_values(1)
                if sym in lvl0:
                    df = raw_5m[sym].dropna(how="all")
                elif sym in lvl1:
                    df = raw_5m.xs(sym, axis=1, level=1).dropna(how="all")
                else:
                    df = pd.DataFrame()
            else:
                df = raw_5m.dropna(how="all")

            df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
            if df.empty or len(df) < 15:
                completeness_rows.append({
                    "Stock": clean,
                    "Status": "⚠️ Incomplete",
                    "Bars_5m": len(df),
                    "Latest_Close": np.nan,
                    "Null_Cells": int(df.isna().sum().sum()) if not df.empty else -1,
                })
                continue

            null_cells = int(df[["Open", "High", "Low", "Close"]].isna().sum().sum())
            last_close = float(df["Close"].iloc[-1])
            completeness_rows.append({
                "Stock": clean,
                "Status": "✅ Complete" if null_cells == 0 and last_close > 0 else "⚠️ Check",
                "Bars_5m": int(len(df)),
                "Latest_Close": round(last_close, 2),
                "Null_Cells": null_cells,
            })

            closes = df["Close"].to_numpy(dtype=float)
            highs = df["High"].to_numpy(dtype=float)
            lows = df["Low"].to_numpy(dtype=float)
            vols = df["Volume"].to_numpy(dtype=float) if "Volume" in df.columns else np.ones_like(closes)

            cost_r_drag = friction_pct / max(sl_p, 0.01)

            for i in range(10, len(closes) - 6):
                ref_prev = closes[i - 10]
                if ref_prev <= 0:
                    continue
                move_pct = ((closes[i] - ref_prev) / ref_prev) * 100.0
                vol_mean = np.mean(vols[max(0, i - 10):i])
                vol_ok = True if vol_mean <= 0 else (vols[i] >= 0.8 * vol_mean)

                if move_pct >= min_move_p and vol_ok:
                    entry = closes[i]
                    target = entry * (1.0 + t1_p / 100.0)
                    stop = entry * (1.0 - sl_p / 100.0)
                    future_h = highs[i + 1:i + 7]
                    future_l = lows[i + 1:i + 7]

                    hit_t1 = bool(np.any(future_h >= target))
                    hit_sl = bool(np.any(future_l <= stop))

                    if hit_t1 and not hit_sl:
                        outcome = "Target_1_Hit"
                        gross_r = t1_p / max(sl_p, 0.01)
                    elif hit_sl and not hit_t1:
                        outcome = "Stop_Loss_Hit"
                        gross_r = -1.0
                    elif hit_t1 and hit_sl:
                        outcome = "Both_In_Window"
                        gross_r = 0.0
                    else:
                        exit_p = closes[i + 6]
                        gross_r = (exit_p - entry) / max(entry - stop, 1e-6)
                        outcome = "Time_Exit"

                    net_r = round(gross_r - cost_r_drag, 2)
                    sim_trades.append({
                        "Stock": clean,
                        "Outcome": outcome,
                        "Gross_R": round(gross_r, 2),
                        "Net_R (After Costs)": net_r,
                    })
        except Exception:
            completeness_rows.append({
                "Stock": clean,
                "Status": "❌ Error",
                "Bars_5m": 0,
                "Latest_Close": np.nan,
                "Null_Cells": -1,
            })

    return pd.DataFrame(completeness_rows), pd.DataFrame(sim_trades)


@st.cache_data(ttl=120)
def evaluate_logged_ledger(ledger_df: pd.DataFrame, friction_pct: float) -> pd.DataFrame:
    if ledger_df.empty:
        return pd.DataFrame()

    symbols = sorted(ledger_df["symbol"].dropna().astype(str).unique().tolist())
    try:
        raw_15m = yf.download(
            symbols,
            period="1mo",
            interval="15m",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        raw_15m = pd.DataFrame()

    rows = []
    for _, r in ledger_df.iterrows():
        sym = str(r["symbol"])
        side = str(r["side"]).upper()
        entry = float(r["entry_price"])
        sl = float(r["stop_loss"])
        t1 = float(r["target_1"])
        t2 = float(r["target_2"])
        logged_dt = _parse_logged_ts_ist(r.get("logged_at_ist"))

        sub = pd.DataFrame()
        if not raw_15m.empty:
            if isinstance(raw_15m.columns, pd.MultiIndex):
                lvl0 = raw_15m.columns.get_level_values(0)
                lvl1 = raw_15m.columns.get_level_values(1)
                if sym in lvl0:
                    sub = raw_15m[sym].dropna(how="all")
                elif sym in lvl1:
                    sub = raw_15m.xs(sym, axis=1, level=1).dropna(how="all")
            elif len(symbols) == 1:
                sub = raw_15m.dropna(how="all")

        if sub.empty or not {"High", "Low", "Close"}.issubset(sub.columns):
            rows.append({
                "pick_id": r["pick_id"],
                "logged_at_ist": r["logged_at_ist"],
                "session_date": r["session_date"],
                "iso_week": r["iso_week"],
                "module": r["module"],
                "symbol": sym.replace(".NS", ""),
                "side": side,
                "entry": round(entry, 2),
                "ltp": np.nan,
                "status": "No Price Feed",
                "t1_hit_flag": 0,
                "sl_hit_flag": 0,
                "gross_r": np.nan,
                "net_r": np.nan,
            })
            continue

        sub = sub.copy()
        idx_dt = pd.to_datetime(sub.index)
        if idx_dt.tz is None:
            idx_dt = idx_dt.tz_localize("Asia/Kolkata")
        else:
            idx_dt = idx_dt.tz_convert("Asia/Kolkata")
        sub.index = idx_dt

        ltp = float(sub["Close"].iloc[-1])

        if logged_dt is not None:
            post_sub = sub[sub.index >= (logged_dt - pd.Timedelta(minutes=15))]
        else:
            post_sub = sub

        risk_pts = max(abs(entry - sl), entry * 0.005)
        cost_pts = entry * (friction_pct / 100.0)
        cost_r = cost_pts / risk_pts

        if post_sub.empty:
            rows.append({
                "pick_id": r["pick_id"],
                "logged_at_ist": r["logged_at_ist"],
                "session_date": r["session_date"],
                "iso_week": r["iso_week"],
                "module": r["module"],
                "symbol": sym.replace(".NS", ""),
                "side": side,
                "entry": round(entry, 2),
                "ltp": round(ltp, 2),
                "status": "⏳ Awaiting Next Session Bar",
                "t1_hit_flag": 0,
                "sl_hit_flag": 0,
                "gross_r": 0.0,
                "net_r": 0.0,
            })
            continue

        status = "⏳ Open / Unresolved"
        t1_flag = 0
        sl_flag = 0
        if side == "SHORT":
            reward_t1_pts = max(entry - t1, 1e-6)
            reward_t2_pts = max(entry - t2, 1e-6)
            gross_r = (entry - ltp) / risk_pts
            for _, bar in post_sub.iterrows():
                if float(bar["High"]) >= sl:
                    status = "🛑 Stop-Loss Touched"
                    sl_flag = 1
                    gross_r = -1.0
                    break
                if float(bar["Low"]) <= t2:
                    status = "✅ Target 2 Reached"
                    t1_flag = 1
                    gross_r = reward_t2_pts / risk_pts
                    break
                if float(bar["Low"]) <= t1 and t1_flag == 0:
                    status = "✅ Target 1 Reached"
                    t1_flag = 1
                    gross_r = reward_t1_pts / risk_pts
        else:
            reward_t1_pts = max(t1 - entry, 1e-6)
            reward_t2_pts = max(t2 - entry, 1e-6)
            gross_r = (ltp - entry) / risk_pts
            for _, bar in post_sub.iterrows():
                if float(bar["Low"]) <= sl:
                    status = "🛑 Stop-Loss Touched"
                    sl_flag = 1
                    gross_r = -1.0
                    break
                if float(bar["High"]) >= t2:
                    status = "✅ Target 2 Reached"
                    t1_flag = 1
                    gross_r = reward_t2_pts / risk_pts
                    break
                if float(bar["High"]) >= t1 and t1_flag == 0:
                    status = "✅ Target 1 Reached"
                    t1_flag = 1
                    gross_r = reward_t1_pts / risk_pts

        rows.append({
            "pick_id": r["pick_id"],
            "logged_at_ist": r["logged_at_ist"],
            "session_date": r["session_date"],
            "iso_week": r["iso_week"],
            "module": r["module"],
            "symbol": sym.replace(".NS", ""),
            "side": side,
            "entry": round(entry, 2),
            "ltp": round(ltp, 2),
            "status": status,
            "t1_hit_flag": t1_flag,
            "sl_hit_flag": sl_flag,
            "gross_r": round(gross_r, 2),
            "net_r": round(gross_r - cost_r, 2),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 0. HARD RISK, POSITION SIZING & NSE COST GUARDRAILS
# ---------------------------------------------------------
with st.expander("🛡️ Hard Risk Guardrail, NSE Fee/Slippage & Position-Size Calculator", expanded=True):
    rc1, rc2, rc3, rc4 = st.columns(4)
    account_cap = rc1.number_input("💰 Trading Capital (₹)", min_value=5000.0, max_value=50000000.0, value=100000.0, step=5000.0)
    risk_per_trade_pct = rc2.number_input("🎯 Max Risk / Trade (%)", min_value=0.25, max_value=3.0, value=1.0, step=0.25)
    max_daily_loss_pct = rc3.number_input("🛑 Daily Kill-Switch Loss (%)", min_value=1.0, max_value=6.0, value=2.0, step=0.5)
    nse_friction_pct = rc4.number_input("🧾 Brokerage + STT + Slippage (%)", min_value=0.02, max_value=0.50, value=0.12, step=0.02)

    max_risk_rs = account_cap * (risk_per_trade_pct / 100.0)
    daily_kill_rs = account_cap * (max_daily_loss_pct / 100.0)
    max_sl_per_day = max(1, int(daily_kill_rs // max(max_risk_rs, 1.0)))

    st.info(
        f"**Hard Execution Rules:** Max risk per trade = **₹{max_risk_rs:,.0f}** | "
        f"Daily Kill-Switch = **₹{daily_kill_rs:,.0f}** (Stop trading for the day after **{max_sl_per_day}** Stop-Loss hit(s)) | "
        f"Cost drag deducted per trade = **{nse_friction_pct:.2f}%**."
    )

# ---------------------------------------------------------
# 1. TOP PICKS BY VIEW + SAFE SHARE QUANTITY SIZER
# ---------------------------------------------------------
st.subheader("⭐ Top Picks by View (With Exact Safe Quantity Sizing)")
chosen_module = st.selectbox("Select View / Scanner", list(MODULE_PICKS.keys()), index=0)
capped_picks = top_n_picks(MODULE_PICKS[chosen_module], CAP_BY_MODULE[chosen_module])
top2_highlight = top_n_picks(capped_picks, 2)

st.markdown("**Top 2 Highlighted Picks (Auto-Sized to Your Max Risk ₹)**")
t2_cols = st.columns(max(1, len(top2_highlight)))
for idx, pk in enumerate(top2_highlight):
    risk_per_share = max(abs(float(pk["entry"]) - float(pk["sl"])), 0.5)
    safe_qty = max(1, int(max_risk_rs // risk_per_share))
    capital_needed = safe_qty * float(pk["entry"])
    with t2_cols[idx]:
        st.metric(
            label=f"#{idx + 1} {pk['symbol'].replace('.NS', '')} ({pk['side']}) — Safe Qty: {safe_qty} sh",
            value=f"₹{pk['entry']:,.2f}",
            delta=f"T1 ₹{pk['t1']:,.2f} | SL ₹{pk['sl']:,.2f}",
        )
        st.caption(f"{pk.get('notes', '')} • Est. Capital: ₹{capital_needed:,.0f} • Max Loss: ₹{safe_qty * risk_per_share:,.0f}")

b1, b2, _ = st.columns([1.6, 1.8, 3.0])
with b1:
    if st.button("📌 Log Top 2 Picks Now", type="primary", use_container_width=True):
        added = record_picks(chosen_module, top2_highlight)
        st.cache_data.clear()
        st.success(f"Saved {added} new Top 2 pick(s) to permanent ledger.")
with b2:
    if st.button(f"📥 Log All ({len(capped_picks)}) in View", use_container_width=True):
        added = record_picks(chosen_module, capped_picks)
        st.cache_data.clear()
        st.success(f"Saved {added} new pick(s) from '{chosen_module}'.")

st.dataframe(pd.DataFrame(capped_picks), use_container_width=True, hide_index=True)

st.markdown("---")

# ---------------------------------------------------------
# 2. FOREVER HISTORY VAULT + AUTOMATIC STRATEGY PAUSE TRIGGER
# ---------------------------------------------------------
st.subheader("🗂️ Forever History Vault, Net R-Performance & Auto-Pause Monitor")
imp_col, exp_col = st.columns([2.2, 1.8])
with imp_col:
    uploaded_hist = st.file_uploader(
        "Import Historical Pick CSV to Merge Forever",
        type=["csv"],
        key="import_hist_csv",
    )
    if uploaded_hist is not None:
        added_hist, total_hist = import_historical_csv(uploaded_hist)
        st.cache_data.clear()
        st.success(f"Merged {added_hist} new historical record(s). Total saved history: {total_hist} rows.")

ledger_df = load_ledger()
with exp_col:
    st.write("")
    if not ledger_df.empty:
        st.download_button(
            "⬇️ Export Master History CSV (Keep Forever)",
            data=ledger_df.to_csv(index=False).encode("utf-8"),
            file_name="kk_master_pick_history.csv",
            mime="text/csv",
            use_container_width=True,
        )

if ledger_df.empty:
    st.info("No picks in history yet. Log picks above or from any scanner page to start tracking Net R-performance.")
else:
    with st.spinner("Evaluating recorded history after NSE brokerage/STT/slippage costs..."):
        hist_eval = evaluate_logged_ledger(ledger_df, nse_friction_pct)

    if not hist_eval.empty:
        mod_options = ["All Modules"] + sorted(hist_eval["module"].dropna().unique().tolist())
        sel_mod_eval = st.selectbox("Filter Recorded Ledger by Scanner Module:", mod_options, index=0)
        eval_view = (
            hist_eval
            if sel_mod_eval == "All Modules"
            else hist_eval[hist_eval["module"] == sel_mod_eval].reset_index(drop=True)
        )

        tot_logged = len(eval_view)
        t1_cnt = int(eval_view["t1_hit_flag"].sum())
        sl_cnt = int(eval_view["sl_hit_flag"].sum())
        avg_gross_r = float(eval_view["gross_r"].dropna().mean()) if not eval_view["gross_r"].dropna().empty else 0.0
        avg_net_r = float(eval_view["net_r"].dropna().mean()) if not eval_view["net_r"].dropna().empty else 0.0

        lk1, lk2, lk3, lk4, lk5 = st.columns(5)
        lk1.metric("Logged Picks", f"{tot_logged}")
        lk2.metric("Target 1 / 2 Hit Rate", f"{(t1_cnt / max(tot_logged, 1)) * 100:.1f}%", f"{t1_cnt} Hits")
        lk3.metric("Stop-Loss Touched", f"{(sl_cnt / max(tot_logged, 1)) * 100:.1f}%", f"{sl_cnt} SL", delta_color="inverse")
        lk4.metric("Avg Gross R", f"{avg_gross_r:+.2f}R")
        lk5.metric("Avg Net R (After Costs)", f"{avg_net_r:+.2f}R")

        eval_display_cols = [
            "logged_at_ist",
            "iso_week",
            "module",
            "symbol",
            "side",
            "entry",
            "ltp",
            "status",
            "gross_r",
            "net_r",
        ]
        st.dataframe(
            eval_view[eval_display_cols]
            .tail(30)
            .style.apply(_color_outcome_row, axis=1)
            .format({
                "entry": "₹{:,.2f}",
                "ltp": "₹{:,.2f}",
                "gross_r": "{:+.2f}R",
                "net_r": "{:+.2f}R",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("🚦 Scanner Module Health & Automatic Pause Guardrail")
        mod_perf = (
            hist_eval.groupby("module", as_index=False)
            .agg(
                Total_Picks=("pick_id", "count"),
                T1_Hits=("t1_hit_flag", "sum"),
                SL_Hits=("sl_hit_flag", "sum"),
                Avg_Gross_R=("gross_r", "mean"),
                Avg_Net_R=("net_r", "mean"),
            )
        )
        mod_perf["T1_Hit_Rate_%"] = np.where(
            mod_perf["Total_Picks"] > 0,
            (mod_perf["T1_Hits"] / mod_perf["Total_Picks"]) * 100.0,
            0.0,
        )

        def _module_verdict(row):
            if row["Total_Picks"] < 5:
                return "🟡 COLLECTING SAMPLE (<5 Picks)"
            if row["T1_Hit_Rate_%"] < 40.0 or row["Avg_Net_R"] < 0:
                return "🛑 PAUSE & REVIEW (Below Threshold)"
            return "✅ ACTIVE — EDGE CONFIRMED"

        mod_perf["Guardrail_Verdict"] = mod_perf.apply(_module_verdict, axis=1)
        st.dataframe(
            mod_perf.style.format({
                "T1_Hit_Rate_%": "{:.1f}%",
                "Avg_Gross_R": "{:+.2f}R",
                "Avg_Net_R": "{:+.2f}R",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("📈 Week-Over-Week Net R Improvement")
        weekly_perf = (
            hist_eval.groupby("iso_week", as_index=False)
            .agg(
                Total_Picks=("pick_id", "count"),
                T1_Hits=("t1_hit_flag", "sum"),
                SL_Hits=("sl_hit_flag", "sum"),
                Avg_Net_R=("net_r", "mean"),
            )
        )
        weekly_perf["T1_Hit_Rate_%"] = np.where(
            weekly_perf["Total_Picks"] > 0,
            (weekly_perf["T1_Hits"] / weekly_perf["Total_Picks"]) * 100.0,
            0.0,
        )
        st.dataframe(
            weekly_perf.style.format({
                "T1_Hit_Rate_%": "{:.1f}%",
                "Avg_Net_R": "{:+.2f}R",
            }),
            use_container_width=True,
            hide_index=True,
        )

st.markdown("---")

# ---------------------------------------------------------
# 3. REPO CODE AUDIT & COST-ADJUSTED 5M WINDOW SIMULATION
# ---------------------------------------------------------
st.subheader("3️⃣ GitHub Repository & Page Health Audit")
df_repo = audit_repo_files()
if not df_repo.empty:
    st.dataframe(df_repo, use_container_width=True, hide_index=True)

c1, c2, c3, c4 = st.columns([1.4, 1.4, 1.4, 1.2])
t1_pct = c1.number_input("🎯 Sim Target 1 (%)", min_value=0.3, max_value=5.0, value=1.2, step=0.1)
sl_pct = c2.number_input("🛑 Sim Stop-Loss (%)", min_value=0.3, max_value=5.0, value=0.8, step=0.1)
min_chg_pct = c3.number_input("📈 Min Intraday Move (%)", min_value=0.0, max_value=3.0, value=0.25, step=0.05)
with c4:
    st.write("")
    if st.button("🔄 Refresh All Audits", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Running 5m data completeness & cost-adjusted Target-1 vs. Stop-Loss audit..."):
    df_comp, df_sim = run_completeness_and_target_audit(t1_pct, sl_pct, min_chg_pct, nse_friction_pct)

st.subheader("4️⃣ Cost-Adjusted Historical 5m Window Audit")
if not df_sim.empty:
    tot_s = len(df_sim)
    t1_h = int((df_sim["Outcome"] == "Target_1_Hit").sum())
    sl_h = int((df_sim["Outcome"] == "Stop_Loss_Hit").sum())
    avg_net_sim = float(df_sim["Net_R (After Costs)"].mean())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sampled Setups", f"{tot_s}")
    k2.metric("Target 1 Hits", f"{t1_h} ({(t1_h / tot_s) * 100:.1f}%)")
    k3.metric("Stop-Loss Hits", f"{sl_h} ({(sl_h / tot_s) * 100:.1f}%)")
    k4.metric("Avg Net R (After Costs)", f"{avg_net_sim:+.2f}R")

    st.dataframe(
        df_sim.style.apply(_color_outcome_row, axis=1).format({
            "Gross_R": "{:+.2f}R",
            "Net_R (After Costs)": "{:+.2f}R",
        }),
        use_container_width=True,
        hide_index=True,
    )
