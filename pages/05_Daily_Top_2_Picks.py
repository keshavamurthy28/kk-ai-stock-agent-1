import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")

st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown(
    "Cross-collaborates **Night Before Pre-Breakout Coils** with **Live Super-Signal Volume Expansion** to isolate the **Top 2 actionable stocks** before full extension."
)

# Unified 120+ NSE Universe synchronized with Night Before & Super-Signal pages
NSE_UNIVERSE = list(dict.fromkeys([
    "BELRISE", "DEEPAKFERT", "ATHERENERG", "ITC", "BHARTIARTL", "PNB", "KALYANKJIL",
    "SBIN", "HDFCBANK", "ICICIBANK", "EICHERMOT", "BSE", "HINDALCO", "TDPOWERSYS",
    "ABB", "V2RETAIL", "KAYNES", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE",
    "TATAMOTORS", "SUNPHARMA", "MARUTI", "NTPC", "POWERGRID", "M&M", "TATASTEEL",
    "HAL", "BEL", "TRENT", "ZOMATO", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES",
    "AMBER", "MSTCLTD", "POWERINDIA", "HONASA", "GLAND", "MANKIND", "DIVISLAB",
    "WOCKPHARMA", "INDUSTOWER", "HINDCOPPER", "DATAPATTNS", "DIXON", "POLYCAB", "KEI",
    "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL",
    "SUZLON", "IREDA", "HUDCO", "NBCC", "SJVN", "NHPC", "BHEL", "SAIL", "NMDC",
    "VEDL", "JSWSTEEL", "JINDALSTEL", "ADANIENT", "ADANIPORTS", "ADANIPOWER",
    "TATAPOWER", "JSWENERGY", "CGPOWER", "SIEMENS", "CUMMINSIND", "THERMAX",
    "TRITURBINE", "KPITTECH", "PERSISTENT", "COFORGE", "LTIM", "TECHM", "WIPRO",
    "HCLTECH", "NAUKRI", "PAYTM", "POLICYBZR", "ANGELONE", "CDSL", "MCX", "IEX",
    "TITAN", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND", "DABUR",
    "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT", "ULTRACEMCO",
    "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE",
    "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"
]))

def get_rvol_scale():
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    m_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    m_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5:
        return 1.0
    mins = max((now_ist - m_open).total_seconds() / 60.0, 5.0)
    return min(375.0 / mins, 25.0)

@st.cache_data(ttl=90)
def compute_top2_confluence(tickers):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame(), {}

    scale = get_rvol_scale()
    candidates = []
    hist_map = {}

    for t in tickers:
        sym = f"{t}.NS"
        try:
            df = raw[sym].dropna() if len(tickers) > 1 else raw.dropna()
            if len(df) < 25:
                continue

            ltp = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1])
            high_p = float(df["High"].iloc[-1])
            low_p = float(df["Low"].iloc[-1])
            prev_c = float(df["Close"].iloc[-2])

            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_pace = float(df["Volume"].iloc[-1]) * scale
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round(vol_pace / vol_avg, 2) if vol_avg > 0 else 1.0

            ema9 = float(df["Close"].ewm(span=9).mean().iloc[-1])
            ema21 = float(df["Close"].ewm(span=21).mean().iloc[-1])
            ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])

            # 1. Night-Before Setup Check (Prior 20D Coil & EMA Alignment)
            res_20d = float(df["High"].iloc[-21:-1].max())
            dist_from_20d = ((prev_c - res_20d) / res_20d) * 100
            atr5 = float((df["High"] - df["Low"]).iloc[-6:-1].mean())
            atr20 = float((df["High"] - df["Low"]).iloc[-21:-1].mean())
            night_before_coil = (-4.0 <= dist_from_20d <= 0.5) and (prev_c > ema21) and (atr5 <= atr20)

            # 2. Live Super-Signal Check (Today's Breakout + Institutional Volume)
            broke_20d_today = ltp >= res_20d
            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.30
            super_signal_live = (pct_chg >= 1.2) and (rvol >= 1.4) and (ltp > open_p) and (ltp > ema9 > ema21)

            # Avoid overextended >9% late chases unless it's the only leader
            if pct_chg < 0.8 or pct_chg > 9.5 or not super_signal_live:
                continue

            # Confluence Score (Prioritizes stocks matching BOTH Night Before + Super Signal)
            score = (pct_chg * 5) + (min(rvol, 15.0) * 6)
            tags = ["Super-Signal Live"]
            if night_before_coil:
                score += 35
                tags.insert(0, "Night-Before Coil Match")
            if broke_20d_today:
                score += 20
                tags.append("20D Resistance Breakout")
            if near_day_high:
                score += 10
                tags.append("Closing Near Day High")

            sl = round(max(low_p, ema21) * 0.995, 2)
            risk = max(ltp - sl, ltp * 0.012)
            t1 = round(ltp + (risk * 1.5), 2)
            t2 = round(ltp + (risk * 3.0), 2)

            candidates.append({
                "Stock": t,
                "LTP": round(ltp, 2),
                "Change_%": pct_chg,
                "Pace_RVOL": round(rvol, 2),
                "Stop_Loss": sl,
                "Target_1": t1,
                "Target_2": t2,
                "Score": round(score, 1),
                "Confluence": " + ".join(tags),
                "Is_Master_Match": night_before_coil
            })
            hist_map[t] = df.tail(35).copy()
        except Exception:
            continue

    if not candidates:
        return pd.DataFrame(), {}
    df_res = pd.DataFrame(candidates).sort_values(by="Score", ascending=False).reset_index(drop=True)
    return df_res, hist_map

if st.sidebar.button("🔄 Force Refresh Top 2 Picks"):
    st.cache_data.clear()

df_ranked, hist_data = compute_top2_confluence(NSE_UNIVERSE)

if df_ranked.empty:
    st.warning("No stocks currently satisfy both institutional volume expansion and trend alignment.")
else:
    top2 = df_ranked.head(2)

    # Confluence Pipeline Summary Table
    st.subheader("🔗 Multi-Page Confluence Pipeline (Night Before ➔ Super-Signal ➔ Top 2)")
    st.dataframe(
        df_ranked.head(5)[["Stock", "LTP", "Change_%", "Pace_RVOL", "Stop_Loss", "Target_1", "Target_2", "Confluence"]],
        use_container_width=True,
        hide_index=True
    )
    st.markdown("---")

    # Render Rank #1 and Rank #2 Execution Cards + Charts
    for idx, row in top2.iterrows():
        rank_num = idx + 1
        stock = row["Stock"]
        badge = "🟢 MASTER CONFLUENCE (Night Before + Super-Signal)" if row["Is_Master_Match"] else "🔵 LIVE SUPER-SIGNAL LEADER"

        st.subheader(f"🏆 Rank #{rank_num}: {stock} (+{row['Change_%']}%) — {badge}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Recommended Entry", f"₹{row['LTP']:,.2f}", f"Pace Vol: {row['Pace_RVOL']}x")
        c2.metric("Strict Stop-Loss", f"₹{row['Stop_Loss']:,.2f}", "Protected Risk")
        c3.metric("Profit Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}", "Book 50% Qty")
        c4.metric("Profit Target 2 (3.0R)", f"₹{row['Target_2']:,.2f}", "Trail Balance")

        st.info(f"💡 **Why Buy ({stock}):** {row['Confluence']}. Price is holding strongly above **EMA 9 & EMA 21** with **{row['Pace_RVOL']}x** institutional volume absorption.")

        # Plot Candlestick + EMA 9/21/50 + Entry/SL/Target Chart
        df_p = hist_data[stock]
        df_p["EMA9"] = df_p["Close"].ewm(span=9).mean()
        df_p["EMA21"] = df_p["Close"].ewm(span=21).mean()
        df_p["EMA50"] = df_p["Close"].ewm(span=50).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_p.index, open=df_p["Open"], high=df_p["High"], low=df_p["Low"], close=df_p["Close"],
            name="Price", increasing_line_color="#00E676", decreasing_line_color="#FF5252"
        ))
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p["EMA9"], mode="lines", name="EMA 9", line=dict(color="#29B6F6", width=1.5)))
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p["EMA21"], mode="lines", name="EMA 21", line=dict(color="#FFA726", width=1.5)))
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p["EMA50"], mode="lines", name="EMA 50", line=dict(color="#AB47BC", width=1.5)))

        fig.add_hline(y=row["Target_1"], line_dash="dash", line_color="#00E676", annotation_text=f"Target 1: ₹{row['Target_1']:,.2f}", annotation_position="top left")
        fig.add_hline(y=row["Stop_Loss"], line_dash="dash", line_color="#FF5252", annotation_text=f"Stop-Loss: ₹{row['Stop_Loss']:,.2f}", annotation_position="bottom left")

        fig.update_layout(
            title=f"Execution Setup Chart: {stock} (Daily Trend & Institutional Levels)",
            template="plotly_dark", height=420, xaxis_rangeslider_visible=False, hovermode="x unified",
            margin=dict(l=10, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
