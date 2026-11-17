import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Leading Sector & Breakout Scanner", layout="wide")

st.title("🚀 Leading Sector Rotation & Pre-Breakout Scanner")
st.caption("Spots institutional accumulation, relative strength divergence, and volatility squeezes BEFORE major moves happen.")

# ---------------------------------------------------------
# 1. CURATED NSE SECTOR UNIVERSE (Fast & Liquid Leaders)
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
    raw = yf.download(all_tickers, period="4mo", interval="1d", group_by="ticker", progress=False, threads=True)
    
    nifty_close = raw["^NSEI"]["Close"].dropna()
    nifty_5d = (nifty_close.iloc[-1] / nifty_close.iloc[-6] - 1) * 100
    nifty_10d = (nifty_close.iloc[-1] / nifty_close.iloc[-11] - 1) * 100

    records = []
    for sector, tickers in SECTOR_STOCKS.items():
        for ticker in tickers:
            try:
                df = raw[ticker].dropna()
                if len(df) < 30:
                    continue
                
                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                vol = df["Volume"]

                ltp = float(close.iloc[-1])
                prev_close = float(close.iloc[-2])
                day_chg = (ltp / prev_close - 1) * 100
                week_chg = (ltp / float(close.iloc[-6]) - 1) * 100
                month_chg = (ltp / float(close.iloc[-22]) - 1) * 100
                ten_day_chg = (ltp / float(close.iloc[-11]) - 1) * 100

                # Leading Indicator 1: Relative Strength vs Nifty
                rs_5d = week_chg - nifty_5d
                rs_10d = ten_day_chg - nifty_10d

                # Leading Indicator 2: Relative Volume Surge (RVOL)
                avg_vol_20 = vol.iloc[-21:-1].mean()
                rvol = float(vol.iloc[-1] / avg_vol_20) if avg_vol_20 > 0 else 1.0

                # Leading Indicator 3: Volatility Squeeze (Bollinger Band Width Rank)
                sma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                bb_width = (4 * std20) / sma20
                curr_bbw = float(bb_width.iloc[-1])
                min_bbw_60 = float(bb_width.iloc[-60:].min())
                is_squeezed = curr_bbw <= (min_bbw_60 * 1.25)

                # Leading Indicator 4: Trend Alignment (Above 20 EMA & 50 EMA)
                ema20 = float(close.ewm(span=20).mean().iloc[-1])
                ema50 = float(close.ewm(span=50).mean().iloc[-1])
                above_ema20 = ltp > ema20
                above_ema50 = ltp > ema50

                # Coiled Spring / Pre-Breakout Score (0 to 100)
                # Rewards: High RS, RVOL surge WITHOUT already spiking >4% today, Squeeze, and EMA support
                score = 0
                if rs_5d > 1.5: score += 25
                if rs_10d > 2.0: score += 15
                if rvol >= 1.3 and -0.5 <= day_chg <= 3.5: score += 30  # Quiet accumulation!
                elif rvol >= 1.8 and day_chg > 3.5: score += 10         # Already moving
                if is_squeezed: score += 15
                if above_ema20 and above_ema50: score += 15

                # 3-Month Sparkline History (last 60 closes)
                sparkline = [round(float(x), 2) for x in close.iloc[-60:].tolist()]

                # Range Position (Day & Month)
                m_low, m_high = float(low.iloc[-22:].min()), float(high.iloc[-22:].max())
                pos_in_month = ((ltp - m_low) / (m_high - m_low) * 100) if m_high > m_low else 50

                records.append({
                    "Symbol": ticker.replace(".NS", ""),
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
                    "3M Trend": sparkline
                })
            except Exception:
                continue

    return pd.DataFrame(records), round(nifty_5d, 2)

with st.spinner("Scanning NSE sectors for early momentum & accumulation..."):
    df_stocks, nifty_5d_ret = fetch_market_data()

if df_stocks.empty:
    st.error("Unable to fetch market data right now. Please try refreshing.")
    st.stop()

# ---------------------------------------------------------
# 3. AGGREGATE SECTOR METRICS
# ---------------------------------------------------------
sector_summary = df_stocks.groupby("Sector").agg(
    Stocks_Count=("Symbol", "count"),
    Day_Chg=("Day %", "mean"),
    Week_Chg=("Week %", "mean"),
    Month_Chg=("Month %", "mean"),
    RS_5D=("RS vs Nifty (5D)", "mean"),
    RS_10D=("RS vs Nifty (10D)", "mean"),
    Avg_RVOL=("RVOL (x)", "mean"),
    Advances=("Day %", lambda x: (x > 0).sum()),
    Above_20EMA_Pct=("Above 20EMA", lambda x: round(x.mean() * 100, 1)),
    Avg_Breakout_Score=("Pre-Breakout Score", "mean")
).reset_index()

sector_summary["Declines"] = sector_summary["Stocks_Count"] - sector_summary["Advances"]
sector_summary["A/D Ratio"] = (sector_summary["Advances"] / sector_summary["Declines"].replace(0, 1)).round(2)
for col in ["Day_Chg", "Week_Chg", "Month_Chg", "RS_5D", "RS_10D", "Avg_RVOL", "Avg_Breakout_Score"]:
    sector_summary[col] = sector_summary[col].round(2)

# ---------------------------------------------------------
# 4. TOP VIEW: TRENDLYNE-STYLE HEATMAP + ROTATION QUADRANT
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🗺️ Sector Heatmap (Trendlyne View)", "🎯 Sector Rotation Quadrant (Advance Signal)"])

with tab1:
    c1, c2 = st.columns([1, 3])
    with c1:
        metric_choice = st.radio(
            "Color Heatmap By:",
            ["RS_5D", "Day_Chg", "Week_Chg", "Avg_Breakout_Score"],
            format_func=lambda x: {
                "RS_5D": "5D Relative Strength vs Nifty (Leading)",
                "Day_Chg": "Day Change % (Live)",
                "Week_Chg": "Week Change %",
                "Avg_Breakout_Score": "Pre-Breakout Score (Early Signal)"
            }[x]
        )
    with c2:
        sector_summary["Label"] = (
            sector_summary["Sector"] + "<br>" +
            sector_summary[metric_choice].astype(str) + (" pts" if metric_choice == "Avg_Breakout_Score" else "%")
        )
        color_scale = "Blues" if metric_choice == "Avg_Breakout_Score" else ["#990000", "#d9534f", "#f5f5f5", "#5cb85c", "#006400"]
        midpoint = None if metric_choice == "Avg_Breakout_Score" else 0

        fig_tree = px.treemap(
            sector_summary,
            path=["Sector"],
            values="Avg_RVOL",  # Box size reflects unusual volume flow!
            color=metric_choice,
            color_continuous_scale=color_scale,
            color_continuous_midpoint=midpoint,
            custom_data=["Day_Chg", "Week_Chg", "RS_5D", "Avg_RVOL", "Above_20EMA_Pct", "Avg_Breakout_Score"]
        )
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[2]:+.2f}% RS | Score: %{customdata[5]:.0f}",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Day Chg: %{customdata[0]:+.2f}%<br>"
                "Week Chg: %{customdata[1]:+.2f}%<br>"
                "5D RS vs Nifty: %{customdata[2]:+.2f}%<br>"
                "Volume Surge (RVOL): %{customdata[3]:.2f}x<br>"
                "Stocks > 20EMA: %{customdata[4]:.1f}%<br>"
                "Pre-Breakout Score: %{customdata[5]:.1f}<extra></extra>"
            )
        )
        fig_tree.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=420)
        st.plotly_chart(fig_tree, use_container_width=True)

with tab2:
    st.markdown("**How to read this:** Sectors in the **Top-Right (Leading)** or crossing from **Bottom-Right into Top-Right (Improving)** with big bubbles (high RVOL) are where institutional money is rotating *before* retail sees big green candles.")
    fig_rrg = px.scatter(
        sector_summary,
        x="RS_10D",
        y="RS_5D",
        size="Avg_RVOL",
        color="Avg_Breakout_Score",
        text="Sector",
        color_continuous_scale="Viridis",
        size_max=45,
        labels={
            "RS_10D": "10-Day Relative Strength vs Nifty (%)",
            "RS_5D": "5-Day Momentum Acceleration vs Nifty (%)",
            "Avg_RVOL": "Volume Surge (RVOL)",
            "Avg_Breakout_Score": "Pre-Breakout Score"
        }
    )
    fig_rrg.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_rrg.add_vline(x=0, line_dash="dash", line_color="gray")
    fig_rrg.update_traces(textposition="top center")
    fig_rrg.update_layout(height=450, margin=dict(t=20, l=20, r=20, b=20))
    st.plotly_chart(fig_rrg, use_container_width=True)

# ---------------------------------------------------------
# 5. SECTOR OVERVIEW TABLE (Like Trendlyne Sector Table)
# ---------------------------------------------------------
st.subheader("📊 Sector Breadth & Rotation Scorecard")
st.dataframe(
    sector_summary.sort_values(by="Avg_Breakout_Score", ascending=False)[
        ["Sector", "Avg_Breakout_Score", "RS_5D", "RS_10D", "Day_Chg", "Week_Chg", "Avg_RVOL", "Above_20EMA_Pct", "Advances", "Declines", "A/D Ratio"]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

# ---------------------------------------------------------
# 6. DRILL-DOWN: PRE-BREAKOUT STOCKS IN SELECTED SECTOR
# ---------------------------------------------------------
st.subheader("🔍 Sector Drill-Down: Stocks Ready to Move Ahead")

col_sel, col_filt = st.columns([2, 2])
with col_sel:
    # Default to the sector with highest Pre-Breakout Score
    top_sector = sector_summary.sort_values(by="Avg_Breakout_Score", ascending=False)["Sector"].iloc[0]
    selected_sector = st.selectbox("Select Sector to Inspect:", list(SECTOR_STOCKS.keys()), index=list(SECTOR_STOCKS.keys()).index(top_sector))

with col_filt:
    hide_extended = st.checkbox("Hide stocks already up > 3.5% today (Only show un-extended setups)", value=True)

sector_df = df_stocks[df_stocks["Sector"] == selected_sector].copy()
if hide_extended:
    sector_df = sector_df[sector_df["Day %"] <= 3.5]

sector_df = sector_df.sort_values(by=["Pre-Breakout Score", "RS vs Nifty (5D)"], ascending=False)

# Stock-level Treemap inside the chosen sector
if not sector_df.empty:
    fig_sub = px.treemap(
        sector_df,
        path=["Symbol"],
        values="RVOL (x)",
        color="RS vs Nifty (5D)",
        color_continuous_scale=["#990000", "#f5f5f5", "#006400"],
        color_continuous_midpoint=0
    )
    fig_sub.update_traces(texttemplate="<b>%{label}</b><br>RS: %{color:+.2f}%")
    fig_sub.update_layout(height=280, margin=dict(t=5, l=5, r=5, b=5))
    st.plotly_chart(fig_sub, use_container_width=True)

# Trendlyne-Style Peer Comparison Table with 3M Sparklines & Range Bars
st.dataframe(
    sector_df[[
        "Symbol", "Pre-Breakout Score", "3M Trend", "LTP", "Day %", "Week %",
        "RS vs Nifty (5D)", "RVOL (x)", "Squeeze", "Month Range %"
    ]],
    column_config={
        "Pre-Breakout Score": st.column_config.ProgressColumn(
            "Early-Move Score",
            help="Higher score = strong relative strength + quiet volume accumulation + tight squeeze",
            format="%d",
            min_value=0,
            max_value=100,
        ),
        "3M Trend": st.column_config.LineChartColumn(
            "3M Price Chart",
            width="medium"
        ),
        "Month Range %": st.column_config.ProgressColumn(
            "Month High-Low Pos %",
            format="%.1f%%",
            min_value=0,
            max_value=100
        ),
        "LTP": st.column_config.NumberColumn("LTP (₹)", format="₹%.2f"),
        "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%"),
        "Week %": st.column_config.NumberColumn("Week %", format="%+.2f%%"),
        "RS vs Nifty (5D)": st.column_config.NumberColumn("5D RS vs Nifty", format="%+.2f%%"),
        "RVOL (x)": st.column_config.NumberColumn("Vol Surge", format="%.2fx"),
    },
    use_container_width=True,
    hide_index=True
)
