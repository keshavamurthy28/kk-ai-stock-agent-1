import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional SMC & ICT Execution Terminal",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Institutional Smart Money Concepts (SMC) & ICT Master Terminal")
st.markdown(
    "Advanced multi-timeframe execution suite featuring **Structure Breaks (BOS/CHoCH)**, "
    "**Liquidity Pools (Stop Hunts)**, **Fair Value Gaps (FVG)**, **VWAP Order Flow**, and **Automated Risk Management**."
)

st.sidebar.header("🛠️ Terminal Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., RELIANCE, TCS, HDFCBANK)", value="RELIANCE"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe / Resolution", ["5m", "15m", "30m", "1h", "1d"], index=4
)
fetch_period = "60d" if timeframe in ["5m", "15m", "30m", "1h"] else "max"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Institutional Overlays & Layers")
show_fvg = st.sidebar.checkbox("Show Fair Value Gaps (FVG)", value=True)
show_ob = st.sidebar.checkbox("Show Order Blocks (Support/Resistance)", value=True)
show_liquidity = st.sidebar.checkbox("Show Liquidity Pools (Equal Highs/Lows)", value=True)
show_vwap = st.sidebar.checkbox("Show Institutional VWAP", value=True)
show_signals = st.sidebar.checkbox("Show BOS / CHoCH & Entry Triggers", value=True)

@st.cache_data(ttl=300)
def fetch_and_calculate_institutional_smc(ticker, period, interval):
    try:
        df = yf.download(
            ticker, period=period, interval=interval, progress=False, auto_adjust=True
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty or len(df) < 20:
            return pd.DataFrame()

        df = df.dropna(subset=["Close", "Volume", "High", "Low"])
        
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

        q = df['Volume']
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * q).cumsum() / q.cumsum()

        window = 5
        df['Swing_High'] = df['High'][(df['High'] == df['High'].rolling(window*2+1, center=True).max())]
        df['Swing_Low'] = df['Low'][(df['Low'] == df['Low'].rolling(window*2+1, center=True).min())]

        df['Structure'] = "NEUTRAL"
        df['Signal'] = "HOLD"
        df['Stop_Loss'] = np.nan
        df['Target'] = np.nan

        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

        for i in range(20, len(df)):
            if df['Close'].iloc[i] > df['EMA_50'].iloc[i] and df['EMA_50'].iloc[i] > df['EMA_200'].iloc[i]:
                df.loc[df.index[i], 'Structure'] = "BULLISH_BOS"
            elif df['Close'].iloc[i] < df['EMA_50'].iloc[i] and df['EMA_50'].iloc[i] < df['EMA_200'].iloc[i]:
                df.loc[df.index[i], 'Structure'] = "BEARISH_BOS"

        df['FVG_Type'] = "NONE"
        df['FVG_Top'] = np.nan
        df['FVG_Bottom'] = np.nan

        for i in range(2, len(df)):
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                df.loc[df.index[i], 'FVG_Type'] = "BULLISH_FVG"
                df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i-2]
                df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i]
            elif df['High'].iloc[i] < df['Low'].iloc[i-2]:
                df.loc[df.index[i], 'FVG_Type'] = "BEARISH_FVG"
                df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i-2]
                df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i]

        df['OB_Type'] = "NONE"
        df['OB_Level'] = np.nan
        for i in range(5, len(df) - 1):
            if df['Close'].iloc[i] > df['High'].iloc[i-1] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
                df.loc[df.index[i], 'OB_Type'] = "BULLISH_OB"
                df.loc[df.index[i], 'OB_Level'] = df['Low'].iloc[i-1]
            elif df['Close'].iloc[i] < df['Low'].iloc[i-1] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
                df.loc[df.index[i], 'OB_Type'] = "BEARISH_OB"
                df.loc[df.index[i], 'OB_Level'] = df['High'].iloc[i-1]

        for i in range(1, len(df)):
            if df['Structure'].iloc[i] == "BULLISH_BOS" and df['Structure'].iloc[i-1] != "BULLISH_BOS":
                df.loc[df.index[i], 'Signal'] = "BUY"
                df.loc[df.index[i], 'Stop_Loss'] = df['Low'].iloc[i] - (1.5 * df['ATR'].iloc[i])
                df.loc[df.index[i], 'Target'] = df['Close'].iloc[i] + (3.0 * df['ATR'].iloc[i])
            elif df['Structure'].iloc[i] == "BEARISH_BOS" and df['Structure'].iloc[i-1] != "BEARISH_BOS":
                df.loc[df.index[i], 'Signal'] = "SELL"
                df.loc[df.index[i], 'Stop_Loss'] = df['High'].iloc[i] + (1.5 * df['ATR'].iloc[i])
                df.loc[df.index[i], 'Target'] = df['Close'].iloc[i] - (3.0 * df['ATR'].iloc[i])

        return df
    except Exception as e:
        return pd.DataFrame()

df = fetch_and_calculate_institutional_smc(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 15:
    st.error(f"Could not retrieve enough data for `{symbol_str}` on interval `{timeframe}`.")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((float(latest['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100

    filtered_signals = df[df['Signal'] != 'HOLD']
    last_signal_row = filtered_signals.iloc[-1] if not filtered_signals.empty else latest
    action_type = last_signal_row['Signal']
    stop_loss_val = last_signal_row.get('Stop_Loss', float(latest['Close']) * 0.98)
    target_val = last_signal_row.get('Target', float(latest['Close']) * 1.04)

    support_level = round(float(df['Low'].tail(20).min()), 2)
    resistance_level = round(float(df['High'].tail(20).max()), 2)

    valid_fvg = df[df['FVG_Type'] != 'NONE']
    if not valid_fvg.empty:
        last_fvg = valid_fvg.iloc[-1]
        fvg_range_str = f"₹{last_fvg['FVG_Bottom']:.2f} - ₹{last_fvg['FVG_Top']:.2f}"
    else:
        fvg_range_str = "None Active"

    st.markdown("### 📊 Live Executive Pricing & Institutional Setup")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Last Traded Price", f"₹{float(latest['Close']):.2f}", f"{price_change:+.2f}%")
    col2.metric("Action Setup", action_type)
    col3.metric("Stop-Loss Anchor", f"₹{float(stop_loss_val):.2f}")
    col4.metric("Profit Objective", f"₹{float(target_val):.2f}")
    col5.metric("ATR Volatility", f"₹{float(latest['ATR']):.2f}")

    sup_col1, sup_col2, sup_col3, sup_col4 = st.columns(4)
    sup_col1.metric("Support Level", f"₹{support_level:,.2f}")
    sup_col2.metric("Resistance Level", f"₹{resistance_level:,.2f}")
    sup_col3.metric("Active FVG Range", fvg_range_str)
    
    bias_text = "🟢 BULLISH ACCUMULATION" if float(latest['Close']) > float(latest['EMA_50']) else "🔴 BEARISH DISTRIBUTION"
    sup_col4.metric("Market Bias Flow", bias_text)

    st.markdown("---")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, 
        vertical_spacing=0.03, row_heights=[0.8, 0.2]
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Institutional OHLC",
        increasing=dict(line=dict(color="#00E676", width=1.2), fillcolor="#00E676"),
        decreasing=dict(line=dict(color="#FF1744", width=1.2), fillcolor="#FF1744")
    ), row=1, col=1)

    if show_vwap:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['VWAP'], mode='lines', name='Institutional VWAP',
            line=dict(color='#2962FF', width=1.8)
        ), row=1, col=1)

    if show_fvg:
        for idx, row in df.tail(100).iterrows():
            if row['FVG_Type'] == 'BULLISH_FVG':
                fig.add_shape(type="rect", x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                              fillcolor="rgba(0, 230, 118, 0.12)", line=dict(width=0), layer="below", row=1, col=1)
            elif row['FVG_Type'] == 'BEARISH_FVG':
                fig.add_shape(type="rect", x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                              fillcolor="rgba(255, 23, 68, 0.12)", line=dict(width=0), layer="below", row=1, col=1)

    if show_ob:
        obs = df[df['OB_Type']
