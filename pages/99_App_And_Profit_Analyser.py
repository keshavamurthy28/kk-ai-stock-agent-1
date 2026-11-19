import ast
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from utils.pick_ledger import (
    import_historical_csv,
    load_ledger,
    record_picks,
    top_n_picks,
)

st.set_page_config(page_title="App & Profit-Booking Analyser", layout="wide")
st.title("🧪 Streamlit App, GitHub Code & Long-Term Profit Analyser")
st.caption(
    "Tracks every logged pick forever (with CSV import/export), evaluates Target-1 vs. Stop-Loss outcomes, "
    "and shows how performance evolves over time. Past hit rates do not guarantee future profits—always use a stop-loss."
)

AUDIT_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "AXISBANK.NS", "LT.NS",
    "BAJFINANCE.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS",
]

MODULE_PICKS = {
    "Night Before -> Morning Top 2": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "Morning Top #1"},
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "Morning Top #2"},
        {"symbol": "INFY.NS", "side": "BUY", "entry": 1090.6, "sl": 1080.0, "t1": 1104.0, "t2": 1115.0, "notes": "Morning Watch #3"},
    ],
    "Matched Super Signal (Top 2 Highlighted)": [
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Matched Super #1"},
        {"symbol": "BHARTIARTL.NS", "side": "BUY", "entry": 2149.8, "sl": 2130.0, "t1": 2175.0, "t2": 2196.0, "notes": "Matched Super #2"},
        {"symbol": "ITC.NS", "side": "BUY", "entry": 301.15, "sl": 298.0, "t1": 305.0, "t2": 308.0, "notes": "Matched Super #3"},
    ],
    "MUDRA Top 5": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "MUDRA #1"},
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "MUDRA #2"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "MUDRA #3"},
        {"symbol": "LT.NS", "side": "BUY", "entry": 4205.7, "sl": 4170.0, "t1": 4252.0, "t2": 4290.0, "notes": "MUDRA #4"},
        {"symbol": "AXISBANK.NS", "side": "BUY", "entry": 1377.5, "sl": 1365.0, "t1": 1394.0, "t2": 1408.0, "notes": "MUDRA #5"},
        {"symbol": "ITC.NS", "side": "BUY", "entry": 301.15, "sl": 298.0, "t1": 305.0, "t2": 308.0, "notes": "MUDRA #6 (trimmed to Top 5)"},
    ],
    "PRIME Top 3": [
        {"symbol": "ICICIBANK.NS", "side": "BUY", "entry": 1606.6, "sl": 1592.0, "t1": 1625.0, "t2": 1640.0, "notes": "PRIME #1"},
        {"symbol": "LT.NS", "side": "BUY", "entry": 4205.7, "sl": 4170.0, "t1": 4252.0, "t2": 4290.0, "notes": "PRIME #2"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "PRIME #3"},
        {"symbol": "INFY.NS", "side": "BUY", "entry": 1090.6, "sl": 1080.0, "t1": 1104.0, "t2": 1115.0, "notes": "PRIME #4 (trimmed to Top 3)"},
    ],
    "Daily Top 2": [
        {"symbol": "RELIANCE.NS", "side": "BUY", "entry": 1376.6, "sl": 1364.0, "t1": 1393.0, "t2": 1406.0, "notes": "Daily Top #1"},
        {"symbol": "AXISBANK.NS", "side": "BUY", "entry": 1377.5, "sl": 1365.0, "t1": 1394.0, "t2": 1408.0, "notes": "Daily Top #2"},
    ],
    "Bearish Top 2": [
        {"symbol": "TCS.NS", "side": "SHORT", "entry": 2347.5, "sl": 2368.0, "t1": 2320.0, "t2": 2298.0, "notes": "Bearish Top #1"},
        {"symbol": "HDFCBANK.NS", "side": "SHORT", "entry": 821.0, "sl": 828.5, "t1": 811.0, "t2": 803.0, "notes": "Bearish Top #2"},
    ],
    "Smart Money Top 2 (Green & Red)": [
        {"symbol": "BHARTIARTL.NS", "side": "BUY", "entry": 2149.8, "sl": 2130.0, "t1": 2175.0, "t2": 2196.0, "notes": "Smart Money Green #1"},
        {"symbol": "SBIN.NS", "side": "BUY", "entry": 1156.2, "sl": 1145.0, "t1": 1170.0, "t2": 1182.0, "notes": "Smart Money Green #2"},
        {"symbol": "TCS.NS", "side": "SHORT", "entry": 2347.5, "sl": 2368.0, "t1": 2320.0, "t2": 2298.0, "notes": "Smart Money Red #1"},
        {"symbol": "HDFCBANK.NS", "side": "SHORT", "entry": 821.0, "sl": 828.5, "t1": 811.0, "t2": 803.0, "notes": "Smart Money Red #2"},
    ],
}

CAP_BY_MODULE = {
    "Night Before -> Morning Top 2": 2,
    "Matched Super Signal (Top 2 Highlighted)": 2,
    "MUDRA Top 5": 5,
    "PRIME Top 3": 3,
    "Daily Top 2": 2,
    "Bearish Top 2": 2,
    "Smart Money Top 2 (Green & Red)": 4,
}


def audit_repo_files() -> pd.DataFrame:
    repo_root = Path(".")
    py_files = sorted(
        [p for p in repo_root.rglob("*.py") if ".git" not in p.parts and "__pycache__" not in p.parts]
    )
    findings = []
    for fpath in py_files:
        try:
            src = fpath.read_text(encoding="utf-8", errors="replace")
            ast.parse(src)
            syntax_ok = True
        except SyntaxError as exc:
            findings.append({
                "File": str(fpath),
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
            "File": str(fpath),
            "Syntax": "✅ OK" if syntax_ok else "❌",
            "Lines": len(src.splitlines()),
            "Cached": "✅ Yes" if has_cache else "⚠️ No",
            "Uses_yfinance": "✅ Yes" if uses_yf else "No",
            "NSE_Direct_Call": "⚠️ Yes" if nse_direct else "No",
            "Audit_Notes": " | ".join(notes),
        })
    return pd.DataFrame(findings)


@st.cache_data(ttl=120)
def run_completeness_and_target_audit(t1_p: float, sl_p: float, min_move_p: float):
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
                        r_val = round(t1_p / max(sl_p, 0.01), 2)
                    elif hit_sl and not hit_t1:
                        outcome = "Stop_Loss_Hit"
                        r_val = -1.0
                    elif hit_t1 and hit_sl:
                        outcome = "Both_In_Window"
                        r_val = 0.0
                    else:
                        exit_p = closes[i + 6]
                        r_val = round((exit_p - entry) / max(entry - stop, 1e-6), 2)
                        outcome = "Time_Exit"

                    sim_trades.append({
                        "Stock": clean,
                        "Outcome": outcome,
                        "R_Multiple": r_val,
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
def evaluate_logged_ledger(ledger_df: pd.DataFrame) -> pd.DataFrame:
    if ledger_df.empty:
        return pd.DataFrame()

    symbols = sorted(ledger_df["symbol"].dropna().astype(str).unique().tolist())
    try:
        raw_5m = yf.download(
            symbols,
            period="5d",
            interval="5m",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        raw_5m = pd.DataFrame()

    rows = []
    for _, r in ledger_df.iterrows():
        sym = str(r["symbol"])
        side = str(r["side"]).upper()
        entry = float(r["entry_price"])
        sl = float(r["stop_loss"])
        t1 = float(r["target_1"])
        t2 = float(r["target_2"])

        sub = pd.DataFrame()
        if not raw_5m.empty:
            if isinstance(raw_5m.columns, pd.MultiIndex):
                lvl0 = raw_5m.columns.get_level_values(0)
                lvl1 = raw_5m.columns.get_level_values(1)
                if sym in lvl0:
                    sub = raw_5m[sym].dropna(how="all")
                elif sym in lvl1:
                    sub = raw_5m.xs(sym, axis=1, level=1).dropna(how="all")
            elif len(symbols) == 1:
                sub = raw_5m.dropna(how="all")

        if sub.empty or not {"High", "Low", "Close"}.issubset(sub.columns):
            rows.append({
                "pick_id": r["pick_id"],
                "logged_at_ist": r["logged_at_ist"],
                "session_date": r["session_date"],
                "iso_week": r["iso_week"],
                "module": r["module"],
                "symbol": sym,
                "side": side,
                "ltp": np.nan,
                "status": "No Price Feed",
                "t1_hit_flag": 0,
                "r_est": np.nan,
            })
            continue

        ltp = float(sub["Close"].iloc[-1])
        max_h = float(sub["High"].max())
        min_l = float(sub["Low"].min())

        if side == "SHORT":
            hit_t1 = min_l <= t1
            hit_t2 = min_l <= t2
            hit_sl = max_h >= sl
            risk_pts = max(sl - entry, 1e-6)
            reward_t1_pts = max(entry - t1, 1e-6)
            move_pts = entry - ltp
        else:
            hit_t1 = max_h >= t1
            hit_t2 = max_h >= t2
            hit_sl = min_l <= sl
            risk_pts = max(entry - sl, 1e-6)
            reward_t1_pts = max(t1 - entry, 1e-6)
            move_pts = ltp - entry

        if hit_t2:
            status = "✅ Target 2 Reached"
            t1_flag = 1
            r_est = round(reward_t1_pts / risk_pts, 2)
        elif hit_t1:
            status = "✅ Target 1 Reached"
            t1_flag = 1
            r_est = round(reward_t1_pts / risk_pts, 2)
        elif hit_sl:
            status = "🛑 Stop-Loss Touched"
            t1_flag = 0
            r_est = -1.0
        else:
            status = "⏳ Open / Unresolved"
            t1_flag = 0
            r_est = round(move_pts / risk_pts, 2)

        rows.append({
            "pick_id": r["pick_id"],
            "logged_at_ist": r["logged_at_ist"],
            "session_date": r["session_date"],
            "iso_week": r["iso_week"],
            "module": r["module"],
            "symbol": sym,
            "side": side,
            "ltp": round(ltp, 2),
            "status": status,
            "t1_hit_flag": t1_flag,
            "r_est": r_est,
        })

    return pd.DataFrame(rows)


# Top Controls
c1, c2, c3, c4 = st.columns([1.4, 1.4, 1.4, 1.2])
t1_pct = c1.number_input("🎯 Target 1 Profit (%)", min_value=0.3, max_value=5.0, value=1.2, step=0.1)
sl_pct = c2.number_input("🛑 Stop-Loss Risk (%)", min_value=0.3, max_value=5.0, value=0.8, step=0.1)
min_chg_pct = c3.number_input("📈 Min Intraday Move (%)", min_value=0.0, max_value=3.0, value=0.25, step=0.05)
with c4:
    st.write("")
    if st.button("🔄 Refresh All Checks", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Section A: Top Picks Selector, Separate Top 2 Highlight & Forever Ledger Logging
st.subheader("⭐ Top Picks by View (Top 2 Highlighted + Exact Top-N Caps)")
chosen_module = st.selectbox("Select View / Scanner", list(MODULE_PICKS.keys()), index=0)
capped_picks = top_n_picks(MODULE_PICKS[chosen_module], CAP_BY_MODULE[chosen_module])
top2_highlight = top_n_picks(capped_picks, 2)

st.markdown("**Top 2 Highlighted Picks (Shown Separately on Top)**")
t2_cols = st.columns(max(1, len(top2_highlight)))
for idx, pk in enumerate(top2_highlight):
    with t2_cols[idx]:
        st.metric(
            label=f"#{idx + 1} {pk['symbol'].replace('.NS', '')} ({pk['side']})",
            value=f"₹{pk['entry']:,.2f}",
            delta=f"T1 ₹{pk['t1']:,.2f} | SL ₹{pk['sl']:,.2f}",
        )
        st.caption(pk.get("notes", ""))

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

# Section B: Forever History Import / Export & Improvement Over Time
st.subheader("🗂️ Forever History Vault (Import Past CSVs, Export Backup & Track Improvement)")
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
    st.info("No picks in history yet. Log picks above or import a historical CSV.")
else:
    st.dataframe(ledger_df.tail(25), use_container_width=True, hide_index=True)

    with st.spinner("Evaluating recorded history & tracking week-over-week improvement..."):
        hist_eval = evaluate_logged_ledger(ledger_df)

    if not hist_eval.empty:
        st.subheader("📈 Improvement Over Time (By Week & Scanner Module)")
        weekly_perf = (
            hist_eval.groupby("iso_week", as_index=False)
            .agg(
                Total_Picks=("pick_id", "count"),
                T1_Hits=("t1_hit_flag", "sum"),
                Avg_R=("r_est", "mean"),
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
                "Avg_R": "{:+.2f}R",
            }),
            use_container_width=True,
            hide_index=True,
        )

        mod_perf = (
            hist_eval.groupby("module", as_index=False)
            .agg(
                Total_Picks=("pick_id", "count"),
                T1_Hits=("t1_hit_flag", "sum"),
                Avg_R=("r_est", "mean"),
            )
        )
        mod_perf["T1_Hit_Rate_%"] = np.where(
            mod_perf["Total_Picks"] > 0,
            (mod_perf["T1_Hits"] / mod_perf["Total_Picks"]) * 100.0,
            0.0,
        )
        st.dataframe(
            mod_perf.style.format({
                "T1_Hit_Rate_%": "{:.1f}%",
                "Avg_R": "{:+.2f}R",
            }),
            use_container_width=True,
            hide_index=True,
        )

# Section C: Repository Health, Live Data Completeness & Sample Target Audit
st.subheader("1️⃣ GitHub Repository & Page Health Audit")
df_repo = audit_repo_files()
if not df_repo.empty:
    st.dataframe(df_repo, use_container_width=True, hide_index=True)

with st.spinner("Checking live data completeness & simulating Target-1 vs. Stop-Loss windows..."):
    df_comp, df_sim = run_completeness_and_target_audit(t1_pct, sl_pct, min_chg_pct)

st.subheader("2️⃣ Live Market Data Completeness Check")
if not df_comp.empty:
    ok_cnt = int((df_comp["Status"] == "✅ Complete").sum())
    st.metric("Complete Feeds", f"{ok_cnt} / {len(df_comp)} Stocks")
    st.dataframe(
        df_comp.style.format({"Latest_Close": "₹{:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("3️⃣ Historical Target-1 vs. Stop-Loss Outcome Audit (Sample 5m Windows)")
if not df_sim.empty:
    tot_s = len(df_sim)
    t1_h = int((df_sim["Outcome"] == "Target_1_Hit").sum())
    sl_h = int((df_sim["Outcome"] == "Stop_Loss_Hit").sum())
    other_h = int((df_sim["Outcome"].isin(["Time_Exit", "Both_In_Window"])).sum())
    avg_r_all = float(df_sim["R_Multiple"].mean())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Sampled Setups", f"{tot_s}")
    k2.metric("Target 1 Hits", f"{t1_h} ({(t1_h / tot_s) * 100:.1f}%)")
    k3.metric("Stop-Loss Hits", f"{sl_h} ({(sl_h / tot_s) * 100:.1f}%)")
    k4.metric("Time / Mixed Exits", f"{other_h}")
    k5.metric("Avg R-Multiple", f"{avg_r_all:+.2f}R")
