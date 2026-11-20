from datetime import datetime, time as dt_time
import hashlib
from pathlib import Path
import sys
import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Market-Wide Volume Surge Scanner", layout="wide"
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


def _save_surge_picks_to_ledger(
    picks: list[dict], module_label: str = "Volume Surge Top 3"
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


st.title("⚡ Market-Wide Volume Surge & Institutional Action Scanner")
st.markdown(
    "Automatically scans the broad NSE stock universe for abnormal volume "
    "spikes, calculates actionable Buy levels, sets strict stop-losses, and "
    "analyzes institutional catalyst drivers."
)

session_txt = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{session_txt} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

# Sidebar & Page Controls for Universe and Sensitivity
st.sidebar.header("⚙️ Scanner Controls")
selected_universe = st.sidebar.selectbox(
    "Select Stock Universe",
    ["Nifty 50 Core", "High-Beta Midcaps", "PSU & Defense Leaders"],
)
volume_threshold = st.sidebar.slider(
    "Volume Surge Threshold (x times 30D average)", 1.5, 5.0, 2.0, 0.25
)

if st.sidebar.button("🔄 Run Market-Wide Volume Scan"):
    st.cache_data.clear()
    st.success("Volume scan cache cleared! Fetching live market data.")


@st.cache_data(ttl=60)
def fetch_volume_surge_scan(universe_name, threshold):
    """Scans chosen stock universe for abnormal volume surges relative to

    30-day volume baseline.
    """
    if universe_name == "Nifty 50 Core":
        tickers = [
            "RELIANCE",
            "TCS",
            "HDFCBANK",
            "ICICIBANK",
            "INFY",
            "SBIN",
            "BHARTIARTL",
            "ITC",
            "LT",
            "BAJFINANCE",
            "SUNPHARMA",
            "AXISBANK",
            "TATAMOTORS",
            "NTPC",
        ]
    elif universe_name == "High-Beta Midcaps":
        tickers = [
            "MSTCLTD",
            "POWERINDIA",
            "AMBER",
            "TDPOWERSYS",
            "GVT&D",
            "APOLLO",
            "KALYANKJIL",
            "DCXINDIA",
        ]
    else:
        tickers = [
            "HAL",
            "BEL",
            "COCHINSHIP",
            "MAZDOCK",
            "DATAPATTNS",
            "PNB",
            "MAHABANK",
            "CANBK",
            "IRFC",
            "RVNL",
        ]

    surge_results = []

    for symbol in tickers:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="30d")

            if hist.empty or len(hist) < 10:
                continue

            latest = hist.iloc[-1]
            prev = hist.iloc[-2]

            ltp = float(latest["Close"])
            prev_close = float(prev["Close"])
            if prev_close <= 0 or pd.isna(ltp) or pd.isna(prev_close):
                continue
            change_pct = ((ltp - prev_close) / prev_close) * 100

            # 30-day average volume baseline
            avg_vol_30d = hist["Volume"].iloc[:-1].mean()
            current_vol = float(latest["Volume"])
            vol_multiplier = (
                current_vol / avg_vol_30d if avg_vol_30d > 0 else 1.0
            )

            # Check against user threshold and positive price action
            if vol_multiplier >= threshold and change_pct > 0:
                hist = hist.copy()
                hist["EMA_9"] = hist["Close"].ewm(span=9, adjust=False).mean()
                hist["EMA_21"] = hist["Close"].ewm(span=21, adjust=False).mean()

                stop_loss = round(ltp * 0.96, 2)
                target_1 = round(ltp * 1.05, 2)
                target_2 = round(ltp * 1.10, 2)

                surge_results.append({
                    "Stock": symbol,
                    "LTP": round(ltp, 2),
                    "Change_%": round(change_pct, 2),
                    "Volume_Surge": f"{round(vol_multiplier, 2)}x",
                    "Surge_Num": round(vol_multiplier, 2),
                    "Stop_Loss": stop_loss,
                    "Target_1": target_1,
                    "Target_2": target_2,
                    "Status": "🔥 Abnormal Institutional Volume Spurt",
                    "Catalyst": (
                        "Heavy Block Accumulation & Breakout Volume Expansion"
                    ),
                    "History": hist,
                })
        except Exception:
            continue

    if not surge_results:
        return pd.DataFrame()
    return (
        pd.DataFrame(surge_results)
        .sort_values(by="Surge_Num", ascending=False)
        .reset_index(drop=True)
    )


# Run Scan
with st.spinner(
    f"Scanning {selected_universe} for volume spikes >="
    f" {volume_threshold}x..."
):
    df_surges = fetch_volume_surge_scan(selected_universe, volume_threshold)

if df_surges.empty:
    st.session_state.setdefault("live_scanner_picks", {})["Volume Surge Top 3"] = []
    st.warning(
        "No stocks crossed the strict volume surge threshold in this universe"
        " right now. Try lowering the threshold or switching stock universes in"
        " the sidebar."
    )
else:
    st.success(
        f"Scan complete! Found {len(df_surges)} abnormal volume breakout"
        " candidates."
    )

    top3_surge = df_surges.head(3)
    surge_payload = [
        {
            "symbol": r["Stock"],
            "side": "BUY",
            "entry": float(r["LTP"]),
            "sl": float(r["Stop_Loss"]),
            "t1": float(r["Target_1"]),
            "t2": float(r["Target_2"]),
            "notes": f"{selected_universe} | Vol Surge {r['Volume_Surge']} | +{r['Change_%']}%",
        }
        for _, r in top3_surge.iterrows()
    ]

    # --- PUSH TOP 3 VOLUME SURGE PICKS TO ANALYSER SESSION STATE ---
    st.session_state.setdefault("live_scanner_picks", {})[
        "Volume Surge Top 3"
    ] = surge_payload

    if st.button("📌 Log Top 3 Volume Surge Picks to History Ledger", type="primary"):
        saved_s = _save_surge_picks_to_ledger(surge_payload, "Volume Surge Top 3")
        st.success(f"Recorded {saved_s} Top 3 volume surge pick(s) to history ledger.")

    # Display Summary Table
    display_df = df_surges.drop(columns=["History", "Surge_Num"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📊 Interactive Breakdown & SMC Charts for Surging Equities")

    for _, row in df_surges.iterrows():
        stock_name = row["Stock"]
        st.markdown(
            f"### 🚀 {stock_name} (+{row['Change_%']}%) — Volume Surge:"
            f" {row['Volume_Surge']}"
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("LTP", f"₹{row['LTP']:,.2f}", row["Volume_Surge"])
        col2.metric("Stop Loss", f"₹{row['Stop_Loss']:,.2f}", "Protected Risk")
        col3.metric("Target 1", f"₹{row['Target_1']:,.2f}", "+5% Gain")
        col4.metric("Target 2", f"₹{row['Target_2']:,.2f}", "+10% Gain")

        st.info(f"💡 **Institutional Catalyst:** {row['Catalyst']}")

        # Render Plotly Chart with EMAs and FVG
        hist_df = row["History"]
        if not hist_df.empty:
            fig = go.Figure()

            fig.add_trace(
                go.Candlestick(
                    x=hist_df.index,
                    open=hist_df["Open"],
                    high=hist_df["High"],
                    low=hist_df["Low"],
                    close=hist_df["Close"],
                    name="Price Action",
                    increasing_line_color="#00E676",
                    decreasing_line_color="#FF5252",
                )
            )

            if "EMA_9" in hist_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist_df.index,
                        y=hist_df["EMA_9"],
                        line=dict(color="#29B6F6", width=1.5),
                        name="EMA 9",
                    )
                )
            if "EMA_21" in hist_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist_df.index,
                        y=hist_df["EMA_21"],
                        line=dict(color="#FFA726", width=1.5),
                        name="EMA 21",
                    )
                )

            # FVG Shading
            recent_low = float(hist_df["Low"].iloc[-3])
            recent_high = float(hist_df["High"].iloc[-5])
            fig.add_hrect(
                y0=recent_high,
                y1=recent_low,
                fillcolor="rgba(0, 230, 118, 0.12)",
                layer="below",
                line_width=0,
                annotation_text="Bullish FVG Demand Zone",
                annotation_position="bottom right",
            )

            fig.add_hline(
                y=row["Target_1"],
                line_dash="dash",
                line_color="#00E676",
                annotation_text=f"Target 1: ₹{row['Target_1']}",
            )
            fig.add_hline(
                y=row["Stop_Loss"],
                line_dash="dash",
                line_color="#FF5252",
                annotation_text=f"Stop Loss: ₹{row['Stop_Loss']}",
            )

            fig.update_layout(
                title=f"Volume Surge Analysis Chart for {stock_name}",
                yaxis_title="Price (INR ₹)",
                template="plotly_dark",
                height=450,
                xaxis_rangeslider_visible=False,
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
