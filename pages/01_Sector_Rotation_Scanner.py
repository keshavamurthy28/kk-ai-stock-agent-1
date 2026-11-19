import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

st.title("🗺️ Sector Heatmap & Breadth Analysis (Beginner-Friendly Guide)")
st.markdown(
    "Spot which market sectors are **stronger or weaker than Nifty 50** so you can "
    "build a focused watchlist instead of guessing blindly."
)

if st.button("🔄 Refresh Live Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

with st.expander("📘 New to Stock Markets? Read This 30-Second Guide First", expanded=True):
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

            stock_records.append({
                "Sector": sector_name,
                "Stock": sym.replace(".NS", ""),
                "LTP": round(s_close, 2),
                "Day Change %": round(s_chg, 2),
                "RS vs Nifty %": round(s_rs, 2),
                "Close Strength %": round(s_close_pos, 1),
                "RVOL": s_rvol,
                "Stock Score": s_score,
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
    # ---------------------------------------------------------
    # 1. TOMORROW'S ADVANCE SECTOR RADAR
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
    # 2. HEATMAP WITH RIGHT-SIDE CLICKABLE DAY CHANGE % COLOR SCALE
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
                color_continuous_scale=["#B71C1C", "#EF5350", "#263238", "#66BB6A", "#1B5E20"],
                color_continuous_midpoint=0,
                range_color=[-3.0, 3.0],
                hover_data=["LTP", "RS vs Nifty %", "Close Strength %", "RVOL", "Stock Score"],
            )
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{color:+.2f}%",
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

    if not filtered_stocks.empty:
        st.subheader(
            f"📋 Stocks in Selected Range ({color_band}) — {len(filtered_stocks)} Stocks"
        )
        st.dataframe(
            filtered_stocks.drop(columns=["BoxSize"]),
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

    st.markdown("---")

    # ---------------------------------------------------------
    # 3. INTERACTIVE SECTOR INSPECTOR & FULL RANKING
    # ---------------------------------------------------------
    st.subheader("🔍 Inspect Stocks Inside One Sector")
    selected_sector = st.selectbox(
        "Pick a sector to see its individual stocks:",
        df_sectors["Sector"].tolist(),
        index=0,
    )

    sector_stocks_view = df_stocks[df_stocks["Sector"] == selected_sector].drop(
        columns=["Sector", "BoxSize"]
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

    st.markdown("---")
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
