from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Bearish Alpha & SMC Short Terminal | Institutional Breakdown",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
current_time_ist = now_ist.time()
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= current_time_ist <= dt_time(15, 30)
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_bearish_picks_to_ledger(picks: list[dict], module_label: str = "Bearish Top 2") -> int:
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
        side = str(p.get("side", "SHORT")).upper()
        entry = float(p["entry"])
        pid = hashlib.sha1(f"{bucket}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")).hexdigest()[:12]
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


st.title("🎯 Institutional Alpha: Daily Top Bearish Intraday Setups (Shorts)")
st.markdown(
    "**Pure Same-Day Short Scanner:** Scans liquid NSE stocks for downward momentum, "
    "price trading below **VWAP** and **20 EMA**, and volume participation (`RVOL`) so you "
    "can plan intraday shorts and **square off (buy back) before 3:30 PM IST**."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Beginner Rulebook: Intraday Shorting, Profit Booking & Square-Off", expanded=False):
    st.markdown(
        "- **How Intraday Shorting Works:** You sell first and buy back later the **same day** before **3:30 PM IST**—if price rises instead of falling, a short loses money.\n"
        "- **No Guaranteed Profit:** Even when a stock is below VWAP and 20 EMA, sudden reversals or short squeezes happen—always honor your **Stop Loss**.\n"
        "- **Book Profit Early:** Consider booking partial or full profit near **Target 1** rather than waiting blindly for **Target 2**. Not financial advice."
    )

# ---------------------------------------------------------
# 1. LIVE CONTROL PANEL & REFRESH
# ---------------------------------------------------------
col_r1, col_r2, col_r3 = st.columns([2.4, 1.6, 1.0])
with col_r2:
    bear_mode = st.selectbox(
        "🛡️ Short Anti-Squeeze Filter:",
        ["Strict (RVOL ≥ 1.3x, -0.7% to -4.2% & R:R ≥ 1.25x)", "Standard Bearish"],
        index=0,
    )
with col_r3:
    st.write("")
    if st.button("🔄 Force Refresh Bearish Scan", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cleared cache and executed market-wide bearish alpha scan!", icon="⚡")
        st.rerun()


def _extract_ticker_df(raw_df, sym):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


# ---------------------------------------------------------
# 2. WHOLE-MARKET BEARISH INSTITUTIONAL ALPHA SCANNER
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_bearish_institutional_picks(strict_mode=True):
    market_universe = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "SBIN.NS", "ITC.NS", "BHARTIARTL.NS", "LICI.NS", "AXISBANK.NS",
        "KOTAKBANK.NS", "LT.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS",
        "TITAN.NS", "ADANIENT.NS", "ADANIPORTS.NS", "TATASTEEL.NS", "NTPC.NS",
        "POWERGRID.NS", "COALINDIA.NS", "ONGC.NS", "BAJAJFINSV.NS", "WIPRO.NS",
        "ASIANPAINT.NS", "HCLTECH.NS", "GRASIM.NS", "TECHM.NS", "INDUSINDBK.NS",
        "DEEPAKFERT.NS", "ANGELONE.NS", "HONASA.NS", "MAXHEALTH.NS", "PNB.NS",
        "CANBK.NS", "TORNTPHARM.NS", "SUPREMEIND.NS", "ETERNAL.NS", "BELRISE.NS",
    ]

    try:
        raw = yf.download(
            market_universe,
            period="5d",
            interval="15m",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    bearish_scored_stocks = []
    min_drop = -4.2 if strict_mode else -5.5
    max_drop = -0.7 if strict_mode else -0.5
    min_rvol_req = 1.30 if strict_mode else 1.10

    for symbol in market_universe:
        try:
            df = _extract_ticker_df(raw, symbol).dropna(
                subset=["Open", "High", "Low", "Close"]
            )
            if df is None or df.empty or len(df) < 15:
                continue

            df = df.reset_index()
            df.rename(columns={df.columns[0]: "Time"}, inplace=True)
            df["Time"] = pd.to_datetime(df["Time"])
            if df["Time"].dt.tz is not None:
                df["Time"] = (
                    df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
                )

            is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
            df["Axis_Str"] = np.where(
                is_new_day,
                df["Time"].dt.strftime("%d %b '%y  %H:%M"),
                df["Time"].dt.strftime("%H:%M  (%d %b)"),
            )

            df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            if vol_series.sum() > 0:
                df["VWAP"] = (
                    (((df["High"] + df["Low"] + df["Close"]) / 3.0) * vol_series)
                    .groupby(df["Time"].dt.date)
                    .cumsum()
                    / vol_series.groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
                ).fillna(df["EMA20"])
            else:
                df["VWAP"] = df["EMA20"]

            ltp = float(df["Close"].iloc[-1])
            df["Date"] = df["Time"].dt.date
            unique_dates = df["Date"].unique()
            if len(unique_dates) >= 2:
                prev_close = float(
                    df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1]
                )
            else:
                prev_close = float(df["Open"].iloc[0])

            if prev_close <= 0 or np.isnan(ltp) or np.isnan(prev_close):
                continue

            change_pct = ((ltp - prev_close) / prev_close) * 100.0

            avg_vol = float(vol_series.iloc[-17:-2].mean()) if len(vol_series) >= 17 else 0.0
            curr_vol = float(vol_series.iloc[-2]) if len(vol_series) >= 2 and pd.notna(vol_series.iloc[-2]) else 0.0
            rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 and curr_vol > 0 else 1.0

            latest_vwap = float(df["VWAP"].iloc[-1])
            latest_ema = float(df["EMA20"].iloc[-1])

            if (
                min_drop <= change_pct <= max_drop
                and ltp <= latest_vwap
                and ltp <= latest_ema
                and rvol >= min_rvol_req
            ):
                v_avg = vol_series.rolling(20, min_periods=1).mean()
                v_col = [
                    (
                        "#FF5252"
                        if (c < o and v >= 1.3 * va)
                        else (
                            "#00E676"
                            if (c >= o and v >= 1.3 * va)
                            else (
                                "rgba(255,82,82,0.38)"
                                if c < o
                                else "rgba(0,230,118,0.38)"
                            )
                        )
                    )
                    for o, c, v, va in zip(df["Open"], df["Close"], vol_series, v_avg)
                ]

                recent_swing_high = float(df["High"].tail(6).max())
                limit_short = round(ltp * 1.003, 2)
                stop_loss = round(
                    min(
                        max(latest_vwap * 1.005, recent_swing_high * 1.002),
                        limit_short * 1.014,
                    ),
                    2,
                )
                stop_loss = max(stop_loss, round(limit_short * 1.006, 2))
                risk_pts = max(stop_loss - limit_short, limit_short * 0.005)
                target_1 = round(limit_short - (risk_pts * 1.5), 2)
                target_2 = round(limit_short - (risk_pts * 2.5), 2)

                rr_t1 = (limit_short - target_1) / max(stop_loss - limit_short, 1e-6)
                if strict_mode and rr_t1 < 1.25:
                    continue

                alpha_score = round(abs(change_pct) * rvol * (latest_vwap / max(ltp, 0.01)), 2)

                bearish_scored_stocks.append({
                    "Symbol": symbol.replace(".NS", ""),
                    "LTP": round(ltp, 2),
                    "Change": round(change_pct, 2),
                    "RVOL": rvol,
                    "Alpha_Score": alpha_score,
                    "Limit_Short": limit_short,
                    "Stop_Loss": stop_loss,
                    "Target_1": target_1,
                    "Target_2": target_2,
                    "DataFrame": df,
                    "Volume_Colors": v_col,
                })
        except Exception:
            continue

    df_res = pd.DataFrame(bearish_scored_stocks)
    if not df_res.empty:
        df_res = df_res.sort_values(by="Alpha_Score", ascending=False).reset_index(
            drop=True
        )
    return df_res


# ---------------------------------------------------------
# 3. ADVANCED INSTITUTIONAL BEARISH PLOTTING ENGINE
# ---------------------------------------------------------
def render_bearish_chart(symbol, df, v_col, entry, sl, t1, t2):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.78, 0.22],
    )
    fig.add_trace(
        go.Candlestick(
            x=df["Axis_Str"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=symbol,
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["Axis_Str"],
            y=df["VWAP"],
            mode="lines",
            name="VWAP",
            line=dict(color="#FFD700", width=1.5),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["Axis_Str"],
            y=df["EMA20"],
            mode="lines",
            name="20 EMA",
            line=dict(color="#29B6F6", width=1.2),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=df["Axis_Str"],
            y=df["Volume"],
            name="Volume",
            marker_color=v_col,
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=entry,
        line_color="#FFD700",
        line_width=1.6,
        annotation_text=f"🔻 SHORT ENTRY: ₹{entry:,.2f}",
        annotation_position="bottom left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=sl,
        line_color="#FF5252",
        line_width=1.6,
        annotation_text=f"🛑 SL: ₹{sl:,.2f}",
        annotation_position="top right",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t1,
        line_dash="dash",
        line_color="#29B6F6",
        line_width=1.4,
        annotation_text=f"🎯 T1 (1.5R): ₹{t1:,.2f}",
        annotation_position="bottom left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t2,
        line_dash="dash",
        line_color="#00E676",
        line_width=1.4,
        annotation_text=f"🚀 T2 (2.5R): ₹{t2:,.2f}",
        annotation_position="bottom right",
        row=1,
        col=1,
    )

    fig.update_layout(
        title=f"📊 {symbol} (15m) | Institutional Bearish Breakdown Blueprint",
        template="plotly_dark",
        height=520,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=40, b=30),
        yaxis=dict(side="right", title="Price (₹)", showgrid=True),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
        xaxis=dict(type="category", rangeslider_visible=False),
        xaxis2=dict(
            type="category", rangeslider_visible=False, tickmode="auto", nticks=12
        ),
    )
    return fig


# ---------------------------------------------------------
# 4. MAIN EXECUTION RENDER BLOCK
# ---------------------------------------------------------
with st.spinner("🔍 Scanning market for institutional bearish breakdown setups..."):
    df_bearish = fetch_bearish_institutional_picks(
        strict_mode=bear_mode.startswith("Strict")
    )

if df_bearish is None or df_bearish.empty:
    st.session_state.setdefault("live_scanner_picks", {})["Bearish Top 2"] = []
    st.warning(
        "⚠️ No stocks currently match bearish breakdown criteria. Try **Standard Bearish** "
        "or click **Force Refresh Bearish Scan** above."
    )
else:
    top2_bearish = df_bearish.head(2)

    # Dedicated Bearish Top 2 Strip
    st.subheader("⭐ Bearish Top 2 Short Picks (Highlighted Separately)")
    b2_cols = st.columns(len(top2_bearish))
    bearish_payload = []
    for idx_b, b_row in top2_bearish.iterrows():
        with b2_cols[idx_b]:
            st.metric(
                label=f"#{idx_b + 1} {b_row['Symbol']} (SHORT)",
                value=f"₹{b_row['LTP']:,.2f}",
                delta=f"{b_row['Change']}% | T1 ₹{b_row['Target_1']:,.2f}",
                delta_color="inverse",
            )
            st.caption(f"Short ₹{b_row['Limit_Short']:,.2f} • SL ₹{b_row['Stop_Loss']:,.2f} • RVOL {b_row['RVOL']}x")
        bearish_payload.append({
            "symbol": b_row["Symbol"],
            "side": "SHORT",
            "entry": float(b_row["Limit_Short"]),
            "sl": float(b_row["Stop_Loss"]),
            "t1": float(b_row["Target_1"]),
            "t2": float(b_row["Target_2"]),
            "notes": f"Bearish Top #{idx_b + 1} | Alpha {b_row['Alpha_Score']} | RVOL {b_row['RVOL']}x",
        })

    # --- PUSH BEARISH TOP 2 PICKS TO ANALYSER SESSION STATE ---
    st.session_state.setdefault("live_scanner_picks", {})[
        "Bearish Top 2"
    ] = bearish_payload

    if st.button("📌 Log Bearish Top 2 Picks to History Ledger", type="primary"):
        saved_2 = _save_bearish_picks_to_ledger(bearish_payload, "Bearish Top 2")
        st.success(f"Recorded {saved_2} Bearish Top 2 pick(s) to history ledger.")

    st.markdown("---")
    st.subheader("🔥 Top Verified Bearish Institutional Picks (Same-Day Short Before 3:30 PM IST)")

    for idx, row in top2_bearish.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

            with c1:
                st.markdown(f"### **#{idx+1} {row['Symbol']}**")
                st.metric(
                    label="Live LTP",
                    value=f"₹{row['LTP']:,.2f}",
                    delta=(
                        f"{row['Change']}% (Bearish Alpha: {row['Alpha_Score']} | RVOL:"
                        f" {row['RVOL']}x)"
                    ),
                    delta_color="inverse",
                )

            with c2:
                st.markdown("**Precision Short Levels**")
                st.write(f"🔻 **Short Entry:** ₹{row['Limit_Short']:,.2f}")
                st.write(f"🛑 **Stop Loss:** ₹{row['Stop_Loss']:,.2f}")

            with c3:
                st.markdown("**Profit Targets (Downside)**")
                st.write(f"🎯 **Target 1 (1.5R):** ₹{row['Target_1']:,.2f}")
                st.write(f"🚀 **Target 2 (2.5R):** ₹{row['Target_2']:,.2f}")

            with c4:
                st.markdown("**Execution Status**")
                st.error("🔴 **BEARISH INTRADAY — COVER BY 3:30 PM IST**")
                if st.button(
                    f"📋 Copy Short Payload ({row['Symbol']})",
                    key=f"bear_{row['Symbol']}",
                ):
                    st.toast(
                        f"Copied {row['Symbol']}! Short: ₹{row['Limit_Short']:,.2f} | T1:"
                        f" ₹{row['Target_1']:,.2f}"
                    )

            with st.expander(
                f"📈 Expand Chart & VWAP Breakdown Structure for #{idx+1} {row['Symbol']}"
            ):
                fig = render_bearish_chart(
                    row["Symbol"],
                    row["DataFrame"],
                    row["Volume_Colors"],
                    row["Limit_Short"],
                    row["Stop_Loss"],
                    row["Target_1"],
                    row["Target_2"],
                )
                st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

            st.markdown("---")
