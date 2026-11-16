import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")

st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown(
    "Prioritizes **🟢 Master Confluence** stocks (predicted in **Night Before Prep** + confirmed in **Matched Super Signal**) with full **SMC Past ➔ Present ➔ Future** execution charts."
)

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
def compute_top2_confluence(tickers, session_nb_list, session_ss_list):
    symbols = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(symbols, period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    scale = get_rvol_scale()
    candidates = []

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
            res_20d = float(df["High"].iloc[-21:-1].max())

            # Night-Before Coil Check (either from session_state or reconstructed)
            dist_prev = ((res_20d - prev_c) / prev_c) * 100
            is_nb_coil = (t in session_nb_list) or (prev_c > ema21 > ema50 and -2.5 <= dist_prev <= 4.0)

            # Live Super-Signal Check
            near_day_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            is_ss_live = (t in session_ss_list) or (pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema21)

            if pct_chg < 0.8 or pct_chg > 9.5 or not is_ss_live:
                continue

            is_master = is_nb_coil and is_ss_live
            broke_20d = ltp >= res_20d

            # Cap RVOL contribution so extreme outliers don't override Master Confluence
            score = (100 if is_master else 0) + (pct_chg * 5) + (min(rvol, 8.0) * 4) + (15 if broke_20d else 0) + (10 if near_day_high else 0)

            tags = []
            if is_master:
                tags.append("Night-Before Coil Match")
            tags.append("Super-Signal Live")
            if broke_20d:
                tags.append("20D Breakout")
            if near_day_high:
                tags.append("Near Day High")

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
                "Is_Master": is_master
            })
        except Exception:
            continue

    if not candidates:
        return pd.DataFrame()
    return pd.DataFrame(candidates).sort_values(by="Score", ascending=False).reset_index(drop=True)

@st.cache_data(ttl=90)
def build_smc_execution_chart(stock_sym, entry_p, sl_p, t1_p, t2_p):
    ticker = f"{stock_sym}.NS"
    df_15m = yf.download(ticker, period="15d", interval="15m", progress=False, auto_adjust=True)
    df_1d = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
    df_4h = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)

    for d in [df_15m, df_1d, df_4h]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.droplevel(1)

    df_15m = df_15m.reset_index()
    dt_col = "Datetime" if "Datetime" in df_15m.columns else "Date"
    df_15m.rename(columns={dt_col: "Time"}, inplace=True)
    df_15m["Time"] = pd.to_datetime(df_15m["Time"])
    if df_15m["Time"].dt.tz is not None:
        df_15m["Time"] = df_15m["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

    # 1. PAST: 1D Resistance/Support & 4H Bullish FVG
    res_1d = float(df_1d["High"].tail(60).max()) if not df_1d.empty else entry_p * 1.05
    sup_1d = float(df_1d["Low"].tail(60).min()) if not df_1d.empty else entry_p * 0.92

    if not df_4h.empty:
        df_4h = df_4h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    bull_fvg = None
    for i in range(2, len(df_4h)):
        if df_4h["Low"].iloc[i] > df_4h["High"].iloc[i - 2]:
            bull_fvg = (float(df_4h["High"].iloc[i - 2]), float(df_4h["Low"].iloc[i]))

    # 2. PAST -> PRESENT: CHoCH / BOS Structure Breaks on 15m
    df_15m["SH"] = df_15m["High"] == df_15m["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df_15m)):
        if df_15m["SH"].iloc[i - 4]:
            last_sh = (df_15m["Time"].iloc[i - 4], float(df_15m["High"].iloc[i - 4]))
        c, pc, t = float(df_15m["Close"].iloc[i]), float(df_15m["Close"].iloc[i - 1]), df_15m["Time"].iloc[i]
        if last_sh and pc <= last_sh[1] and c > last_sh[1]:
            sigs.append({"t": t, "p": float(df_15m["Low"].iloc[i]), "x0": last_sh[0], "y": last_sh[1]})
            last_sh = None

    fig = go.Figure(data=[go.Candlestick(
        x=df_15m["Time"], open=df_15m["Open"], high=df_15m["High"], low=df_15m["Low"], close=df_15m["Close"],
        name=stock_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252"
    )])

    # Plot 4H Bullish FVG Demand Zone (What Happened)
    if bull_fvg:
        fig.add_hrect(
            y0=bull_fvg[0], y1=bull_fvg[1], fillcolor="rgba(0, 230, 118, 0.14)", layer="below", line_width=0,
            annotation_text=f"PAST: 4H Bullish FVG Demand ({bull_fvg[0]:,.0f}-{bull_fvg[1]:,.0f})", annotation_position="bottom left"
        )

    # Plot Recent CHoCH Structural Breakouts
    for idx_s, s in enumerate(sigs[-4:]):
        lbl = "PRESENT: CHoCH Trigger" if idx_s == len(sigs[-4:]) - 1 else "PAST: CHoCH/BOS"
        fig.add_shape(type="line", x0=s["x0"], x1=s["t"], y0=s["y"], y1=s["y"], line=dict(color="#00E676", width=1.2, dash="dot"))
        fig.add_annotation(x=s["t"], y=s["y"], text=lbl, showarrow=False, yshift=10, font=dict(size=9, color="#00E676"))

    # Plot PRESENT Buy Pointer & Strict Stop-Loss
    curr_t = df_15m["Time"].iloc[-1]
    fig.add_annotation(
        x=curr_t, y=entry_p, text=f"🟢 NOW: BUY @ ₹{entry_p:,.2f}", showarrow=True, arrowhead=2,
        arrowcolor="#00E676", ax=-45, ay=30, font=dict(color="#00E676", size=11)
    )
    fig.add_hline(y=sl_p, line_dash="solid", line_color="#FF5252", line_width=1.5, annotation_text=f"🛑 STRICT SL: ₹{sl_p:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252")

    # Plot FUTURE Profit Targets (Target 1 & Target 2)
    fig.add_hline(y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.5, annotation_text=f"🎯 FUTURE TARGET 1 (1.5R): ₹{t1_p:,.2f}", annotation_position="top right", annotation_font_color="#29B6F6")
    fig.add_hline(y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.5, annotation_text=f"🚀 FUTURE TARGET 2 (3.0R): ₹{t2_p:,.2f}", annotation_position="top left", annotation_font_color="#00E676")

    rb = [dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")]
    fig.update_layout(
        title=f"SMC Execution Roadmap: {stock_sym} (15m Structure + 4H FVG + Future Targets)",
        template="plotly_dark", height=520, dragmode="pan", hovermode="x unified",
        margin=dict(l=10, r=60, t=45, b=35),
        yaxis=dict(side="right", title="Price (₹)", fixedrange=False),
        xaxis=dict(
            rangeslider_visible=False, rangebreaks=rb,
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=5, label="5D", step="day", stepmode="backward"),
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(step="all", label="All")
                ],
                bgcolor="#1E222D", activecolor="#2962FF", font=dict(color="white", size=11), x=0.0, y=-0.15
            )
        )
    )
    return fig

if st.sidebar.button("🔄 Force Refresh Top 2 Picks"):
    st.cache_data.clear()

nb_session = st.session_state.get("night_before_watchlist", [])
ss_session = st.session_state.get("super_signal_confirmed", [])

df_ranked = compute_top2_confluence(NSE_UNIVERSE, nb_session, ss_session)

if df_ranked.empty:
    st.warning("No stocks currently satisfy both institutional volume expansion and trend alignment.")
else:
    top2 = df_ranked.head(2)

    st.subheader("🔗 Multi-Page Confluence Pipeline (Night Before ➔ Super-Signal ➔ Top 2)")
    st.dataframe(
        df_ranked.head(5)[["Stock", "LTP", "Change_%", "Pace_RVOL", "Stop_Loss", "Target_1", "Target_2", "Confluence"]],
        use_container_width=True, hide_index=True
    )
    st.markdown("---")

    for idx, row in top2.iterrows():
        rank_num = idx + 1
        stock = row["Stock"]
        badge = "🟢 MASTER CONFLUENCE (Night Before + Super-Signal)" if row["Is_Master"] else "🔵 LIVE SUPER-SIGNAL LEADER"

        st.subheader(f"🏆 Rank #{rank_num}: {stock} (+{row['Change_%']}%) — {badge}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 NOW: Buy Entry", f"₹{row['LTP']:,.2f}", f"Pace Vol: {row['Pace_RVOL']}x")
        c2.metric("🛑 Strict Stop-Loss", f"₹{row['Stop_Loss']:,.2f}", "Protected Risk")
        c3.metric("🎯 FUTURE: Target 1", f"₹{row['Target_1']:,.2f}", "Book 50% Qty (1.5R)")
        c4.metric("🚀 FUTURE: Target 2", f"₹{row['Target_2']:,.2f}", "Trail Balance (3.0R)")

        st.info(
            f"🧭 **Past ➔ Present ➔ Future Roadmap ({stock}):** "
            f"**PAST:** Coiled in Night-Before accumulation above 4H FVG demand. "
            f"**PRESENT:** Triggered live CHoCH breakout ({row['Confluence']}) at **₹{row['LTP']:,.2f}**. "
            f"**FUTURE:** Hold with strict SL at **₹{row['Stop_Loss']:,.2f}** toward **₹{row['Target_1']:,.2f}** and **₹{row['Target_2']:,.2f}**."
        )

        fig_smc = build_smc_execution_chart(stock, row["LTP"], row["Stop_Loss"], row["Target_1"], row["Target_2"])
        st.plotly_chart(fig_smc, use_container_width=True, config={"scrollZoom": True})
        st.markdown("---")
