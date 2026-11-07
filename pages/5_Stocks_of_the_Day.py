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

# -------------------------------------------------------------------
# 1. SIDEBAR CONTROLS
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# 2. ROBUST DATA & INSTITUTIONAL SMC ENGINE
# -------------------------------------------------------------------
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
        
        # --- True Range & ATR ---
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

        # --- Institutional VWAP ---
        q = df['Volume']
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * q).cumsum() / q.cumsum()

        # --- Swing Highs & Lows ---
        window = 5
        df['Swing_High'] = df['High'][(df['High'] == df['High'].rolling(window*2+1, center=True).max())]
        df['Swing_Low'] = df['Low'][(df['Low'] == df['Low'].rolling(window*2+1, center=True).min())]

        # --- Market Structure & Trend ---
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

        # --- Fair Value Gaps (FVG) ---
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

        # --- Order Blocks ---
        df['OB_Type'] = "NONE"
        df['OB_Level'] = np.nan
        for i in range(5, len(df) - 1):
            if df['Close'].iloc[i] > df['High'].iloc[i-1] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
                df.loc[df.index[i], 'OB_Type'] = "BULLISH_OB"
                df.loc[df.index[i], 'OB_Level'] = df['Low'].iloc[i-1]
            elif df['Close'].iloc[i] < df['Low'].iloc[i-1] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
                df.loc[df.index[i], 'OB_Type'] = "BEARISH_OB"
                df.loc[df.index[i], 'OB_Level'] = df['High'].iloc[i-1]

        # --- Execution Signals ---
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
    st.error(f"Could not retrieve enough data for `{symbol_str}` on interval `{timeframe}`. Please check the ticker symbol or try a different timeframe.")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((float(latest['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100

    # -------------------------------------------------------------------
    # 3. EXECUTIVE METRICS BAR
    # -------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Traded Price", f"₹{float(latest['Close']):.2f}", f"{price_change:+.2f}%")
    
    bias_text = "🟢 BULLISH INSTITUTIONAL ACCUMULATION" if float(latest['Close']) > float(latest['EMA_50']) else "🔴 BEARISH DISTRIBUTION / MARKDOWN"
    c2.metric("Market Bias & Flow", bias_text)
    c3.metric("ATR Volatility", f"₹{float(latest['ATR']):.2f}")
    c4.metric("Smart Money Phase", "Markup / Expansion" if float(latest['Close']) > float(latest['EMA_50']) else "Markdown / Trap")

    # -------------------------------------------------------------------
    # 4. MULTI-PANE INSTITUTIONAL PLOTLY CHART
    # -------------------------------------------------------------------
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
        obs = df[df['OB_Type'] != 'NONE'].tail(30)
        for idx, row in obs.iterrows():
            color = "#00E676" if row['OB_Type'] == 'BULLISH_OB' else "#FF1744"
            fig.add_shape(type="line", x0=idx, y0=row['OB_Level'], x1=df.index[-1], y1=row['OB_Level'],
                          line=dict(color=color, width=1.5, dash="dash"), row=1, col=1)

    if show_liquidity:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Swing_High'], mode='markers', name='Sell-Side Liquidity',
            marker=dict(symbol='circle-open', size=8, color='#FFD700')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Swing_Low'], mode='markers', name='Buy-Side Liquidity',
            marker=dict(symbol='circle-open', size=8, color='#00FFFF')
        ), row=1, col=1)

    if show_signals:
        buy_pts = df[df['Signal'] == 'BUY']
        sell_pts = df[df['Signal'] == 'SELL']

        if not buy_pts.empty:
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['Low'] * 0.992, mode='text+markers',
                text=['BOS BUY'] * len(buy_pts), textposition='bottom center',
                textfont=dict(color='#00E676', size=10, family='Arial Black'),
                marker=dict(symbol='triangle-up', size=14, color='#00E676'), name='Institutional Buy'
            ), row=1, col=1)

        if not sell_pts.empty:
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['High'] * 1.008, mode='text+markers',
                text=['BOS SELL'] * len(sell_pts), textposition='top center',
                textfont=dict(color='#FF1744', size=10, family='Arial Black'),
                marker=dict(symbol='triangle-down', size=14, color='#FF1744'), name='Institutional Sell'
            ), row=1, col=1)

    vol_colors = ["#00E676" if row['Close'] >= row['Open'] else "#FF1744" for _, row in df.iterrows()]
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], marker_color=vol_colors, name="Session Volume"
    ), row=2, col=1)

    fig.update_layout(
        title=f"{symbol_str} Institutional Order Flow & Liquidity Suite",
        template="plotly_dark",
        dragmode='pan',
        xaxis_rangeslider_visible=False,
        height=820,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    chart_config = {
        'scrollZoom': True,
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'responsive': True
    }

    st.plotly_chart(fig, use_container_width=True, config=chart_config)

    # -------------------------------------------------------------------
    # 5. PROFESSIONAL RISK-MANAGEMENT MATRIX
    # -------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Institutional Risk & Position Sizing Matrix")
    
    filtered_signals = df[df['Signal'] != 'HOLD']
    last_signal_row = filtered_signals.iloc[-1] if not filtered_signals.empty else latest
    action_type = last_signal_row['Signal']
    stop_loss_val = last_signal_row.get('Stop_Loss', float(latest['Close']) * 0.98)
    target_val = last_signal_row.get('Target', float(latest['Close']) * 1.04)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Dominant Setup", action_type)
    col_b.metric("Stop-Loss Anchor (₹)", f"₹{float(stop_loss_val):.2f}")
    col_c.metric("Profit Objective (₹)", f"₹{float(target_val):.2f}")
    
    risk_per_share = abs(float(latest['Close']) - float(stop_loss_val))
    reward_per_share = abs(float(target_val) - float(latest['Close']))
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0
    col_d.metric("Risk-Reward Ratio", f"1 : {rr_ratio:.2f}")

    st.markdown(
        "### 🧠 Expert Strategist Notes:\n"
        f"- **Institutional VWAP Interaction:** Price is currently trading {'above' if float(latest['Close']) > float(latest['VWAP']) else 'below'} the institutional VWAP benchmark.\n"
        "- **Liquidity Pools (Yellow/Cyan Circles):** Stop-hunt targets where algorithmic trading desks absorb retail liquidity.\n"
        "- **Fair Value Gaps (Colored Blocks):** Imbalance zones where unmitigated institutional orders reside."
    )
