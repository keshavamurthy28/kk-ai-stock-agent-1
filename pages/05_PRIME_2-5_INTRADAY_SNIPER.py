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

# Page Configuration
st.set_page_config(
    page_title="Institutional Alpha Intraday Sniper | MU₹A Rendezvous",
    layout="wide",
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


def _save_prime_picks_to_ledger(picks: list[dict], module_label: str = "PRIME Top 3") -> int:
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


st.title("🎯 Institutional Alpha Intraday Sniper Terminal (Anti-Trap)")
st.markdown(
    "**Beginner-Friendly Sniper Guide:** Scans NSE stocks for intraday trend alignment "
    "(above VWAP & 20 EMA), volume surge (`RVOL`), and volatility-based targets/stop-loss "
    "to help you plan disciplined setups—not guaranteed profits."
)

# ---------------------------------------------------------
# 1. TOP CONTROLS & LIVE REFRESH
# ---------------------------------------------------------
col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([2.2, 1.5, 1.2, 1.0])
with col_ctrl1:
    session_badge = (
        "🟢 NSE Live Session (9:15 AM – 3:30 PM IST)"
        if is_market_open
        else "🟡 Pre-Market / Market Closed"
    )
    st.caption(f"{session_badge} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")
with col_ctrl2:
    sniper_mode = st.selectbox(
        "🛡️ Sniper Anti-Trap Filter:",
        ["Strict (RVOL ≥ 1.3x & ≤5.5% Move)", "Standard Sniper"],
        index=0,
    )
with col_ctrl3:
    auto_refresh = st.toggle("Auto-Refresh (60s)", value=False)
with col_ctrl4:
    st.write("")
    if st.button("🔄 Force Refresh Sniper Scans", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cleared cache and running fresh sniper scan...", icon="⚡")
        st.rerun()

with st.expander("📘 Beginner Guide: How to Read Sniper Levels & Book Profit", expanded=False):
    st.markdown(
        "- **VWAP & 20 EMA:** Price holding above VWAP and 20 EMA shows intraday buyer strength; dropping below suggests weakness.\n"
        "- **RVOL (Relative Volume):** Above **1.1x–1.3x+** shows stronger activity than usual.\n"
        "- **When to Buy:** Wait until active market hours (**9:15 AM IST**) and look for orderly strength rather than chasing sudden spikes blindly.\n"
        "- **When to Book Profit:** Consider booking partial or full profit near **Target 1** first rather than holding out blindly for **Target 2**, and honor your **Stop-Loss** if momentum fails. Not financial advice."
    )

# Clean Stock-to-Sector Mapping (Standardized without .NS suffixes)
STOCK_SECTOR_MAP = {
    "RELIANCE": "Energy & Oil",
    "TCS": "Software & Services",
    "HDFCBANK": "Banking & Finance",
    "ICICIBANK": "Banking & Finance",
    "INFY": "Software & Services",
    "SBIN": "Banking & Finance",
    "ITC": "FMCG",
    "BHARTIARTL": "Telecommunications",
    "LICI": "Financial Services",
    "AXISBANK": "Banking & Finance",
    "KOTAKBANK": "Banking & Finance",
    "LT": "Capital Goods",
    "BAJFINANCE": "Banking & Finance",
    "MARUTI": "Automobiles",
    "SUNPHARMA": "Healthcare",
    "TITAN": "Consumer Durables",
    "ADANIENT": "Diversified",
    "ADANIPORTS": "Transportation",
    "TATASTEEL": "Metals & Mining",
    "NTPC": "Energy & Oil",
    "POWERGRID": "Energy & Oil",
    "COALINDIA": "Energy & Oil",
    "ONGC": "Energy & Oil",
    "BAJAJFINSV": "Banking & Finance",
    "WIPRO": "Software & Services",
    "ASIANPAINT": "Consumer Durables",
    "HCLTECH": "Software & Services",
    "GRASIM": "Cement & Construction",
    "TECHM": "Software & Services",
    "INDUSINDBK": "Banking & Finance",
    "DEEPAKFERT": "Fertilizers",
    "ANGELONE": "Financial Services",
    "HONASA": "FMCG",
    "MAXHEALTH": "Healthcare",
    "PNB": "Banking & Finance",
    "CANBK": "Banking & Finance",
    "TORNTPHARM": "Healthcare",
    "SUPREMEIND": "Capital Goods",
    "ETERNAL": "Retailing",
    "BELRISE": "Automobiles",
    "TATACOMM": "Telecommunications",
    "PIDILITIND": "Chemicals",
    "SRF": "Chemicals",
    "HAL": "Defense & Aerospace",
    "BEL": "Defense & Aerospace",
}


def _extract_ticker_df(raw_df, sym, total_tickers):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if total_tickers > 1 and isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


# ---------------------------------------------------------
# 2. FAST BATCH SNIPER SCANNER (5m INTRADAY + 14d DAILY ATR)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_institutional_sniper_picks(strict_mode=True):
    market_universe = list(STOCK_SECTOR_MAP.keys())
    symbols = [f"{s}.NS" for s in market_universe]
    sniper_rows = []

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
        raw_1d = yf.download(
            symbols,
            period="20d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    min_rvol_req = 1.30 if strict_mode else 1.10
    max_chg_req = 5.50 if strict_mode else 6.50
    min_rr_req = 1.15 if strict_mode else 0.0

    for clean_sym in market_universe:
        symbol = f"{clean_sym}.NS"
        sector_name = STOCK_SECTOR_MAP.get(clean_sym, "General")
        try:
            df = _extract_ticker_df(raw_5m, symbol, len(symbols)).dropna(
                subset=["Close", "Open", "High", "Low"]
            )
            if df is None or df.empty or len(df) < 20:
                continue

            df = df.reset_index()
            df.rename(columns={df.columns[0]: "Time"}, inplace=True)
            df["Time"] = pd.to_datetime(df["Time"])
            if df["Time"].dt.tz is not None:
                df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

            is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
            df["Axis_Str"] = np.where(
                is_new_day,
                df["Time"].dt.strftime("%d %b '%y  %H:%M"),
                df["Time"].dt.strftime("%H:%M  (%d %b)"),
            )

            df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
            vol_series = df["Volume"] if "Volume" in df else pd.Series(0.0, index=df.index)
            typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0

            if vol_series.sum() > 0:
                df["VWAP"] = (
                    (typical_price * vol_series)
                    .groupby(df["Time"].dt.date)
                    .cumsum()
                    / vol_series.groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
                ).fillna(df["EMA20"])
            else:
                df["VWAP"] = typical_price.rolling(20, min_periods=1).mean()

            ltp = float(df["Close"].iloc[-1])
            df["Date"] = df["Time"].dt.date
            unique_dates = df["Date"].unique()
            if len(unique_dates) >= 2:
                prev_close = float(df[df["Date"] == unique_dates[-2]]["Close"].iloc[-1])
            else:
                prev_close = float(df["Open"].iloc[0])

            if prev_close <= 0 or np.isnan(ltp) or np.isnan(prev_close):
                continue

            change_pct = ((ltp - prev_close) / prev_close) * 100.0

            avg_vol = float(vol_series.iloc[-20:-2].mean()) if len(vol_series) >= 22 else 0.0
            curr_vol = float(vol_series.iloc[-2]) if len(vol_series) >= 2 and pd.notna(vol_series.iloc[-2]) else 0.0
            rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 and curr_vol > 0 else 1.0

            latest_vwap = float(df["VWAP"].iloc[-1])
            latest_ema = float(df["EMA20"].iloc[-1])

            df_daily = _extract_ticker_df(raw_1d, symbol, len(symbols)).dropna(
                subset=["High", "Low", "Close"]
            )
            if df_daily is not None and not df_daily.empty and len(df_daily) >= 5:
                d_tail = df_daily.tail(14)
                tr = np.maximum(
                    d_tail["High"] - d_tail["Low"],
                    np.maximum(
                        abs(d_tail["High"] - d_tail["Close"].shift(1)),
                        abs(d_tail["Low"] - d_tail["Close"].shift(1)),
                    ),
                )
                atr_14 = float(tr.dropna().mean()) if not tr.dropna().empty else (ltp * 0.03)
            else:
                atr_14 = ltp * 0.03

            if (
                0.4 <= change_pct <= max_chg_req
                and ltp >= latest_vwap
                and ltp >= latest_ema
                and rvol >= min_rvol_req
            ):
                v_avg = vol_series.rolling(20, min_periods=1).mean()
                v_col = [
                    (
                        "#00E676"
                        if (c >= o and v >= 1.3 * va)
                        else (
                            "#FF5252"
                            if (c < o and v >= 1.3 * va)
                            else (
                                "rgba(0,230,118,0.38)" if c >= o else "rgba(255,82,82,0.38)"
                            )
                        )
                    )
                    for o, c, v, va in zip(df["Open"], df["Close"], vol_series, v_avg)
                ]

                vwap_buy = round(latest_vwap * 0.995, 2)
                stop_loss = round(latest_vwap * 0.990, 2)
                t1 = round(ltp + (atr_14 * 0.8), 2)
                t2 = round(ltp + (atr_14 * 1.3), 2)

                risk_from_buy = max(vwap_buy - stop_loss, vwap_buy * 0.004)
                reward_t1 = max(t1 - vwap_buy, 0.01)
                rr_ratio = reward_t1 / risk_from_buy

                if strict_mode and rr_ratio < min_rr_req:
                    continue

                alpha_score = round(change_pct * rvol * (ltp / max(latest_vwap, 0.01)), 2)

                sniper_rows.append({
                    "Symbol": clean_sym,
                    "Sector": sector_name,
                    "LTP": round(ltp, 2),
                    "Change": round(change_pct, 2),
                    "RVOL": rvol,
                    "Alpha_Score": alpha_score,
                    "ATR": round(atr_14, 2),
                    "VWAP_Buy": vwap_buy,
                    "Stop_Loss": stop_loss,
                    "Target_1": t1,
                    "Target_2": t2,
                    "DataFrame": df,
                    "Volume_Colors": v_col,
                })
        except Exception:
            continue

    if not sniper_rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(sniper_rows)
        .sort_values(by="Alpha_Score", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------
# 3. PLOTTING FUNCTION
# ---------------------------------------------------------
def render_sniper_chart(symbol, df, v_col, entry, sl, t1, t2, atr):
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
        annotation_text=f"🟡 VWAP BUY: ₹{entry:,.2f}",
        annotation_position="bottom left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=sl,
        line_color="#FF5252",
        line_width=1.6,
        annotation_text=f"🛑 SL: ₹{sl:,.2f}",
        annotation_position="bottom right",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t1,
        line_dash="dash",
        line_color="#29B6F6",
        line_width=1.4,
        annotation_text=f"🎯 TARGET 1: ₹{t1:,.2f}",
        annotation_position="top left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t2,
        line_dash="dash",
        line_color="#00E676",
        line_width=1.4,
        annotation_text=f"🚀 TARGET 2: ₹{t2:,.2f}",
        annotation_position="top right",
        row=1,
        col=1,
    )
    fig.update_layout(
        title=f"📊 {symbol} (5m) | 14D ATR: ₹{atr}",
        template="plotly_dark",
        height=520,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=40, b=30),
        yaxis=dict(side="right", title="Price (₹)", showgrid=True),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
        xaxis=dict(type="category", rangeslider_visible=False),
        xaxis2=dict(type="category", rangeslider_visible=False, tickmode="auto", nticks=12),
    )
    return fig


# ---------------------------------------------------------
# 4. MAIN RENDER BLOCK
# ---------------------------------------------------------
with st.spinner("🎯 Scanning market-wide intraday sniper setups..."):
    df_sniper = fetch_institutional_sniper_picks(
        strict_mode=sniper_mode.startswith("Strict")
    )

if df_sniper is None or df_sniper.empty:
    st.warning(
        "⚠️ No stocks currently meet the sniper confluence filters. "
        "Try **Standard Sniper** or click **Force Refresh Sniper Scans** above."
    )
else:
    top3_sniper = df_sniper.head(3)

    # Dedicated PRIME Top 3 Strip
    st.subheader("⭐ PRIME Top 3 Sniper Picks (Highlighted Separately)")
    p3_cols = st.columns(len(top3_sniper))
    prime_payload = []
    for idx_p, p_row in top3_sniper.iterrows():
        with p3_cols[idx_p]:
            st.metric(
                label=f"#{idx_p + 1} {p_row['Symbol']} ({p_row['Sector']})",
                value=f"₹{p_row['LTP']:,.2f}",
                delta=f"+{p_row['Change']}% | T1 ₹{p_row['Target_1']:,.2f}",
            )
            st.caption(f"Buy ₹{p_row['VWAP_Buy']:,.2f} • SL ₹{p_row['Stop_Loss']:,.2f} • RVOL {p_row['RVOL']}x")
        prime_payload.append({
            "symbol": p_row["Symbol"],
            "side": "BUY",
            "entry": float(p_row["VWAP_Buy"]),
            "sl": float(p_row["Stop_Loss"]),
            "t1": float(p_row["Target_1"]),
            "t2": float(p_row["Target_2"]),
            "notes": f"PRIME #{idx_p + 1} | Alpha {p_row['Alpha_Score']} | RVOL {p_row['RVOL']}x",
        })

    if st.button("📌 Log PRIME Top 3 Picks to History Ledger", type="primary"):
        saved_3 = _save_prime_picks_to_ledger(prime_payload, "PRIME Top 3")
        st.success(f"Recorded {saved_3} PRIME Top 3 pick(s) to history ledger.")

    st.markdown("---")
    st.subheader("🏆 Intraday Sniper Ranking (VWAP, 20 EMA & RVOL Filtered)")
    for idx, row in top3_sniper.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
            with c1:
                st.markdown(f"### **#{idx+1} {row['Symbol']}**")
                st.caption(f"📂 **Sector:** {row['Sector']}")
                st.metric(
                    label="Price",
                    value=f"₹{row['LTP']:,.2f}",
                    delta=f"+{row['Change']}% (Alpha: {row['Alpha_Score']} | RVOL: {row['RVOL']}x)",
                )
            with c2:
                st.markdown("**Sniper Reference Levels**")
                st.write(f"🟡 **VWAP Buy Zone:** ₹{row['VWAP_Buy']:,.2f}")
                st.write(f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']:,.2f}")
            with c3:
                st.markdown("**ATR Target Matrix**")
                st.write(f"🎯 **Target 1:** ₹{row['Target_1']:,.2f}")
                st.write(f"🚀 **Target 2:** ₹{row['Target_2']:,.2f}")
            with c4:
                st.markdown("**Plan Status**")
                st.success("✅ **SNIPER BUY WATCH**")
                if st.button(
                    f"📋 Copy Sniper Payload ({row['Symbol']})", key=f"snip_{row['Symbol']}"
                ):
                    st.toast(
                        f"Copied {row['Symbol']} ({row['Sector']})! VWAP Buy: "
                        f"₹{row['VWAP_Buy']:,.2f} | T1: ₹{row['Target_1']:,.2f}"
                    )

            with st.expander(
                f"📈 Expand 5m Intraday Sniper Chart & Levels for #{idx+1} "
                f"{row['Symbol']} ({row['Sector']})"
            ):
                fig = render_sniper_chart(
                    row["Symbol"],
                    row["DataFrame"],
                    row["Volume_Colors"],
                    row["VWAP_Buy"],
                    row["Stop_Loss"],
                    row["Target_1"],
                    row["Target_2"],
                    row["ATR"],
                )
                st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

            st.markdown("---")

if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
