from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Smart Money Flow & Pulse Terminal", layout="wide"
)

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


def _save_smart_money_picks_to_ledger(
    picks: list[dict], module_label: str = "Smart Money Top 2 Green & Red"
) -> int:
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
        pid = hashlib.sha1(
            f"{bucket}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")
        ).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)
        new_rows.append({
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
    if not new_rows:
        return 0
    out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True).drop_duplicates(
        subset=["pick_id"], keep="first"
    )
    out.to_csv(ledger_file, index=False)
    return len(new_rows)


st.title("⚡ Institutional Smart Money Flow & Reverse-Engineering Terminal")
st.caption(
    "Decodes Where Capital Is Rotating From → Into, Intraday Accumulation vs. Distribution Footprints, Top 2 Green/Red Picks & 15m Charting."
)

c_ref1, c_ref2, c_ref3, c_ref4 = st.columns([1.4, 1.5, 1.1, 2.0])
with c_ref1:
    if st.button("🔄 Refresh Smart Money Flows", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with c_ref2:
    flow_mode = st.selectbox(
        "🛡️ Flow Quality Filter:",
        ["Strict (RVOL ≥ 1.15x & Close Conviction)", "All Flow Movers"],
        index=0,
    )
with c_ref3:
    live_stream = st.toggle("🌊 Auto-Stream (30s)", value=False)
with c_ref4:
    status_txt = "🟢 Live NSE Session" if is_market_open else "🟡 Pre-Market / Market Closed"
    st.caption(f"{status_txt} • Synced: **{now_ist.strftime('%I:%M:%S %p IST')}**")

with st.expander("📘 Reverse-Engineering Secrets: How We Decode Who & How Money Moves", expanded=False):
    st.markdown(
        "- **1. Sector Rotation Bridge (Outflow → Inflow):** When FIIs/DIIs rotate capital, they sell one heavy sector (e.g., IT) and deploy into another (e.g., Autos or Banks) simultaneously.\n"
        "- **2. Opening Gap vs. Intraday Drive:** If most of the % move happened *after* the open (`Intraday Drive %`) with high `RVOL` and a close near the high (`Close Strength ≥ 75%`), institutions accumulated steadily all day rather than trapping retail on a morning gap.\n"
        "- **3. Peak Session Window (First Hour vs. Closing Hour):** Heavy volume in `9:15–10:30 AM` signals overnight order execution; heavy volume in `2:30–3:30 PM` signals institutional closing-bell positioning.\n"
        "- **Transparency Note:** Public market feeds show price and volume footprints—not broker client names. Always confirm live price action and use a stop-loss. Not financial advice."
    )

SECTOR_STOCKS = {
    "Banking & Finance": ["SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS"],
    "Energy & Oil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
}


def _extract_ticker_df(raw_df, ticker):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if ticker in raw_df.columns.get_level_values(0):
            return raw_df[ticker].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


def _reverse_engineer_footprint(
    chg_pct: float,
    gap_pct: float,
    intraday_drive_pct: float,
    rvol: float,
    close_pos: float,
    peak_window: str,
) -> tuple[str, str]:
    if chg_pct > 0.5:
        if rvol >= 1.35 and close_pos >= 72 and intraday_drive_pct > 0.4:
            return (
                "🏦 Institutional Sweep Accumulation",
                f"Steady intraday buying (+{intraday_drive_pct:.2f}% post-open) with {rvol}x RVOL & {close_pos:.0f}% high close; peak activity in {peak_window}.",
            )
        if gap_pct > 1.0 and intraday_drive_pct <= 0.1:
            return (
                "⚠️ Gap-Up Fade / Profit Booking",
                f"Opened +{gap_pct:.2f}% higher on overnight cues, but intraday follow-through stalled ({intraday_drive_pct:+.2f}%).",
            )
        if rvol >= 1.15 and close_pos >= 60:
            return (
                "📈 Steady Rotational Inflow",
                f"Gradual accumulation ({rvol}x RVOL) with buyers defending pullbacks into {peak_window}.",
            )
        return (
            "🌿 Light Drift / Retail Follow-Through",
            f"Positive price drift (+{chg_pct:.2f}%) on moderate volume ({rvol}x RVOL); watch for RVOL > 1.2x confirmation.",
        )
    elif chg_pct < -0.5:
        if rvol >= 1.35 and close_pos <= 28 and intraday_drive_pct < -0.4:
            return (
                "🔻 Institutional Supply / Distribution",
                f"Heavy selling pressure ({intraday_drive_pct:.2f}% post-open) with {rvol}x RVOL & weak {close_pos:.0f}% close; peak dump in {peak_window}.",
            )
        if gap_pct < -1.0 and intraday_drive_pct > 0.3:
            return (
                "🛡️ Gap-Down Absorption (Smart Dip Buy)",
                f"Opened {gap_pct:.2f}% lower, but buyers absorbed supply intraday (+{intraday_drive_pct:.2f}% recovery).",
            )
        return (
            "📉 Sector Outflow / Long Unwinding",
            f"Capital rotating out ({chg_pct:.2f}%, close at {close_pos:.0f}% of range) with {rvol}x RVOL.",
        )
    return (
        "⚖️ Two-Way Institutional Equilibrium",
        f"Balanced buy/sell turnover ({rvol}x RVOL) without directional breakout yet.",
    )


@st.cache_data(ttl=60)
def fetch_smart_money_pulse():
    all_syms = [s for stocks in SECTOR_STOCKS.values() for s in stocks]
    raw_1d = yf.download(
        all_syms, period="5d", interval="1d", group_by="ticker", progress=False, auto_adjust=True
    )
    raw_15m = yf.download(
        all_syms, period="5d", interval="15m", group_by="ticker", progress=False, auto_adjust=True
    )
    rows = []

    for sector, syms in SECTOR_STOCKS.items():
        for sym in syms:
            df = _extract_ticker_df(raw_1d, sym).dropna(subset=["Close", "High", "Low", "Open"])
            if len(df) < 2:
                continue

            close_now = float(df["Close"].iloc[-1])
            open_now = float(df["Open"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            high_now = float(df["High"].iloc[-1])
            low_now = float(df["Low"].iloc[-1])

            if close_prev == 0 or any(np.isnan(x) for x in [close_now, open_now, close_prev, high_now, low_now]):
                continue

            vol_now = float(df["Volume"].iloc[-1]) if "Volume" in df and pd.notna(df["Volume"].iloc[-1]) else 0.0
            vol_hist = df["Volume"].iloc[:-1].dropna() if "Volume" in df and len(df) > 2 else pd.Series(dtype=float)
            vol_avg = float(vol_hist.mean()) if not vol_hist.empty else vol_now

            chg_pct = ((close_now - close_prev) / close_prev) * 100.0
            gap_pct = ((open_now - close_prev) / close_prev) * 100.0
            intraday_drive_pct = ((close_now - open_now) / max(open_now, 0.01)) * 100.0
            rvol = round(vol_now / vol_avg, 2) if vol_avg > 0 and vol_now > 0 else 1.0
            rng = high_now - low_now
            close_pos = ((close_now - low_now) / rng) * 100.0 if rng > 0 else 50.0

            # Intraday 15m reverse-engineering: Buy-Bar vs Sell-Bar turnover & Peak Session Window
            df_intra = _extract_ticker_df(raw_15m, sym).dropna(subset=["Close", "Open"])
            buy_cr = 0.0
            sell_cr = 0.0
            peak_window = "Opening Bell (9:15–10:30)"
            if not df_intra.empty:
                idx_ist = pd.to_datetime(df_intra.index)
                if idx_ist.tz is None:
                    idx_ist = idx_ist.tz_localize("Asia/Kolkata")
                else:
                    idx_ist = idx_ist.tz_convert("Asia/Kolkata")
                df_intra = df_intra.copy()
                df_intra.index = idx_ist
                latest_session = df_intra.index.date[-1]
                day_bars = df_intra[df_intra.index.date == latest_session]
                if not day_bars.empty and "Volume" in day_bars.columns:
                    bar_cr = (day_bars["Close"] * day_bars["Volume"]) / 1e7
                    buy_cr = float(bar_cr[day_bars["Close"] >= day_bars["Open"]].sum())
                    sell_cr = float(bar_cr[day_bars["Close"] < day_bars["Open"]].sum())

                    peak_ts = bar_cr.idxmax()
                    hr_min = peak_ts.hour * 60 + peak_ts.minute
                    if hr_min < 10 * 60 + 30:
                        peak_window = f"Opening Hour ({peak_ts.strftime('%H:%M')} IST)"
                    elif hr_min < 14 * 60 + 15:
                        peak_window = f"Mid-Session ({peak_ts.strftime('%H:%M')} IST)"
                    else:
                        peak_window = f"Closing Hour ({peak_ts.strftime('%H:%M')} IST)"

            net_bar_delta_cr = round(buy_cr - sell_cr, 2)
            turnover_cr = (close_now * vol_now) / 1e7
            abnormal_ratio = max(rvol - 0.85, 0.1) if rvol > 1.0 else 0.15
            direction = 1 if chg_pct >= 0 else -1
            est_flow_cr = round(direction * turnover_cr * abnormal_ratio * 0.12, 2)

            carry_score = round(
                float(np.clip((chg_pct + 2.5) * 12, 0, 45))
                + float((close_pos / 100.0) * 35)
                + float(np.clip(rvol * 10, 0, 20)),
                1,
            )

            footprint_tag, mechanism_note = _reverse_engineer_footprint(
                chg_pct, gap_pct, intraday_drive_pct, rvol, close_pos, peak_window
            )

            if est_flow_cr >= 0:
                ref_entry = round(close_now * 0.996, 2)
                ref_sl = round(close_now * 0.982, 2)
                ref_t1 = round(close_now * 1.021, 2)
                ref_t2 = round(close_now * 1.038, 2)
            else:
                ref_entry = round(close_now * 1.003, 2)
                ref_sl = round(close_now * 1.016, 2)
                ref_t1 = round(close_now * 0.980, 2)
                ref_t2 = round(close_now * 0.962, 2)

            rows.append({
                "Symbol": sym.replace(".NS", ""),
                "Sector": sector,
                "Price": round(close_now, 2),
                "Change %": round(chg_pct, 2),
                "Gap %": round(gap_pct, 2),
                "Intraday Drive %": round(intraday_drive_pct, 2),
                "Est. Flow (Cr)": est_flow_cr,
                "Buy vs Sell Bar (Cr)": net_bar_delta_cr,
                "RVOL": rvol,
                "Close Strength %": round(close_pos, 1),
                "Carry Score": carry_score,
                "Peak Activity": peak_window,
                "Who & How (Footprint)": footprint_tag,
                "Reverse-Engineered Mechanism": mechanism_note,
                "Ref_Entry": ref_entry,
                "Ref_SL": ref_sl,
                "Ref_T1": ref_t1,
                "Ref_T2": ref_t2,
            })

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values(by="Est. Flow (Cr)", ascending=False)
        .reset_index(drop=True)
    )


def render_inline_smc_chart(symbol_clean):
    ticker = f"{symbol_clean}.NS"
    df_c = yf.Ticker(ticker).history(period="5d", interval="15m", auto_adjust=True)
    if df_c is None or df_c.empty:
        st.warning(f"Intraday chart unavailable for {symbol_clean}.")
        return

    df_c["EMA20"] = df_c["Close"].ewm(span=20, adjust=False).mean()
    typical_price = (df_c["High"] + df_c["Low"] + df_c["Close"]) / 3.0
    if "Volume" in df_c and df_c["Volume"].sum() > 0:
        df_c["VWAP"] = (
            (typical_price * df_c["Volume"])
            .groupby(df_c.index.date)
            .cumsum()
            / df_c["Volume"].groupby(df_c.index.date).cumsum().replace(0, np.nan)
        ).fillna(df_c["EMA20"])
    else:
        df_c["VWAP"] = typical_price.rolling(20, min_periods=1).mean()

    df_c = df_c.tail(85)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.76, 0.24],
    )
    fig.add_trace(
        go.Candlestick(
            x=df_c.index,
            open=df_c["Open"],
            high=df_c["High"],
            low=df_c["Low"],
            close=df_c["Close"],
            name=symbol_clean,
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["VWAP"],
            mode="lines",
            name="VWAP / Anchor",
            line=dict(color="#FFD700", width=1.6),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["EMA20"],
            mode="lines",
            name="20 EMA",
            line=dict(color="#29B6F6", width=1.3),
        ),
        row=1,
        col=1,
    )

    vol_colors = [
        "#00E676" if c >= o else "#FF5252"
        for o, c in zip(df_c["Open"], df_c["Close"])
    ]
    fig.add_trace(
        go.Bar(
            x=df_c.index,
            y=df_c["Volume"],
            name="Volume",
            marker_color=vol_colors,
        ),
        row=2,
        col=1,
    )

    last_close = float(df_c["Close"].iloc[-1])
    last_vwap = float(df_c["VWAP"].iloc[-1])
    fig.update_layout(
        title=(
            f"📈 {symbol_clean} — 15m Chart, VWAP/Anchor (₹{last_vwap:,.2f})"
            f" & 20 EMA | Last Price: ₹{last_close:,.2f}"
        ),
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=50, t=45, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


df_pulse = fetch_smart_money_pulse()

if not df_pulse.empty:
    strict_flow = flow_mode.startswith("Strict")

    inflow = df_pulse[df_pulse["Est. Flow (Cr)"] > 0]["Est. Flow (Cr)"].sum()
    outflow = abs(df_pulse[df_pulse["Est. Flow (Cr)"] < 0]["Est. Flow (Cr)"].sum())
    net_bias = inflow - outflow

    top_in_row = df_pulse.iloc[0]
    top_out_row = df_pulse.sort_values(by="Est. Flow (Cr)", ascending=True).iloc[0]

    # Sector-level net flow aggregation to reveal where capital is leaving vs entering
    sec_flow = (
        df_pulse.groupby("Sector", as_index=False)["Est. Flow (Cr)"]
        .sum()
        .sort_values(by="Est. Flow (Cr)", ascending=False)
    )
    donor_sectors = sec_flow[sec_flow["Est. Flow (Cr)"] < 0].sort_values(by="Est. Flow (Cr)", ascending=True)
    receiver_sectors = sec_flow[sec_flow["Est. Flow (Cr)"] > 0].sort_values(by="Est. Flow (Cr)", ascending=False)

    donor_txt = (
        f"{donor_sectors.iloc[0]['Sector']} (₹{donor_sectors.iloc[0]['Est. Flow (Cr)']:+.0f} Cr)"
        if not donor_sectors.empty
        else "Broad Market Cash"
    )
    receiver_txt = (
        f"{receiver_sectors.iloc[0]['Sector']} (₹{receiver_sectors.iloc[0]['Est. Flow (Cr)']:+.0f} Cr)"
        if not receiver_sectors.empty
        else "Defensive Cash"
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 Total Est. Inflow", f"₹{inflow:,.0f} Cr", f"Top: {top_in_row['Symbol']} (₹{top_in_row['Est. Flow (Cr)']:+.0f} Cr)")
    m2.metric("🔴 Total Est. Outflow", f"₹{outflow:,.0f} Cr", f"Heaviest: {top_out_row['Symbol']} (₹{top_out_row['Est. Flow (Cr)']:+.0f} Cr)")
    m3.metric("🔄 Rotation Source → Target", f"{receiver_txt.split(' (')[0]}", f"From: {donor_txt}")
    m4.metric(
        "⚖️ Net Est. Bias",
        f"₹{net_bias:+,.0f} Cr",
        "Bullish Edge" if net_bias >= 0 else "Bearish Pressure",
    )

    st.info(
        f"🕵️ **Capital Rotation Decode:** Money is rotating **OUT OF {donor_txt}** (led by **{top_out_row['Symbol']}**, "
        f"{top_out_row['Who & How (Footprint)']}) and **INTO {receiver_txt}** (led by **{top_in_row['Symbol']}**, "
        f"{top_in_row['Who & How (Footprint)']})."
    )

    st.markdown("---")

    # 1. DEDICATED TOP 2 GREEN (INFLOW) & TOP 2 RED (OUTFLOW) PICKS WITH MECHANISM
    st.subheader("⭐ Smart Money Top 2 Green (Inflow) & Top 2 Red (Outflow) Picks")
    green_pool = df_pulse[df_pulse["Est. Flow (Cr)"] > 0].copy()
    red_pool = df_pulse[df_pulse["Est. Flow (Cr)"] < 0].copy()

    if strict_flow:
        strict_green = green_pool[(green_pool["RVOL"] >= 1.15) & (green_pool["Close Strength %"] >= 55.0)]
        if not strict_green.empty:
            green_pool = strict_green
        strict_red = red_pool[(red_pool["RVOL"] >= 1.15) & (red_pool["Close Strength %"] <= 45.0)]
        if not strict_red.empty:
            red_pool = strict_red

    top2_green = green_pool.sort_values(
        by=["Est. Flow (Cr)", "Carry Score"], ascending=[False, False]
    ).head(2).reset_index(drop=True)
    top2_red = red_pool.sort_values(
        by=["Est. Flow (Cr)", "Close Strength %"], ascending=[True, True]
    ).head(2).reset_index(drop=True)

    sm_ledger_payload = []
    col_g, col_r = st.columns(2)

    with col_g:
        st.markdown("#### 🟢 Top 2 Green — Smart Inflow (Long Bias)")
        if top2_green.empty:
            st.info("No positive inflow stocks matched right now.")
        else:
            for idx_g, g_row in top2_green.iterrows():
                st.success(
                    f"**#{idx_g + 1} GREEN: {g_row['Symbol']} ({g_row['Sector']})** — LTP ₹{g_row['Price']:,.2f} ({g_row['Change %']:+.2f}%)\n\n"
                    f"• **Who & How:** {g_row['Who & How (Footprint)']} • **Peak:** {g_row['Peak Activity']}\n\n"
                    f"• **Why:** {g_row['Reverse-Engineered Mechanism']}\n\n"
                    f"• **Watch Buy:** ₹{g_row['Ref_Entry']:,.2f} | **SL:** ₹{g_row['Ref_SL']:,.2f} | **T1:** ₹{g_row['Ref_T1']:,.2f} | **T2:** ₹{g_row['Ref_T2']:,.2f}"
                )
                sm_ledger_payload.append({
                    "symbol": g_row["Symbol"],
                    "side": "BUY",
                    "entry": float(g_row["Ref_Entry"]),
                    "sl": float(g_row["Ref_SL"]),
                    "t1": float(g_row["Ref_T1"]),
                    "t2": float(g_row["Ref_T2"]),
                    "notes": f"Smart Money Green #{idx_g + 1} | {g_row['Who & How (Footprint)']} | Flow ₹{g_row['Est. Flow (Cr)']:+.2f} Cr",
                })

    with col_r:
        st.markdown("#### 🔴 Top 2 Red — Smart Outflow (Short Bias)")
        if top2_red.empty:
            st.info("No heavy outflow stocks matched right now.")
        else:
            for idx_r, r_row in top2_red.iterrows():
                st.error(
                    f"**#{idx_r + 1} RED: {r_row['Symbol']} ({r_row['Sector']})** — LTP ₹{r_row['Price']:,.2f} ({r_row['Change %']:+.2f}%)\n\n"
                    f"• **Who & How:** {r_row['Who & How (Footprint)']} • **Peak:** {r_row['Peak Activity']}\n\n"
                    f"• **Why:** {r_row['Reverse-Engineered Mechanism']}\n\n"
                    f"• **Watch Short:** ₹{r_row['Ref_Entry']:,.2f} | **SL:** ₹{r_row['Ref_SL']:,.2f} | **T1:** ₹{r_row['Ref_T1']:,.2f} | **T2:** ₹{r_row['Ref_T2']:,.2f}"
                )
                sm_ledger_payload.append({
                    "symbol": r_row["Symbol"],
                    "side": "SHORT",
                    "entry": float(r_row["Ref_Entry"]),
                    "sl": float(r_row["Ref_SL"]),
                    "t1": float(r_row["Ref_T1"]),
                    "t2": float(r_row["Ref_T2"]),
                    "notes": f"Smart Money Red #{idx_r + 1} | {r_row['Who & How (Footprint)']} | Flow ₹{r_row['Est. Flow (Cr)']:+.2f} Cr",
                })

    # --- PUSH SMART MONEY PICKS TO ANALYSER SESSION STATE ---
    st.session_state.setdefault("live_scanner_picks", {})[
        "Smart Money Top 2 Green & Red"
    ] = sm_ledger_payload

    if sm_ledger_payload and st.button(
        "📌 Log Smart Money Top 2 Green & Red Picks to History Ledger", type="primary"
    ):
        saved_sm = _save_smart_money_picks_to_ledger(
            sm_ledger_payload, "Smart Money Top 2 Green & Red"
        )
        st.success(f"Recorded {saved_sm} Smart Money Top 2 Green/Red pick(s) to history ledger.")

    st.markdown("---")

    # 2. 3-TIER CAPITAL ROTATION SANKEY (WHERE MONEY LEAVES -> ROTATION BRIDGE -> WHERE IT GOES)
    st.subheader("🌊 Capital Rotation Pipeline: Where Money Leaves → Where It Goes")
    st.caption(
        "Left nodes show sectors losing capital (Red), middle bridge shows active capital reallocation, and right nodes show sectors & top stocks absorbing the inflow (Green)."
    )

    outflow_stocks = df_pulse[df_pulse["Est. Flow (Cr)"] < 0].sort_values(by="Est. Flow (Cr)", ascending=True).head(6)
    inflow_stocks = df_pulse[df_pulse["Est. Flow (Cr)"] > 0].sort_values(by="Est. Flow (Cr)", ascending=False).head(8)

    if not outflow_stocks.empty and not inflow_stocks.empty:
        out_labels = [f"🔴 {r['Symbol']} ({r['Sector']})" for _, r in outflow_stocks.iterrows()]
        bridge_label = ["🔄 Institutional Capital Reallocation"]
        in_sec_list = sorted(inflow_stocks["Sector"].unique().tolist())
        in_sec_labels = [f"📂 {s}" for s in in_sec_list]
        in_stk_labels = [f"🟢 {r['Symbol']}" for _, r in inflow_stocks.iterrows()]

        nodes_3tier = out_labels + bridge_label + in_sec_labels + in_stk_labels
        idx_map = {name: i for i, name in enumerate(nodes_3tier)}

        src_3, tgt_3, val_3, col_3 = [], [], [], []

        # Outflow stocks -> Center Rotation Bridge
        for _, r in outflow_stocks.iterrows():
            lbl = f"🔴 {r['Symbol']} ({r['Sector']})"
            src_3.append(idx_map[lbl])
            tgt_3.append(idx_map[bridge_label[0]])
            val_3.append(max(abs(float(r["Est. Flow (Cr)"])), 1.0))
            col_3.append("rgba(255, 82, 82, 0.45)")

        # Center Rotation Bridge -> Inflow Sectors
        sec_in_sums = inflow_stocks.groupby("Sector")["Est. Flow (Cr)"].sum()
        for sec_name, tot_v in sec_in_sums.items():
            src_3.append(idx_map[bridge_label[0]])
            tgt_3.append(idx_map[f"📂 {sec_name}"])
            val_3.append(max(float(tot_v), 1.0))
            col_3.append("rgba(41, 182, 246, 0.42)")

        # Inflow Sectors -> Inflow Stocks
        for _, r in inflow_stocks.iterrows():
            src_3.append(idx_map[f"📂 {r['Sector']}"])
            tgt_3.append(idx_map[f"🟢 {r['Symbol']}"])
            val_3.append(max(float(r["Est. Flow (Cr)"]), 1.0))
            col_3.append("rgba(0, 230, 118, 0.48)")

        node_colors = (
            ["#FF5252"] * len(out_labels)
            + ["#FFD700"]
            + ["#29B6F6"] * len(in_sec_labels)
            + ["#00E676"] * len(in_stk_labels)
        )

        fig_rot = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=16,
                        thickness=18,
                        line=dict(color="black", width=0.5),
                        label=nodes_3tier,
                        color=node_colors,
                    ),
                    link=dict(source=src_3, target=tgt_3, value=val_3, color=col_3),
                )
            ]
        )
        fig_rot.update_layout(
            title="Reverse-Engineered Rotation: Selling Source (Left) → Absorbing Sectors & Stocks (Right)",
            template="plotly_dark",
            height=440,
            margin=dict(l=10, r=10, t=40, b=15),
        )
        st.plotly_chart(fig_rot, use_container_width=True)

    with st.expander("View Full Sector-to-Stock Sankey Stream (All Tracked Stocks)", expanded=False):
        sectors = list(df_pulse["Sector"].unique())
        symbols = list(df_pulse["Symbol"].unique())
        nodes = sectors + symbols
        node_idx = {name: i for i, name in enumerate(nodes)}

        sources = [node_idx[s] for s in df_pulse["Sector"]]
        targets = [node_idx[sym] for sym in df_pulse["Symbol"]]
        values = [max(abs(v), 0.5) for v in df_pulse["Est. Flow (Cr)"]]
        link_colors = [
            "rgba(0, 230, 118, 0.45)" if v >= 0 else "rgba(255, 82, 82, 0.45)"
            for v in df_pulse["Est. Flow (Cr)"]
        ]

        fig_sankey = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=18,
                        line=dict(color="black", width=0.5),
                        label=nodes,
                        color=["#29B6F6"] * len(sectors)
                        + [
                            "#00E676" if v >= 0 else "#FF5252"
                            for v in df_pulse["Est. Flow (Cr)"]
                        ],
                    ),
                    link=dict(
                        source=sources, target=targets, value=values, color=link_colors
                    ),
                )
            ]
        )
        fig_sankey.update_layout(
            template="plotly_dark", height=430, margin=dict(l=10, r=10, t=15, b=15)
        )
        st.plotly_chart(fig_sankey, use_container_width=True)

    st.markdown("---")

    # 3. SECTOR FILTER + REVERSE-ENGINEERED LEDGER + INLINE SMC CHART LAUNCHER
    st.subheader("📋 Reverse-Engineered Flow & Mechanism Ledger (Click Any Row for 15m Chart)")
    sector_options = ["All Sectors"] + sorted(df_pulse["Sector"].unique().tolist())
    chosen_sector = st.selectbox("Filter Ledger by Sector:", sector_options, index=0)

    df_view = (
        df_pulse
        if chosen_sector == "All Sectors"
        else df_pulse[df_pulse["Sector"] == chosen_sector].reset_index(drop=True)
    )

    display_cols = [
        "Symbol",
        "Sector",
        "Price",
        "Change %",
        "Gap %",
        "Intraday Drive %",
        "Est. Flow (Cr)",
        "Buy vs Sell Bar (Cr)",
        "RVOL",
        "Close Strength %",
        "Peak Activity",
        "Who & How (Footprint)",
        "Reverse-Engineered Mechanism",
    ]

    st.caption("Select any row to inspect its 15-minute candlesticks, VWAP/anchor, and 20 EMA below.")

    event = st.dataframe(
        df_view[display_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Gap %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Intraday Drive %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Est. Flow (Cr)": st.column_config.NumberColumn(format="₹%+.2f Cr"),
            "Buy vs Sell Bar (Cr)": st.column_config.NumberColumn(format="₹%+.2f Cr"),
            "RVOL": st.column_config.NumberColumn(format="%.2fx"),
            "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    selected_rows = event.selection.rows if event and event.selection else []
    active_symbol = (
        df_view.iloc[selected_rows[0]]["Symbol"]
        if selected_rows
        else df_view.iloc[0]["Symbol"]
    )

    st.markdown("---")
    render_inline_smc_chart(active_symbol)
else:
    st.warning("⚠️ Unable to load flow data right now. Click **Refresh Smart Money Flows** to retry.")

if live_stream:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
