import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide")
st.title("📊 Advanced Smart Money Concepts (SMC) & Institutional FVG Terminal")

with st.expander("📘 Beginner Guide: Intervals, Indicators & Zoom Controls", expanded=False):
    st.markdown(
        "- **Candle Intervals:** Use short intervals (`1m`, `5m`, `15m`) for intraday timing and longer intervals (`1D`, `1W`, `1M`) for broader trend context.\n"
        "- **Select Extra Indicators:** Choose only the indicators you need (`VWAP`, `20/50/200 EMA`, `Bollinger Bands`, `RSI 14`) so your chart stays clear and adaptable.\n"
        "- **Zoom Intraday to Long-Term:** Pick **Full History / Long-Term** or **All Loaded Candles** to see the full loaded range, or scroll/drag directly on the chart. Always verify live prices on your broker and use a stop-loss. Not financial advice."
    )

INTERVAL_OPTIONS = [
    "1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"
]
INDICATOR_OPTIONS = [
    "VWAP",
    "20 EMA",
    "50 EMA",
    "200 EMA",
    "Bollinger Bands",
    "RSI (14)",
]

# Top Control Bar (Symbol, Candle Interval, Technical Indicators, SMC Layers)
c1, c2 = st.columns([1.2, 2.8])
raw_sym = c1.text_input("Enter NSE Stock Symbol", value="LICHSGFIN").strip().upper()
ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"

tf_choice = c2.selectbox(
    "Candle Interval (TradingView Style)",
    INTERVAL_OPTIONS,
    index=0,
)

ind_col, smc_col = st.columns([1.6, 1.6])
selected_indicators = ind_col.multiselect(
    "📈 Technical Indicators (Add / Remove Dynamically)",
    INDICATOR_OPTIONS,
    default=["VWAP", "20 EMA"],
)
show_layers = smc_col.multiselect(
    "🧱 Active SMC Layers",
    [
        "4H FVG",
        "Order Blocks",
        "BOS / CHoCH",
        "Liquidity (BSL/SSL)",
        "Discount/Premium 50%",
    ],
    default=["4H FVG", "Order Blocks", "BOS / CHoCH", "Liquidity (BSL/SSL)"],
)


@st.cache_data(ttl=15)
def fetch_clean_smc(sym, tf):
    p_map = {
        "1m": "5d",
        "2m": "5d",
        "3m": "5d",
        "5m": "10d",
        "10m": "10d",
        "15m": "15d",
        "30m": "30d",
        "1h": "60d",
        "4h": "60d",
        "1D": "2y",
        "1W": "5y",
        "1M": "5y",
    }
    i_map = {
        "1m": "1m",
        "2m": "1m",
        "3m": "1m",
        "5m": "5m",
        "10m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "1h",
        "1D": "1d",
        "1W": "1wk",
        "1M": "1mo",
    }

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

    if tf in ["2m", "3m", "10m", "4h"]:
        rule_map = {
            "2m": ("2min", "0min"),
            "3m": ("3min", "0min"),
            "10m": ("10min", "0min"),
            "4h": ("4h", "15min"),
        }
        rule, offset = rule_map[tf]
        df = (
            df.set_index("Time")
            .resample(rule, offset=offset)
            .agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            })
            .dropna(subset=["Open", "High", "Low", "Close"])
            .reset_index()
        )

    if df4 is not None and not df4.empty and {"Open", "High", "Low", "Close"}.issubset(set(df4.columns)):
        df4.index = pd.to_datetime(df4.index)
        if df4.index.tz is not None:
            df4.index = df4.index.tz_convert("Asia/Kolkata").tz_localize(None)
        df4 = (
            df4.resample("4h", offset="15min")
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
            .dropna()
        )

    return df, df4, df1


df, df_4h, df_1d = fetch_clean_smc(ticker, tf_choice)

if df.empty:
    st.error(f"No data returned for {ticker}. Please verify the NSE symbol.")
else:
    df = df.reset_index(drop=True)
    ltp = float(df["Close"].iloc[-1])
    is_intraday_tf = tf_choice in ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h"]

    if not is_intraday_tf:
        df["Axis_Str"] = df["Time"].dt.strftime("%d %b '%y")
    else:
        is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
        df["Axis_Str"] = np.where(
            is_new_day,
            df["Time"].dt.strftime("%d %b '%y  %H:%M"),
            df["Time"].dt.strftime("%H:%M  (%d %b)"),
        )

    # Calculate Optional Technical Indicators
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    if df["Volume"].sum() > 0:
        df["VWAP"] = (
            (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"])
            .groupby(df["Time"].dt.date)
            .cumsum()
            / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
        ).fillna(df["EMA20"])
    else:
        df["VWAP"] = df["EMA20"]

    bb_mid = df["Close"].rolling(20, min_periods=1).mean()
    bb_std = df["Close"].rolling(20, min_periods=1).std().fillna(0.0)
    df["BB_Upper"] = bb_mid + (2.0 * bb_std)
    df["BB_Lower"] = bb_mid - (2.0 * bb_std)

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    latest_vwap = float(df["VWAP"].iloc[-1])

    v_avg = df["Volume"].rolling(20, min_periods=1).mean()
    v_col = [
        (
            "#00E676"
            if (c >= o and v >= 1.5 * va)
            else (
                "#FF5252"
                if (c < o and v >= 1.5 * va)
                else ("rgba(0,230,118,0.38)" if c >= o else "rgba(255,82,82,0.38)")
            )
        )
        for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
    ]

    def map_time_to_str(ts):
        idx = int((df["Time"] - ts).abs().idxmin())
        return df["Axis_Str"].iloc[idx]

    # 1. Higher-Timeframe (4H) Bullish & Bearish Fair Value Gaps (FVG)
    bull_fvg, bear_fvg = None, None
    if df_4h is not None and len(df_4h) >= 3:
        for i in range(len(df_4h) - 1, 1, -1):
            if bull_fvg is None and (df_4h["Low"].iloc[i] - df_4h["High"].iloc[i - 2]) > 0.05:
                bull_fvg = (
                    df_4h.index[i - 2],
                    float(df_4h["High"].iloc[i - 2]),
                    float(df_4h["Low"].iloc[i]),
                )
            if bear_fvg is None and (df_4h["Low"].iloc[i - 2] - df_4h["High"].iloc[i]) > 0.05:
                bear_fvg = (
                    df_4h.index[i - 2],
                    float(df_4h["High"].iloc[i]),
                    float(df_4h["Low"].iloc[i - 2]),
                )
            if bull_fvg and bear_fvg:
                break

    # 2. Institutional Bullish Order Block
    bull_ob = None
    for i in range(len(df) - 2, 1, -1):
        is_red = df["Close"].iloc[i] < df["Open"].iloc[i]
        next_strong_green = (df["Close"].iloc[i + 1] > df["Open"].iloc[i + 1]) and (
            df["Volume"].iloc[i + 1] >= 1.4 * v_avg.iloc[i + 1]
        )
        if is_red and next_strong_green:
            bull_ob = (
                df["Axis_Str"].iloc[i],
                float(df["Low"].iloc[i]),
                float(df["High"].iloc[i]),
            )
            break

    # 3. Market Structure: Swing Highs -> BOS & CHoCH
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df)):
        if df["SH"].iloc[i - 4]:
            last_sh = (df["Axis_Str"].iloc[i - 4], float(df["High"].iloc[i - 4]))
        if (
            last_sh
            and float(df["Close"].iloc[i - 1]) <= last_sh[1]
            and float(df["Close"].iloc[i]) > last_sh[1]
        ):
            sigs.append({
                "t_str": df["Axis_Str"].iloc[i],
                "x0_str": last_sh[0],
                "y": round(last_sh[1], 2),
            })
            last_sh = None

    # 4. Liquidity Pools (BSL / SSL) & Equilibrium (50%)
    lookback = min(len(df), 80)
    bsl_level = round(float(df["High"].iloc[-lookback:].max()), 2)
    ssl_level = round(float(df["Low"].iloc[-lookback:].min()), 2)
    eq_level = round((bsl_level + ssl_level) / 2.0, 2)
    zone_tag = (
        "DISCOUNT ZONE (Good Value) 🟢"
        if ltp <= eq_level
        else "PREMIUM ZONE (Wait Pullback) 🟠"
    )

    # 5. Reference Execution Levels
    if bull_ob and bull_ob[1] <= ltp <= bull_ob[2] * 1.02:
        entry_p = round(bull_ob[2], 2)
    elif bull_fvg and bull_fvg[1] <= ltp <= bull_fvg[2] * 1.02:
        entry_p = round(bull_fvg[2], 2)
    elif sigs:
        entry_p = round(max(sigs[-1]["y"], latest_vwap), 2)
    else:
        entry_p = round(max(latest_vwap, ltp * 0.995), 2)

    raw_sl = (
        bull_ob[1] * 0.996
        if bull_ob
        else (bull_fvg[1] * 0.996 if bull_fvg else entry_p * 0.988)
    )
    sl_p = round(min(raw_sl, entry_p * 0.99), 2)
    risk = max(entry_p - sl_p, entry_p * 0.008)
    t1_p = round(entry_p + risk * 1.5, 2)
    t2_p = round(max(bsl_level, entry_p + risk * 2.5), 2)

    st.subheader(f"📊 Institutional SMC Execution Blueprint: {raw_sym} ({tf_choice})")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Last Price", f"₹{ltp:,.2f}", "Above VWAP ✅" if ltp >= latest_vwap else "Below VWAP ⚠️")
    m2.metric("🟡 Reference Buy", f"₹{entry_p:,.2f}", zone_tag)
    m3.metric("🛑 Stop-Loss", f"₹{sl_p:,.2f}", "Below Order Block / FVG")
    m4.metric("🎯 Target 1 (1.5R)", f"₹{t1_p:,.2f}", "Book Profit First")
    m5.metric("🚀 Target 2 (BSL / 2.5R)", f"₹{t2_p:,.2f}", "Stretch Target")

    # Quick Zoom Range Selector (Intraday -> Full Long-Term Range)
    z_col1, z_col2 = st.columns([2.6, 2.4])
    zoom_preset = z_col1.radio(
        "Timeline Zoom (Intraday to Full Loaded History)",
        [
            "Last 1 Day (Intraday)",
            "Last 5 Days",
            "Full History / Long-Term",
        ],
        index=0 if is_intraday_tf else 2,
        horizontal=True,
    )
    z_col2.caption(
        "💡 Scroll wheel or drag on the chart to zoom in/out across minutes, days, or full loaded history."
    )

    show_rsi = "RSI (14)" in selected_indicators
    n_rows = 3 if show_rsi else 2
    row_heights = [0.64, 0.18, 0.18] if show_rsi else [0.78, 0.22]
    vertical_spacing = 0.025 if show_rsi else 0.02

    end_str = df["Axis_Str"].iloc[-1]

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=vertical_spacing,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Axis_Str"],
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

    if "VWAP" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["VWAP"],
                mode="lines",
                name="VWAP",
                line=dict(color="#FFD700", width=1.5),
            ),
            row=1,
            col=1,
        )
    if "20 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA20"],
                mode="lines",
                name="20 EMA",
                line=dict(color="#29B6F6", width=1.2),
            ),
            row=1,
            col=1,
        )
    if "50 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA50"],
                mode="lines",
                name="50 EMA",
                line=dict(color="#FFA726", width=1.3),
            ),
            row=1,
            col=1,
        )
    if "200 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA200"],
                mode="lines",
                name="200 EMA",
                line=dict(color="#EC407A", width=1.4),
            ),
            row=1,
            col=1,
        )
    if "Bollinger Bands" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["BB_Upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="rgba(179, 157, 219, 0.7)", width=1.1, dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["BB_Lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="rgba(179, 157, 219, 0.7)", width=1.1, dash="dash"),
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(x=df["Axis_Str"], y=df["Volume"], name="Volume", marker_color=v_col),
        row=2,
        col=1,
    )

    if show_rsi:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["RSI14"],
                mode="lines",
                name="RSI (14)",
                line=dict(color="#CE93D8", width=1.4),
            ),
            row=3,
            col=1,
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#FF5252", line_width=1, row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00E676", line_width=1, row=3, col=1)

    if "4H FVG" in show_layers:
        if bull_fvg:
            xs_str = map_time_to_str(bull_fvg[0])
            fig.add_shape(
                type="rect",
                x0=xs_str,
                x1=end_str,
                y0=bull_fvg[1],
                y1=bull_fvg[2],
                fillcolor="rgba(0, 230, 118, 0.14)",
                line=dict(color="rgba(0, 230, 118, 0.4)", width=1),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=xs_str,
                y=bull_fvg[2],
                text=f"4H Demand FVG (₹{bull_fvg[1]:,.1f}–₹{bull_fvg[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=10,
                font=dict(size=10, color="#00E676"),
                row=1,
                col=1,
            )
        if bear_fvg:
            xs_b_str = map_time_to_str(bear_fvg[0])
            fig.add_shape(
                type="rect",
                x0=xs_b_str,
                x1=end_str,
                y0=bear_fvg[1],
                y1=bear_fvg[2],
                fillcolor="rgba(255, 82, 82, 0.12)",
                line=dict(color="rgba(255, 82, 82, 0.4)", width=1),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=xs_b_str,
                y=bear_fvg[1],
                text=f"4H Supply FVG (₹{bear_fvg[1]:,.1f}–₹{bear_fvg[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=-12,
                font=dict(size=10, color="#FF5252"),
                row=1,
                col=1,
            )

    if "Order Blocks" in show_layers and bull_ob:
        fig.add_shape(
            type="rect",
            x0=bull_ob[0],
            x1=end_str,
            y0=bull_ob[1],
            y1=bull_ob[2],
            fillcolor="rgba(41, 182, 246, 0.16)",
            line=dict(color="#29B6F6", width=1, dash="dot"),
            layer="below",
            row=1,
            col=1,
        )
        fig.add_annotation(
            x=bull_ob[0],
            y=bull_ob[1],
            text=f"🏦 Bullish OB (₹{bull_ob[1]:,.1f}–₹{bull_ob[2]:,.1f})",
            showarrow=False,
            xanchor="left",
            yshift=-12,
            font=dict(size=10, color="#29B6F6"),
            row=1,
            col=1,
        )

    if "BOS / CHoCH" in show_layers:
        for idx_s, s in enumerate(sigs[-3:]):
            is_latest = idx_s == len(sigs[-3:]) - 1
            fig.add_shape(
                type="line",
                x0=s["x0_str"],
                x1=s["t_str"],
                y0=s["y"],
                y1=s["y"],
                line=dict(color="#00E676", width=1.4, dash="dot"),
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=s["t_str"],
                y=s["y"],
                text=f"CHoCH ▲ @ ₹{s['y']}" if is_latest else f"BOS ▲ @ ₹{s['y']}",
                showarrow=False,
                yshift=12,
                font=dict(size=10, color="#00E676"),
                row=1,
                col=1,
            )

    if "Liquidity (BSL/SSL)" in show_layers:
        fig.add_hline(
            y=bsl_level,
            line_dash="dot",
            line_color="#AB47BC",
            line_width=1.2,
            annotation_text=f"💧 BSL: ₹{bsl_level:,.2f}",
            annotation_position="top left",
            annotation_font_color="#CE93D8",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=ssl_level,
            line_dash="dot",
            line_color="#FF7043",
            line_width=1.2,
            annotation_text=f"💧 SSL: ₹{ssl_level:,.2f}",
            annotation_position="bottom left",
            annotation_font_color="#FFAB91",
            row=1,
            col=1,
        )

    if "Discount/Premium 50%" in show_layers:
        fig.add_hline(
            y=eq_level,
            line_dash="dashdot",
            line_color="#9E9E9E",
            line_width=1.0,
            annotation_text=f"⚖️ 50% EQ: ₹{eq_level:,.2f}",
            annotation_position="top right",
            annotation_font_color="#BDBDBD",
            row=1,
            col=1,
        )

    fig.add_hline(
        y=entry_p,
        line_dash="solid",
        line_color="#FFD700",
        line_width=1.6,
        annotation_text=f"🟡 BUY: ₹{entry_p:,.2f}",
        annotation_position="bottom left",
        annotation_font_color="#FFD700",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=sl_p,
        line_dash="solid",
        line_color="#FF5252",
        line_width=1.6,
        annotation_text=f"🛑 SL: ₹{sl_p:,.2f}",
        annotation_position="bottom right",
        annotation_font_color="#FF5252",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t1_p,
        line_dash="dash",
        line_color="#29B6F6",
        line_width=1.4,
        annotation_text=f"🎯 T1: ₹{t1_p:,.2f}",
        annotation_position="top left",
        annotation_font_color="#29B6F6",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=t2_p,
        line_dash="dash",
        line_color="#00E676",
        line_width=1.4,
        annotation_text=f"🚀 T2: ₹{t2_p:,.2f}",
        annotation_position="top right",
        annotation_font_color="#00E676",
        row=1,
        col=1,
    )

    if zoom_preset == "Last 1 Day (Intraday)" and is_intraday_tf:
        last_date = df["Time"].dt.date.iloc[-1]
        start_idx = max(0, int(df[df["Time"].dt.date == last_date].index[0]) - 5)
    elif zoom_preset == "Last 5 Days" and is_intraday_tf:
        unique_dates = sorted(df["Time"].dt.date.unique())
        target_d = unique_dates[-5] if len(unique_dates) >= 5 else unique_dates[0]
        start_idx = max(0, int(df[df["Time"].dt.date >= target_d].index[0]))
    else:
        start_idx = 0

    active_ind_text = ", ".join(selected_indicators) if selected_indicators else "None"

    fig.update_layout(
        title=f"{raw_sym} ({tf_choice}) | Price: ₹{ltp:,.2f} | Indicators: {active_ind_text}",
        template="plotly_dark",
        height=740 if show_rsi else 680,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=45, b=40),
        yaxis=dict(
            side="right",
            title="Price (₹)",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikecolor="#78909C",
            spikethickness=1,
            spikedash="dash",
        ),
        yaxis2=dict(side="right", title="Volume", showgrid=False),
    )

    if show_rsi:
        fig.update_yaxes(side="right", title="RSI", range=[0, 100], row=3, col=1)

    bottom_axis_row = n_rows
    for r_idx in range(1, n_rows + 1):
        axis_kwargs = dict(
            type="category",
            rangeslider_visible=False,
            range=[start_idx, len(df) + 3],
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikecolor="#78909C",
            spikethickness=1,
            spikedash="dash",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
        )
        if r_idx == bottom_axis_row:
            axis_kwargs.update(
                tickmode="auto",
                nticks=15,
                tickangle=0,
                tickfont=dict(size=11, color="#B0BEC5"),
            )
        fig.update_xaxes(axis_kwargs, row=r_idx, col=1)

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
