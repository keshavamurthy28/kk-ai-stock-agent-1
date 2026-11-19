import ast
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="App & Profit-Booking Analyser", layout="wide")
st.title("🧪 Streamlit App, GitHub Code & Profit-Booking Analyser")
st.caption(
    "Audits repository page health, live data completeness, and historical Target-1 vs. Stop-Loss outcomes. "
    "Past hit rates do not guarantee future profits—always verify live quotes and use a stop-loss."
)

AUDIT_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "AXISBANK.NS", "LT.NS",
    "BAJFINANCE.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS",
]

c1, c2, c3, c4 = st.columns([1.4, 1.4, 1.4, 1.2])
t1_pct = c1.number_input("🎯 Target 1 Profit (%)", min_value=0.3, max_value=5.0, value=1.2, step=0.1)
sl_pct = c2.number_input("🛑 Stop-Loss Risk (%)", min_value=0.3, max_value=5.0, value=0.8, step=0.1)
min_chg_pct = c3.number_input("📈 Min Intraday Move (%)", min_value=0.0, max_value=3.0, value=0.25, step=0.05)
with c4:
    st.write("")
    if st.button("🔄 Run Full Audit", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def audit_repo_files():
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
            src = ""
            syntax_ok = False
            findings.append({
                "File": str(fpath),
                "Syntax": "❌ Error",
                "Lines": 0,
                "Cache_TTL": "N/A",
                "Uses_yfinance": "Unknown",
                "NSE_Scrape_Risk": "Check",
                "Notes": f"SyntaxError line {exc.lineno}: {exc.msg}",
            })
            continue

        lines = len(src.splitlines())
        uses_yf = "yfinance" in src or "yf." in src
        has_cache = "@st.cache_data" in src or "@st.cache_resource" in src
        has_try = "try:" in src and "except" in src
        nse_direct = "nseindia.com" in src.lower()

        notes = []
        if uses_yf and not has_cache:
            notes.append("No @st.cache_data found (may slow down or hit rate limits)")
        if uses_yf and not has_try:
            notes.append("Missing try/except around data fetch")
        if nse_direct:
            notes.append("Direct NSE endpoint call (may block/fallback on cloud)")
        if not notes:
            notes.append("Clean structure & guarded data handling")

        findings.append({
            "File": str(fpath),
            "Syntax": "✅ OK" if syntax_ok else "❌",
            "Lines": lines,
            "Cached": "✅ Yes" if has_cache else "⚠️ No",
            "Uses_yfinance": "✅ Yes" if uses_yf else "No",
            "NSE_Direct_Call": "⚠️ Yes" if nse_direct else "No",
            "Audit_Notes": " | ".join(notes),
        })
    return pd.DataFrame(findings)


@st.cache_data(ttl=120)
def run_completeness_and_target_audit(t1_p, sl_p, min_move_p):
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

            df.index = pd.to_datetime(df.index)
            if df.index.tz is not None:
                df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

            null_cells = int(df[["Open", "High", "Low", "Close"]].isna().sum().sum())
            last_close = float(df["Close"].iloc[-1])
            completeness_rows.append({
                "Stock": clean,
                "Status": "✅ Complete" if null_cells == 0 and last_close > 0 else "⚠️ Check",
                "Bars_5m": int(len(df)),
                "Latest_Close": round(last_close, 2),
                "Null_Cells": null_cells,
            })

            # Evaluate historical candidate signals across available 5m bars (excluding final 6 bars)
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
                        r_val = round(((exit_p - entry) / max(entry - stop, 1e-6)), 2)
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


st.subheader("1️⃣ GitHub Repository & Page Health Audit")
df_repo = audit_repo_files()
if not df_repo.empty:
    st.dataframe(df_repo, use_container_width=True, hide_index=True)
else:
    st.info("No Python files detected in the current working directory.")

with st.spinner("Checking live data completeness & simulating historical Target-1 vs. Stop-Loss outcomes..."):
    df_comp, df_sim = run_completeness_and_target_audit(t1_pct, sl_pct, min_chg_pct)

st.subheader("2️⃣ Live Market Data Completeness Check")
if not df_comp.empty:
    ok_count = int((df_comp["Status"] == "✅ Complete").sum())
    st.metric("Complete Feeds", f"{ok_count} / {len(df_comp)} Stocks")
    st.dataframe(
        df_comp.style.format({"Latest_Close": "₹{:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("3️⃣ Historical Target-1 vs. Stop-Loss Outcome Audit (Sample 5m Windows)")
st.caption(
    "This checks how often candidate momentum bars reached Target 1 vs. Stop-Loss over the next six 5m bars in recent history. "
    "Treat this as a diagnostic check—not a promise of future profit."
)
if df_sim.empty:
    st.info("No historical candidate setups matched the current threshold in the sampled window.")
else:
    total_s = len(df_sim)
    t1_hits = int((df_sim["Outcome"] == "Target_1_Hit").sum())
    sl_hits = int((df_sim["Outcome"] == "Stop_Loss_Hit").sum())
    both_hits = int((df_sim["Outcome"] == "Both_In_Window").sum())
    time_exits = int((df_sim["Outcome"] == "Time_Exit").sum())
    avg_r = float(df_sim["R_Multiple"].mean())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Sampled Setups", f"{total_s}")
    k2.metric("Target 1 Hits", f"{t1_hits} ({(t1_hits/total_s)*100:.1f}%)")
    k3.metric("Stop-Loss Hits", f"{sl_hits} ({(sl_hits/total_s)*100:.1f}%)")
    k4.metric("Time / Mixed Exits", f"{time_exits + both_hits}")
    k5.metric("Avg R-Multiple", f"{avg_r:+.2f}R")
