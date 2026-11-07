import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced SMC & ICT Execution Terminal",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Pro Smart Money Concepts (SMC) & ICT Execution Terminal")
st.markdown(
    "Advanced institutional charting featuring **Structure Breaks (CHoCH/BOS)**, **Fair Value Gaps (FVG)**, "
    "**Dynamic Support/Resistance Order Blocks**, and **Automated Risk-Managed Stop-Loss & Target levels**."
)

# -------------------------------------------------------------------
# 1. SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("🛠️ Terminal Controls")
stock_input = st.sidebar.text_input(
    "Stock Ticker (e.g., HDFCBANK, INFY, RELIANCE)", value="HDFCBANK"
).upper()
symbol_str = (
    f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["5m", "15m", "30m", "1h", "1d"], index=4
)
fetch_period = "60d" if timeframe in ["5m", "15m", "30m", "1h"] else "max"

st.sidebar.markdown("---")
st.sidebar.header("⚙️ SMC & ICT Overlays")
show_fvg = st.sidebar.checkbox("Show Fair Value Gaps (FVG)", value=True)
show_ob = st.sidebar.checkbox("Show Order Blocks (Support/Resistance)", value=True)
show_signals = st.sidebar.checkbox("Show Buy / Sell Entry & Stop-Loss Signals", value=True)
show_supertrend = st.sidebar.checkbox("Show SuperTrend Trend Line", value=True)

# -------------------------------------------------------------------
# 2. SMC & ICT CALCULATION ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_and_calculate_smc(ticker, period, interval):
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty or len(df) < 20:
        return df

    # --- ATR & SuperTrend for Stop-Loss Calculations ---
    period_atr = 10
    mult = 3.0
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period_atr).mean()

    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_Upper'] = hl2 + (mult * df['ATR'])
    df['Basic_Lower'] = hl2 - (mult * df['ATR'])

    upper_list = [0.0] * len(df)
    lower_list = [0.0] * len(df)
    st_list = [0.0] * len(df)
    trend_list = [1] * len(df)

    close = df['Close'].values
    basic_upper = df['Basic_Upper'].values
    basic_lower = df['Basic_Lower'].values

    for i in range(1, len(df)):
        if basic_upper[i] < upper_list[i-1] or close[i-1] > upper_list[i-1]:
            upper_list[i] = basic_upper[i]
        else:
            upper_list[i] = upper_list[i-1]

        if basic_lower[i] > lower_list[i-1] or close[i-1] < lower_list[i-1]:
            lower_list[i] = basic_lower[i]
        else:
            lower_list[i] = lower_list[i-1]

        if trend_list[i-1] == 1:
            if close[i] <= lower_list[i]:
                trend_list[i] = -1
                st_list[i] = upper_list[i]
            else:
                trend_list[i] = 1
                st_list[i] = lower_list[i]
        else:
            if close[i] >= upper_list[i]:
                trend_list[i] = 1
                st_list[i] = lower_list[i]
            else:
                trend_list[i] = -1
                st_list[i] = upper_list[i]

    df['SuperTrend'] = st_list
    df['Trend'] = trend_list

    # --- Fair Value Gaps (FVG) ---
    df['FVG_Type'] = "NONE"
    df['FVG_Top'] = np.nan
    df['FVG_Bottom'] = np.nan

    for i in range(2, len(df)):
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:  # Bullish Imbalance
            df.loc[df.index[i], 'FVG_Type'] = "BULLISH_FVG"
            df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i-2]
            df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i]
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:  # Bearish Imbalance
            df.loc[df.index[i], 'FVG_Type'] = "BEARISH_FVG"
            df.loc[df.index[i], 'FVG_Top'] = df['Low'].iloc[i-2]
            df.loc[df.index[i], 'FVG_Bottom'] = df['High'].iloc[i]

    # --- Order Blocks (Support / Resistance Zones) ---
    df['OB_Type'] = "NONE"
    df['OB_Level'] = np.nan
    for i in range(5, len(df) - 1):
        # Bullish Order Block (Last down candle before strong up move)
        if df['Close'].iloc[i] > df['High'].iloc[i-1] and df['Close'].iloc[i-1] < df['Open'].iloc[i-1]:
            df.loc[df.index[i], 'OB_Type'] = "BULLISH_OB"
            df.loc[df.index[i], 'OB_Level'] = df['Low'].iloc[i-1]
        # Bearish Order Block (Last up candle before strong down move)
        elif df['Close'].iloc[i] < df['Low'].iloc[i-1] and df['Close'].iloc[i-1] > df['Open'].iloc[i-1]:
            df.loc[df.index[i], 'OB_Type'] = "BEARISH_OB"
            df.loc[df.index[i], 'OB_Level'] = df['High'].iloc[i-1]

    # --- Execution Signals with Stop-Loss & Target ---
    df['Signal'] = "HOLD"
    df['Stop_Loss'] = np.nan
    df['Target'] = np.nan

    for i in range(1, len(df)):
        if df['Trend'].iloc[i] == 1 and df['Trend'].iloc[i-1] == -1:
            df.loc[df.index[i], 'Signal'] = "BUY"
            df.loc[df.index[i], 'Stop_Loss'] = df['Low'].iloc[i] - (1.5 * df['ATR'].iloc[i])
            df.loc[df.index[i], 'Target'] = df['Close'].iloc[i] + (3.0 * df['ATR'].iloc[i])
        elif df['Trend'].iloc[i] == -1 and df['Trend'].iloc[i-1] == 1:
            df.loc[df.index[i], 'Signal'] = "SELL"
            df.loc[df.index[i], 'Stop_Loss'] = df['High'].iloc[i] + (1.5 * df['ATR'].iloc[i])
            df.loc[df.index[i], 'Target'] = df['Close'].iloc[i] - (3.0 * df['ATR'].iloc[i])

    return df

with st.spinner(f"Computing SMC Order Blocks, FVG & Risk Levels for `{symbol_str}`..."):
    df = fetch_and_calculate_smc(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 10:
    st.error(f"Could not retrieve enough data for `{symbol_str}` on interval `{timeframe}`.")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

    # -------------------------------------------------------------------
    # 3. EXECUTIVE METRICS BAR
    # -------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Traded Price", f"₹{latest['Close']:.2f}", f"{price_change:+.2f}%")
    c2.metric("Market Bias", "🟢 BULLISH (BUY ZONE)" if latest['Trend'] == 1 else "🔴 BEARISH (SELL ZONE)")
    c3.metric("ATR Volatility", f"₹{latest['ATR']:.2f}")
    c4.metric("Smart Money Status", "Accumulation Phase" if latest['Trend'] == 1 else "Distribution Phase")

    # -------------------------------------------------------------------
    # 4. TRADINGVIEW-STYLE CLEAN EXECUTION CHART
    # -------------------------------------------------------------------
    fig = go.Figure()

    # Clean Candlesticks (Strict Green/Red institutional coloring)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Price Action",
        increasing=dict(line=dict(color="#00E676", width=1.2), fillcolor="#00E676"),
        decreasing=dict(line=dict(color="#FF1744", width=1.2), fillcolor="#FF1744")
    ))

    # SuperTrend Line
    if show_supertrend:
        bullish_st = df.copy()
        bullish_st.loc[bullish_st['Trend'] == -1, 'SuperTrend'] = np.nan
        bearish_st = df.copy()
        bearish_st.loc[bearish_st['Trend'] == 1, 'SuperTrend'] = np.nan

        fig.add_trace(go.Scatter(
            x=bullish_st.index, y=bullish_st['SuperTrend'], mode='lines', name='SuperTrend Support',
            line=dict(color='#00E676', width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=bearish_st.index, y=bearish_st['SuperTrend'], mode='lines', name='SuperTrend Resistance',
            line=dict(color='#FF1744', width=2.5)
        ))

    # Fair Value Gaps (FVG) Shaded Zones
    if show_fvg:
        for idx, row in df.iterrows():
            if row['FVG_Type'] == 'BULLISH_FVG':
                fig.add_shape(
                    type="rect", x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                    fillcolor="rgba(0, 230, 118, 0.12)", line=dict(width=0), layer="below"
                )
            elif row['FVG_Type'] == 'BEARISH_FVG':
                fig.add_shape(
                    type="rect", x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                    fillcolor="rgba(255, 23, 68, 0.12)", line=dict(width=0), layer="below"
                )

    # Order Blocks (Support & Resistance Levels)
    if show_ob:
        obs = df[df['OB_Type'] != 'NONE']
        for idx, row in obs.iterrows():
            color = "#00E676" if row['OB_Type'] == 'BULLISH_OB' else "#FF1744"
            fig.add_shape(
                type="line", x0=idx, y0=row['OB_Level'], x1=df.index[-1], y1=row['OB_Level'],
                line=dict(color=color, width=1.5, dash="dash"),
            )

    # Buy / Sell Execution Signals with Stop-Loss & Target markers
    if show_signals:
        buy_pts = df[df['Signal'] == 'BUY']
        sell_pts = df[df['Signal'] == 'SELL']

        if not buy_pts.empty:
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['Low'] * 0.992,
                mode='text+markers', text=['BUY LONG'] * len(buy_pts),
                textposition='bottom center', textfont=dict(color='#00E676', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-up', size=15, color='#00E676'), name='Buy Trigger'
            ))

        if not sell_pts.empty:
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['High'] * 1.008,
                mode='text+markers', text=['SELL SHORT'] * len(sell_pts),
                textposition='top center', textfont=dict(color='#FF1744', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-down', size=15, color='#FF1744'), name='Sell Trigger'
            ))

    # Layout Configuration for TradingView Hand-Pan & Scroll-Zoom
    fig.update_layout(
        title=f"{symbol_str} Smart Money Execution Terminal (SMC, FVG & Risk Levels)",
        template="plotly_dark",
        dragmode='pan',
        xaxis_rangeslider_visible=False,
        height=780,
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
    # 5. ACTIONABLE TRADE SETUP SUMMARY
    # -------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Active Trade Setup & Risk Management Summary")
    
    last_signal_row = df[df['Signal'] != 'HOLD'].iloc[-1] if not df[df['Signal'] == 'HOLD'].empty else latest
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Latest Action Signal", last_signal_row['Signal'])
    col_b.metric("Recommended Stop-Loss (₹)", f"₹{last_signal_row.get('Stop_Loss', latest['Close'] * 0.98):.2f}")
    col_c.metric("Profit Target (₹)", f"₹{last_signal_row.get('Target', latest['Close'] * 1.04):.2f}")

    st.markdown(
        "- **Fair Value Gaps (Shaded Boxes):** Institutional imbalance zones where price tends to gravitate back to fill before continuation.\n"
        "- **Order Block Lines (Dashed Lines):** Key institutional support and resistance pivot levels.\n"
        "- **Hand Pan & Zoom:** Click and drag to move freely across the chart, and scroll to zoom in/out."
    )
