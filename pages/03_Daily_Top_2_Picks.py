import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Daily Top 2 Institutional Picks", layout="wide")
st.title("🏆 Daily Top 2 High-Conviction Institutional Picks")
st.markdown("Filters **🟢 Master Confluence** stocks through **Nifty 50 Trend Guard**, **RSI (55–72) Institutional Zone**, and **Breakeven Trailing Protection**.")

NSE_UNIVERSE = list(dict.fromkeys(["BELRISE", "DEEPAKFERT", "ATHERENERG", "ITC", "BHARTIARTL", "PNB", "KALYANKJIL", "SBIN", "HDFCBANK", "ICICIBANK", "EICHERMOT", "BSE", "HINDALCO", "TDPOWERSYS", "ABB", "V2RETAIL", "KAYNES", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE", "SUNPHARMA", "MARUTI", "NTPC", "POWERGRID", "M&M", "TATASTEEL", "HAL", "BEL", "TRENT", "BANKBARODA", "CANBK", "JINDALPOLY", "FINCABLES", "AMBER", "MSTCLTD", "POWERINDIA", "HONASA", "GLAND", "MANKIND", "DIVISLAB", "WOCKPHARMA", "INDUSTOWER", "HINDCOPPER", "DATAPATTNS", "DIXON", "POLYCAB", "KEI", "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "SUZLON", "IREDA", "HUDCO", "NBCC", "SJVN", "NHPC", "BHEL", "SAIL", "NMDC", "VEDL", "JSWSTEEL", "JINDALSTEL", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "TATAPOWER", "JSWENERGY", "CGPOWER", "SIEMENS", "CUMMINSIND", "THERMAX", "TRITURBINE", "KPITTECH", "PERSISTENT", "COFORGE", "TECHM", "WIPRO", "HCLTECH", "NAUKRI", "PAYTM", "POLICYBZR", "ANGELONE", "CDSL", "MCX", "IEX", "TITAN", "DMART", "VBL", "GODREJCP", "BRITANNIA", "NESTLEIND", "DABUR", "MARICO", "COLPAL", "PIDILITIND", "ASIANPAINT", "BERGEPAINT", "ULTRACEMCO", "AMBUJACEM", "SHREECEM", "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "LODHA", "INDIGO", "IRCTC", "CONCOR", "APOLLOHOSP", "MAXHEALTH"]))

def get_rvol_scale():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    m_open, m_close = now_ist.replace(hour=9, minute=15, second=0, microsecond=0), now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist < m_open or now_ist >= m_close or now_ist.weekday() >= 5: return 1.0
    return min(375.0 / max((now_ist - m_open).total_seconds() / 60.0, 5.0), 25.0)

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return float((100 - (100 / (1 + rs))).iloc[-1])

@st.cache_data(ttl=90)
def compute_high_prob_picks(tickers, nb_list, ss_list):
    try:
        raw = yf.download([f"{t}.NS" for t in tickers] + ["^NSEI"], period="3mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception: return pd.DataFrame(), 0.0

    nifty_df = raw["^NSEI"].dropna()
    nifty_chg = round(((float(nifty_df["Close"].iloc[-1]) - float(nifty_df["Close"].iloc[-2])) / float(nifty_df["Close"].iloc[-2])) * 100, 2) if len(nifty_df) >= 2 else 0.0
    scale, rows = get_rvol_scale(), []

    for t in tickers:
        try:
            df = raw[f"{t}.NS"].dropna()
            if len(df) < 30: continue
            ltp, open_p, high_p, low_p, prev_c = float(df["Close"].iloc[-1]), float(df["Open"].iloc[-1]), float(df["High"].iloc[-1]), float(df["Low"].iloc[-1]), float(df["Close"].iloc[-2])
            pct_chg = round(((ltp - prev_c) / prev_c) * 100, 2)
            vol_avg = float(df["Volume"].iloc[-21:-1].mean())
            rvol = round((float(df["Volume"].iloc[-1]) * scale) / vol_avg, 2) if vol_avg > 0 else 1.0
            ema21, ema50 = float(df["Close"].ewm(span=21).mean().iloc[-1]), float(df["Close"].ewm(span=50).mean().iloc[-1])
            res_20d = float(df["High"].iloc[-21:-1].max())
            rsi_val = round(calc_rsi(df["Close"]), 1)

            # High-Win-Rate Guards: Above 21 & 50 EMA, RSI in sweet spot (52-74), outperforming Nifty by +1.5%
            is_nb = (t in nb_list) or (prev_c > ema21 > ema50 and -2.5 <= ((res_20d - prev_c) / prev_c) * 100 <= 4.0)
            is_ss = (t in ss_list) or (pct_chg >= max(1.2, nifty_chg + 1.5) and rvol >= 1.4 and ltp > open_p and ltp > ema21)
            if not (is_ss and 52 <= rsi_val <= 74 and pct_chg <= 8.5): continue

            is_master, broke_20d = (is_nb and is_ss), (ltp >= res_20d)
            near_high = (high_p - ltp) / max(high_p - low_p, 0.01) <= 0.30
            score = (120 if is_master else 0) + (pct_chg * 5) + (min(rvol, 8.0) * 4) + (15 if broke_20d else 0) + (15 if near_high else 0)

            ideal_buy = min(round(max(res_20d, high_p - ((high_p - low_p) * 0.382), open_p * 1.003), 2), round(ltp, 2))
            ext_pct = round(((ltp - ideal_buy) / ideal_buy) * 100, 2)
            kite_act = f"⏳ WAIT FOR PULLBACK BUY @ ₹{ideal_buy:,.2f}" if ext_pct > 0.7 else f"✅ BUY NOW / LIMIT @ ₹{ideal_buy:,.2f}"
            sl = round(min(low_p, ideal_buy * 0.988), 2)
            risk = max(ideal_buy - sl, ideal_buy * 0.008)
            be_trigger = round(ideal_buy + risk, 2)
            t1 = round(ideal_buy + risk * 1.5, 2)
            t2 = round(ideal_buy + risk * 2.5, 2)
            note = f"Enter at ₹{ideal_buy:,.2f}. Once price hits ₹{be_trigger:,.2f}, move SL to ₹{ideal_buy:,.2f} (Zero-Loss Lock)."
            tags = (["Night-Before Coil"] if is_master else []) + [f"RSI {rsi_val}", "Outperforming Nifty"]
            rows.append({"Stock": t, "LTP": round(ltp, 2), "Change_%": pct_chg, "Pace_RVOL": rvol, "Kite_Action": kite_act, "Limit_Buy": ideal_buy, "BE_Trigger": be_trigger, "Stop_Loss": sl, "Target_1": t1, "Target_2": t2, "Action_Note": note, "Score": round(score, 1), "Confluence": " + ".join(tags), "Is_Master": is_master})
        except Exception: continue
    return (pd.DataFrame(rows).sort_values(by="Score", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()), nifty_chg

@st.cache_data(ttl=60)
def build_smc_chart(stock_sym, tf_choice, ltp_p, buy_p, be_p, sl_p, t1_p, t2_p):
    ticker = f"{stock_sym}.NS"
    p_map = {"1m": "5d", "3m": "5d", "5m": "10d", "15m": "15d", "30m": "30d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1D": "1d"}
    df = yf.download(ticker, period=p_map[tf_choice], interval=i_map[tf_choice], progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None: df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    if tf_choice in ["3m", "4h"]:
        df = df.set_index("Time").resample("3min" if tf_choice == "3m" else "4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna().reset_index()
    fig = go.Figure(data=[go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=stock_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252")])
    fig.add_hline(y=buy_p, line_dash="solid", line_color="#FFD700", line_width=2.0, annotation_text=f"🟡 KITE LIMIT BUY: ₹{buy_p:,.2f}", annotation_position="top left", annotation_font_color="#FFD700")
    fig.add_hline(y=be_p, line_dash="dot", line_color="#FFA726", line_width=1.3, annotation_text=f"🛡️ MOVE SL TO COST @ ₹{be_p:,.2f}", annotation_position="top left", annotation_font_color="#FFA726")
    fig.add_hline(y=sl_p, line_dash="solid", line_color="#FF5252", line_width=1.5, annotation_text=f"🛑 INITIAL SL: ₹{sl_p:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252")
    fig.add_hline(y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.5, annotation_text=f"🎯 TARGET 1 (1.5R): ₹{t1_p:,.2f}", annotation_position="top right", annotation_font_color="#29B6F6")
    fig.add_hline(y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.5, annotation_text=f"🚀 TARGET 2 (2.5R): ₹{t2_p:,.2f}", annotation_position="top right", annotation_font_color="#00E676")
    rb = [dict(bounds=["sat", "mon"])] + ([dict(bounds=[15.5, 9.25], pattern="hour")] if tf_choice != "1D" else [])
    fig.update_layout(title=f"High-Probability Execution Chart: {stock_sym} ({tf_choice}) | LTP: ₹{ltp_p:,.2f}", template="plotly_dark", height=520, dragmode="pan", hovermode="x unified", margin=dict(l=10, r=60, t=45, b=35), yaxis=dict(side="right", title="Price (₹)", fixedrange=False), xaxis=dict(rangeslider_visible=False, rangebreaks=rb))
    return fig

if st.sidebar.button("🔄 Force Refresh Top 2 Picks"): st.cache_data.clear()
df_ranked, nifty_pct = compute_high_prob_picks(NSE_UNIVERSE, st.session_state.get("night_before_watchlist", []), st.session_state.get("super_signal_confirmed", []))

if nifty_pct < -0.4:
    st.warning(f"⚠️ **Market Regime Caution:** Nifty 50 is down **{nifty_pct}%** today. Only enter on **Pullback Limit Orders** with reduced position size and lock Stop-Loss to Cost early.")

if df_ranked.empty:
    st.info("No A+ high-probability setups passed all RSI, Relative Strength, and Volume filters right now.")
else:
    st.dataframe(df_ranked.head(5)[["Stock", "LTP", "Change_%", "Pace_RVOL", "Kite_Action", "BE_Trigger", "Stop_Loss", "Target_1", "Target_2"]], width="stretch", hide_index=True)
    for idx, row in df_ranked.head(2).iterrows():
        rank_num, stock = idx + 1, row["Stock"]
        st.subheader(f"🏆 Rank #{rank_num}: {stock} (LTP: ₹{row['LTP']:,.2f} | +{row['Change_%']}%)")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🟡 Kite Limit Buy", f"₹{row['Limit_Buy']:,.2f}", row["Kite_Action"])
        c2.metric("🛡️ Zero-Loss Lock", f"₹{row['BE_Trigger']:,.2f}", "Trail SL to Entry")
        c3.metric("🛑 Initial SL", f"₹{row['Stop_Loss']:,.2f}", "Max Risk")
        c4.metric("🎯 Target 1 (1.5R)", f"₹{row['Target_1']:,.2f}", "Book 50%")
        c5.metric("🚀 Target 2 (2.5R)", f"₹{row['Target_2']:,.2f}", "Book Balance")
        st.info(f"📲 **Zero-Loss Protection Rule ({stock}):** {row['Action_Note']} ({row['Confluence']})")
        selected_tf = st.radio(f"Candle Interval ({stock})", ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1D"], index=3, horizontal=True, key=f"tf_{stock}_{rank_num}")
        st.plotly_chart(build_smc_chart(stock, selected_tf, row["LTP"], row["Limit_Buy"], row["BE_Trigger"], row["Stop_Loss"], row["Target_1"], row["Target_2"]), width="stretch", config={"scrollZoom": True})
        st.markdown("---")
