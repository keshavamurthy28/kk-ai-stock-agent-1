from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MU$₹A Rendezvous 2-5% Intraday Sniper", layout="wide")

st.title("🎯 MU$₹A Rendezvous: 2%–5% Intraday Sniper Terminal")

# Check current IST market time to protect beginners from late-day entries
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
cur_time = now_ist.time()

if cur_time < datetime.strptime("09:20", "%H:%M").time():
    st.info("⏳ **Pre-Market / Opening Volatility (Before 9:20 AM IST):** Wait for the first 15-minute candle to settle before placing intraday orders.")
elif cur_time <= datetime.strptime("11:45", "%H:%M").time():
    st.success("🟢 **PRIME INTRADAY WINDOW (9:20 AM – 11:45 AM IST):** Best window to enter `🎯 PRIME 2-5% SNIPER` breakouts.")
elif cur_time <= datetime.strptime("14:15", "%H:%M").time():
    st.warning("🟡 **MID-DAY SESSION (11:45 AM – 2:15 PM IST):** Only enter pullbacks near the Yellow VWAP line with strict stop-loss.")
else:
    st.error("🛑 **LATE SESSION / MARKET CLOSING (After 2:15 PM IST):** Do NOT take fresh intraday trades now—insufficient time for a 2–5% move before 3:30 PM close.")

st.markdown(
    "🎯 **PRIME 2-5% SNIPER:** Up `+1.2%` to `+4.2%` with `>= 1.5x` Volume (Best Risk-Reward for 2–4% Intraday)  |  "
    "🟢 **EXTENDED / SWING BREAKOUT:** Already up `> 4.2%` (Avoid chasing intraday; wait for pullback)"
)

UNIVERSE = {
    "LICHSGFIN": "LIC Housing Finance",
    "MCX": "Multi Commodity Exchange",
    "CDSL": "Central Depository Services",
    "BELRISE": "Belrise Industries",
    "ITC": "ITC Limited",
    "DEEPAKFERT": "Deepak Fertilisers",
    "MAXHEALTH": "Max Healthcare",
    "KALYANKJIL": "Kalyan Jewellers",
    "KARURVYSYA": "Karur Vysya Bank",
    "BSE": "BSE Limited",
    "APOLLOMICRO": "Apollo Micro Systems",
    "AUROPHARMA": "Aurobindo Pharma",
    "SBIN": "State Bank of India",
    "BANKBARODA": "Bank of Baroda",
    "INDIANB": "Indian Bank",
    "UNIONBANK": "Union Bank of India",
    "CANBK": "Canara Bank",
    "IDFCFIRSTB": "IDFC First Bank",
    "ABCAPITAL": "Aditya Birla Capital",
    "JIOFIN": "Jio Financial Services",
    "ETERNAL": "Eternal Limited",
    "TITAN": "Titan Company",
    "DIVISLAB": "Divi's Laboratories",
    "GRASIM": "Grasim Industries",
    "PRESTIGE": "Prestige Estates",
    "INDHOTEL": "Indian Hotels Co.",
    "BEL": "Bharat Electronics",
    "LT": "Larsen & Toubro",
    "MUTHOOTFIN": "Muthoot Finance",
    "MANKIND": "Mankind Pharma",
}


@st.cache_data(ttl=60)
def scan_intraday_sniper(symbols_dict):
    tickers = [f"{s}.NS" for s in symbols_dict.keys()]
    raw = yf.download(tickers, period="1mo", interval="1d", group_by="ticker", progress=False, threads=True)
    rows = []

    for sym, name in symbols_dict.items():
        t_key = f"{sym}.NS"
        try:
            df_s = raw[t_key].dropna(subset=["Close", "Volume"]) if len(tickers) > 1 else raw.dropna(subset=["Close", "Volume"])
            if len(df_s) < 6:
                continue

            ltp = float(df_s["Close"].iloc[-1])
            prev_close = float(df_s["Close"].iloc[-2])
            chg_pct = ((ltp - prev_close) / prev_close) * 100.0

            cur_vol = float(df_s["Volume"].iloc[-1])
            avg_vol = float(df_s["Volume"].iloc[-11:-1].mean()) if len(df_s) >= 11 else float(df_s["Volume"].iloc[:-1].mean())
            rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            # Classify specifically for 2-5% Intraday Sniper vs Extended
            is_prime_sniper = (1.2 <= chg_pct <= 4.2) and (rvol >= 1.5)
            is_extended = (chg_pct > 4.2) and (rvol >= 1.5)

            if is_prime_sniper:
                status = "🎯 PRIME 2-5% SNIPER"
                action = "BUY INTRADAY"
                score = 100 + (rvol * 5) + chg_pct
            elif is_extended:
                status = "⚠️ EXTENDED (>4.2%)"
                action = "WAIT PULLBACK"
                score = 60 + rvol
            elif chg_pct > 0.5 and rvol >= 1.2:
                status = "🔵 BUILDING MOMENTUM"
                action = "WATCHLIST"
                score = 40 + (rvol * 3) + chg_pct
            else:
                status = "⚪ LOW VOLUME / FLAT"
                action = "AVOID"
                score = chg_pct

            # Tight Intraday Risk & 2.2% / 4.0% Profit Targets
            sl = round(ltp * 0.988, 2)        # -1.2% hard intraday stop-loss
            t1 = round(ltp * 1.022, 2)        # +2.2% realistic intraday Target 1
            t2 = round(ltp * 1.040, 2)        # +4.0% stretch intraday Target 2

            rows.append({
                "Score": score,
                "Stock": sym,
                "Company": name,
                "Sniper_Status": status,
                "Action": action,
                "LTP": round(ltp, 2),
                "Change_%": round(chg_pct, 2),
                "Volume_Surge": rvol,
                "Intraday_SL (-1.2%)": sl,
                "Target_1 (+2.2%)": t1,
                "Target_2 (+4.0%)": t2,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    res_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False).head(12).reset_index(drop=True)
    res_df.insert(0, "Rank", range(1, len(res_df) + 1))
    return res_df.drop(columns=["Score"])


with st.spinner("Filtering Prime 2%–5% Intraday Sniper setups..."):
    rank_df = scan_intraday_sniper(UNIVERSE)

selected_sym = "LICHSGFIN"

if not rank_df.empty:
    st.subheader("🏆 Intraday 2%–5% Sniper Ranking Table")
    st.caption("👇 **Click any `🎯 PRIME 2-5% SNIPER` row** to load its intraday chart, VWAP entry, -1.2% Stop-Loss, and +2.2% / +4.0% Targets.")

    def style_sniper_rows(row):
        val = str(row["Sniper_Status"])
        if "PRIME" in val:
            return ["background-color: rgba(0, 230, 118, 0.18)"] * len(row)
        elif "EXTENDED" in val:
            return ["background-color: rgba(255, 193, 7, 0.12)"] * len(row)
        elif "BUILDING" in val:
            return ["background-color: rgba(41, 182, 246, 0.10)"] * len(row)
        return [""] * len(row)

    styled_df = (
        rank_df.drop(columns=["Company"])
        .style.apply(style_sniper_rows, axis=1)
        .format({
            "LTP": "₹{:,.2f}",
            "Change_%": "{:+.2f}%",
            "Volume_Surge": "{:.2f}x",
            "Intraday_SL (-1.2%)": "₹{:,.2f}",
            "Target_1 (+2.2%)": "₹{:,.2f}",
            "Target_2 (+4.0%)": "₹{:,.2f}",
        })
    )

    event = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if event and event.selection and event.selection.rows:
        selected_sym = rank_df.iloc[event.selection.rows[0]]["Stock"]
    else:
        selected_sym = rank_df.iloc[0]["Stock"]

st.markdown("---")

c1, c2 = st.columns([1, 2])
all_syms = list(UNIVERSE.keys())
default_idx = all_syms.index(selected_sym) if selected_sym in all_syms else 0
active_sym = c1.selectbox("Active Projected Stock", all_syms, index=default_idx)
tf_choice = c2.radio("Intraday Candle Interval", ["5m", "15m", "1h", "4h", "1D"], index=0, horizontal=True)


@st.cache_data(ttl=15)
def fetch_chart_data(sym, tf):
    t_obj = yf.Ticker(f"{sym}.NS")
    p_map = {"5m": "5d", "15m": "15d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "1h", "1D": "1d"}
    df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
        df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

    if tf == "4h":
        df = (
            df.set_index("Time")
            .resample("4h", offset="15min")
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
            .dropna()
            .reset_index()
        )
    return df


df = fetch_chart_data(active_sym, tf_choice)

if not df.empty:
    ltp = float(df["Close"].iloc[-1])
    company_name = UNIVERSE.get(active_sym, active_sym)

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["VWAP"] = (
        (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"]).groupby(df["Time"].dt.date).cumsum()
        / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
    )
    latest_vwap = float(df["VWAP"].iloc[-1]) if not np.isnan(df["VWAP"].iloc[-1]) else ltp

    # Pullback entry near VWAP or 0.4% below LTP
    buy_zone = round(max(latest_vwap, ltp * 0.996), 2) if ltp >= latest_vwap else round(ltp, 2)
    sl_price = round(buy_zone * 0.988, 2)      # -1.2% Stop-Loss
    t1_price = round(buy_zone * 1.022, 2)      # +2.2% Target 1
    t2_price = round(buy_zone * 1.040, 2)      # +4.0% Target 2
    breakeven_trigger = round(buy_zone * 1.011, 2)  # +1.1% Zero-Loss Lock

    st.subheader(f"📊 Intraday 2%–5% Execution Plan: {company_name} ({active_sym})")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live LTP", f"₹{ltp:,.2f}", "Above VWAP ✅" if ltp >= latest_vwap else "Below VWAP ⚠️")
    m2.metric("🟡 Limit Buy Zone", f"₹{buy_zone:,.2f}", "Enter Only Above VWAP")
    m3.metric("🛑 Hard SL (-1.2%)", f"₹{sl_price:,.2f}", "Exit Immediately If Hit")
    m4.metric("🎯 Target 1 (+2.2%)", f"₹{t1_price:,.2f}", "Book 70% Quantity")
    m5.metric("🚀 Target 2 (+4.0%)", f"₹{t2_price:,.2f}", "Book Balance 30%")

    st.info(
        f"**⚡ 3-Step Intraday Rule for {active_sym}:**  \n"
        f"1. **Check VWAP First:** Only buy if the price candle is **above the Yellow VWAP line (₹{latest_vwap:,.2f})** between **9:30 AM and 11:45 AM**.  \n"
        f"2. **Zero-Loss Lock:** As soon as price hits **₹{breakeven_trigger:,.2f} (+1.1%)**, move your Stop-Loss from ₹{sl_price:,.2f} up to your buy price (**₹{buy_zone:,.2f}**).  \n"
        f"3. **Book Profit:** Sell 70% of your shares at **₹{t1_price:,.2f} (+2.2%)** and exit the rest at **₹{t2_price:,.2f} (+4.0%)** or before 3:15 PM."
    )

    v_avg = df["Volume"].rolling(20, min_periods=1).mean()
    v_col = [
        "#00E676" if (c >= o and v >= 1.5 * va)
        else ("#FF5252" if (c < o and v >= 1.5 * va)
              else ("rgba(0,230,118,0.40)" if c >= o else "rgba(255,82,82,0.40)"))
        for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
    ]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.78, 0.22])

    fig.add_trace(
        go.Candlestick(
            x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name=active_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252",
        ),
        row=1, col=1,
    )
    fig.add_trace(go.Scatter(x=df["Time"], y=df["VWAP"], mode="lines", name="VWAP", line=dict(color="#FFD700", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], mode="lines", name="20 EMA", line=dict(color="#29B6F6", width=1.2)), row=1, col=1)
    fig.add_trace(go.Bar(x=df["Time"], y=df["Volume"], name="Volume", marker_color=v_col), row=2, col=1)

    fig.add_hline(y=buy_zone, line_dash="solid", line_color="#FFD700", line_width=1.6,
                  annotation_text=f"🟡 BUY: ₹{buy_zone:,.2f}", annotation_position="bottom left", annotation_font_color="#FFD700", row=1, col=1)
    fig.add_hline(y=sl_price, line_dash="solid", line_color="#FF5252", line_width=1.6,
                  annotation_text=f"🛑 SL (-1.2%): ₹{sl_price:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252", row=1, col=1)
    fig.add_hline(y=t1_price, line_dash="dash", line_color="#29B6F6", line_width=1.4,
                  annotation_text=f"🎯 T1 (+2.2%): ₹{t1_price:,.2f}", annotation_position="top left", annotation_font_color="#29B6F6", row=1, col=1)
    fig.add_hline(y=t2_price, line_dash="dash", line_color="#00E676", line_width=1.4,
                  annotation_text=f"🚀 T2 (+4.0%): ₹{t2_price:,.2f}", annotation_position="top right", annotation_font_color="#00E676", row=1, col=1)

    rb = [dict(bounds=["sat", "mon"])]
    if tf_choice != "1D":
        rb.append(dict(bounds=[15.5, 9.25], pattern="hour"))

    tv_tickformats = [
        dict(dtickrange=[None, 86400000], value="%H:%M<br>%d %b"),
        dict(dtickrange=[86400000, "M1"], value="%d %b<br>%Y"),
        dict(dtickrange=["M1", None], value="%b '%y"),
    ]

    fig.update_layout(
        title=f"{active_sym} ({tf_choice}) | LTP: ₹{ltp:,.2f} | Yellow Line = VWAP (Buy Only Above VWAP)",
        template="plotly_dark", height=640, dragmode="pan", hovermode="x unified", showlegend=False,
        margin=dict(l=10, r=65, t=45, b=35),
        yaxis=dict(side="right", title="Price (₹)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
        xaxis=dict(rangeslider_visible=False, rangebreaks=rb, tickformatstops=tv_tickformats, showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        xaxis2=dict(rangeslider_visible=False, rangebreaks=rb, tickformatstops=tv_tickformats, showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
