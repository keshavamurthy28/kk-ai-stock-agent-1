import ast
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from urllib import error, request
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

ist = pytz.timezone("Asia/Kolkata")
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LEDGER_COLS = [
    "pick_id",
    "logged_at_ist",
    "slot_5m_ist",
    "session_date",
    "iso_week",
    "source_mode",
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


def _bucket_5m_ist(dt_obj: datetime) -> str:
    dt_ist = dt_obj.astimezone(ist) if dt_obj.tzinfo else ist.localize(dt_obj)
    floored_min = (dt_ist.minute // 5) * 5
    slot = dt_ist.replace(minute=floored_min, second=0, microsecond=0)
    return slot.strftime("%Y-%m-%d %H:%M")


def _sync_ledger_to_github_if_configured(df: pd.DataFrame) -> tuple[bool, str]:
    """Optional GitHub persistence when GITHUB_TOKEN & GITHUB_REPO are set in st.secrets."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        rel_path = st.secrets.get("LEDGER_REPO_PATH", "data_ledger/pick_click_ledger.csv")
    except Exception:
        return False, "Secrets not configured"

    if not token or not repo:
        return False, "Local CSV only (no GitHub token/repo)"

    api_url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "kk-ai-stock-agent-1",
    }

    sha = None
    try:
        req_get = request.Request(f"{api_url}?ref={branch}", headers=headers, method="GET")
        with request.urlopen(req_get, timeout=8) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
            sha = meta.get("sha")
    except error.HTTPError as exc:
        if exc.code != 404:
            return False, f"GitHub GET error ({exc.code})"
    except Exception as exc:
        return False, f"GitHub GET failed: {exc}"

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    payload = {
        "message": f"chore(ledger): 5m auto-sync ({len(df)} rows)",
        "content": base64.b64encode(csv_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        req_put = request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        with request.urlopen(req_put, timeout=10):
            return True, "Synced to GitHub"
    except Exception as exc:
        return False, f"GitHub PUT failed: {exc}"


def top_n_picks(picks: list[dict], n: int) -> list[dict]:
    return list(picks[:n]) if picks else []


def load_ledger() -> pd.DataFrame:
    if LEDGER_FILE.exists():
        df = pd.read_csv(LEDGER_FILE)
        for col in LEDGER_COLS:
            if col not in df.columns:
                df[col] = ""
        return df[LEDGER_COLS]
    return pd.DataFrame(columns=LEDGER_COLS)


def _normalize_symbol(raw_sym: str) -> str:
    sym = str(raw_sym).strip().upper()
    if not sym.endswith(".NS") and not sym.endswith(".BO"):
        sym = f"{sym}.NS"
    return sym


def record_picks(
    module_label: str,
    picks: list[dict],
    source_mode: str = "MANUAL",
    slot_override: str | None = None,
    sync_github: bool = False,
) -> int:
    if not picks:
        return 0

    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    now_i = datetime.now(ist)
    ts_str = now_i.strftime("%Y-%m-%d %H:%M:%S IST")
    s_date = now_i.strftime("%Y-%m-%d")
    i_week = f"{now_i.isocalendar().year}-W{now_i.isocalendar().week:02d}"
    slot_5m = slot_override or _bucket_5m_ist(now_i)

    existing = load_ledger()
    seen = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()

    rows = []
    for p in picks:
        try:
            sym = _normalize_symbol(p["symbol"])
            side = str(p.get("side", "BUY")).upper()
            entry = float(p["entry"])
            sl = float(p["sl"])
            t1 = float(p["t1"])
            t2 = float(p.get("t2", t1))
        except Exception:
            continue

        pid = hashlib.sha1(
            f"{slot_5m}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")
        ).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)

        rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_str,
            "slot_5m_ist": slot_5m,
            "session_date": s_date,
            "iso_week": i_week,
            "source_mode": source_mode,
            "module": module_label,
            "symbol": sym,
            "side": side,
            "entry_price": round(entry, 2),
            "stop_loss": round(sl, 2),
            "target_1": round(t1, 2),
            "target_2": round(t2, 2),
            "notes": str(p.get("notes", "")),
        })

    if not rows:
        return 0

    out = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
        subset=["pick_id"], keep="first"
    )
    out.to_csv(LEDGER_FILE, index=False)

    if sync_github:
        _sync_ledger_to_github_if_configured(out)

    return len(rows)


def import_historical_csv(uploaded_file) -> tuple[int, int]:
    incoming = pd.read_csv(uploaded_file)
    existing = load_ledger()
    before = len(existing)
    merged = pd.concat([existing, incoming], ignore_index=True)
    for col in LEDGER_COLS:
        if col not in merged.columns:
            merged[col] = ""
    if "pick_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["pick_id"], keep="first")
    merged = merged[LEDGER_COLS]
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(LEDGER_FILE, index=False)
    return max(0, len(merged) - before), len(merged)


st.set_page_config(page_title="App, Risk Guardrail & Profit Analyser", layout="wide")
st.title("🧪 App, Risk Guardrail & Net Profit-Booking Analyser")
st.caption(
    "Auto-captures projected scanner picks in 5-minute IST intervals, evaluates Target 1 / Target 2 & Stop-Loss outcomes "
    "after NSE brokerage/STT/slippage costs, and flags underperforming modules. Not financial advice."
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


def _collect_all_projected_picks() -> dict[str, list[dict]]:
    """Merges static MODULE_PICKS with any live picks pushed into st.session_state by other pages."""
    combined = {
        mod: top_n_picks(picks, CAP_BY_MODULE.get(mod, len(picks)))
        for mod, picks in MODULE_PICKS.items()
    }
    session_live = st.session_state.get("live_scanner_picks")
    if isinstance(session_live, dict):
        for mod_name, pk_list in session_live.items():
            if isinstance(pk_list, list) and pk_list:
                combined[str(mod_name)] = pk_list
    return combined


def _is_nse_market_window(now_ist: datetime) -> bool:
    if now_ist.weekday() >= 5:
        return False
    mins = now_ist.hour * 60 + now_ist.minute
    return (9 * 60 + 15) <= mins <= (15 * 60 + 30)


def _run_5m_auto_capture(
    all_module_picks: dict[str, list[dict]],
    capture_all_modules: bool,
    selected_module: str,
    market_hours_only: bool,
    sync_github: bool,
) -> tuple[int, str]:
    now_i = datetime.now(ist)
    slot_5m = _bucket_5m_ist(now_i)

    if market_hours_only and not _is_nse_market_window(now_i):
        return 0, f"Outside NSE hours (9:15–15:30 IST) • Slot {slot_5m}"

    last_slot = st.session_state.get("last_5m_auto_slot")
    if last_slot == slot_5m:
        return 0, f"Slot {slot_5m} already captured"

    added_total = 0
    if capture_all_modules:
        for mod_name, pk_list in all_module_picks.items():
            added_total += record_picks(
                module_label=mod_name,
                picks=pk_list,
                source_mode="AUTO_5M",
                slot_override=slot_5m,
                sync_github=sync_github,
            )
    else:
        added_total = record_picks(
            module_label=selected_module,
            picks=all_module_picks.get(selected_module, []),
            source_mode="AUTO_5M",
            slot_override=slot_5m,
            sync_github=sync_github,
        )

    st.session_state["last_5m_auto_slot"] = slot_5m
    if added_total > 0:
        st.cache_data.clear()
    return added_total, f"Slot {slot_5m} (+{added_total} new)"


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
def evaluate_logged_ledger(ledger_df: pd.DataFrame, friction_pct: float, max_risk_rs: float) -> pd.DataFrame:
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
        sym = _normalize_symbol(str(r["symbol"]))
        side = str(r["side"]).upper()
        entry = float(r["entry_price"])
        sl = float(r["stop_loss"])
        t1 = float(r["target_1"])
        t2 = float(r.get("target_2", t1))
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
                "slot_5m_ist": r.get("slot_5m_ist", ""),
                "source_mode": r.get("source_mode", "MANUAL"),
                "session_date": r["session_date"],
                "iso_week": r["iso_week"],
                "module": r["module"],
                "symbol": sym.replace(".NS", ""),
                "side": side,
                "entry": round(entry, 2),
                "ltp": np.nan,
                "status": "No Price Feed",
                "t1_hit_flag": 0,
                "t2_hit_flag": 0,
                "sl_hit_flag": 0,
                "gross_r": np.nan,
                "net_r": np.nan,
                "est_net_pnl_rs": np.nan,
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
                "slot_5m_ist": r.get("slot_5m_ist", ""),
                "source_mode": r.get("source_mode", "MANUAL"),
                "session_date": r["session_date"],
                "iso_week": r["iso_week"],
                "module": r["module"],
                "symbol": sym.replace(".NS", ""),
                "side": side,
                "entry": round(entry, 2),
                "ltp": round(ltp, 2),
                "status": "⏳ Awaiting Next Session Bar",
                "t1_hit_flag": 0,
                "t2_hit_flag": 0,
                "sl_hit_flag": 0,
                "gross_r": 0.0,
                "net_r": 0.0,
                "est_net_pnl_rs": 0.0,
            })
            continue

        status = "⏳ Open / Unresolved"
        t1_flag = 0
        t2_flag = 0
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
                    t2_flag = 1
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
                    t2_flag = 1
                    gross_r = reward_t2_pts / risk_pts
                    break
                if float(bar["High"]) >= t1 and t1_flag == 0:
                    status = "✅ Target 1 Reached"
                    t1_flag = 1
                    gross_r = reward_t1_pts / risk_pts

        net_r = round(gross_r - cost_r, 2)
        est_net_pnl = round(net_r * max_risk_rs, 0)

        rows.append({
            "pick_id": r["pick_id"],
            "logged_at_ist": r["logged_at_ist"],
            "slot_5m_ist": r.get("slot_5m_ist", ""),
            "source_mode": r.get("source_mode", "MANUAL"),
            "session_date": r["session_date"],
            "iso_week": r["iso_week"],
            "module": r["module"],
            "symbol": sym.replace(".NS", ""),
            "side": side,
            "entry": round(entry, 2),
            "ltp": round(ltp, 2),
            "status": status,
            "t1_hit_flag": t1_flag,
            "t2_hit_flag": t2_flag,
            "sl_hit_flag": sl_flag,
            "gross_r": round(gross_r, 2),
            "net_r": net_r,
            "est_net_pnl_rs": est_net_pnl,
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
# 1. TOP PICKS BY VIEW + 5-MINUTE BACKEND AUTO-CAPTURE
# ---------------------------------------------------------
all_mod_picks = _collect_all_projected_picks()

st.subheader("⭐ Top Picks by View + 5-Minute Backend Auto-Logger")
ac1, ac2, ac3, ac4 = st.columns([1.5, 1.5, 1.5, 1.5])
auto_5m_enabled = ac1.toggle("⏱️ 5m Auto-Capture Active", value=True)
capture_all_mods = ac2.toggle("📡 Capture All Modules", value=True)
market_hrs_only = ac3.toggle("🕒 NSE Hours Only (9:15–15:30)", value=False)
sync_gh_enabled = ac4.toggle("☁️ Sync to GitHub Secrets", value=False)

chosen_module = st.selectbox("Select View / Scanner", list(all_mod_picks.keys()), index=0)
capped_picks = all_mod_picks[chosen_module]
top2_highlight = top_n_picks(capped_picks, 2)

if auto_5m_enabled:
    _, auto_msg = _run_5m_auto_capture(
        all_module_picks=all_mod_picks,
        capture_all_modules=capture_all_mods,
        selected_module=chosen_module,
        market_hours_only=market_hrs_only,
        sync_github=sync_gh_enabled,
    )
    st.caption(f"🤖 **5m Backend Engine Status:** {auto_msg}")

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

b1, b2, b3, _ = st.columns([1.4, 1.5, 1.6, 2.5])
with b1:
    if st.button("📌 Log Top 2 Now", type="primary", use_container_width=True):
        added = record_picks(chosen_module, top2_highlight, source_mode="MANUAL", sync_github=sync_gh_enabled)
        st.cache_data.clear()
        st.success(f"Saved {added} new Top 2 pick(s).")
with b2:
    if st.button(f"📥 Log All ({len(capped_picks)}) in View", use_container_width=True):
        added = record_picks(chosen_module, capped_picks, source_mode="MANUAL", sync_github=sync_gh_enabled)
        st.cache_data.clear()
        st.success(f"Saved {added} new pick(s) from '{chosen_module}'.")
with b3:
    if st.button("⚡ Force 5m Snapshot All Now", use_container_width=True):
        slot_now = _bucket_5m_ist(datetime.now(ist))
        total_snap = 0
        for m_name, p_list in all_mod_picks.items():
            total_snap += record_picks(
                m_name, p_list, source_mode="AUTO_5M_FORCE", slot_override=slot_now, sync_github=sync_gh_enabled
            )
        st.cache_data.clear()
        st.success(f"Captured {total_snap} pick(s) for 5m slot {slot_now}.")

st.dataframe(pd.DataFrame(capped_picks), use_container_width=True, hide_index=True)

st.markdown("---")

# ---------------------------------------------------------
# 2. FOREVER HISTORY VAULT + TARGET ACHIEVED & AUTO-PAUSE
# ---------------------------------------------------------
st.subheader("🗂️ Forever History Vault, Target-Hit Tracker & Auto-Pause Monitor")
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
    st.info("No picks in history yet. Enable 5m Auto-Capture or log picks above to start tracking Target hits & Net R.")
else:
    with st.spinner("Evaluating recorded history (Target 1, Target 2 & Stop-Loss) after NSE costs..."):
        hist_eval = evaluate_logged_ledger(ledger_df, nse_friction_pct, max_risk_rs)

    if not hist_eval.empty:
        f1, f2 = st.columns(2)
        mod_options = ["All Modules"] + sorted(hist_eval["module"].dropna().unique().tolist())
        sel_mod_eval = f1.selectbox("Filter Recorded Ledger by Scanner Module:", mod_options, index=0)

        src_options = ["All Sources"] + sorted(hist_eval["source_mode"].dropna().unique().tolist())
        sel_src_eval = f2.selectbox("Filter by Capture Source:", src_options, index=0)

        eval_view = hist_eval.copy()
        if sel_mod_eval != "All Modules":
            eval_view = eval_view[eval_view["module"] == sel_mod_eval]
        if sel_src_eval != "All Sources":
            eval_view = eval_view[eval_view["source_mode"] == sel_src_eval]
        eval_view = eval_view.reset_index(drop=True)

        tot_logged = len(eval_view)
        t1_cnt = int(eval_view["t1_hit_flag"].sum())
        t2_cnt = int(eval_view["t2_hit_flag"].sum())
        sl_cnt = int(eval_view["sl_hit_flag"].sum())
        avg_gross_r = float(eval_view["gross_r"].dropna().mean()) if not eval_view["gross_r"].dropna().empty else 0.0
        avg_net_r = float(eval_view["net_r"].dropna().mean()) if not eval_view["net_r"].dropna().empty else 0.0
        sum_net_pnl = float(eval_view["est_net_pnl_rs"].dropna().sum()) if not eval_view["est_net_pnl_rs"].dropna().empty else 0.0

        lk1, lk2, lk3, lk4, lk5, lk6 = st.columns(6)
        lk1.metric("Tracked Picks", f"{tot_logged}")
        lk2.metric("Target 1 Hit Rate", f"{(t1_cnt / max(tot_logged, 1)) * 100:.1f}%", f"{t1_cnt} T1 ({t2_cnt} T2)")
        lk3.metric("Stop-Loss Touched", f"{(sl_cnt / max(tot_logged, 1)) * 100:.1f}%", f"{sl_cnt} SL", delta_color="inverse")
        lk4.metric("Avg Gross R", f"{avg_gross_r:+.2f}R")
        lk5.metric("Avg Net R", f"{avg_net_r:+.2f}R")
        lk6.metric("Est. Net P&L", f"₹{sum_net_pnl:+,.0f}")

        targets_achieved_df = eval_view[eval_view["t1_hit_flag"] == 1]
        st.markdown("**🎯 Targets Achieved Log (Target 1 / Target 2 Hits)**")
        if targets_achieved_df.empty:
            st.caption("No targets reached yet in the filtered window.")
        else:
            st.dataframe(
                targets_achieved_df[["slot_5m_ist", "source_mode", "module", "symbol", "side", "entry", "ltp", "status", "net_r", "est_net_pnl_rs"]]
                .tail(20)
                .style.apply(_color_outcome_row, axis=1)
                .format({
                    "entry": "₹{:,.2f}",
                    "ltp": "₹{:,.2f}",
                    "net_r": "{:+.2f}R",
                    "est_net_pnl_rs": "₹{:+,.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

        eval_display_cols = [
            "logged_at_ist",
            "slot_5m_ist",
            "source_mode",
            "iso_week",
            "module",
            "symbol",
            "side",
            "entry",
            "ltp",
            "status",
            "gross_r",
            "net_r",
            "est_net_pnl_rs",
        ]
        st.dataframe(
            eval_view[eval_display_cols]
            .tail(40)
            .style.apply(_color_outcome_row, axis=1)
            .format({
                "entry": "₹{:,.2f}",
                "ltp": "₹{:,.2f}",
                "gross_r": "{:+.2f}R",
                "net_r": "{:+.2f}R",
                "est_net_pnl_rs": "₹{:+,.0f}",
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
                T2_Hits=("t2_hit_flag", "sum"),
                SL_Hits=("sl_hit_flag", "sum"),
                Avg_Gross_R=("gross_r", "mean"),
                Avg_Net_R=("net_r", "mean"),
                Est_Net_PnL_Rs=("est_net_pnl_rs", "sum"),
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
                "Est_Net_PnL_Rs": "₹{:+,.0f}",
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
                Est_Net_PnL_Rs=("est_net_pnl_rs", "sum"),
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
                "Est_Net_PnL_Rs": "₹{:+,.0f}",
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
