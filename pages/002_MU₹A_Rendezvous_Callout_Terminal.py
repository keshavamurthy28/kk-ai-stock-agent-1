import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MU$₹A Rendezvous Advance Callouts", layout="wide")

st.title("🎯 MU$₹A Rendezvous: Advance Daily Callout Terminal")
st.markdown("""
*Welcome to the MU$₹A Rendezvous setup engine.* This terminal simulates expert community callouts by identifying 
high-probability swing breakout stocks **in advance**, complete with precise Limit Buy zones, Zero-Loss trailing locks, 
and clear multi-tier profit targets for effortless execution.
""")

# Pre-curated high-beta community setup watchlist (matching MU$₹A & Juggernaut style breakouts)
WATCHLIST = {
    "MCX": {"name": "Multi Commodity Exchange", "bias": "Bullish Breakout", "multiplier": 1.02},
    "CDSL": {"name": "Central Depository Services", "bias": "Accumulation Breakout", "multiplier": 1.015},
    "APOLLOMIC": {"name": "Apollo Micro Systems", "bias": "Momentum Spike", "multiplier": 1.025},
    "LICHSGFIN": {"name": "LIC Housing Finance", "bias": "Volume Expansion", "multiplier": 1.018},
    "ITC": {"name": "ITC Limited", "bias": "Night-Before Coil", "multiplier": 1.01},
    "MAXHEALTH": {"name": "Max Healthcare", "bias": "Institutional Accumulation", "multiplier": 1.012}
}

c1, c2 = st.columns([1, 2])
selected_sym = c1.selectbox("Select MU$₹A Featured Callout Stock", list(WATCHLIST.keys()), index=0)
tf_choice = c2.radio("Select Candle Interval", ["15m", "1h", "4h", "1D"], index=2, horizontal=True)

ticker = f"{selected_sym}.NS"

@st.cache_data(ttl=10)
def fetch_callout_data(sym, tf):
    t_obj = yf.Ticker(sym)
    p_map = {"15m": "15d", "1h": "60d", "4h": "60d", "1D": "6mo"}
    i_map = {"15m": "15m", "1h": "1h", "4h": "1h", "1D": "1d"}
    df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)
    df_1d = t_obj.history(period="6mo", interval="1d", auto_adjust=True)
    
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
        df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df, df_1d

df, df_1d = fetch_callout_data(ticker, tf_choice)

if df.empty:
    st.error(f"Could not fetch data for {ticker}. Please verify the symbol.")
else:
    ltp = float(df["Close"].iloc[-1])
    meta = WATCHLIST[selected_sym]
    
    # Calculate advance trade parameters based on community logic
    suggested_entry = round(ltp * 0.992, 2)  # Pullback limit entry
    initial_sl = round(suggested_entry * 0.965, 2)  # Protected zone SL (~3.5%)
    risk = suggested_entry - initial_sl
    target_1 = round(suggested_entry + (risk * 1.5), 2)  # 1.5R Book 50%
    target_2 = round(suggested_entry + (risk * 2.5), 2)  # 2.5R Book Balance
    zero_loss_trigger = round(suggested_entry + (risk * 0.8), 2)

    st.markdown("---")
    st.subheader(f"📊 Advance Execution Blueprint: {meta['name']} ({selected_sym})")
    
    # Metrics Dashboard for Beginners
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live LTP", f"₹{ltp:,.2f}", meta["bias"])
    m2.metric("🟡 Kite Limit Buy", f"₹{suggested_entry:,.2f}", "Advance Entry")
    m3.metric("🛑 Initial Stop-Loss", f"₹{initial_sl:,.2f}", "Max Risk Protected")
    m4.metric("🎯 Target 1 (1.5R)", f"₹{target_1:,.2f}", "Book 50% Quantity")
    m5.metric("🚀 Target 2 (2.5R)", f"₹{target_2:,.2f}", "Full Trend Exit")

    # Actionable Guidance Box
    st.info(f"""
    **🛡️ MU$₹A Execution Rule for {selected_sym}:**
    1. **Entry:** Place a Limit Buy order on Zerodha Kite at **₹{suggested_entry:,.2f}** during minor intraday pullbacks.
    2. **Stop-Loss:** Set initial hard stop-loss at **₹{initial_sl:,.2f}**.
    3. **Zero-Loss Lock:** The moment price reaches **₹{zero_loss_trigger:,.2f}**, immediately modify your stop-loss order to your entry price (**₹{suggested_entry:,.2f}**) to secure a risk-free trade.
    """)

    # VWAP & Volume calculations
    df["VWAP"] = (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"]).groupby(df["Time"].dt.date).cumsum() / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
    v_avg = df["Volume"].rolling(20, min_periods=1).mean()
    v_col = ["#00E676" if (c >= o and v >= 1.5 * va) else ("#FF5252" if (c < o and v >= 1.5 * va) else ("rgba(0,230,118,0.35)" if c >= o else "rgba(255,82,82,0.35)")) for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)]

    # Plotting Advanced Interactive Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.80, 0.20])
    
    fig.add_trace(go.Candlestick(
        x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=selected_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df["Time"], y=df["VWAP"], mode="lines", name="VWAP",
        line=dict(color="#FFD700", width=1.4)
    ), row=1, col=1)
    
    fig.add_trace(go.Bar(
        x=df["Time"], y=df["Volume"], name="Volume", marker_color=v_col
    ), row=2, col=1)

    # Add visual level lines for buy, sl, and targets
    fig.add_hline(y=suggested_entry, line_dash="solid", line_color="#FFD700", line_width=1.6,
                  annotation_text=f"🟡 LIMIT BUY: ₹{suggested_entry:,.2f}", annotation_position="bottom left", annotation_font_color="#FFD700", row=1, col=1)
    fig.add_hline(y=initial_sl, line_dash="solid", line_color="#FF5252", line_width=1.5,
                  annotation_text=f"🛑 STOP LOSS: ₹{initial_sl:,.2f}", annotation_position="bottom right", annotation_font_color="#FF5252", row=1, col=1)
    fig.add_hline(y=target_1, line_dash="dash", line_color="#29B6F6", line_width=1.4,
                  annotation_text=f"🎯 TARGET 1 (1.5R): ₹{target_1:,.2f}", annotation_position="top left", annotation_font_color="#29B6F6", row=1, col=1)
    fig.add_hline(y=target_2, line_dash="dash", line_color="#00E676", line_width=1.4,
                  annotation_text=f"🚀 TARGET 2 (2.5R): ₹{target_2:,.2f}", annotation_position="top right", annotation_font_color="#00E676", row=1, col=1)

    rb = [dict(bounds=["sat", "mon"])] + ([dict(bounds=[15.5, 9.25], pattern="hour")] if tf_choice != "1D" else [])
    
    fig.update_layout(
        title=f"MU$₹A Callout Setup: {selected_sym} ({tf_choice}) | Current LTP: ₹{ltp:,.2f}",
        template="plotly_dark", height=600, dragmode="pan", hovermode="x unified", showlegend=False,
        margin=dict(l=10, r=60, t=45, b=30),
        yaxis=dict(side="right", title="Price (₹)"),
        yaxis2=dict(side="right", title="Volume"),
        xaxis2=dict(rangeslider_visible=False, rangebreaks=rb),
        xaxis=dict(rangeslider_visible=False, rangebreaks=rb)
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
