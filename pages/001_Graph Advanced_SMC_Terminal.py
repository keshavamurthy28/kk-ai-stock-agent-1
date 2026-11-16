import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide")

st.title("📊 Advanced Smart Money Concepts (SMC) & FVG Terminal")
st.markdown("Multi-timeframe institutional analysis combining **1D Support/Resistance**, **4H Fair Value Gaps (FVG)**, and **15m CHoCH Execution Triggers**.")

# Top Control Bar (Fully visible below title)
c_sym, c_tf = st.columns([2, 6])
with c_sym:
    stock_input = st.text_input("Enter NSE Stock Symbol", value="RELIANCE").upper().strip()
ticker_symbol = f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input

with c_tf:
    timeframe = st.radio("Select Candle Interval", ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1D"], index=3, horizontal=True)

period_map = {"1m": "5d", "3m": "5d", "5m": "10d", "15m": "30d", "30m": "30d", "1h": "60d", "4h": "60d", "1D": "1y"}
interval_map = {"1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "1h", "1D": "1d"}

@st.cache_data(ttl=60)
def fetch_smart_money_data(ticker, period, interval="1d", resample_tf=None):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.reset_index()
        dt_col = "Datetime" if "Datetime" in df.columns else "Date"
        df.rename(columns={dt_col: "Time"}, inplace=True)
        df["Time"] = pd.to_datetime(df["Time"])
        if df["Time"].dt.tz is not None: df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        if resample_tf:
            df = df.set_index("Time").resample(resample_tf).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna().reset_index()
        return df
    except Exception:
        return pd.DataFrame()

resample_rule = "3min" if timeframe == "3m" else ("4h" if timeframe == "4h" else None)
df_chart = fetch_smart_money_data(ticker_symbol, period_map[timeframe], interval_map[timeframe], resample_rule)
df_1d = fetch_smart_money_data(ticker_symbol, "6mo", "1d")
df_4h = fetch_smart_money_data(ticker_symbol, "60d", "1h", "4h")

if df_chart.empty or len(df_chart) < 10:
    st.warning(f"Could not retrieve live data for {ticker_symbol}. Please check the symbol or try another ticker.")
else:
    # 1. 1D Support & Resistance
    resistance = float(df_1d["High"].tail(60).max()) if not df_1d.empty else float(df_chart["High"].max())
    support = float(df_1d["Low"].tail(60).min()) if not df_1d.empty else float(df_chart["Low"].min())
    current_price = float(df_chart["Close"].iloc[-1])
    midpoint_price = (resistance + support) / 2

    # 2. 4H Fair Value Gaps (FVG)
    bull_fvg_4h, bear_fvg_4h = None, None
    for i in range(2, len(df_4h)):
        if df_4h["Low"].iloc[i] > df_4h["High"].iloc[i - 2]:
            bull_fvg_4h = (float(df_4h["High"].iloc[i - 2]), float(df_4h["Low"].iloc[i]))
        if df_4h["High"].iloc[i] < df_4h["Low"].iloc[i - 2]:
            bear_fvg_4h = (float(df_4h["High"].iloc[i]), float(df_4h["Low"].iloc[i - 2]))

    # 3. CHoCH & Buy/Sell/SL Pointers on Execution Timeframe
    df_chart["SH"] = df_chart["High"] == df_chart["High"].rolling(9, center=True).max()
    df_chart["SL"] = df_chart["Low"] == df_chart["Low"].rolling(9, center=True).min()
    signals, last_sh, last_sl, trend = [], None, None, "neutral"
    for i in range(4, len(df_chart)):
        if df_chart["SH"].iloc[i - 4]: last_sh = (df_chart["Time"].iloc[i - 4], float(df_chart["High"].iloc[i - 4]))
        if df_chart["SL"].iloc[i - 4]: last_sl = (df_chart["Time"].iloc[i - 4], float(df_chart["Low"].iloc[i - 4]))
        c, pc, t = float(df_chart["Close"].iloc[i]), float(df_chart["Close"].iloc[i - 1]), df_chart["Time"].iloc[i]
        if sh := last_sh:
            if pc <= sh[1] and c > sh[1]:
                sl_p = last_sl[1] * 0.998 if last_sl else float(df_chart["Low"].iloc[i]) * 0.995
                signals.append({"t": t, "p": float(df_chart["Low"].iloc[i]), "type": "BUY", "lbl": "Bullish CHoCH" if trend != "bull" else "BOS", "x0": sh[0], "y": sh[1], "sl": round(sl_p, 2)})
                trend, last_sh = "bull", None
        if sl := last_sl:
            if pc >= sl[1] and c < sl[1]:
                sl_p = last_sh[1] * 1.002 if last_sh else float(df_chart["High"].iloc[i]) * 1.005
                signals.append({"t": t, "p": float(df_chart["High"].iloc[i]), "type": "SELL", "lbl": "Bearish CHoCH" if trend != "bear" else "BOS", "x0": sl[0], "y": sl[1], "sl": round(sl_p, 2)})
                trend, last_sl = "bear", None

    fig = go.Figure(data=[go.Candlestick(x=df_chart["Time"], open=df_chart["Open"], high=df_chart["High"], low=df_chart["Low"], close=df_chart["Close"], name="Price Action", increasing_line_color="#00E676", decreasing_line_color="#FF5252")])

    fig.add_hline(y=resistance, line_dash="dash", line_color="#FF5252", annotation_text=f"1D Resistance / Sell Zone ({resistance:,.2f})", annotation_position="top left")
    fig.add_hline(y=support, line_dash="dash", line_color="#00E676", annotation_text=f"1D Support / Demand Zone ({support:,.2f})", annotation_position="bottom left")

    b_y0, b_y1 = bear_fvg_4h if bear_fvg_4h else (midpoint_price * 1.01, midpoint_price * 1.03)
    g_y0, g_y1 = bull_fvg_4h if bull_fvg_4h else (midpoint_price * 0.97, midpoint_price * 0.99)
    fig.add_hrect(y0=b_y0, y1=b_y1, fillcolor="rgba(255, 82, 82, 0.15)", layer="below", line_width=0, annotation_text=f"4H Bearish FVG ({b_y0:,.0f}-{b_y1:,.0f})", annotation_position="top right")
    fig.add_hrect(y0=g_y0, y1=g_y1, fillcolor="rgba(0, 230, 118, 0.15)", layer="below", line_width=0, annotation_text=f"4H Bullish FVG ({g_y0:,.0f}-{g_y1:,.0f})", annotation_position="bottom right")

    for s in signals[-6:]:
        col = "#00E676" if s["type"] == "BUY" else "#FF5252"
        fig.add_shape(type="line", x0=s["x0"], x1=s["t"], y0=s["y"], y1=s["y"], line=dict(color=col, width=1.2, dash="dot"))
        fig.add_annotation(x=s["t"], y=s["y"], text=s["lbl"], showarrow=False, yshift=10 if s["type"] == "BUY" else -10, font=dict(size=9, color=col))
        fig.add_annotation(x=s["t"], y=s["p"], text=f"▲ BUY @ {s['p']:.0f}" if s["type"] == "BUY" else f"▼ SELL @ {s['p']:.0f}", showarrow=True, arrowhead=2, arrowcolor=col, ay=25 if s["type"] == "BUY" else -25, font=dict(color=col, size=10))

    latest_sig = signals[-1] if signals else None
    stop_loss = latest_sig["sl"] if latest_sig else (round(resistance * 1.005, 2) if current_price > midpoint_price else round(support * 0.995, 2))
    fig.add_hline(y=stop_loss, line_dash="solid", line_color="#FF9800", annotation_text=f"🛑 Stop-Loss Point ({stop_loss:,.2f})", annotation_position="bottom right", annotation_font_color="#FF9800")

    rb = [dict(bounds=["sat", "mon"])] + ([dict(bounds=[15.5, 9.25], pattern="hour")] if timeframe != "1D" else [])
    fig.update_layout(
        title=f"Institutional SMC Chart for {ticker_symbol} ({timeframe} Timeframe) | LTP: ₹{current_price:,.2f}",
        yaxis=dict(title="Price (INR ₹)", side="right", fixedrange=False),
        xaxis=dict(title="Timeline", rangeslider_visible=False, rangebreaks=rb, rangeselector=dict(buttons=[dict(count=1, label="1D", step="day", stepmode="backward"), dict(count=5, label="5D", step="day", stepmode="backward"), dict(count=7, label="1W", step="day", stepmode="backward"), dict(count=1, label="1M", step="month", stepmode="backward"), dict(count=3, label="3M", step="month", stepmode="backward"), dict(count=6, label="6M", step="month", stepmode="backward"), dict(count=1, label="1Y", step="year", stepmode="backward"), dict(step="all", label="All")], bgcolor="#1E222D", activecolor="#2962FF", font=dict(color="white", size=11), x=0.0, y=-0.15)),
        template="plotly_dark", height=650, dragmode="pan", hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.markdown("---")
    st.subheader("🎯 Top-Down Institutional Setup (1D ➔ 4H ➔ 15m) & Risk-Reward")
    col1, col2, col3, col4 = st.columns(4)

    if (latest_sig and latest_sig["type"] == "SELL") or (not latest_sig and current_price > midpoint_price):
        setup_type = "📉 Bearish Sell Setup (1D/4H Supply)"
        entry_price = round(latest_sig["p"], 2) if latest_sig else round(current_price, 2)
        target_1 = round(entry_price - abs(stop_loss - entry_price) * 1.5, 2)
        target_2 = round(support, 2)
    else:
        setup_type = "📈 Bullish Buy Setup (1D/4H Demand)"
        entry_price = round(latest_sig["p"], 2) if latest_sig else round(current_price, 2)
        target_1 = round(entry_price + abs(entry_price - stop_loss) * 1.5, 2)
        target_2 = round(resistance, 2)

    col1.metric("Buy / Sell Entry & Bias", f"₹{entry_price:,.2f}", setup_type)
    col2.metric("Recommended Stop-Loss", f"₹{stop_loss:,.2f}", "Protected Zone")
    col3.metric("Target 1 (1.5R)", f"₹{target_1:,.2f}", "Partial Profit Booking")
    col4.metric("Target 2 (Major 1D S/R)", f"₹{target_2:,.2f}", "Full Trend Exit")

    st.info(f"💡 **Top-Down Rule (1D ➔ 4H ➔ 15m):** For **{ticker_symbol}**, align with 1D Support/Resistance, wait for pullback into the **4H FVG zone**, and execute on **{timeframe} CHoCH** confirmation around **₹{entry_price:,.2f}** with strict Stop-Loss at **₹{stop_loss:,.2f}**.")
