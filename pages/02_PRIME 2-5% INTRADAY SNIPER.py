from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MU$₹A Rendezvous 2-5% Intraday Sniper", layout="wide")

st.title("🎯 MU$₹A Rendezvous: Realistic ADR & Intraday Sniper Terminal")

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
cur_time = now_ist.time()

if cur_time < datetime.strptime("09:20", "%H:%M").time():
    st.info("⏳ **Pre-Market / Opening Volatility (Before 9:20 AM IST):** Wait for the first 15-minute candle to settle before placing intraday orders.")
elif cur_time <= datetime.strptime("11:45", "%H:%M").time():
    st.success("🟢 **PRIME INTRADAY WINDOW (9:20 AM – 11:45 AM IST):** Best window to enter `🎯 FRESH ROOM LEFT` breakouts.")
elif cur_time <= datetime.strptime("14:15", "%H:%M").time():
    st.warning("🟡 **MID-DAY SESSION (11:45 AM – 2:15 PM IST):** Only enter stocks with `>= 40%` Daily Range remaining near VWAP.")
else:
    st.error("🛑 **LATE SESSION / MARKET CLOSING (After 2:15 PM IST):** Do NOT take fresh intraday trades now—most daily ranges are already exhausted.")

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
            df_s = raw[t_key].dropna(subset=["Close", "Volume", "High", "Low", "Open"]) if len(tickers) > 1 else raw.dropna(subset=["Close", "Volume", "High", "Low", "Open"])
            if len(df_s) < 15:
                continue

            ltp = float(df_s["Close"].iloc[-1])
            day_open = float(df_s["Open"].iloc[-1])
            day_high = float(df_s["High"].iloc[-1])
            day_low = float(df_s["Low"].iloc[-1])
            prev_close = float(df_s["Close"].iloc[-2])

            chg_pct = ((ltp - prev_close) / prev_close) * 100.0
            cur_vol = float(df_s["Volume"].iloc[-1])
            avg_vol = float(df_s["Volume"].iloc[-11:-1].mean())
            rvol = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            # True 14-Day ATR (Average Daily Range in Rupees)
            tr = np.maximum(
                df_s["High"].iloc[-15:-1] - df_s["Low"].iloc[-15:-1],
                np.maximum(
                    abs(df_s["High"].iloc[-15:-1] - df_s["Close"].iloc[-16:-2]),
                    abs(df_s["Low"].iloc[-15:-1] - df_s["Close"].iloc[-16:-2]),
                ),
            )
            atr_14 = float(tr.mean())
            today_moved = day_high - day_low
            range_used_pct = round((today_moved / atr_14) * 100.0, 0) if atr_14 > 0 else 100.0

            # Anchor realistic intraday targets from Day Open / Support (NOT chased afternoon high)
            base_anchor = round((day_open + day_low) / 2.0, 2) if ltp > day_open else day_open
            t1 = round(base_anchor + (atr_14 * 0.90), 2)
            t2 = round(base_anchor + (atr_14 * 1.35), 2)
            sl = round(max(day_low * 0.996, ltp - (atr_14 * 0.55)), 2)

            if ltp >= t1 and rvol >= 1.3:
                status = "✅ T1 ALREADY HIT TODAY"
                action = "BOOKED / WAIT DIP"
                score = 70 + rvol
            elif chg_pct > 0.8 and rvol >= 1.4 and range_used_pct < 85:
                status = "🎯 FRESH ROOM LEFT"
                action = "BUY PULLBACK"
                score = 110 + (rvol * 4) + (100 - range_used_pct) * 0.2
            elif chg_pct > 0.5 and rvol >= 1.2:
                status = "🔵 BUILDING MOMENTUM"
                action = "WATCHLIST"
                score = 50 + (rvol * 3)
            else:
                status = "⚪ LOW VOLUME / EXHAUSTED"
                action = "AVOID"
                score = chg_pct

            rows.append({
                "Score": score,
                "Stock": sym,
                "Company": name,
                "Sniper_Status": status,
                "Action": action,
                "LTP": round(ltp, 2),
                "Change_%": round(chg_pct, 2),
                "Volume_Surge": rvol,
                "Daily_ATR_Used": f"{int(range_used_pct)}%",
                "Intraday_SL": sl,
                "Realistic_T1": t1,
                "Stretch_T2": t2,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    res_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False).head(12).reset_index(drop=True)
    res_df.insert(0, "Rank", range(1, len(res_df) + 1))
    return res_df.drop(columns=["Score"])


with st.spinner("Calculating 14-Day ATR & Intraday Range Remaining..."):
    rank_df = scan_intraday_sniper(UNIVERSE)

selected_sym = "LICHSGFIN"

if not rank_df.empty:
    st.subheader("🏆 Intraday ATR-Adjusted Sniper Ranking Table")
    st.caption("👇 **Only enter `🎯 FRESH ROOM LEFT` stocks where `Daily_ATR_Used` is below 85%.** If `T1 ALREADY HIT TODAY` shows, the move already happened!")

    def style_sniper_rows(row):
        val = str(row["Sniper_Status"])
        if "FRESH ROOM" in val:
            return ["background-color: rgba(0, 230, 118, 0.18)"] * len(row)
        elif "ALREADY HIT" in val:
            return ["background-color: rgba(255, 193, 7, 0.14)"] * len(row)
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
            "Intraday_SL": "₹{:,.2f}",
            "Realistic_T1": "₹{:,.2f}",
            "Stretch_T2": "₹{:,.2f}",
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
    df_1d = t_obj.history(period="1mo", interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

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
    return df, df_1d


df, df_1d = fetch_chart_data(active_sym, tf_choice)

if not df.empty and not df_1d.empty:
    ltp = float(df["Close"].iloc[-1])
    company_name = UNIVERSE.get(active_sym, active_sym)

    # Calculate true 14-day ATR & Today's Session Anchor
    tr = np.maximum(
        df_1d["High"].iloc[-15:-1] - df_1d["Low"].iloc[-15:-1],
        np.maximum(
            abs(df_1d["High"].iloc[-15:-1] - df_1d["Close"].iloc[-16:-2]),
            abs(df_1d["Low"].iloc[-15:-1] - df_1d["Close"].iloc[-16:-2]),
        ),
    )
    atr_14 = float(tr.mean())
    today_open = float(df_1d["Open"].iloc[-1])
    today_low = float(df_1d["Low"].iloc[-1])
    today_high = float(df_1d["High"].iloc[-1])

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["VWAP"] = (
        (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"]).groupby(df["Time"].dt.date).cumsum()
        / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
    )
    latest_vwap = float(df["VWAP"].iloc[-1]) if not np.isnan(df["VWAP"].iloc[-1]) else ltp

    # Anchor targets to morning breakout base (VWAP / Open) instead of afternoon high
    buy_zone = round(latest_vwap, 2)
    sl_price = round(max(today_low * 0.996, buy_zone - (atr_14 * 0.55)), 2)
    t1_price = round(buy_zone + (atr_14 * 0.90), 2)
    t2_price = round(buy_zone + (atr_14 * 1.35), 2)
    t1_already_hit = today_high >= t1_price

    st.subheader(f"📊 Realistic ADR Execution Plan: {company_name} ({active_sym})")

    if t1_already_hit:
        st.warning(
            f"⚠️ **Notice on {active_sym}:** Today's high (**₹{today_high:,.2f}**) ALREADY reached/passed the realistic 1-day ATR Target 1 (**₹{t1_price:,.2f}**)! "
            f"Do NOT chase at ₹{ltp:,.2f} expecting another full intraday leg today—wait for tomorrow's fresh morning setup."
        )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live LTP", f"₹{ltp:,.2f}", f"14D Avg Range: ₹{atr_14:,.2f}")
    m2.metric("🟡 VWAP Pullback Buy", f"₹{buy_zone:,.2f}", "Ideal Morning Entry")
    m3.metric("🛑 Structure Stop-Loss", f"₹{sl_price:,.2f}", "Below Morning Low / ATR")
    m4.metric("🎯 Realistic T1 (0.9x ATR)", f"₹{t1_price:,.2f}", "Achieved ✅" if t1_already_hit else "High-Prob Intraday Target")
    m5.metric("🚀 Stretch T2 (1.35x ATR)", f"₹{t2_price:,.2f}", "Strong Trend Day Only")

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
                  annotation_text=f"🟡 VWAP BUY: ₹{buy_zone:,.2f}", annotation_position="bottom left", annotation_font_color="#FFD700", row=1, col=1)
    fig.add_hline(y=sl_price, line_dash="solid", line_color="#FF5252", line_width=1.6,
                  annotation_text=f"🛑 SL: ₹{sl_price:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252", row=1, col=1)
    fig.add_hline(y=t1_price, line_dash="dash", line_color="#29B6F6", line_width=1.4,
                  annotation_text=f"🎯 REALISTIC T1: ₹{t1_price:,.2f}", annotation_position="top left", annotation_font_color="#29B6F6", row=1, col=1)
    fig.add_hline(y=t2_price, line_dash="dash", line_color="#00E676", line_width=1.4,
                  annotation_text=f"🚀 STRETCH T2: ₹{t2_price:,.2f}", annotation_position="top right", annotation_font_color="#00E676", row=1, col=1)

    rb = [dict(bounds=["sat", "mon"])]
    if tf_choice != "1D":
        rb.append(dict(bounds=[15.5, 9.25], pattern="hour"))

    tv_tickformats = [
        dict(dtickrange=[None, 86400000], value="%H:%M<br>%d %b"),
        dict(dtickrange=[86400000, "M1"], value="%d %b<br>%Y"),
        dict(dtickrange=["M1", None], value="%b '%y"),
    ]

    fig.update_layout(
        title=f"{active_sym} ({tf_choice}) | LTP: ₹{ltp:,.2f} | 14D Avg Daily Move (ATR): ₹{atr_14:,.2f}",
        template="plotly_dark", height=640, dragmode="pan", hovermode="x unified", showlegend=False,
        margin=dict(l=10, r=65, t=45, b=35),
        yaxis=dict(side="right", title="Price (₹)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
        xaxis=dict(rangeslider_visible=False, rangebreaks=rb, tickformatstops=tv_tickformats, showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        xaxis2=dict(rangeslider_visible=False, rangebreaks=rb, tickformatstops=tv_tickformats, showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
