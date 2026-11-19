from datetime import datetime
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")
LEDGER_DIR = Path("data_ledger")
LEDGER_DIR.mkdir(parents=True, exist_ok=True)
LEDGER_FILE = LEDGER_DIR / "pick_click_ledger.csv"

LEDGER_COLUMNS = [
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


def _normalize_symbol(sym: str) -> str:
    s = str(sym).strip().upper()
    if not s:
        return ""
    if s.endswith(".NS") or s.endswith(".BO") or s.startswith("^"):
        return s
    return f"{s}.NS"


def _make_pick_id(ts_str: str, module: str, symbol: str, side: str, entry: float) -> str:
    raw = f"{ts_str}|{module}|{symbol}|{side}|{entry:.4f}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def top_n_picks(picks: list[dict], n: int) -> list[dict]:
    """Enforces exact Top N selection (e.g., Top 2, Top 3, Top 5)."""
    return list(picks[: max(0, int(n))])


def load_ledger() -> pd.DataFrame:
    if LEDGER_FILE.exists():
        try:
            df = pd.read_csv(LEDGER_FILE)
            for col in LEDGER_COLUMNS:
                if col not in df.columns:
                    df[col] = np.nan
            df = df[LEDGER_COLUMNS].drop_duplicates(subset=["pick_id"], keep="first")
            return df.reset_index(drop=True)
        except Exception:
            pass
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def save_ledger(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    for col in LEDGER_COLUMNS:
        if col not in clean.columns:
            clean[col] = np.nan
    clean = clean[LEDGER_COLUMNS].drop_duplicates(subset=["pick_id"], keep="first").reset_index(drop=True)
    clean.to_csv(LEDGER_FILE, index=False)
    return clean


def record_picks(module_name: str, picks: list[dict], dedupe_within_minute: bool = True) -> int:
    """Appends picks permanently to the ledger with IST date & ISO week tags."""
    if not picks:
        return 0

    now_ist = datetime.now(IST)
    ts_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    session_date = now_ist.strftime("%Y-%m-%d")
    iso_week = f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}"

    existing = load_ledger()
    existing_ids = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()

    new_rows = []
    for p in picks:
        sym = _normalize_symbol(p.get("symbol", ""))
        if not sym:
            continue
        side = str(p.get("side", "BUY")).strip().upper()
        entry = float(p.get("entry", p.get("entry_price", 0.0)))
        sl = float(p.get("sl", p.get("stop_loss", 0.0)))
        t1 = float(p.get("t1", p.get("target_1", 0.0)))
        t2 = float(p.get("t2", p.get("target_2", 0.0)))
        notes = str(p.get("notes", "")).strip()

        bucket_ts = now_ist.strftime("%Y-%m-%d %H:%M") if dedupe_within_minute else ts_str
        pid = _make_pick_id(bucket_ts, module_name, sym, side, entry)
        if pid in existing_ids:
            continue
        existing_ids.add(pid)

        new_rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_str,
            "session_date": session_date,
            "iso_week": iso_week,
            "module": module_name,
            "symbol": sym,
            "side": side,
            "entry_price": round(entry, 2),
            "stop_loss": round(sl, 2),
            "target_1": round(t1, 2),
            "target_2": round(t2, 2),
            "notes": notes,
        })

    if not new_rows:
        return 0

    combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
    save_ledger(combined)
    return len(new_rows)


def import_historical_csv(uploaded_file) -> tuple[int, int]:
    """Merges an uploaded historical CSV into the permanent ledger without losing existing rows."""
    incoming = pd.read_csv(uploaded_file)
    if incoming.empty:
        return 0, len(load_ledger())

    now_ist = datetime.now(IST)
    default_ts = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    default_date = now_ist.strftime("%Y-%m-%d")
    default_week = f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}"

    rows = []
    for _, r in incoming.iterrows():
        ts_val = str(r.get("logged_at_ist", default_ts))
        dt_parsed = pd.to_datetime(ts_val.replace(" IST", ""), errors="coerce")
        if pd.notna(dt_parsed):
            s_date = dt_parsed.strftime("%Y-%m-%d")
            i_week = f"{dt_parsed.isocalendar().year}-W{dt_parsed.isocalendar().week:02d}"
        else:
            s_date = str(r.get("session_date", default_date))
            i_week = str(r.get("iso_week", default_week))

        mod_val = str(r.get("module", "Imported Historical Pick"))
        sym_val = _normalize_symbol(r.get("symbol", ""))
        if not sym_val:
            continue
        side_val = str(r.get("side", "BUY")).strip().upper()
        entry_val = float(r.get("entry_price", r.get("entry", 0.0)))
        sl_val = float(r.get("stop_loss", r.get("sl", 0.0)))
        t1_val = float(r.get("target_1", r.get("t1", 0.0)))
        t2_val = float(r.get("target_2", r.get("t2", 0.0)))
        notes_val = str(r.get("notes", ""))

        pid = str(r.get("pick_id", "")).strip()
        if not pid or pid == "nan":
            pid = _make_pick_id(ts_val, mod_val, sym_val, side_val, entry_val)

        rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_val,
            "session_date": s_date,
            "iso_week": i_week,
            "module": mod_val,
            "symbol": sym_val,
            "side": side_val,
            "entry_price": round(entry_val, 2),
            "stop_loss": round(sl_val, 2),
            "target_1": round(t1_val, 2),
            "target_2": round(t2_val, 2),
            "notes": notes_val,
        })

    existing = load_ledger()
    before_cnt = len(existing)
    merged = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    merged = save_ledger(merged)
    added_cnt = max(0, len(merged) - before_cnt)
    return added_cnt, len(merged)
