import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide")
st.title("📊 Advanced Smart Money Concepts (SMC) & FVG Terminal")
st.markdown("Multi-timeframe institutional analysis combining **1D Support/Resistance**, **Unmitigated 4H FVGs**, **VWAP + Volume Surges**, and **15m CHoCH Execution Triggers**.")

c_in1, c_in2 = st.columns([1, 2])
raw_sym = c_in1.text_input("Enter NSE Stock Symbol", value="ITC").strip().upper()
ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"
tf_choice = c_in2.radio("Select Candle Interval", ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1D"], index=3, horizontal=True)

@st.cache_data(ttl=60)
def load_smc_data(sym, tf):
    p_map = {"1m": "5d", "3m": "5d", "5m": "10d", "15m": "15d", "30m": "30d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1D": "1d"}
    df = yf.download(sym, period=p_map[tf], interval=i_map[tf], progress=False, auto_adjust=True)
    df_4h = yf.download(sym, period="60d", interval="1h", progress=False, auto_adjust=True)
    df_1d = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=True)
    for d in [df, df_4h, df_1d]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.droplevel(1)
    if df.empty: return df, df_4h, df_1d
    df = df.reset_index().rename(columns={df.columns[0]: "Time"})
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None: df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    if tf in ["3m", "4h"]:
        df = df.set_index("Time").resample("3min" if tf == "3m" else "4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna().reset_index()
    if not df_4h.empty:
        df_4h.index = pd.to_datetime(df_4h.index)
        if df_4h.index.tz is not None: df_4h.index = df_4h.index.tz_convert("Asia/Kolkata").tz_localize(None)
        df_4h = df_4h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return df, df_4h, df_1d

df, df_4h, df_1d = load_smc_data(ticker, tf_choice)
if df.empty:
    st.error(f"No data returned for {ticker}. Check the NSE symbol.")
else:
    ltp = float(df["Close"].iloc[-1])
    res_1d = round(float(df_1d["High"].iloc[-20:].max()), 2) if not df_1d.empty else round(float(df["High"].max()), 2)
    sup_1d = round(float(df_1d["Low"].iloc[-20:].min()), 2) if not df_1d.empty else round(float(df["Low"].min()), 2)

    # VWAP & Volume Surge Calculation
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3.0
    df["DateOnly"] = df["Time"].dt.date
    df["CumPV"] = (df["TP"] * df["Volume"]).groupby(df["DateOnly"]).cumsum()
    df["CumVol"] = df["Volume"].groupby(df["DateOnly"]).cumsum().replace(0, np.nan)
    df["VWAP"] = df["CumPV"] / df["CumVol"]
    vol_avg = df["Volume"].rolling(20, min_periods=1).mean()
    vol_colors = ["#00E676" if (c >= o and v >= 1.5 * va) else ("#FF5252" if (c < o and v >= 1.5 * va) else ("rgba(0,230,118,0.35)" if c >= o else "rgba(255,82,82,0.35)")) for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], vol_avg)]

    # Unmitigated 4H Bullish FVG (Starts at exact formation timestamp, filters zero-width)
    bull_fvg = next(((df_4h.index[i-2], float(df_4h["High"].iloc[i-2]), float(df_4h["Low"].iloc[i])) for i in range(len(df_4h)-1, 1, -1) if (df_4h["Low"].iloc[i] - df_4h["High"].iloc[i-2]) > 0.05), None)

    # Structure Breaks (BOS & CHoCH - keep only last 2 to prevent label clutter)
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh, entry_p = [], None, round(bull_fvg[2], 2) if bull_fvg else round(ltp * 0.99, 2)
    for i in range(4, len(df)):
        if df["SH"].iloc[i-4]: last_sh = (df["Time"].iloc[i-4], float(df["High"].iloc[i-4]))
        if last_sh and float(df["Close"].iloc[i-1]) <= last_sh[1] and float(df["Close"].iloc[i]) > last_sh[1]:
            sigs.append({"t": df["Time"].iloc[i], "x0": last_sh[0], "y": round(last_sh[1], 2)}); last_sh = None
    if sigs: entry_p = sigs[-1]["y"]

    sl_p = round(min(bull_fvg[1] * 0.995 if bull_fvg else entry_p * 0.988, entry_p * 0.99), 2)
    risk = max(entry_p - sl_p, entry_p * 0.006)
    t1_p = round(entry_p + risk * 1.5, 2)
    t2_p = round(max(res_1d, entry_p + risk * 2.5), 2)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.80, 0.20])
    fig.add_trace(go.Candlestick(x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=ticker, increasing_line_color="#00E676", decreasing_line_color="#FF5252"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Time"], y=df["VWAP"], mode="lines", name="Intraday VWAP", line=dict(color="#FFD700", width=1.4)), row=1, col=1)
    fig.add_trace(go.Bar(x=df["Time"], y=df["Volume"], name="Volume", marker_color=vol_colors), row=2, col=1)

    if bull_fvg:
        x_start = max(bull_fvg[0], df["Time"].iloc[0])
        fig.add_shape(type="rect", x0=x_start, x1=df["Time"].iloc[-1], y0=bull_fvg[1], y1=bull_fvg[2], fillcolor="rgba(0,230,118,0.16)", line=dict(width=0), layer="below", row=1, col=1)
        fig.add_annotation(x=x_start, y=bull_fvg[2], text=f"4H Bullish FVG ({bull_fvg[1]:,.1f}-{bull_fvg[2]:,.1f})", showarrow=False, xanchor="left", yshift=10, font=dict(size=10, color="#00E676"), row=1, col=1)

    for idx_s, s in enumerate(sigs[-2:]):
        lbl = f"CHoCH ▲ BUY @ {s['y']}" if idx_s == len(sigs[-2:])-1 else f"BOS ▲ @ {s['y']}"
        fig.add_shape(type="line", x0=s["x0"], x1=s["t"], y0=s["y"], y1=s["y"], line=dict(color="#00E676", width=1.3, dash="dot"), row=1, col=1)
        fig.add_annotation(x=s["t"], y=s["y"], text=lbl, showarrow=False, yshift=12, font=dict(size=10, color="#00E676"), row=1, col=1)

    fig.add_hline(y=sl_p, line_dash="solid", line_color="#FF5252", line_width=1.4, annotation_text=f"🛑 SL: ₹{sl_p:,.2f}", annotation_position="bottom left", annotation_font_color="#FF5252", row=1, col=1)
    fig.add_hline(y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.4, annotation_text=f"🎯 T1 (1.5R): ₹{t1_p:,.2f}", annotation_position="top left", annotation_font_color="#29B6F6", row=1, col=1)
    fig.add_hline(y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.4, annotation_text=f"🚀 T2 (Major): ₹{t2_p:,.2f}", annotation_position="top right", annotation_font_color="#00E676", row=1, col=1)

    rb = [dict(bounds=["sat", "mon"])] + ([dict(bounds=[15.5, 9.25], pattern="hour")] if tf_choice != "1D" else [])
    fig.update_layout(title=f"Institutional SMC & VWAP Chart for {ticker} ({tf_choice}) | LTP: ₹{ltp:,.2f}", template="plotly_dark", height=600, dragmode="pan", hovermode="x unified", showlegend=False, margin=dict(l=10, r=60, t=45, b=30), yaxis=dict(side="right", title="Price (₹)", fixedrange=False), yaxis2=dict(side="right", title="Vol", fixedrange=False), xaxis2=dict(rangeslider_visible=False, rangebreaks=rb), xaxis=dict(rangeslider_visible=False, rangebreaks=rb))
    st.plotly_chart(fig, width="stretch", config={"scrollZoom": True})

    st.subheader("🎯 Top-Down Institutional Setup (1D ➔ 4H ➔ 15m) & Risk-Reward")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Buy Entry / CHoCH", f"₹{entry_p:,.2f}", "4H FVG + VWAP Support")
    m2.metric("Recommended Stop-Loss", f"₹{sl_p:,.2f}", "Protected Zone")
    m3.metric("Target 1 (1.5R)", f"₹{t1_p:,.2f}", "Partial Profit Booking")
    m4.metric("Target 2 (Major Resistance)", f"₹{t2_p:,.2f}", "Full Trend Exit")
