import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide")
st.title("📊 Advanced Smart Money Concepts (SMC) & Institutional FVG Terminal")

# Top Control Bar
c1, c2, c3 = st.columns([1.2, 2.2, 1.6])
raw_sym = c1.text_input("Enter NSE Stock Symbol", value="ITC").strip().upper()
ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"
tf_choice = c2.radio(
    "Candle Interval (TradingView / Kite Style)",
    ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1D"],
    index=2,
    horizontal=True,
)
show_layers = c3.multiselect(
    "Active SMC Layers",
    ["4H FVG", "Order Blocks", "BOS / CHoCH", "Liquidity (BSL/SSL)", "Discount/Premium 50%"],
    default=["4H FVG", "Order Blocks", "BOS / CHoCH", "Liquidity (BSL/SSL)"],
)


@st.cache_data(ttl=10)
def fetch_clean_smc(sym, tf):
    p_map = {"1m": "5d", "3m": "5d", "5m": "10d", "15m": "15d", "30m": "30d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1D": "1d"}
    t_obj = yf.Ticker(sym)
    df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)
    df4 = t_obj.history(period="60d", interval="1h", auto_adjust=True)
    df1 = t_obj.history(period="6mo", interval="1d", auto_adjust=True)

    req = {"Open", "High", "Low", "Close", "Volume"}
    if df is None or df.empty or not req.issubset(set(df.columns)):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
        df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

    if tf in ["3m", "4h"]:
        rule = "3min" if tf == "3m" else "4h"
        offset = "0min" if tf == "3m" else "15min"
        df = (
            df.set_index("Time")
            .resample(rule, offset=offset)
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
            .dropna()
            .reset_index()
        )

    if df4 is not None and not df4.empty and {"Open", "High", "Low", "Close"}.issubset(set(df4.columns)):
        df4.index = pd.to_datetime(df4.index)
        if df4.index.tz is not None:
            df4.index = df4.index.tz_convert("Asia/Kolkata").tz_localize(None)
        df4 = df4.resample("4h", offset="15min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()

    return df, df4, df1


df, df_4h, df_1d = fetch_clean_smc(ticker, tf_choice)

if df.empty:
    st.error(f"No data returned for {ticker}. Please verify the NSE symbol.")
else:
    ltp = float(df["Close"].iloc[-1])
    res_1d = (
        round(float(df_1d["High"].iloc[-20:].max()), 2)
        if (df_1d is not None and not df_1d.empty and "High" in df_1d.columns)
        else round(float(df["High"].max()), 2)
    )
    sup_1d = (
        round(float(df_1d["Low"].iloc[-20:].min()), 2)
        if (df_1d is not None and not df_1d.empty and "Low" in df_1d.columns)
        else round(float(df["Low"].min()), 2)
    )

    # Core Indicators: Intraday VWAP + 20 EMA + Volume Surge
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["VWAP"] = (
        (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"]).groupby(df["Time"].dt.date).cumsum()
        / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
    )
    latest_vwap = float(df["VWAP"].iloc[-1]) if not np.isnan(df["VWAP"].iloc[-1]) else ltp

    v_avg = df["Volume"].rolling(20, min_periods=1).mean()
    v_col = [
        "#00E676" if (c >= o and v >= 1.5 * va)
        else ("#FF5252" if (c < o and v >= 1.5 * va)
              else ("rgba(0,230,118,0.38)" if c >= o else "rgba(255,82,82,0.38)"))
        for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
    ]

    # 1. Higher-Timeframe (4H) Bullish & Bearish Fair Value Gaps (FVG)
    bull_fvg, bear_fvg = None, None
    if df_4h is not None and len(df_4h) >= 3:
        for i in range(len(df_4h) - 1, 1, -1):
            if bull_fvg is None and (df_4h["Low"].iloc[i] - df_4h["High"].iloc[i - 2]) > 0.05:
                bull_fvg = (df_4h.index[i - 2], float(df_4h["High"].iloc[i - 2]), float(df_4h["Low"].iloc[i]))
            if bear_fvg is None and (df_4h["Low"].iloc[i - 2] - df_4h["High"].iloc[i]) > 0.05:
                bear_fvg = (df_4h.index[i - 2], float(df_4h["High"].iloc[i]), float(df_4h["Low"].iloc[i - 2]))
            if bull_fvg and bear_fvg:
                break

    # 2. Institutional Bullish Order Block (Last red candle before high-volume green impulse)
    bull_ob = None
    for i in range(len(df) - 2, 1, -1):
        is_red = df["Close"].iloc[i] < df["Open"].iloc[i]
        next_strong_green = (df["Close"].iloc[i + 1] > df["Open"].iloc[i + 1]) and (df["Volume"].iloc[i + 1] >= 1.4 * v_avg.iloc[i + 1])
        if is_red and next_strong_green:
            bull_ob = (df["Time"].iloc[i], float(df["Low"].iloc[i]), float(df["High"].iloc[i]))
            break

    # 3. Market Structure: Swing Highs -> BOS & CHoCH
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df)):
        if df["SH"].iloc[i - 4]:
            last_sh = (df["Time"].iloc[i - 4], float(df["High"].iloc[i - 4]))
        if last_sh and float(df["Close"].iloc[i - 1]) <= last_sh[1] and float(df["Close"].iloc[i]) > last_sh[1]:
            sigs.append({"t": df["Time"].iloc[i], "x0": last_sh[0], "y": round(last_sh[1], 2)})
            last_sh = None

    # 4. Liquidity Pools (Buy-Side BSL & Sell-Side SSL) & Equilibrium (50%)
    lookback = min(len(df), 60)
    bsl_level = round(float(df["High"].iloc[-lookback:].max()), 2)
    ssl_level = round(float(df["Low"].iloc[-lookback:].min()), 2)
    eq_level = round((bsl_level + ssl_level) / 2.0, 2)
    zone_tag = "DISCOUNT ZONE (Good Value) 🟢" if ltp <= eq_level else "PREMIUM ZONE (Wait Pullback) 🟠"

    # 5. Smart Trade Execution Levels (Anchored to SMC Structure + VWAP)
    if bull_ob and bull_ob[1] <= ltp <= bull_ob[2] * 1.02:
        entry_p = round(bull_ob[2], 2)
    elif bull_fvg and bull_fvg[1] <= ltp <= bull_fvg[2] * 1.02:
        entry_p = round(bull_fvg[2], 2)
    elif sigs:
        entry_p = round(max(sigs[-1]["y"], latest_vwap), 2)
    else:
        entry_p = round(max(latest_vwap, ltp * 0.995), 2)

    raw_sl = bull_ob[1] * 0.996 if bull_ob else (bull_fvg[1] * 0.996 if bull_fvg else entry_p * 0.988)
    sl_p = round(min(raw_sl, entry_p * 0.99), 2)
    risk = max(entry_p - sl_p, entry_p * 0.008)
    t1_p = round(entry_p + risk * 1.5, 2)
    t2_p = round(max(bsl_level, entry_p + risk * 2.5), 2)
    breakeven_p = round(entry_p + risk * 0.8, 2)

    # Top Execution Blueprint Header (Matching Sniper Style)
    st.subheader(f"📊 Institutional SMC Execution Blueprint: {raw_sym} ({tf_choice})")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live LTP", f"₹{ltp:,.2f}", "Above VWAP ✅" if ltp >= latest_vwap else "Below VWAP ⚠️")
    m2.metric("🟡 Limit Buy / Entry", f"₹{entry_p:,.2f}", zone_tag)
    m3.metric("🛑 Hard Stop-Loss", f"₹{sl_p:,.2f}", "Below Order Block / FVG")
    m4.metric("🎯 Target 1 (1.5R)", f"₹{t1_p:,.2f}", "Book 60% Profit")
    m5.metric("🚀 Target 2 (BSL / 2.5R)", f"₹{t2_p:,.2f}", "Full Liquidity Target")

    st.info(
        f"**⚡ Beginner SMC Execution Rule for {raw_sym}:**  \n"
        f"1. **Smart Entry:** Place a Limit Buy around **₹{entry_p:,.2f}** (aligned with VWAP ₹{latest_vwap:,.2f} & institutional demand). Avoid chasing far above VWAP.  \n"
        f"2. **Zero-Loss Lock:** Once price reaches **₹{breakeven_p:,.2f}**, trail your Stop-Loss from ₹{sl_p:,.2f} up to your entry price (**₹{entry_p:,.2f}**) to make the trade 100% risk-free.  \n"
        f"3. **Profit Booking:** Book 60% at **₹{t1_p:,.2f}** and trail the rest toward Buy-Side Liquidity (**₹{t2_p:,.2f}**)."
    )

    # Build Dual-Pane TradingView / Kite Style Chart
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.78, 0.22],
    )

    # Candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df["Time"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )

    # VWAP & 20 EMA
    fig.add_trace(
        go.Scatter(x=df["Time"], y=df["VWAP"], mode="lines", name="VWAP", line=dict(color="#FFD700", width=1.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["Time"], y=df["EMA20"], mode="lines", name="20 EMA", line=dict(color="#29B6F6", width=1.2)),
        row=1,
        col=1,
    )

    # Volume Bars
    fig.add_trace(
        go.Bar(x=df["Time"], y=df["Volume"], name="Volume", marker_color=v_col),
        row=2,
        col=1,
    )

    # Layer 1: 4H FVG Zones
    if "4H FVG" in show_layers:
        if bull_fvg:
            xs = max(bull_fvg[0], df["Time"].iloc[0])
            fig.add_shape(
                type="rect", x0=xs, x1=df["Time"].iloc[-1], y0=bull_fvg[1], y1=bull_fvg[2],
                fillcolor="rgba(0, 230, 118, 0.14)", line=dict(color="rgba(0, 230, 118, 0.4)", width=1),
                layer="below", row=1, col=1,
            )
            fig.add_annotation(
                x=xs, y=bull_fvg[2], text=f"4H Demand FVG (₹{bull_fvg[1]:,.1f}–₹{bull_fvg[2]:,.1f})",
                showarrow=False, xanchor="left", yshift=10, font=dict(size=10, color="#00E676"), row=1, col=1,
            )
        if bear_fvg:
            xs_b = max(bear_fvg[0], df["Time"].iloc[0])
            fig.add_shape(
                type="rect", x0=xs_b, x1=df["Time"].iloc[-1], y0=bear_fvg[1], y1=bear_fvg[2],
                fillcolor="rgba(255, 82, 82, 0.12)", line=dict(color="rgba(255, 82, 82, 0.4)", width=1),
                layer="below", row=1, col=1,
            )
            fig.add_annotation(
                x=xs_b, y=bear_fvg[1], text=f"4H Supply FVG (₹{bear_fvg[1]:,.1f}–₹{bear_fvg[2]:,.1f})",
                showarrow=False, xanchor="left", yshift=-12, font=dict(size=10, color="#FF5252"), row=1, col=1,
            )

    # Layer 2: Institutional Bullish Order Block
    if "Order Blocks" in show_layers and bull_ob:
        xs_ob = max(bull_ob[0], df["Time"].iloc[0])
        fig.add_shape(
            type="rect", x0=xs_ob, x1=df["Time"].iloc[-1], y0=bull_ob[1], y1=bull_ob[2],
            fillcolor="rgba(41, 182, 246, 0.16)", line=dict(color="#29B6F6", width=1, dash="dot"),
            layer="below", row=1, col=1,
        )
        fig.add_annotation(
            x=xs_ob, y=bull_ob[1], text=f"🏦 Bullish OB (₹{bull_ob[1]:,.1f}–₹{bull_ob[2]:,.1f})",
            showarrow=False, xanchor="left", yshift=-12, font=dict(size=10, color="#29B6F6"), row=1, col=1,
        )

    # Layer 3: BOS / CHoCH Structural Breaks
    if "BOS / CHoCH" in show_layers:
        for idx_s, s in enumerate(sigs[-3:]):
            is_latest = idx_s == len(sigs[-3:]) - 1
            fig.add_shape(
                type="line", x0=s["x0"], x1=s["t"], y0=s["y"], y1=s["y"],
                line=dict(color="#00E676", width=1.4, dash="dot"), row=1, col=1,
            )
            fig.add_annotation(
                x=s["t"], y=s["y"],
                text=f"CHoCH ▲ @ ₹{s['y']}" if is_latest else f"BOS ▲ @ ₹{s['y']}",
                showarrow=False, yshift=12, font=dict(size=10, color="#00E676"), row=1, col=1,
            )

    # Layer 4: Liquidity Pools (BSL / SSL)
    if "Liquidity (BSL/SSL)" in show_layers:
        fig.add_hline(
            y=bsl_level, line_dash="dot", line_color="#AB47BC", line_width=1.2,
            annotation_text=f"💧 BSL (Buy-Side Liquidity): ₹{bsl_level:,.2f}",
            annotation_position="top left", annotation_font_color="#CE93D8", row=1, col=1,
        )
        fig.add_hline(
            y=ssl_level, line_dash="dot", line_color="#FF7043", line_width=1.2,
            annotation_text=f"💧 SSL (Sell-Side Liquidity): ₹{ssl_level:,.2f}",
            annotation_position="bottom left", annotation_font_color="#FFAB91", row=1, col=1,
        )

    # Layer 5: Equilibrium 50% Line
    if "Discount/Premium 50%" in show_layers:
        fig.add_hline(
            y=eq_level, line_dash="dashdot", line_color="#9E9E9E", line_width=1.0,
            annotation_text=f"⚖️ 50% Equilibrium: ₹{eq_level:,.2f}",
            annotation_position="top right", annotation_font_color="#BDBDBD", row=1, col=1,
        )

    # Core Execution Lines (BUY, SL, T1, T2)
    fig.add_hline(
        y=entry_p, line_dash="solid", line_color="#FFD700", line_width=1.6,
        annotation_text=f"🟡 BUY ZONE: ₹{entry_p:,.2f}",
        annotation_position="bottom left", annotation_font_color="#FFD700", row=1, col=1,
    )
    fig.add_hline(
        y=sl_p, line_dash="solid", line_color="#FF5252", line_width=1.6,
        annotation_text=f"🛑 SL: ₹{sl_p:,.2f}",
        annotation_position="bottom right", annotation_font_color="#FF5252", row=1, col=1,
    )
    fig.add_hline(
        y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.4,
        annotation_text=f"🎯 T1 (1.5R): ₹{t1_p:,.2f}",
        annotation_position="top left", annotation_font_color="#29B6F6", row=1, col=1,
    )
    fig.add_hline(
        y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.4,
        annotation_text=f"🚀 T2 (2.5R): ₹{t2_p:,.2f}",
        annotation_position="top right", annotation_font_color="#00E676", row=1, col=1,
    )

    # Remove weekend & overnight off-market gaps
    rb = [dict(bounds=["sat", "mon"])]
    if tf_choice != "1D":
        rb.append(dict(bounds=[15.5, 9.25], pattern="hour"))

    # TradingView / Zerodha Kite style X-axis: Time on top, Date below
    tv_tickformats = [
        dict(dtickrange=[None, 86400000], value="%H:%M<br>%d %b"),
        dict(dtickrange=[86400000, "M1"], value="%d %b<br>%Y"),
        dict(dtickrange=["M1", None], value="%b '%y"),
    ]

    fig.update_layout(
        title=f"SMC & Institutional Flow: {raw_sym} ({tf_choice}) | LTP: ₹{ltp:,.2f} | Yellow: VWAP | Blue: 20 EMA",
        template="plotly_dark",
        height=660,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=45, b=35),
        yaxis=dict(side="right", title="Price (₹)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
        xaxis=dict(
            rangeslider_visible=False,
            rangebreaks=rb,
            tickformatstops=tv_tickformats,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
        ),
        xaxis2=dict(
            rangeslider_visible=False,
            rangebreaks=rb,
            tickformatstops=tv_tickformats,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
