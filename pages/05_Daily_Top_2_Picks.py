import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")
st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown("Prioritizes **🟢 Master Confluence** stocks (predicted in **Night Before Prep** + confirmed in **Matched Super Signal**) with **Exact Kite Limit Buy Zones** and **SMC Past ➔ Present ➔ Future** charts.")

NSE_UNIVERSE = list(dict.fromkeys(["BELRISE", "DEEPAKFERT", "ATHERENERG", "ITC", "BHARTIARTL", "PNB", "KALYANKJIL", "SBIN", "HDFCBANK", "ICICIBANK", "EICHERMOT", "BSE", "HINDALCO", "TDPOWERSYS", "ABB", "V2RETAIL", "KAYNES", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE", "SUNPHARMA", "MARUTI", "NTPC", "POWERGRID", "M&M", "TATASTEEL", "HAL", "BEL", "TRENT", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES", "AMBER", "MSTCLTD", "POWERINDIA", "HONASA", "GLAND", "MANKIND", "DIVISLAB", "WOCKPHARMA", "INDUSTOWER", "HINDCOPPER", "DATAPATTNS", "DIXON", "POLYCAB", "KEI", "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "SUZLON", "IREDA", "HUDCO", "NBCC", "SJVN", "NHPC", "BHEL", "SAIL", "NMDC", "VEDL", "JSWSTEEL", "JINDALSTEL", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "TATAPOWER", "JSWENERGY", "CGPOWER", "SIEMENS", "CUMMINSIND", "THERMAX", "TRITURBINE", "KPITTECH", "PERSISTENT", "COFORGE", "TECHM", "WIPRO", "HCLTECH", "NAUKRI", "PAYTM", "POLICYBZR", "ANGELONE", "CDSL", "MCX", "IEX", "TITAN", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND", "DABUR", "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT", "ULTRACEMCO", "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"]))

def get_rvol_scale():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    m_open, m_close = now_ist.replace(hour=9, minute=15, second=0, microsecond=0), now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5: return 1.0
    return min(375.0 / max((now_ist - m_open).total_seconds() / 60.0, 5.0), 25.0)

@st.cache_data(ttl=90)
def compute_top2_confluence(tickers, nb_list, ss_list):
    try: raw = yf.download([f"{t}.NS" for t in tickers], period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception: return pd.DataFrame()
    scale, rows = get_rvol_scale(), []
    for t in tickers:
        try:
            df = raw[f"{t}.NS"].dropna()
            if len(df) < 25: continue
            ltp, open_p, high_p, low_p, prev_c = float(df["Close"].iloc[-1]), float(df["Open"].iloc[-1]), float(df["High"].iloc[-1]), float(df["Low"].iloc[-1]), float(df["Close"].iloc[-2])
            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round((float(df["Volume"].iloc[-1]) * scale) / vol_avg, 2) if vol_avg > 0 else 1.0
            ema21, ema50 = float(df["Close"].ewm(span=21).mean().iloc[-1]), float(df["Close"].ewm(span=50).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())
            is_nb = (t in nb_list) or (prev_c > ema21 > ema50 and -2.5 <= ((res_20d - prev_c) / prev_c) * 100 <= 4.0)
            is_ss = (t in ss_list) or (pct_chg >= 1.2 and rvol >= 1.3 and ltp > open_p and ltp > ema21)
            if pct_chg < 0.8 or pct_chg > 9.5 or not is_ss: continue
            is_master, broke_20d = (is_nb and is_ss), (ltp >= res_20d)
            near_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.35
            score = (100 if is_master else 0) + (pct_chg * 5) + (min(rvol, 8.0) * 4) + (15 if broke_20d else 0) + (10 if near_high else 0)
            ideal_buy = min(round(max(res_20d, high_p - ((high_p - low_p) * 0.382), open_p * 1.003), 2), round(ltp, 2))
            ext_pct = round(((ltp - ideal_buy) / ideal_buy) * 100, 2)
            kite_act = f"⏳ WAIT FOR PULLBACK BUY @ ₹{ideal_buy:,.2f}" if ext_pct > 0.8 else f"✅ BUY NOW / LIMIT @ ₹{ideal_buy:,.2f}"
            note = f"Extended +{ext_pct}% above retest. Place Kite Limit Order at ₹{ideal_buy:,.2f}." if ext_pct > 0.8 else f"Inside optimal entry zone! Execute Buy near ₹{ideal_buy:,.2f}."
            sl = round(min(low_p, ideal_buy * 0.988), 2)
            risk = max(ideal_buy - sl, ideal_buy * 0.008)
            tags = (["Night-Before Coil"] if is_master else []) + ["Super-Signal Live"] + (["20D Breakout"] if broke_20d else [])
            rows.append({"Stock": t, "LTP": round(ltp, 2), "Change_%": pct_chg, "Pace_RVOL": rvol, "Kite_Action": kite_act, "Limit_Buy": ideal_buy, "Stop_Loss": sl, "Target_1": round(ideal_buy + risk * 1.5, 2), "Target_2": round(ideal_buy + risk * 3.0, 2), "Action_Note": note, "Score": round(score, 1), "Confluence": " + ".join(tags), "Is_Master": is_master})
        except Exception: continue
    return pd.DataFrame(rows).sort_values(by="Score", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()

@st.cache_data(ttl=60)
def build_smc_chart(stock_sym, tf_choice, ltp_p, buy_p, sl_p, t1_p, t2_p):
    ticker = f"{stock_sym}.NS"
    p_map = {"1m": "5d", "3m": "5d", "5m": "10d", "15m": "15d", "30m": "30d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1D": "1d"}
    df = yf.download(ticker, period=p_map[tf_choice], interval=i_map[tf_choice], progress=False, auto_adjust=True)
    df_4h = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)
    for d in [df, df_4h]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.droplevel(1)
    df = df.reset_index()
    df = df.rename(columns={"Datetime" if "Datetime" in df.columns else "Date": "Time"})
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None: df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    if tf_choice in ["3m", "4h"]:
        df = df.set_index("Time").resample("3min" if tf_choice == "3m" else "4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna().reset_index()
    if not df_4h.empty: df_4h = df_4h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    bull_fvg = next(((float(df_4h["High"].iloc[i-2]), float(df_4h["Low"].iloc[i])) for i in range(len(df_4h)-1, 1, -1) if df_4h["Low"].iloc[i] > df_4h["High"].iloc[i-2]), None)
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df)):
        if df["SH"].iloc[i-4]: last_sh = (df["Time"].iloc[i-4], float(df["High"].iloc[i-4]))
        if last_sh and float(df["Close"].iloc[i-1]) <= last_sh[1] and float(df["Close"].iloc[i]) > last_sh[1]:
            sigs.append({"t": df["Time"].iloc[i], "x0": last_sh[0], "y": last_sh[1]}); last_sh = None
    fig = go.Figure(data=[go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=stock_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252")])
    if bull_fvg: fig.add_hrect(y0=bull_fvg[0], y1=bull_fvg[1], fillcolor="rgba(0,230,118,0.14)", layer="below", line_width=0, annotation_text=f"PAST: 4H Bullish FVG ({bull_fvg[0]:,.1f}-{bull_fvg[1]:,.1f})", annotation_position="bottom left")
    for idx_s, s in enumerate(sigs[-4:]):
        fig.add_shape(type="line", x0=s["x0"], x1=s["t"], y0=s["y"], y1=s["y"], line=dict(color="#00E676", width=1.2, dash="dot"))
        fig.add_annotation(x=s["t"], y=s["y"], text="PRESENT: CHoCH Breakout" if idx_s == len(sigs[-4:])-1 else "PAST: BOS", showarrow=False, yshift=10, font=dict(size=9, color="#00E676"))
    fig.add_hline(y=buy_p, line_dash="solid", line_color="#FFD700", line_width=2.0, annotation_text=f"🟡 KITE LIMIT BUY: ₹{buy_p:,.2f} (LTP: ₹{ltp_p:,.2f})", annotation_position="top left", annotation_font_color="#FFD700")
    fig.add_hline(y=sl_p, line_dash="solid", line_color="#FF5252", line_width=1.5, annotation_text=f"🛑 STRICT SL: ₹{sl_p:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252")
    fig.add_hline(y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.5, annotation_text=f"🎯 TARGET 1 (1.5R): ₹{t1_p:,.2f}", annotation_position="top right", annotation_font_color="#29B6F6")
    fig.add_hline(y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.5, annotation_text=f"🚀 TARGET 2 (3.0R): ₹{t2_p:,.2f}", annotation_position="top right", annotation_font_color="#00E676")
    rb = [dict(bounds=["sat", "mon"])] + ([dict(bounds=[15.5, 9.25], pattern="hour")] if tf_choice != "1D" else [])
    fig.update_layout(title=f"SMC Kite Execution Chart: {stock_sym} ({tf_choice}) | LTP: ₹{ltp_p:,.2f}", template="plotly_dark", height=540, dragmode="pan", hovermode="x unified", margin=dict(l=10, r=60, t=45, b=35), yaxis=dict(side="right", title="Price (₹)", fixedrange=False), xaxis=dict(rangeslider_visible=False, rangebreaks=rb, rangeselector=dict(buttons=[dict(count=1, label="1D", step="day", stepmode="backward"), dict(count=5, label="5D", step="day", stepmode="backward"), dict(count=7, label="1W", step="day", stepmode="backward"), dict(count=1, label="1M", step="month", stepmode="backward"), dict(step="all", label="All")], bgcolor="#1E222D", activecolor="#2962FF", font=dict(color="white", size=11), x=0.0, y=-0.15)))
    return fig

if st.sidebar.button("🔄 Force Refresh Top 2 Picks"): st.cache_data.clear()
df_ranked = compute_top2_confluence(NSE_UNIVERSE, st.session_state.get("night_before_watchlist", []), st.session_state.get("super_signal_confirmed", []))

if df_ranked.empty:
    st.warning("No stocks currently satisfy institutional volume expansion and trend alignment.")
else:
    st.subheader("🔗 Multi-Page Confluence Pipeline (Night Before ➔ Super-Signal ➔ Kite Limit Plan)")
    st.dataframe(df_ranked.head(5)[["Stock", "LTP", "Change_%", "Pace_RVOL", "Kite_Action", "Stop_Loss", "Target_1", "Target_2"]], width="stretch", hide_index=True)
    st.markdown("---")
    for idx, row in df_ranked.head(2).iterrows():
        rank_num, stock = idx + 1, row["Stock"]
        badge = "🟢 MASTER CONFLUENCE" if row["Is_Master"] else "🔵 LIVE SUPER-SIGNAL"
        st.subheader(f"🏆 Rank #{rank_num}: {stock} (LTP: ₹{row['LTP']:,.2f} | +{row['Change_%']}%) — {badge}")
        c1
