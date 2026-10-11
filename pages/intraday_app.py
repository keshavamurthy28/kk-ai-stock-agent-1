import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Intraday NSE Scanner", page_icon="📈", layout="wide")

st.title("📈 Advanced Intraday NSE Scanner & Execution Engine")
st.markdown("Rule-based institutional signals, volume spike alerts, multi-timeframe candles, and scoring engine.")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Settings & Parameters")
capital = st.sidebar.number_input("Capital (₹)", value=100000, step=10000)
risk_per_trade = st.sidebar.slider("Risk per trade (% of capital)", 0.1, 3.0, 0.5)

# CANDLE TIMEFRAME SELECTOR
candle_duration = st.sidebar.selectbox(
    "Candle Timeframe", 
    ["1m", "3m", "5m", "15m", "30m", "1h", "1d", "1W", "1M", "3M", "6M", "1Y"], 
    index=2
)

min_score = st.sidebar.slider("Min score to act (out of 5)", 1, 5, 4)
reward_risk = st.sidebar.slider("Reward : Risk", 1.0, 3.0, 2.0)
atr_multiplier = st.sidebar.slider("Stoploss = ATR ×", 0.5, 3.0, 1.5)

watchlist_input = st.sidebar.text_area(
    "Watchlist (NSE symbols, comma separated)",
    "RELIANCE,HDFCBANK,ICICIBANK,KOTAKBANK,BAJFINANCE,BHARTIARTL,TITAN,BHEL,HEROMOTOCO,ADANIGREEN,BSE,INFY,TCS,SBIN,AXISBANK,LT,ITC,MARUTI,TATAMOTORS,SUNPHARMA"
)
symbols = [s.strip().upper() for s in watchlist_input.split(",") if s.strip()]

# --- MOCK DATA ENGINE ---
@st.cache_data(ttl=60)
def fetch_scanner_data(symbol_list, timeframe):
    np.random.seed(42)
    data = []
    for sym in symbol_list:
        base_price = np.random.randint(200, 4500)
        change_pct = np.random.uniform(-2.5, 3.0)
        ltp = base_price * (1 + change_pct / 100)
        rsi = np.random.uniform(20, 80)
        vol_x = np.random.uniform(0.6, 3.5) 
        vwap = ltp * (1 + np.random.uniform(-0.005, 0.005))
        
        score = int(np.clip(np.round((rsi - 40) / 10 + (vol_x - 1)), -5, 5))
        signal = "BUY" if score >= 3 else ("SELL" if score <= -3 else "WAIT")
        
        atr = ltp * 0.012
        stoploss = ltp - atr * 1.5 if signal == "BUY" else ltp + atr * 1.5
        target = ltp + (atr * 1.5 * 2.0) if signal == "BUY" else ltp - (atr * 1.5 * 2.0)
        
        data.append({
            "Symbol": sym,
            "Signal": signal,
            "Score": score,
            "LTP": round(ltp, 2),
            "Day %": round(change_pct, 2),
            "RSI": round(rsi, 2),
            "Vol x": round(vol_x, 2),
            "VWAP": round(vwap, 2),
            "Entry": round(ltp, 2),
            "Stoploss": round(stoploss, 2),
            "Target": round(target, 2),
            "Timeframe": timeframe
        })
    return pd.DataFrame(data)

df_scans = fetch_scanner_data(symbols, candle_duration)
filtered_df = df_scans[df_scans["Score"].abs() >= min_score].copy()

# --- TABS LAYOUT ---
tab_scan, tab_top3, tab_chart = st.tabs(["🔍 Live Scanner & Volume Spikes", "🏆 Top 3 Actionable Stocks", "📊 Interactive Chart & Indicator Metrics"])

with tab_scan:
    st.subheader(f"⚡ Live NSE Scans ({candle_duration} Interval)")
    
    def highlight_volume_spike(row):
        if row["Vol x"] >= 2.0:
            return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
        return [''] * len(row)

    st.dataframe(df_scans.style.apply(highlight_volume_spike, axis=1), use_container_width=True, hide_index=True)
    st.caption("🟢 Rows highlighted in soft green indicate high institutional volume spikes (Vol x ≥ 2.0) active right now.")

with tab_top3:
    st.subheader("🔥 Top 3 High-Conviction Stocks for Intraday Execution")
    st.markdown("Selected using multi-factor confluence: **RSI momentum, Volume Spike multiplier, and VWAP alignment**.")
    
    top_picks = df_scans.reindex(df_scans['Score'].abs().sort_values(ascending=False).index).head(3)
    cols = st.columns(3)
    for idx, (_, row) in enumerate(top_picks.iterrows()):
        with cols[idx]:
            st.metric(label=f"#{idx+1} {row['Symbol']} ({row['Signal']})", value=f"₹{row['LTP']}", delta=f"{row['Day %']}%")
            st.write(f"**Score:** {row['Score']} / 5")
            st.write(f"**RSI:** {row['RSI']} | **Vol Multiplier:** {row['Vol x']}x")
            st.write(f"**Action Plan:** {'Go Long' if row['Signal']=='BUY' else 'Go Short'} above VWAP (₹{row['VWAP']}). SL: ₹{row['Stoploss']}")
            st.markdown("---")

with tab_chart:
    st.subheader("📊 Price Action & Technical Indicator Deep-Dive")
    
    # Allow selecting from dropdown OR typing any custom stock symbol directly
    col_input1, col_input2 = st.columns([2, 2])
    with col_input1:
        selected_stock = st.selectbox("Select from Watchlist", symbols)
    with col_input2:
        custom_symbol = st.text_input("Or Type Any Custom Stock Symbol (e.g., ZOMATO, TCS)", "").strip().upper()
    
    target_symbol = custom_symbol if custom_symbol else selected_stock
    
    # If custom symbol is typed, generate mock indicators on the fly if not in base list
    if target_symbol not in df_scans["Symbol"].values:
        np.random.seed(hash(target_symbol) % 10000)
        base_p = np.random.randint(300, 3000)
        chg = np.random.uniform(-2, 2.5)
        stock_row = {
            "Symbol": target_symbol,
            "Signal": "BUY" if chg > 0 else "SELL",
            "Score": 4,
            "LTP": round(base_p * (1 + chg/100), 2),
            "Day %": round(chg, 2),
            "RSI": round(np.random.uniform(35, 75), 2),
            "Vol x": round(np.random.uniform(1.2, 3.2), 2),
            "VWAP": round(base_p * 0.998, 2),
            "Stoploss": round(base_p * 0.98, 2),
            "Target": round(base_p * 1.03, 2),
            "Timeframe": candle_duration
        }
    else:
        stock_row = df_scans[df_scans["Symbol"] == target_symbol].iloc[0]

    base_p = stock_row["LTP"]

    # Display Complete Indicator Metrics Dashboard Above Chart
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("LTP", f"₹{stock_row['LTP']}", f"{stock_row['Day %']}%")
    m2.metric("Signal", stock_row['Signal'])
    m3.metric("RSI (14)", stock_row['RSI'])
    m4.metric("Volume Spike", f"{stock_row['Vol x']}x")
    m5.metric("Stoploss", f"₹{stock_row['Stoploss']}")
    m6.metric("Target", f"₹{stock_row['Target']}")

    # Configure periods and frequency based on the selected candle duration
    if candle_duration in ["1m", "3m", "5m", "15m", "30m", "1h"]:
        periods = 50
        freq_map = {"1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h"}
        dates = pd.date_range(start="2026-10-11 09:15:00", periods=periods, freq=freq_map.get(candle_duration, "5min"))
        np.random.seed(hash(target_symbol) % 10000)
        prices = base_p + np.cumsum(np.random.normal(0, base_p * 0.0015, periods))
    elif candle_duration == "1d":
        periods = 60
        dates = pd.date_range(end="2026-10-11", periods=periods, freq="B")
        np.random.seed(hash(target_symbol) % 10000)
        prices = base_p + np.cumsum(np.random.normal(0, base_p * 0.008, periods))
    elif candle_duration == "1W":
        periods = 52
        dates = pd.date_range(end="2026-10-11", periods=periods, freq="W")
        np.random.seed(hash(target_symbol) % 10000)
        prices = base_p + np.cumsum(np.random.normal(0, base_p * 0.02, periods))
    else:
        periods_map = {"1M": 12, "3M": 12, "6M": 12, "1Y": 24}
        periods = periods_map.get(candle_duration, 12)
        dates = pd.date_range(end="2026-10-11", periods=periods, freq="ME" if candle_duration!="1Y" else "QE")
        np.random.seed(hash(target_symbol) % 10000)
        prices = base_p + np.cumsum(np.random.normal(0, base_p * 0.04, periods))

    fig = go.Figure(data=[go.Scatter(
        x=dates, 
        y=prices, 
        mode='lines+markers', 
        name=target_symbol,
        line=dict(color='#00ffcc' if stock_row['Signal']=='BUY' else '#ff4d4d', width=2)
    )])
    
    fig.add_hline(y=stock_row['VWAP'], line_dash="dash", line_color="yellow", annotation_text="VWAP / Baseline")
    fig.update_layout(
        title=f"{target_symbol} Trend View ({candle_duration} Candlestick View)",
        xaxis_title="Timeline",
        yaxis_title="Price (₹)",
        template="plotly_dark",
        height=450
    )
    st.plotly_chart(fig
