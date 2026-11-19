from datetime import datetime
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz

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
except ModuleNotFoundError:
    IST = pytz.timezone("Asia/Kolkata")
    LEDGER_DIR = REPO_ROOT / "data_ledger"
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

    def top_n_picks(picks: list[dict], n: int) -> list[dict]:
        return list(picks[: max(0, int(n))])

    def load_ledger() -> pd.DataFrame:
        if LEDGER_FILE.exists():
            try:
                df = pd.read_csv(LEDGER_FILE)
                for col in LEDGER_COLUMNS:
                    if col not in df.columns:
                        df[col] = np.nan
                return df[LEDGER_COLUMNS].drop_duplicates(subset=["pick_id"], keep="first").reset_index(drop=True)
            except Exception:
                pass
        return pd.DataFrame(columns=LEDGER_COLUMNS)

    def _save_fallback(df: pd.DataFrame) -> pd.DataFrame:
        clean = df[LEDGER_COLUMNS].drop_duplicates(subset=["pick_id"], keep="first").reset_index(drop=True)
        clean.to_csv(LEDGER_FILE, index=False)
        return clean

    def record_picks(module_name: str, picks: list[dict], dedupe_within_minute: bool = True) -> int:
        if not picks:
            return 0
        now_ist = datetime.now(IST)
        ts_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        s_date = now_ist.strftime("%Y-%m-%d")
        i_week = f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}"
        existing = load_ledger()
        seen = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()
        rows = []
        for p in picks:
            sym = str(p.get("symbol", "")).strip().upper()
            if not sym:
                continue
            if not (sym.endswith(".NS") or sym.endswith(".BO") or sym.startswith("^")):
                sym = f"{sym}.NS"
            side = str(p.get("side", "BUY")).strip().upper()
            entry = float(p.get("entry", p.get("entry_price", 0.0)))
            sl = float(p.get("sl", p.get("stop_loss", 0.0)))
            t1 = float(p.get("t1", p.get("target_1", 0.0)))
            t2 = float(p.get("t2", p.get("target_2", 0.0)))
            bucket = now_ist.strftime("%Y-%m-%d %H:%M") if dedupe_within_minute else ts_str
            pid = hashlib.sha1(f"{bucket}|{module_name}|{sym}|{side}|{entry:.4f}".encode("utf-8")).hexdigest()[:12]
            if pid in seen:
                continue
            seen.add(pid)
            rows.append({
                "pick_id": pid,
                "logged_at_ist": ts_str,
                "session_date": s_date,
                "iso_week": i_week,
                "module": module_name,
                "symbol": sym,
                "side": side,
                "entry_price": round(entry, 2),
                "stop_loss": round(sl, 2),
                "target_1": round(t1, 2),
                "target_2": round(t2, 2),
                "notes": str(p.get("notes", "")).strip(),
            })
        if not rows:
            return 0
        _save_fallback(pd.concat([existing, pd.DataFrame(rows)], ignore_index=True))
        return len(rows)

    def import_historical_csv(uploaded_file) -> tuple[int, int]:
        incoming = pd.read_csv(uploaded_file)
        if incoming.empty:
            return 0, len(load_ledger())
        now_ist = datetime.now(IST)
        existing = load_ledger()
        before = len(existing)
        rows = []
        for _, r in incoming.iterrows():
            ts_val = str(r.get("logged_at_ist", now_ist.strftime("%Y-%m-%d %H:%M:%S IST")))
            sym_val = str(r.get("symbol", "")).strip().upper()
            if not sym_val:
                continue
            if not (sym_val.endswith(".NS") or sym_val.endswith(".BO") or sym_val.startswith("^")):
                sym_val = f"{sym_val}.NS"
            side_val = str(r.get("side", "BUY")).strip().upper()
            entry_val = float(r.get("entry_price", r.get("entry", 0.0)))
            pid = str(r.get("pick_id", "")).strip()
            if not pid or pid == "nan":
                pid = hashlib.sha1(f"{ts_val}|import|{sym_val}|{side_val}|{entry_val:.4f}".encode("utf-8")).hexdigest()[:12]
            rows.append({
                "pick_id": pid,
                "logged_at_ist": ts_val,
                "session_date": str(r.get("session_date", now_ist.strftime("%Y-%m-%d"))),
                "iso_week": str(r.get("iso_week", f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}")),
                "module": str(r.get("module", "Imported Historical Pick")),
                "symbol": sym_val,
                "side": side_val,
                "entry_price": round(entry_val, 2),
                "stop_loss": round(float(r.get("stop_loss", r.get("sl", 0.0))), 2),
                "target_1": round(float(r.get("target_1", r.get("t1", 0.0))), 2),
                "target_2": round(float(r.get("target_2", r.get("t2", 0.0))), 2),
                "notes": str(r.get("notes", "")),
            })
        merged = _save_fallback(pd.concat([existing, pd.DataFrame(rows)], ignore_index=True))
        return max(0, len(merged) - before), len(merged)
