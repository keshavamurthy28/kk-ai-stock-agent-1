from datetime import datetime
import hashlib
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_sector_picks_to_ledger(
    picks: list[dict], module_label: str = "Sector Rotation Top 2 Green & Red"
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


st.title("🗺️ Sector Heatmap & Breadth Analysis (Beginner-Friendly Guide)")
st.markdown(
    "Spot which market sectors are **stronger or weaker than Nifty 50** so you can "
    "build a focused watchlist instead of guessing blindly."
)

col_btn1, col_btn2, col_btn3 = st.columns([1.2, 1.8, 2.5])
with col_btn1:
    if st.button("🔄 Refresh Live Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
    sector_pick_mode = st.selectbox(
        "🛡️ Sector Pick Quality:",
        ["Strict (RVOL ≥ 1.15x & Strong RS)", "All Leaders / Laggards"],
        index=0,
    )
with col_btn3:
    st.write("")
    show_extra_tables = st.toggle("Show Detailed Data Tables", value=False)

with st.expander("📘 New to Stock Markets? Read This 30-Second Guide First", expanded=False):
    st.markdown(
        "- **Why Sectors Matter:** Stocks in strong sectors often get more buyer support; weak sectors can drag prices down.\n"
        "- **RS vs Nifty % (Relative Strength):** Positive (`+`) means the sector/stock performed **better** than Nifty 50; negative (`-`) means **worse**.\n"
        "- **Close Strength %:** Close to **100%** means it finished near the day's high (strong buying); close to **0%** means near the day's low (selling pressure).\n"
        "- **RVOL (Relative Volume):** Around **1.0x** is normal volume; **1.5x+** means noticeably higher activity than recent days.\n"
        "- **Safety Reminder:** This is a **watchlist & research tool**, not guaranteed advice. Always use a stop-loss and start small."
    )

# Core Sectoral Indices + Top Constituent Stocks for Drill-Down & Real Volume
SECTOR_CONSTITUENTS = {
    "NIFTY PSU BANK": {
        "index": "^CNXPSUBANK",
        "stocks": ["SBIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS", "INDIANB.NS"],
    },
    "NIFTY BANK": {
        "index": "^NSEBANK",
        "stocks": ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS", "AUBANK.NS"],
    },
    "NIFTY IT": {
        "index": "^CNXIT",
        "stocks": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "MPHASIS.NS"],
    },
    "NIFTY PHARMA": {
        "index": "^CNXPHARMA",
        "stocks": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "AUROPHARMA.NS"],
    },
    "NIFTY AUTO": {
        "index": "^CNXAUTO",
        "stocks": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "TVSMOTOR.NS"],
    },
    "NIFTY FMCG": {
        "index": "^CNXFMCG",
        "stocks": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", "VBL.NS"],
    },
    "NIFTY METAL": {
        "index": "^CNXMETAL",
        "stocks": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "VEDL.NS", "NMDC.NS", "NATIONALUM.NS"],
    },
    "NIFTY ENERGY": {
        "index": "^CNXENERGY",
        "stocks": ["RELIANCE.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS", "COALINDIA.NS", "TATAPOWER.NS"],
    },
    "NIFTY REALTY": {
        "index": "^CNXREALTY",
        "stocks": ["DLF.NS", "MACROTECH.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "PHOENIXLTD.NS"],
    },
    "NIFTY INFRA": {
        "index": "^CNXINFRA",
        "stocks": ["LT.NS", "BHARTIARTL.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "GRASIM.NS", "SIEMENS.NS"],
    },
    "NIFTY FIN SERVICE": {
        "index": "NIFTY_FIN_SERVICE.NS",
        "stocks": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "JIOFIN.NS", "CHOLAFIN.NS", "SHRIRAMFIN.NS", "PFC.NS"],
    },
}


def _extract_ticker_df(raw_df, ticker):
    """Safely extracts a single ticker DataFrame from yf.download output."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if ticker in raw_df.columns.get_level_values(0):
            return raw_df[ticker].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=300)
def fetch_drilldown_sector_data():
    all_tickers = ["^NSEI"]
    for info in SECTOR_CONSTITUENTS.values():
        all_tickers.append(info["index"])
        all_tickers.extend(info["stocks"])
    all_tickers = sorted(list(set(all_tickers)))

    raw = yf.download(
        all_tickers, period="5d", interval="1d", group_by="ticker", progress=False
    )
    nifty_df = _extract_ticker_df(raw, "^NSEI").dropna(subset=["Close"])
    if len(nifty_df) < 2:
        return None, None, 0.0

    nifty_chg = (
        (float(nifty_df["Close"].iloc[-1]) - float(nifty_df["Close"].iloc[-2]))
        / float(nifty_df["Close"].iloc[-2])
    ) * 100

    sector_records = []
    stock_records = []

    for sector_name, info in SECTOR_CONSTITUENTS.items():
        df_idx = _extract_ticker_df(raw, info["index"]).dropna(subset=["Close", "High", "Low"])
        if len(df_idx) < 2:
            continue

        close_today = float(df_idx["Close"].iloc[-1])
        close_prev = float(df_idx["Close"].iloc[-2])
        high_today = float(df_idx["High"].iloc[-1])
        low_today = float(df_idx["Low"].iloc[-1])

        if close_prev == 0 or np.isnan(close_today) or np.isnan(close_prev):
            continue

        day_chg = ((close_today - close_prev) / close_prev) * 100
        rel_strength = day_chg - nifty_chg
        candle_range = high_today - low_today
        close_pos = (
            ((close_today - low_today) / candle_range) * 100
            if candle_range > 0
            else 50.0
        )

        sector_rvols = []
        for sym in info["stocks"]:
            df_s = _extract_ticker_df(raw, sym).dropna(subset=["Close", "High", "Low"])
            if len(df_s) < 2:
                continue

            s_close = float(df_s["Close"].iloc[-1])
            s_prev = float(df_s["Close"].iloc[-2])
            s_high = float(df_s["High"].iloc[-1])
            s_low = float(df_s["Low"].iloc[-1])

            if s_prev == 0 or any(np.isnan(x) for x in [s_close, s_prev, s_high, s_low]):
                continue

            s_vol = float(df_s["Volume"].iloc[-1]) if "Volume" in df_s and pd.notna(df_s["Volume"].iloc[-1]) else 0.0
            vol_history = df_s["Volume"].iloc[:-1].dropna() if "Volume" in df_s and len(df_s) > 2 else pd.Series(dtype=float)
            s_vol_avg = float(vol_history.mean()) if not vol_history.empty else s_vol

            s_chg = ((s_close - s_prev) / s_prev) * 100
            s_rs = s_chg - nifty_chg
            s_range = s_high - s_low
            s_close_pos = (
                ((s_close - s_low) / s_range) * 100 if s_range > 0 else 50.0
            )
            s_rvol = round(s_vol / s_vol_avg, 2) if s_vol_avg > 0 and s_vol > 0 else 1.0
            sector_rvols.append(s_rvol)

            s_score = round(
                float(np.clip((s_rs + 2.5) * 12, 0, 45))
                + float((s_close_pos / 100.0) * 35)
                + float(np.clip(s_rvol * 10, 0, 20)),
                1,
            )
            chg_rounded = round(s_chg, 2)

            if s_rs >= 0:
                ref_entry = round(s_close * 0.996, 2)
                ref_sl = round(s_close * 0.982, 2)
                ref_t1 = round(s_close * 1.021, 2)
                ref_t2 = round(s_close * 1.038, 2)
            else:
                ref_entry = round(s_close * 1.003, 2)
                ref_sl = round(s_close * 1.016, 2)
                ref_t1 = round(s_close * 0.980, 2)
                ref_t2 = round(s_close * 0.962, 2)

            stock_records.append({
                "Sector": sector_name,
                "Stock": sym.replace(".NS", ""),
                "LTP": round(s_close, 2),
                "Day Change %": chg_rounded,
                "ChangeLabel": f"{chg_rounded:+.2f}%",
                "RS vs Nifty %": round(s_rs, 2),
                "Close Strength %": round(s_close_pos, 1),
                "RVOL": s_rvol,
                "Stock Score": s_score,
                "Ref_Entry": ref_entry,
                "Ref_SL": ref_sl,
                "Ref_T1": ref_t1,
                "Ref_T2": ref_t2,
                "BoxSize": max(s_score, 15.0),
            })

        avg_sector_rvol = round(float(np.mean(sector_rvols)), 2) if sector_rvols else 1.0

        rs_score = float(np.clip((rel_strength + 2.0) * 15, 0, 45))
        close_score = float((close_pos / 100.0) * 35)
        vol_score = float(np.clip(avg_sector_rvol * 10, 0, 20))
        total_score = round(rs_score + close_score + vol_score, 1)

        if total_score >= 65 and rel_strength > 0:
            signal = "🔥 STRONG WATCHLIST (Outperforming)"
        elif total_score >= 52 and rel_strength > 0:
            signal = "🟢 POSITIVE WATCHLIST (Above Nifty)"
        elif rel_strength < -1.0 and close_pos < 30:
            signal = "🔴 WEAK / LAGGING SECTOR"
        else:
            signal = "⚪ MIXED / SIDEWAYS"

        sector_records.append({
            "Sector": sector_name,
            "LTP": round(close_today, 2),
            "Day Change %": round(day_chg, 2),
            "RS vs Nifty %": round(rel_strength, 2),
            "Close Strength %": round(close_pos, 1),
            "RVOL": f"{avg_sector_rvol}x",
            "Momentum Score": total_score,
            "Beginner Takeaway": signal,
        })

    if not sector_records or not stock_records:
        return None, None, round(float(nifty_chg), 2)

    df_sec = (
        pd.DataFrame(sector_records)
        .dropna(subset=["Day Change %", "Momentum Score"])
        .sort_values(by="Momentum Score", ascending=False)
        .reset_index(drop=True)
    )
    df_stk = (
        pd.DataFrame(stock_records)
        .dropna(subset=["Day Change %", "Stock Score"])
        .sort_values(by="Stock Score", ascending=False)
        .reset_index(drop=True)
    )
    return df_sec, df_stk, round(float(nifty_chg), 2)


df_sectors, df_stocks, nifty_day_chg = fetch_drilldown_sector_data()

if df_sectors is not None and not df_sectors.empty and df_stocks is not None and not df_stocks.empty:
    strict_sec_mode = sector_pick_mode.startswith("Strict")

    # ---------------------------------------------------------
    # 1. TOP SECTORS TO WATCH
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("🔮 Top Sectors to Watch Next (Strength vs. Nifty)")
    st.caption(
        f"Compares sector movement against Nifty 50 ({nifty_day_chg:+.2f}%), "
        "where the price closed in the day's range, and trading volume."
    )

    top_2 = df_sectors.head(2)
    col1, col2 = st.columns(2)

    with col1:
        s1 = top_2.iloc[0]
        top_s1_stocks = ", ".join(
            df_stocks[df_stocks["Sector"] == s1["Sector"]].head(3)["Stock"].tolist()
        )
        st.success(
            f"**#1 STRONGEST SECTOR: {s1['Sector']}**\n\n"
            f"• **Strength Score:** {s1['Momentum Score']}/100 | **Vs. Nifty:** {s1['RS vs Nifty %']:+.2f}%\n"
            f"• **Where It Closed:** Top {max(0, 100 - s1['Close Strength %']):.0f}% of day's range ({s1['RVOL']} Vol)\n"
            f"• **Stocks to Study First:** **{top_s1_stocks}**"
        )

    if len(top_2) > 1:
        with col2:
            s2 = top_2.iloc[1]
            top_s2_stocks = ", ".join(
                df_stocks[df_stocks["Sector"] == s2["Sector"]].head(3)["Stock"].tolist()
            )
            st.info(
                f"**#2 RUNNER-UP SECTOR: {s2['Sector']}**\n\n"
                f"• **Strength Score:** {s2['Momentum Score']}/100 | **Vs. Nifty:** {s2['RS vs Nifty %']:+.2f}%\n"
                f"• **Where It Closed:** {s2['Close Strength %']:.0f}% of day's range ({s2['RVOL']} Vol)\n"
                f"• **Stocks to Study First:** **{top_s2_stocks}**"
            )

    st.markdown("---")

    # ---------------------------------------------------------
    # 1B. DEDICATED TOP 2 GREEN & TOP 2 RED SECTOR PICKS
    # ---------------------------------------------------------
    st.subheader("⭐ Sector Rotation Top 2 Green (Outperformers) & Top 2 Red (Laggards)")
    green_sec_pool = df_stocks[df_stocks["RS vs Nifty %"] > 0].copy()
    red_sec_pool = df_stocks[df_stocks["RS vs Nifty %"] < 0].copy()

    if strict_sec_mode:
        g_strict = green_sec_pool[(green_sec_pool["RVOL"] >= 1.15) & (green_sec_pool["Close Strength %"] >= 55.0)]
        if not g_strict.empty:
            green_sec_pool = g_strict
        r_strict = red_sec_pool[(red_sec_pool["RVOL"] >= 1.15) & (red_sec_pool["Close Strength %"] <= 45.0)]
        if not r_strict.empty:
            red_sec_pool = r_strict

    top2_sec_green = green_sec_pool.sort_values(
        by=["Stock Score", "RS vs Nifty %"], ascending=[False, False]
    ).head(2).reset_index(drop=True)
    top2_sec_red = red_sec_pool.sort_values(
        by=["Stock Score", "RS vs Nifty %"], ascending=[True, True]
    ).head(2).reset_index(drop=True)

    sec_ledger_payload = []
    sg_col, sr_col = st.columns(2)

    with sg_col:
        st.markdown("#### 🟢 Top 2 Green — Sector Leaders (Long Bias)")
        if top2_sec_green.empty:
            st.info("No positive relative-strength sector stocks matched.")
        else:
            for idx_sg, sg_row in top2_sec_green.iterrows():
                st.success(
                    f"**#{idx_sg + 1} GREEN: {sg_row['Stock']} ({sg_row['Sector']})** — LTP ₹{sg_row['LTP']:,.2f} ({sg_row['Day Change %']:+.2f}%)\n\n"
                    f"• **RS vs Nifty:** {sg_row['RS vs Nifty %']:+.2f}% | **Score:** {sg_row['Stock Score']}/100 | **RVOL:** {sg_row['RVOL']}x\n\n"
                    f"• **Watch Buy:** ₹{sg_row['Ref_Entry']:,.2f} | **SL:** ₹{sg_row['Ref_SL']:,.2f} | **T1:** ₹{sg_row['Ref_T1']:,.2f} | **T2:** ₹{sg_row['Ref_T2']:,.2f}"
                )
                sec_ledger_payload.append({
                    "symbol": sg_row["Stock"],
                    "side": "BUY",
                    "entry": float(sg_row["Ref_Entry"]),
                    "sl": float(sg_row["Ref_SL"]),
                    "t1": float(sg_row["Ref_T1"]),
                    "t2": float(sg_row["Ref_T2"]),
                    "notes": f"Sector Rotation Green #{idx_sg + 1} ({sg_row['Sector']}) | RS {sg_row['RS vs Nifty %']:+.2f}%",
                })

    with sr_col:
        st.markdown("#### 🔴 Top 2 Red — Sector Laggards (Short Bias)")
        if top2_sec_red.empty:
            st.info("No negative relative-strength sector stocks matched.")
        else:
            for idx_sr, sr_row in top2_sec_red.iterrows():
                st.error(
                    f"**#{idx_sr + 1} RED: {sr_row['Stock']} ({sr_row['Sector']})** — LTP ₹{sr_row['LTP']:,.2f} ({sr_row['Day Change %']:+.2f}%)\n\n"
                    f"• **RS vs Nifty:** {sr_row['RS vs Nifty %']:+.2f}% | **Score:** {sr_row['Stock Score']}/100 | **RVOL:** {sr_row['RVOL']}x\n\n"
                    f"• **Watch Short:** ₹{sr_row['Ref_Entry']:,.2f} | **SL:** ₹{sr_row['Ref_SL']:,.2f} | **T1:** ₹{sr_row['Ref_T1']:,.2f} | **T2:** ₹{sr_row['Ref_T2']:,.2f}"
                )
                sec_ledger_payload.append({
                    "symbol": sr_row["Stock"],
                    "side": "SHORT",
                    "entry": float(sr_row["Ref_Entry"]),
                    "sl": float(sr_row["Ref_SL"]),
                    "t1": float(sr_row["Ref_T1"]),
                    "t2": float(sr_row["Ref_T2"]),
                    "notes": f"Sector Rotation Red #{idx_sr + 1} ({sr_row['Sector']}) | RS {sr_row['RS vs Nifty %']:+.2f}%",
                })

    if sec_ledger_payload and st.button(
        "📌 Log Sector Rotation Top 2 Green & Red Picks to History Ledger", type="primary"
    ):
        saved_sec = _save_sector_picks_to_ledger(
            sec_ledger_payload, "Sector Rotation Top 2 Green & Red"
        )
        st.success(f"Recorded {saved_sec} Sector Rotation Top 2 Green/Red pick(s) to history ledger.")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. HEATMAP WITH RIGHT-SIDE FILTER
    # ---------------------------------------------------------
    st.subheader("🗺️ Interactive Sector → Stock Drill-Down Heatmap")
    st.caption(
        "Click a Sector box to zoom in, or filter by Day Change % on the right. "
        "Green = gained today, Red = fell today."
    )

    map_col, scale_col = st.columns([0.88, 0.12])

    with scale_col:
        st.markdown("**Day Change %**")
        color_band = st.radio(
            "Day Change %",
            options=[
                "All",
                "🟩 +2% to +5%",
                "🟢 +1% to +2%",
                "🌿 0% to +1%",
                "🔻 0% to -1%",
                "🔴 -1% to -2%",
                "🟥 -2% to -5%",
            ],
            index=0,
            label_visibility="collapsed",
        )

    band_limits = {
        "All": (-10.0, 10.0),
        "🟩 +2% to +5%": (2.0, 10.0),
        "🟢 +1% to +2%": (1.0, 2.0),
        "🌿 0% to +1%": (0.0, 1.0),
        "🔻 0% to -1%": (-1.0, 0.0),
        "🔴 -1% to -2%": (-2.0, -1.0),
        "🟥 -2% to -5%": (-10.0, -2.0),
    }
    min_c, max_c = band_limits[color_band]

    filtered_stocks = df_stocks[
        (df_stocks["Day Change %"] >= min_c) & (df_stocks["Day Change %"] <= max_c)
    ].copy()

    with map_col:
        if not filtered_stocks.empty:
            fig = px.treemap(
                filtered_stocks,
                path=[px.Constant("ALL NSE SECTORS"), "Sector", "Stock"],
                values="BoxSize",
                color="Day Change %",
                custom_data=["ChangeLabel"],
                color_continuous_scale=["#B71C1C", "#EF5350", "#263238", "#66BB6A", "#1B5E20"],
                color_continuous_midpoint=0,
                range_color=[-3.0, 3.0],
                hover_data=["LTP", "RS vs Nifty %", "Close Strength %", "RVOL", "Stock Score"],
            )
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{customdata[0]}",
                textfont=dict(size=13),
                maxdepth=3,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(
                template="plotly_dark",
                height=560,
                margin=dict(l=5, r=5, t=25, b=5),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No stocks currently in {color_band}. Try 'All' or another range on the right.")

    st.markdown("---")

    # ---------------------------------------------------------
    # 3. FOCUSED SECTOR INSPECTOR
    # ---------------------------------------------------------
    st.subheader("🔍 Inspect Stocks Inside One Sector")
    selected_sector = st.selectbox(
        "Pick a sector to see its individual stocks:",
        df_sectors["Sector"].tolist(),
        index=0,
    )

    clean_drop = ["Sector", "BoxSize", "ChangeLabel", "Ref_Entry", "Ref_SL", "Ref_T1", "Ref_T2"]
    sector_stocks_view = df_stocks[df_stocks["Sector"] == selected_sector].drop(
        columns=clean_drop
    )
    st.dataframe(
        sector_stocks_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stock Score": st.column_config.ProgressColumn(
                "Stock Score", format="%.1f", min_value=0, max_value=100
            ),
            "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
            "RVOL": st.column_config.NumberColumn(format="%.2fx"),
        },
    )

    # ---------------------------------------------------------
    # 4. OPTIONAL DETAILED TABLES
    # ---------------------------------------------------------
    if show_extra_tables:
        st.markdown("---")
        if not filtered_stocks.empty:
            st.subheader(
                f"📋 Stocks in Selected Range ({color_band}) — {len(filtered_stocks)} Stocks"
            )
            st.dataframe(
                filtered_stocks.drop(columns=clean_drop),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Stock Score": st.column_config.ProgressColumn(
                        "Stock Score", format="%.1f", min_value=0, max_value=100
                    ),
                    "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
                    "RVOL": st.column_config.NumberColumn(format="%.2fx"),
                },
            )

        st.subheader("📊 Full Sector Ranking Table")
        st.dataframe(
            df_sectors,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Momentum Score": st.column_config.ProgressColumn(
                    "Momentum Score", format="%.1f", min_value=0, max_value=100
                ),
                "Day Change %": st.column_config.NumberColumn(format="%+.2f%%"),
                "RS vs Nifty %": st.column_config.NumberColumn(format="%+.2f%%"),
                "Close Strength %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
else:
    st.warning("⚠️ Unable to fetch sectoral index data right now. Please click **Refresh Live Data**.")
