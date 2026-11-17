import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Connected Sector & Breakout Terminal", layout="wide")

# ---------------------------------------------------------
# 0. NAVIGATION STATE (3-Level Drill-Down)
# ---------------------------------------------------------
if "nav_sector" not in st.session_state:
    st.session_state.nav_sector = None
if "nav_stock" not in st.session_state:
    st.session_state.nav_stock = None

def reset_to_all():
    st.session_state.nav_sector = None
    st.session_state.nav_stock = None

def reset_to_sector():
    st.session_state.nav_stock = None

# ---------------------------------------------------------
# 1. CURATED NSE SECTOR UNIVERSE
# ---------------------------------------------------------
SECTOR_STOCKS = {
    "Banking & Finance": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS", "SHRIRAMFIN.NS", "CHOLAFIN.NS", "PFC.NS", "RECLTD.NS"],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS", "KPITTECH.NS", "TATAELXSI.NS"],
    "Automobiles & Auto Comp": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "TVSMOTOR.NS", "HEROMOTOCO.NS", "BHARATFORG.NS", "SONACOMS.NS", "MOTHERSON.NS"],
    "Pharma & Healthcare": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "LUPIN.NS", "AUROPHARMA.NS", "TORNTPHARM.NS", "ALKEM.NS", "MAXHEALTH.NS"],
    "Capital Goods & Defence": ["LT.NS", "SIEMENS.NS", "ABB.NS", "HAL.NS", "BEL.NS", "BHEL.NS", "CUMMINSIND.NS", "THERMAX.NS", "CGPOWER.NS", "SOLARINDS.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "JINDALSTEL.NS", "NMDC.NS", "NATIONALUM.NS", "SAIL.NS", "HINDZINC.NS", "APLAPOLLO.NS"],
    "Oil, Gas & Power": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS", "ADANIPOWER.NS", "BPCL.NS", "IOC.NS", "GAIL.NS", "NHPC.NS"],
    "Realty & Infrastructure": ["DLF.NS", "MACROTECH.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "PHOENIXLTD.NS", "BRIGADE.NS", "IRB.NS", "NCC.NS", "KPIL.NS"],
    "FMCG & Consumer": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "VBL.NS", "TATACONSUM.NS", "GODREJCP.NS", "DABUR.NS", "TRENT.NS", "TITAN.NS"],
    "Chemicals & Fertilizers": ["PIDILITIND.NS", "SRF.NS", "UPL.NS", "PIIND.NS", "DEEPAKNTR.NS", "NAVINFLUOR.NS", "TATACHEM.NS", "COROMANDEL.NS", "CHAMBLFERT.NS", "AARTIIND.NS"]
}

# ---------------------------------------------------------
# 2. DATA FETCHER & LEADING INDICATOR ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=900)
def fetch_market_data():
    all_tickers = ["^NSEI"] + [t for stocks in SECTOR_STOCKS.values() for t in stocks]
    raw = yf.download(all_tickers, period="6mo", interval="1d", group_by="ticker", progress=False, threads=True)
    
    nifty_close = raw["^NSEI"]["Close"].dropna()
    nifty_5d = (nifty_close.iloc[-1] / nifty_close.iloc[-6] - 1) * 100
    nifty_10d = (nifty_close.iloc[-1] / nifty_close.iloc[-11] - 1) * 100

    records = []
    ohlcv_store = {}

    for sector, tickers in SECTOR_STOCKS.items():
        for ticker in tickers:
            try:
                df = raw[ticker].dropna()
                if len(df) < 35:
                    continue
                
                sym = ticker.replace(".NS", "")
                ohlcv_store[sym] = df

                close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
                ltp = float(close.iloc[-1])
                prev_close = float(close.iloc[-2])
                day_chg = (ltp / prev_close - 1) * 100
                week_chg = (ltp / float(close.iloc[-6]) - 1) * 100
                month_chg = (ltp / float(close.iloc[-22]) - 1) * 100
                ten_day_chg = (ltp / float(close.iloc[-11]) - 1) * 100

                # Leading Metrics
                rs_5d = week_chg - nifty_5d
                rs_10d = ten_day_chg - nifty_10d
                avg_vol_20 = vol.iloc[-21:-1].mean()
                rvol = float(vol.iloc[-1] / avg_vol_20) if avg_vol_20 > 0 else 1.0

                # Volatility Squeeze
                sma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                bb_width = (4 * std20) / sma20
                is_squeezed = float(bb_width.iloc[-1]) <= (float(bb_width.iloc[-60:].min()) * 1.25)

                # EMAs
                ema20 = float(close.ewm(span=20).mean().iloc[-1])
                ema50 = float(close.ewm(span=50).mean().iloc[-1])
                above_ema20 = ltp > ema20
                above_ema50 = ltp > ema50

                # Pre-Breakout Score (0-100)
                score = 0
                if rs_5d > 1.5: score += 25
                if rs_10d > 2.0: score += 15
                if rvol >= 1.3 and -0.5 <= day_chg <= 3.5: score += 30
                elif rvol >= 1.8 and day_chg > 3.5: score += 10
                if is_squeezed: score += 15
                if above_ema20 and above_ema50: score += 15

                sparkline = [round(float(x), 2) for x in close.iloc[-60:].tolist()]
                m_low, m_high = float(low.iloc[-22:].min()), float(high.iloc[-22:].max())
                pos_in_month = ((ltp - m_low) / (m_high - m_low) * 100) if m_high > m_low else 50

                records.append({
                    "Symbol": sym,
                    "Sector": sector,
                    "LTP": round(ltp, 2),
                    "Day %": round(day_chg, 2),
                    "Week %": round(week_chg, 2),
                    "Month %": round(month_chg, 2),
                    "RS vs Nifty (5D)": round(rs_5d, 2),
                    "RS vs Nifty (10D)": round(rs_10d, 2),
                    "RVOL (x)": round(rvol, 2),
                    "Squeeze": "🔥 Yes" if is_squeezed else "No",
                    "Above 20EMA": above_ema20,
                    "Pre-Breakout Score": score,
                    "Month Range %": round(pos_in_month, 1),
                    "3M Trend": sparkline,
                    "EMA20": round(ema20, 2),
                    "EMA50": round(ema50, 2)
                })
            except Exception:
                continue

    return pd.DataFrame(records), ohlcv_store, round(nifty_5d, 2)

with st.spinner("Loading live NSE sector & stock scanner..."):
    df_stocks, ohlcv_store, nifty_5d_ret = fetch_market_data()

if df_stocks.empty:
    st.error("Market data temporarily unavailable. Please refresh.")
    st.stop()

# Aggregate Sector Metrics
sector_summary = df_stocks.groupby("Sector").agg(
    Stocks_Count=("Symbol", "count"),
    Day_Chg=("Day %", "mean"),
    Week_Chg=("Week %", "mean"),
    RS_5D=("RS vs Nifty (5D)", "mean"),
    RS_10D=("RS vs Nifty (10D)", "mean"),
    Avg_RVOL=("RVOL (x)", "mean"),
    Advances=("Day %", lambda x: (x > 0).sum()),
    Above_20EMA_Pct=("Above 20EMA", lambda x: round(x.mean() * 100, 1)),
    Avg_Breakout_Score=("Pre-Breakout Score", "mean")
).reset_index()

sector_summary["Declines"] = sector_summary["Stocks_Count"] - sector_summary["Advances"]
sector_summary["A/D Ratio"] = (sector_summary["Advances"] / sector_summary["Declines"].replace(0, 1)).round(2)
for col in ["Day_Chg", "Week_Chg", "RS_5D", "RS_10D", "Avg_RVOL", "Avg_Breakout_Score"]:
    sector_summary[col] = sector_summary[col].round(2)

# ---------------------------------------------------------
# BREADCRUMB BAR (Like Trendlyne: MARKETS / SECTOR / STOCK)
# ---------------------------------------------------------
b1, b2, b3, b4 = st.columns([1.2, 2, 2, 4])
with b1:
    if st.button("🏠 All Sectors", use_container_width=True):
        reset_to_all()
        st.rerun()
with b2:
    if st.session_state.nav_sector:
        if st.button(f"📂 {st.session_state.nav_sector}", use_container_width=True):
            reset_to_sector()
            st.rerun()
with b3:
    if st.session_state.nav_stock:
        st.button(f"📈 {st.session_state.nav_stock}", disabled=True, use_container_width=True)

st.divider()

# =========================================================
# LEVEL 3 VIEW: DEEP-DIVE STOCK TERMINAL (When a Stock is clicked)
# =========================================================
if st.session_state.nav_stock:
    sym = st.session_state.nav_stock
    row = df_stocks[df_stocks["Symbol"] == sym].iloc[0]
    hist = ohlcv_store[sym].copy()

    st.header(f"📈 {sym} — Pre-Breakout & Institutional Setup ({row['Sector']})")

    # Top KPI Strip
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("LTP", f"₹{row['LTP']}", f"{row['Day %']:+.2f}%")
    m2.metric("Early-Move Score", f"{row['Pre-Breakout Score']} / 100")
    m3.metric("5D RS vs Nifty", f"{row['RS vs Nifty (5D)']:+.2f}%")
    m4.metric("Volume Surge", f"{row['RVOL (x)']}x")
    m5.metric("Bollinger Squeeze", row["Squeeze"])
    m6.metric("20 EMA / 50 EMA", f"₹{row['EMA20']} / ₹{row['EMA50']}")

    # Calculate Indicators for Chart
    hist["EMA20"] = hist["Close"].ewm(span=20).mean()
    hist["EMA50"] = hist["Close"].ewm(span=50).mean()
    
    # RSI (14)
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    hist["RSI"] = 100 - (100 / (1 + gain / loss))

    # Interactive 3-Pane Chart (Price + FVG/EMAs, Volume, RSI)
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{sym} Daily Price, EMAs & Bullish Fair Value Gaps", "Volume vs 20D Avg", "RSI (14)")
    )

    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name="Price"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA20"], line=dict(color="#00bfff", width=1.5), name="20 EMA"), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA50"], line=dict(color="#ffa500", width=1.5), name="50 EMA"), row=1, col=1)

    # Detect Recent Bullish Fair Value Gaps (SMC FVG)
    for i in range(max(2, len(hist) - 30), len(hist)):
        if hist["Low"].iloc[i] > hist["High"].iloc[i - 2]:
            fig.add_shape(
                type="rect", x0=hist.index[i - 2], x1=hist.index[-1],
                y0=hist["High"].iloc[i - 2], y1=hist["Low"].iloc[i],
                fillcolor="rgba(0, 200, 83, 0.18)", line=dict(width=0), row=1, col=1
            )

    vol_colors = ["#00c853" if c >= o else "#ff5252" for c, o in zip(hist["Close"], hist["Open"])]
    fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], marker_color=vol_colors, name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], line=dict(color="#ab47bc", width=1.5), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="green", row=3, col=1)

    fig.update_layout(height=650, xaxis_rangeslider_visible=False, margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Actionable Trade Levels Box
    atr14 = float((hist["High"] - hist["Low"]).rolling(14).mean().iloc[-1])
    entry_zone = f"₹{row['LTP']} – ₹{round(row['LTP'] * 1.005, 2)}"
    stop_loss = round(row["LTP"] - (1.5 * atr14), 2)
    target_1 = round(row["LTP"] + (2.5 * atr14), 2)
    target_2 = round(row["LTP"] + (4.0 * atr14), 2)

    st.info(
        f"**🎯 Swing / Breakout Reference Levels (ATR-Based):**  "
        f"**Trigger Zone:** {entry_zone}  |  **Stop Loss:** ₹{stop_loss}  |  "
        f"**Target 1:** ₹{target_1}  |  **Target 2:** ₹{target_2}"
    )

# =========================================================
# LEVEL 2 VIEW: SECTOR DRILL-DOWN (When a Sector Box is clicked)
# =========================================================
elif st.session_state.nav_sector:
    sec = st.session_state.nav_sector
    sec_meta = sector_summary[sector_summary["Sector"] == sec].iloc[0]
    sec_df = df_stocks[df_stocks["Sector"] == sec].copy()

    st.header(f"🟢 {sec} — Sector Analysis & Pre-Breakout Stocks")

    # Summary Cards (Just like Trendlyne's 3 bottom cards)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sector Day / Week %", f"{sec_meta['Day_Chg']:+.2f}%", f"{sec_meta['Week_Chg']:+.2f}% (1W)")
    c2.metric("5D RS vs Nifty", f"{sec_meta['RS_5D']:+.2f}%", f"Nifty 5D: {nifty_5d_ret:+.2f}%")
    c3.metric("Advance / Decline", f"{int(sec_meta['Advances'])} : {int(sec_meta['Declines'])}", f"A/D Ratio: {sec_meta['A/D Ratio']}")
    c4.metric("Stocks > 20 EMA", f"{sec_meta['Above_20EMA_Pct']}%", f"Early-Move Score: {sec_meta['Avg_Breakout_Score']}")

    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        hide_extended = st.checkbox("Hide stocks already up > 3.5% today (Show un-extended setups only)", value=False)
    with col_f2:
        st.caption("👆 **Click any stock box in the heatmap OR click a row in the table below to open its full chart & levels.**")

    if hide_extended:
        sec_df = sec_df[sec_df["Day %"] <= 3.5]

    sec_df = sec_df.sort_values(by=["Pre-Breakout Score", "RS vs Nifty (5D)"], ascending=False)

    # Interactive Stock Treemap (Click a stock box to drill down!)
    if not sec_df.empty:
        fig_sub = px.treemap(
            sec_df,
            path=["Symbol"],
            values="RVOL (x)",
            color="Day %",
            color_continuous_scale=["#990000", "#d9534f", "#f5f5f5", "#5cb85c", "#006400"],
            color_continuous_midpoint=0,
            custom_data=["LTP", "Day %", "RS vs Nifty (5D)", "RVOL (x)", "Pre-Breakout Score"]
        )
        fig_sub.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[1]:+.2f}% | Score: %{customdata[4]}",
            hovertemplate=(
                "<b>%{label}</b><br>LTP: ₹%{customdata[0]}<br>Day: %{customdata[1]:+.2f}%<br>"
                "5D RS: %{customdata[2]:+.2f}%<br>RVOL: %{customdata[3]:.2f}x<br>"
                "Pre-Breakout Score: %{customdata[4]}/100<extra></extra>"
            )
        )
        fig_sub.update_layout(height=340, margin=dict(t=10, l=10, r=10, b=10))
        
        stock_event = st.plotly_chart(fig_sub, use_container_width=True, on_select="rerun", key="stock_tree")
        if stock_event and stock_event.selection and stock_event.selection.points:
            clicked_stock = stock_event.selection.points[0].get("label")
            if clicked_stock and clicked_stock in ohlcv_store:
                st.session_state.nav_stock = clicked_stock
                st.rerun()

    # Interactive Peer Comparison Table (Click any row to open Stock Terminal)
    st.subheader(f"{sec} Peer Comparison (Click a row to inspect stock)")
    table_event = st.dataframe(
        sec_df[[
            "Symbol", "Pre-Breakout Score", "3M Trend", "LTP", "Day %", "Week %",
            "Month %", "RS vs Nifty (5D)", "RVOL (x)", "Squeeze", "Month Range %"
        ]],
        column_config={
            "Pre-Breakout Score": st.column_config.ProgressColumn("Early-Move Score", format="%d", min_value=0, max_value=100),
            "3M Trend": st.column_config.LineChartColumn("3M Price Chart", width="medium"),
            "Month Range %": st.column_config.ProgressColumn("Month High-Low %", format="%.1f%%", min_value=0, max_value=100),
            "LTP": st.column_config.NumberColumn("LTP (₹)", format="₹%.2f"),
            "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%"),
            "Week %": st.column_config.NumberColumn("Week %", format="%+.2f%%"),
            "Month %": st.column_config.NumberColumn("Month %", format="%+.2f%%"),
            "RS vs Nifty (5D)": st.column_config.NumberColumn("5D RS vs Nifty", format="%+.2f%%"),
            "RVOL (x)": st.column_config.NumberColumn("Vol Surge", format="%.2fx"),
        },
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="peer_table"
    )
    if table_event and table_event.selection and table_event.selection.rows:
        row_idx = table_event.selection.rows[0]
        selected_sym = sec_df.iloc[row_idx]["Symbol"]
        st.session_state.nav_stock = selected_sym
        st.rerun()

# =========================================================
# LEVEL 1 VIEW: MASTER SECTOR HEATMAP & ROTATION QUADRANT
# =========================================================
else:
    st.header("🗺️ NSE Sector Heatmap & Rotation Scanner")
    st.caption("👆 **Click any green or red Sector box below to drill into its constituent stocks and pre-breakout setups.**")

    tab1, tab2 = st.tabs(["🗺️ Interactive Sector Heatmap (Click Box to Open)", "🎯 Sector Rotation Quadrant (Advance Signal)"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        with c1:
            metric_choice = st.radio(
                "Color Heatmap By:",
                ["Day_Chg", "Week_Chg", "RS_5D", "Avg_Breakout_Score"],
                format_func=lambda x: {
                    "Day_Chg": "Day Change % (Trendlyne View)",
                    "Week_Chg": "Week Change %",
                    "RS_5D": "5D Relative Strength vs Nifty (Leading)",
                    "Avg_Breakout_Score": "Pre-Breakout Score (Early Signal)"
                }[x]
            )
        with c2:
            color_scale = "Blues" if metric_choice == "Avg_Breakout_Score" else ["#990000", "#d9534f", "#f5f5f5", "#5cb85c", "#006400"]
            midpoint = None if metric_choice == "Avg_Breakout_Score" else 0

            fig_tree = px.treemap(
                sector_summary,
                path=["Sector"],
                values="Avg_RVOL",
                color=metric_choice,
                color_continuous_scale=color_scale,
                color_continuous_midpoint=midpoint,
                custom_data=["Day_Chg", "Week_Chg", "RS_5D", "Avg_RVOL", "Above_20EMA_Pct", "Avg_Breakout_Score"]
            )
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}% Day | %{customdata[2]:+.2f}% RS",
                hovertemplate=(
                    "<b>%{label}</b> (Click to open)<br>"
                    "Day Chg: %{customdata[0]:+.2f}%<br>"
                    "Week Chg: %{customdata[1]:+.2f}%<br>"
                    "5D RS vs Nifty: %{customdata[2]:+.2f}%<br>"
                    "Volume Surge (RVOL): %{customdata[3]:.2f}x<br>"
                    "Stocks > 20EMA: %{customdata[4]:.1f}%<br>"
                    "Pre-Breakout Score: %{customdata[5]:.1f}<extra></extra>"
                )
            )
            fig_tree.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=440)

            sector_event = st.plotly_chart(fig_tree, use_container_width=True, on_select="rerun", key="main_sector_tree")
            if sector_event and sector_event.selection and sector_event.selection.points:
                clicked_sector = sector_event.selection.points[0].get("label")
                if clicked_sector and clicked_sector in SECTOR_STOCKS:
                    st.session_state.nav_sector = clicked_sector
                    st.rerun()

    with tab2:
        st.markdown("**Advance Rotation Signal:** Sectors moving into the **Top-Right quadrant** with large bubbles (high RVOL) are gaining institutional momentum *before* big daily breakouts happen.")
        fig_rrg = px.scatter(
            sector_summary,
            x="RS_10D", y="RS_5D", size="Avg_RVOL", color="Avg_Breakout_Score",
            text="Sector", color_continuous_scale="Viridis", size_max=45,
            labels={"RS_10D": "10D RS vs Nifty (%)", "RS_5D": "5D RS Momentum (%)", "Avg_RVOL": "Volume Surge"}
        )
        fig_rrg.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_rrg.add_vline(x=0, line_dash="dash", line_color="gray")
        fig_rrg.update_traces(textposition="top center")
        fig_rrg.update_layout(height=450, margin=dict(t=20, l=20, r=20, b=20))
        st.plotly_chart(fig_rrg, use_container_width=True)

    # Sector Table (Also clickable to drill into a sector!)
    st.subheader("📊 Sector Breadth & Rotation Table (Click any row to drill in)")
    sorted_sec = sector_summary.sort_values(by="Avg_Breakout_Score", ascending=False).reset_index(drop=True)
    sec_table_event = st.dataframe(
        sorted_sec[[
            "Sector", "Avg_Breakout_Score", "Day_Chg", "Week_Chg", "RS_5D",
            "RS_10D", "Avg_RVOL", "Above_20EMA_Pct", "Advances", "Declines", "A/D Ratio"
        ]],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="sector_overview_table"
    )
    if sec_table_event and sec_table_event.selection and sec_table_event.selection.rows:
        s_idx = sec_table_event.selection.rows[0]
        st.session_state.nav_sector = sorted_sec.iloc[s_idx]["Sector"]
        st.rerun()
