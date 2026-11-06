import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="ICT & Smart Money Trading Terminal",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Pro ICT & Smart Money Concepts (FVG, Volume Profile & Retracements)")
st.markdown(
    "Interactive institutional terminal featuring **Fixed Range Volume Profile**, **Fair Value Gaps (FVG)**, **SuperTrend**, and **Order Blocks**."
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
st.sidebar.header("⚙️ ICT & Institutional Overlays")
show_candlestick = st.sidebar.checkbox("Show Candlesticks (OHLC)", value=True)
show_fvg = st.sidebar.checkbox("Show Fair Value Gaps (FVG)", value=True)
show_volume_profile = st.sidebar.checkbox("Show Fixed Range Volume Profile", value=True)
show_supertrend = st.sidebar.checkbox("Show SuperTrend Line", value=True)
show_signals = st.sidebar.checkbox("Show Buy / Sell Signal Markers", value=True)

# -------------------------------------------------------------------
# 2. DATA FETCHER & ICT INDICATOR ENGINE
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_and_calculate_ict(ticker, period, interval):
    df = yf.download(
        ticker, period=period, interval=interval, progress=False, auto_adjust=True
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty or len(df) < 15:
        return df

    # --- SuperTrend Calculation ---
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

    # --- Fair Value Gap (FVG) Detection ---
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

    # --- Actionable Signals ---
    df['Signal'] = "HOLD"
    for i in range(1, len(df)):
        if df['Trend'].iloc[i] == 1 and df['Trend'].iloc[i-1] == -1:
            df.loc[df.index[i], 'Signal'] = "BUY"
        elif df['Trend'].iloc[i] == -1 and df['Trend'].iloc[i-1] == 1:
            df.loc[df.index[i], 'Signal'] = "SELL"

    return df

with st.spinner(f"Computing ICT Fair Value Gaps and Volume Profile for `{symbol_str}`..."):
    df = fetch_and_calculate_ict(symbol_str, fetch_period, timeframe)

if df.empty or len(df) < 10:
    st.error(f"Could not retrieve enough data for `{symbol_str}` on interval `{timeframe}`.")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price_change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

    # -------------------------------------------------------------------
    # 3. METRICS BAR
    # -------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Traded Price", f"₹{latest['Close']:.2f}", f"{price_change:+.2f}%")
    c2.metric("Market Structure", "BULLISH (UP)" if latest['Trend'] == 1 else "BEARISH (DOWN)")
    c3.metric("Active ATR", f"₹{latest['ATR']:.2f}")
    c4.metric("ICT Bias", "🟢 Premium Accumulation" if latest['Trend'] == 1 else "🔴 Discount Distribution")

    # -------------------------------------------------------------------
    # 4. CHART GENERATION (SAFE SUBPLOT LAYOUT)
    # -------------------------------------------------------------------
    fig = go.Figure()

    # Candlestick Pane
    if show_candlestick:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="OHLC Candles"
        ))

    # SuperTrend Line
    if show_supertrend:
        bullish_st = df.copy()
        bullish_st.loc[bullish_st['Trend'] == -1, 'SuperTrend'] = np.nan
        bearish_st = df.copy()
        bearish_st.loc[bearish_st['Trend'] == 1, 'SuperTrend'] = np.nan

        fig.add_trace(go.Scatter(
            x=bullish_st.index, y=bullish_st['SuperTrend'], mode='lines', name='SuperTrend Support',
            line=dict(color='#00E676', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=bearish_st.index, y=bearish_st['SuperTrend'], mode='lines', name='SuperTrend Resistance',
            line=dict(color='#FF1744', width=2)
        ))

    # Fair Value Gaps (FVG) Shaded Boxes
    if show_fvg:
        for idx, row in df.iterrows():
            if row['FVG_Type'] == 'BULLISH_FVG':
                fig.add_shape(
                    type="rect",
                    x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                    fillcolor="rgba(0, 230, 118, 0.2)", line=dict(width=0),
                    layer="below"
                )
            elif row['FVG_Type'] == 'BEARISH_FVG':
                fig.add_shape(
                    type="rect",
                    x0=idx, y0=row['FVG_Bottom'], x1=df.index[-1], y1=row['FVG_Top'],
                    fillcolor="rgba(255, 23, 68, 0.2)", line=dict(width=0),
                    layer="below"
                )

    # Volume Profile Nodes
    if show_volume_profile and not df.empty:
        price_min, price_max = df['Low'].min(), df['High'].max()
        bins = 15
        price_bins = np.linspace(price_min, price_max, bins)
        volume_bins = np.zeros(bins - 1)
        
        for _, row in df.iterrows():
            p = row['Close']
            v = row['Volume']
            for b in range(len(price_bins) - 1):
                if price_bins[b] <= p < price_bins[b+1]:
                    volume_bins[b] += v
                    break

        max_vol = volume_bins.max() if volume_bins.max() > 0 else 1
        scaled_vol = (volume_bins / max_vol) * (df.index[-1] - df.index[0]) * 0.15 # Safe scaling

        bin_centers = (price_bins[:-1] + price_bins[1:]) / 2
        
        # Add volume nodes as horizontal lines / bars
        for center, vol in zip(bin_centers, volume_bins):
            if vol > 0:
                fig.add_shape(
                    type="rect",
                    x0=df.index[0], y0=center - (price_max-price_min)/(bins*2),
                    x1=df.index[0] + pd.Timedelta(days=int(len(df)*0.08)), y1=center + (price_max-price_min)/(bins*2),
                    fillcolor="rgba(41, 182, 246, 0.5)", line=dict(width=0),
                    layer="below"
                )

    # Buy/Sell Signal Markers
    if show_signals:
        buy_pts = df[df['Signal'] == 'BUY']
        sell_pts = df[df['Signal'] == 'SELL']

        if not buy_pts.empty:
            fig.add_trace(go.Scatter(
                x=buy_pts.index, y=buy_pts['Low'] * 0.992,
                mode='text+markers', text=['Buy long'] * len(buy_pts),
                textposition='bottom center', textfont=dict(color='#00E676', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-up', size=14, color='#00E676'), name='Buy Signal'
            ))
        if not sell_pts.empty:
            fig.add_trace(go.Scatter(
                x=sell_pts.index, y=sell_pts['High'] * 1.008,
                mode='text+markers', text=['Sell short'] * len(sell_pts),
                textposition='top center', textfont=dict(color='#FF1744', size=11, family='Arial Black'),
                marker=dict(symbol='triangle-down', size=14, color='#FF1744'), name='Sell Signal'
            ))

    # TradingView Navigation Layout (Hand Pan + Scroll Zoom)
    fig.update_layout(
        title=f"{symbol_str} Price Action, Fair Value Gaps (FVG) & Volume Profile",
        template="plotly_dark",
        dragmode='pan',
        xaxis_rangeslider_visible=False,
        height=750,
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
    # 5. ICT STRATEGY EXPLANATION GUIDE
    # -------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🎓 ICT & Smart Money Concept Guide")
    st.markdown(
        "- **Fair Value Gaps (FVG - Shaded Boxes):** Green and red rectangular zones highlight price imbalances where institutional order flow left unfilled liquidity.\n"
        "- **Volume Profile Nodes:** Blue density bars on the left highlight high-volume transaction nodes.\n"
        "- **Hand Icon Pan & Zoom:** Use your mouse wheel to zoom in/out and click + drag to move across the chart effortlessly."
    )
