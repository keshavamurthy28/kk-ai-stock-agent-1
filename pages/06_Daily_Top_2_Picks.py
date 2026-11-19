from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Same-Day Intraday & Long-Term Watchlist",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)
is_late_session = is_market_open and now_ist.time() >= dt_time(14, 45)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_top2_to_ledger(picks: list[dict]) -> int:
    if not picks:
        return 0
    if callable(_ledger_record_picks):
        try:
            return int(_ledger_record_picks("Daily Top 2", picks))
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
        pid = hashlib.sha1(f"{bucket}|Daily Top 2|{sym}|{side}|{entry:.4f}".encode("utf-8")).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)
        new_rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_str,
            "session_date": s_date,
            "iso_week": i_week,
            "module": "Daily Top 2",
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


st.title("⚡ Pure Same-Day Intraday Setups + Separate Long-Term Table")
st.markdown(
    "**Same-Day Intraday Focus:** Designed for **buy today & exit today (before 3:30 PM IST)** "
    "with disciplined profit-booking targets and hard stop-losses—paired with a **separate table** "
    "for longer-term stocks so you don't mix timeframes."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

if is_late_session:
    st.warning(
        "⏰ **Late Session Reminder (After 2:45 PM IST):** Avoid chasing fresh intraday entries late in the day and review open intraday trades before **3:30 PM IST**."
    )

with st.expander("📘 Beginner Rulebook: Same-Day Profit Booking & Risk Guardrails", expanded=True):
    st.markdown(
        "- **No 'Pakka' Guarantee:** Even strong setups can reverse in live trading—never treat any scanner signal as guaranteed profit.\n"
        "- **Same-Day Exit Rule:** For **Intraday (Buy Today / Sell Today)**, look to book profit around **Target 1** first, honor your **Stop-Loss**, and exit before **3:30 PM IST**.\n"
        "- **Separate Long-Term Table:** Use the **Long-Term Watchlist** table below only for multi-day/positional study—not for same-day scalping. Not financial advice."
    )

UNIVERSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "SBIN.NS",
    "ITC.NS",
    "BHARTIARTL.NS",
    "AXISBANK.NS",
    "LT.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "TATASTEEL.NS",
    "NTPC.NS",
    "ONGC.NS",
    "VEDL.NS",
    "HINDALCO.NS",
]

col_f1, col_f2, col_f3, col_r1 = st.columns([2.2, 1.3, 1.5, 1.4])
with col_f1:
    intraday_bias = st.selectbox(
        "🎯 Same-Day Intraday Direction:",
        [
            "Bullish Intraday (Buy Today / Sell Today)",
            "Bearish Intraday (Short / Cover Today)",
        ],
        index=0,
    )
with col_f2:
    max_risk_inr = st.number_input(
        "💰 Max Risk / Trade (₹)",
        min_value=100.0,
        max_value=100000.0,
        value=500.0,
        step=100.0,
    )
with col_f3:
    quality_mode = st.selectbox(
        "🛡️ SL-Reduction Guardrails:",
        ["Strict (Vol ≥ 1.2x & R:R ≥ 1.25x)", "Balanced (Standard VWAP + Move)"],
        index=0,
    )
with col_r1:
    st.write("")
    if st.button("🔄 Refresh Intraday & Long-Term", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Refreshing live 5m intraday & daily long-term tables...", icon="⚡")
        st.rerun()

lt_filter = st.selectbox(
    "🏦 Long-Term Filter:",
    ["All Stocks", "Strong Uptrend Only", "Pullback Above 50 EMA"],
    index=0,
)


def _extract_ticker_df(raw_df, sym):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        lvl0 = raw_df.columns.get_level_values(0)
        lvl1 = raw_df.columns.get_level_values(1)
        if sym in lvl0:
            return raw_df[sym].dropna(how="all")
        if sym in lvl1:
            return raw_df.xs(sym, axis=1, level=1).dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=60)
def fetch_intraday_and_longterm_tables(direction_choice, risk_budget_inr, strict_guardrails):
    bullish_mode = "Bullish Intraday" in direction_choice
    intraday_rows = []
    longterm_rows = []

    try:
        raw_5m = yf.download(
            UNIVERSE,
            period="5d",
            interval="5m",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
        raw_1d = yf.download(
            UNIVERSE,
            period="3mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    for symbol in UNIVERSE:
        clean_sym = symbol.replace(".NS", "")

        # --- 1. PURE SAME-DAY INTRADAY (5m + VWAP + Volatility & R:R Guardrails) ---
        try:
            df_5m = _extract_ticker_df(raw_5m, symbol).dropna(
                subset=["Open", "High", "Low", "Close"]
            )
            if df_5m is not None and len(df_5m) >= 20:
                df_5m = df_5m.copy()
                df_5m.index = pd.to_datetime(df_5m.index)
                if df_5m.index.tz is not None:
                    df_5m.index = df_5m.index.tz_convert("Asia/Kolkata").tz_localize(None)

                today_dates = df_5m.index.date
                latest_date = today_dates[-1]
                df_today = df_5m[df_5m.index.date == latest_date]
                prev_days = df_5m[df_5m.index.date < latest_date]

                ltp_5m = float(df_5m["Close"].iloc[-1])
                prev_close_ref = (
                    float(prev_days["Close"].iloc[-1])
                    if not prev_days.empty
                    else float(df_today["Open"].iloc[0])
                )

                vol_s = (
                    df_today["Volume"]
                    if "Volume" in df_today and df_today["Volume"].sum() > 0
                    else None
                )
                if vol_s is not None:
                    tp = (df_today["High"] + df_today["Low"] + df_today["Close"]) / 3.0
                    vwap_val = float(
                        (tp * vol_s).cumsum().iloc[-1] / vol_s.cumsum().iloc[-1]
                    )
                    avg_bar_vol = float(df_5m["Volume"].tail(40).mean())
                    last_bar_vol = float(df_5m["Volume"].iloc[-1])
                    vol_ratio = (
                        round(last_bar_vol / avg_bar_vol, 2)
                        if avg_bar_vol > 0
                        else 1.0
                    )
                else:
                    vwap_val = float(df_today["Close"].mean())
                    vol_ratio = 1.0

                bar_range_pct = (
                    ((df_5m["High"] - df_5m["Low"]) / df_5m["Close"].replace(0, np.nan))
                    .tail(30)
                    .mean()
                    * 100.0
                )
                avg_5m_move_pct = (
                    float(bar_range_pct)
                    if not np.isnan(bar_range_pct) and bar_range_pct > 0
                    else 0.25
                )
                t1_pct = float(np.clip(avg_5m_move_pct * 4.5, 0.75, 1.8)) / 100.0
                t2_pct = float(np.clip(avg_5m_move_pct * 8.5, 1.4, 3.0)) / 100.0

                if prev_close_ref > 0 and not np.isnan(ltp_5m):
                    intra_chg = round(
                        ((ltp_5m - prev_close_ref) / prev_close_ref) * 100, 2
                    )
                    vwap_dist_pct = round(
                        ((ltp_5m - vwap_val) / max(vwap_val, 0.01)) * 100, 2
                    )
                    recent_swing_low = float(df_5m["Low"].tail(8).min())
                    recent_swing_high = float(df_5m["High"].tail(8).max())

                    if bullish_mode and intra_chg > 0.25 and ltp_5m >= vwap_val * 0.998:
                        sl_candidate = min(
                            vwap_val * 0.996,
                            recent_swing_low * 0.998,
                            ltp_5m * 0.992,
                        )
                        sl_intra = round(min(sl_candidate, ltp_5m * 0.995), 2)
                        t1_intra = round(ltp_5m * (1.0 + t1_pct), 2)
                        t2_intra = round(ltp_5m * (1.0 + t2_pct), 2)

                        per_share_risk = max(ltp_5m - sl_intra, ltp_5m * 0.004)
                        per_share_t1 = max(t1_intra - ltp_5m, 0.01)
                        rr_t1 = round(per_share_t1 / per_share_risk, 2)

                        if strict_guardrails:
                            if vol_ratio < 1.20 or vwap_dist_pct > 1.50 or rr_t1 < 1.25:
                                continue

                        qty_est = max(1, int(risk_budget_inr // per_share_risk))
                        est_t1_profit = round(qty_est * per_share_t1, 0)
                        stretch_tag = (
                            "Extended (>1.5% VWAP)"
                            if vwap_dist_pct > 1.5
                            else ("Sweet Spot (≤1.5% VWAP)" if vwap_dist_pct >= 0.15 else "Near VWAP")
                        )
                        score_intra = round(intra_chg * max(vol_ratio, 0.8) * min(rr_t1, 2.5), 2)

                        intraday_rows.append({
                            "Stock": clean_sym,
                            "Plan": "BUY & EXIT TODAY",
                            "LTP": round(ltp_5m, 2),
                            "Chg_%": intra_chg,
                            "VWAP": round(vwap_val, 2),
                            "VWAP_Gap_%": vwap_dist_pct,
                            "Vol_Pace": f"{vol_ratio:.2f}x",
                            "Stop_Loss": sl_intra,
                            "Target_1_Book": t1_intra,
                            "Target_2_Stretch": t2_intra,
                            "RR_T1": rr_t1,
                            "Est_Qty": qty_est,
                            "Est_T1_₹": est_t1_profit,
                            "Entry_Zone": stretch_tag,
                            "Exit_Rule": "Sell before 3:30 PM IST",
                            "Score": score_intra,
                        })
                    elif (
                        (not bullish_mode)
                        and intra_chg < -0.25
                        and ltp_5m <= vwap_val * 1.002
                    ):
                        sl_candidate = max(
                            vwap_val * 1.004,
                            recent_swing_high * 1.002,
                            ltp_5m * 1.008,
                        )
                        sl_intra = round(max(sl_candidate, ltp_5m * 1.005), 2)
                        t1_intra = round(ltp_5m * (1.0 - t1_pct), 2)
                        t2_intra = round(ltp_5m * (1.0 - t2_pct), 2)

                        per_share_risk = max(sl_intra - ltp_5m, ltp_5m * 0.004)
                        per_share_t1 = max(ltp_5m - t1_intra, 0.01)
                        rr_t1 = round(per_share_t1 / per_share_risk, 2)

                        if strict_guardrails:
                            if vol_ratio < 1.20 or vwap_dist_pct < -1.50 or rr_t1 < 1.25:
                                continue

                        qty_est = max(1, int(risk_budget_inr // per_share_risk))
                        est_t1_profit = round(qty_est * per_share_t1, 0)
                        stretch_tag = (
                            "Extended (<-1.5% VWAP)"
                            if vwap_dist_pct < -1.5
                            else ("Sweet Spot (≥-1.5% VWAP)" if vwap_dist_pct <= -0.15 else "Near VWAP")
                        )
                        score_intra = round(abs(intra_chg) * max(vol_ratio, 0.8) * min(rr_t1, 2.5), 2)

                        intraday_rows.append({
                            "Stock": clean_sym,
                            "Plan": "SHORT / EXIT TODAY",
                            "LTP": round(ltp_5m, 2),
                            "Chg_%": intra_chg,
                            "VWAP": round(vwap_val, 2),
                            "VWAP_Gap_%": vwap_dist_pct,
                            "Vol_Pace": f"{vol_ratio:.2f}x",
                            "Stop_Loss": sl_intra,
                            "Target_1_Book": t1_intra,
                            "Target_2_Stretch": t2_intra,
                            "RR_T1": rr_t1,
                            "Est_Qty": qty_est,
                            "Est_T1_₹": est_t1_profit,
                            "Entry_Zone": stretch_tag,
                            "Exit_Rule": "Cover before 3:30 PM IST",
                            "Score": score_intra,
                        })
        except Exception:
            pass

        # --- 2. SEPARATE LONG-TERM TREND TABLE (1d EMA20 & EMA50) ---
        try:
            df_1d = _extract_ticker_df(raw_1d, symbol).dropna(subset=["Close"])
            if df_1d is not None and len(df_1d) >= 50:
                close_1d = float(df_1d["Close"].iloc[-1])
                prev_1d = float(df_1d["Close"].iloc[-2])
                ema20_1d = float(
                    df_1d["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
                )
                ema50_1d = float(
                    df_1d["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
                )

                if prev_1d > 0 and not np.isnan(close_1d):
                    day_chg_1d = round(((close_1d - prev_1d) / prev_1d) * 100, 2)
                    if close_1d > ema20_1d > ema50_1d:
                        trend_tag = "🟢 Uptrend (Above 20 & 50 EMA)"
                    elif close_1d >= ema50_1d:
                        trend_tag = "🟡 Pullback / Mixed Trend"
                    else:
                        trend_tag = "🔴 Below 50 EMA"

                    lt_score = round(
                        ((close_1d - ema50_1d) / max(ema50_1d, 0.01)) * 100
                        + day_chg_1d,
                        2,
                    )
                    longterm_rows.append({
                        "Stock": clean_sym,
                        "Horizon": "Multi-Week / Long-Term",
                        "Close": round(close_1d, 2),
                        "Day_%": day_chg_1d,
                        "EMA_20": round(ema20_1d, 2),
                        "EMA_50": round(ema50_1d, 2),
                        "Long_Term_SL_Zone": round(ema50_1d * 0.97, 2),
                        "Trend_Status": trend_tag,
                        "Score": lt_score,
                    })
        except Exception:
            pass

    df_intra = (
        pd.DataFrame(intraday_rows)
        .sort_values(by="Score", ascending=False)
        .drop(columns=["Score"])
        .reset_index(drop=True)
        if intraday_rows
        else pd.DataFrame()
    )
    df_lt = (
        pd.DataFrame(longterm_rows)
        .sort_values(by="Score", ascending=False)
        .drop(columns=["Score"])
        .reset_index(drop=True)
        if longterm_rows
        else pd.DataFrame()
    )
    return df_intra, df_lt


is_strict = quality_mode.startswith("Strict")
with st.spinner("Scanning live 5m intraday setups & daily long-term trends..."):
    df_intraday, df_longterm = fetch_intraday_and_longterm_tables(
        intraday_bias, max_risk_inr, is_strict
    )

# ---------------------------------------------------------
# TABLE 1: PURE SAME-DAY INTRADAY WATCHLIST
# ---------------------------------------------------------
st.subheader("🎯 Table 1: Same-Day Intraday Setups (Buy & Exit Today)")
if df_intraday.empty:
    st.info(
        "ℹ️ No stocks matched the same-day intraday filter right now. Try **Balanced** mode, "
        "click **Refresh Intraday & Long-Term**, or switch direction above."
    )
else:
    st.dataframe(
        df_intraday.style.format({
            "LTP": "₹{:,.2f}",
            "Chg_%": "{:+.2f}%",
            "VWAP": "₹{:,.2f}",
            "VWAP_Gap_%": "{:+.2f}%",
            "Stop_Loss": "₹{:,.2f}",
            "Target_1_Book": "₹{:,.2f}",
            "Target_2_Stretch": "₹{:,.2f}",
            "RR_T1": "{:.2f}x",
            "Est_T1_₹": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Quick Same-Day Execution Cards (Top 2)")
    top2_records = []
    for idx, row in df_intraday.head(2).iterrows():
        c1, c2, c3, c4 = st.columns([2.1, 1.9, 2.0, 2.0])
        c1.metric(
            f"#{idx+1} {row['Stock']}",
            f"₹{row['LTP']:,.2f}",
            f"{row['Chg_%']:+.2f}% | {row['Entry_Zone']}",
        )
        c2.metric(
            "🛑 Same-Day Stop-Loss",
            f"₹{row['Stop_Loss']:,.2f}",
            f"Qty ~{row['Est_Qty']} (Max ₹{max_risk_inr:,.0f} risk)",
        )
        c3.metric(
            "🎯 Target 1 (Book Profit)",
            f"₹{row['Target_1_Book']:,.2f}",
            f"Est. +₹{row['Est_T1_₹']:,.0f} ({row['RR_T1']:.2f}R)",
        )
        c4.metric(
            "🚀 Target 2 (Stretch)",
            f"₹{row['Target_2_Stretch']:,.2f}",
            row["Exit_Rule"],
        )
        top2_records.append({
            "symbol": row["Stock"],
            "side": "SHORT" if "SHORT" in str(row["Plan"]).upper() else "BUY",
            "entry": float(row["LTP"]),
            "sl": float(row["Stop_Loss"]),
            "t1": float(row["Target_1_Book"]),
            "t2": float(row["Target_2_Stretch"]),
            "notes": f"{row['Entry_Zone']} | Vol {row['Vol_Pace']} | R:R {row['RR_T1']:.2f}x",
        })

    if top2_records and st.button("📌 Log Top 2 Intraday Picks to History Ledger", type="primary"):
        saved_n = _save_top2_to_ledger(top2_records)
        st.success(f"Recorded {saved_n} Top 2 pick(s) to the history ledger.")

st.markdown("---")

# ---------------------------------------------------------
# TABLE 2: SEPARATE LONG-TERM WATCHLIST
# ---------------------------------------------------------
st.subheader("🏦 Table 2: Separate Long-Term Watchlist (Multi-Week / Positional Study)")
st.caption(
    "Kept separate from same-day intraday trades so longer-term trend stocks aren't confused with intraday entries."
)

if df_longterm.empty:
    st.info("ℹ️ Long-term daily trend data is currently unavailable.")
else:
    df_lt_view = df_longterm.copy()
    if lt_filter == "Strong Uptrend Only":
        df_lt_view = df_lt_view[df_lt_view["Trend_Status"].str.startswith("🟢")]
    elif lt_filter == "Pullback Above 50 EMA":
        df_lt_view = df_lt_view[df_lt_view["Trend_Status"].str.startswith("🟡")]

    if df_lt_view.empty:
        st.info(f"ℹ️ No long-term stocks match '{lt_filter}' right now.")
    else:
        st.dataframe(
            df_lt_view.style.format({
                "Close": "₹{:,.2f}",
                "Day_%": "{:+.2f}%",
                "EMA_20": "₹{:,.2f}",
                "EMA_50": "₹{:,.2f}",
                "Long_Term_SL_Zone": "₹{:,.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
