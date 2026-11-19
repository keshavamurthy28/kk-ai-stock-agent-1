import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Smart Money Flow & Pulse Terminal", layout="wide"
)

st.title("⚡ Institutional Smart Money Flow & Pulse Terminal")
st.caption(
    "Volume-Weighted Money Flow Estimates, Carry-Forward Watchlist Radar & Interactive 15m Charting."
)

if st.button("🔄 Refresh Smart Money Flows", type="primary"):
    st.cache_data.clear()
    st.rerun()

with st.expander("📘 Beginner Guide: How to Read This Page Safely", expanded=False):
    st.markdown(
        "- **Est. Flow (Cr):** An **estimate** based on price direction and unusual volume—not an official exchange institutional report.\n"
        "- **RVOL (Relative Volume):** Around **1.0x** is average activity; **1.5x+** shows stronger-than-usual participation.\n"
        "- **Close Strength %:** Near **100%** means price closed near the day's high; near **0%** means near the day's low.\n"
        "- **Carry-Forward Radar:** Helps shortlist strong/weak stocks for your watchlist—always confirm live price action after **9:15 AM IST** and use a stop-loss. Not financial advice."
    )

SECTOR_STOCKS = {
    "Banking & Finance": ["SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS"],
    "Energy & Oil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
}


def _extract_ticker_df(raw_df, ticker):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        if ticker in raw_df.columns.get_level_values(0):
            return raw_df[ticker].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=300)
def fetch_smart_money_pulse():
    all_syms = [s for stocks in SECTOR_STOCKS.values() for s in stocks]
    raw = yf.download(
        all_syms, period="5d", interval="1d", group_by="ticker", progress=False
    )
    rows = []

    for sector, syms in SECTOR_STOCKS.items():
        for sym in syms:
            df = _extract_ticker_df(raw, sym).dropna(subset=["Close", "High", "Low"])
            if len(df) < 2:
                continue

            close_now = float(df["Close"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            high_now = float(df["High"].iloc[-1])
            low_now = float(df["Low"].iloc[-1])

            if close_prev == 0 or any(np.isnan(x) for x in [close_now, close_prev, high_now, low_now]):
                continue

            vol_now = float(df["Volume"].iloc[-1]) if "Volume" in df and pd.notna(df["Volume"].iloc[-1]) else 0.0
            vol_hist = df["Volume"].iloc[:-1].dropna() if "Volume" in df and len(df) > 2 else pd.Series(dtype=float)
            vol_avg = float(vol_hist.mean()) if not vol_hist.empty else vol_now

            chg_pct = ((close_now - close_prev) / close_prev) * 100
            rvol = round(vol_now / vol_avg, 2) if vol_avg > 0 and vol_now > 0 else 1.0
            rng = high_now - low_now
            close_pos = ((close_now - low_now) / rng) * 100 if rng > 0 else 50.0

            # Estimated Flow (Cr) based on abnormal volume surge & price direction
            turnover_cr = (close_now * vol_now) / 1e7
            abnormal_ratio = max(rvol - 0.85, 0.1) if rvol > 1.0 else 0.15
            direction = 1 if chg_pct >= 0 else -1
            est_flow_cr = round(direction * turnover_cr * abnormal_ratio * 0.12, 2)

            carry_score = round(
                float(np.clip((chg_pct + 2.5) * 12, 0, 45))
                + float((close_pos / 100.0) * 35)
                + float(np.clip(rvol * 10, 0, 20)),
                1,
            )

            rows.append({
                "Symbol": sym.replace(".NS", ""),
                "Sector": sector,
                "Price": round(close_now, 2),
                "Change %": round(chg_pct, 2),
                "Est. Flow (Cr)": est_flow_cr,
                "RVOL": rvol,
                "Close Strength %": round(close_pos, 1),
                "Carry Score": carry_score,
                "Watchlist Signal": (
                    "🔥 STRONG CARRY WATCH"
                    if carry_score >= 65 and est_flow_cr > 0
                    else (
                        "🔴 WEAK / SHORT WATCH"
                        if chg_pct < -1.0 and close_pos < 30
                        else "⚪ NEUTRAL WATCH"
                    )
                ),
            })

    if not rows:
        return pd.DataFrame()

    df_out = (
        pd.DataFrame(rows)
        .sort_values(by="Est. Flow (Cr)", ascending=False)
        .reset_index(drop=True)
    )
    return df_out


def render_inline_smc_chart(symbol_clean):
    ticker = f"{symbol_clean}.NS"
    df_c = yf.Ticker(ticker).history(period="5d", interval="15m", auto_adjust=True)
    if df_c is None or df_c.empty:
        st.warning(f"Intraday chart unavailable for {symbol_clean}.")
        return

    df_c["EMA20"] = df_c["Close"].ewm(span=20, adjust=False).mean()
    typical_price = (df_c["High"] + df_c["Low"] + df_c["Close"]) / 3.0
    if "Volume" in df_c and df_c["Volume"].sum() > 0:
        df_c["VWAP"] = (
            (typical_price * df_c["Volume"])
            .groupby(df_c.index.date)
            .cumsum()
            / df_c["Volume"].groupby(df_c.index.date).cumsum().replace(0, np.nan)
        ).fillna(df_c["EMA20"])
    else:
        df_c["VWAP"] = typical_price.rolling(20, min_periods=1).mean()

    df_c = df_c.tail(85)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.76, 0.24],
    )
    fig.add_trace(
        go.Candlestick(
            x=df_c.index,
            open=df_c["Open"],
            high=df_c["High"],
            low=df_c["Low"],
            close=df_c["Close"],
            name=symbol_clean,
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["VWAP"],
            mode="lines",
            name="VWAP / Anchor",
            line=dict(color="#FFD700", width=1.6),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["EMA20"],
            mode="lines",
            name="20 EMA",
            line=dict(color="#29B6F6", width=1.3),
        ),
        row=1,
        col=1,
    )

    vol_colors = [
        "#00E676" if c >= o else "#FF5252"
        for o, c in zip(df_c["Open"], df_c["Close"])
    ]
    fig.add_trace(
        go.Bar(
            x=df_c.index,
            y=df_c["Volume"],
            name="Volume",
            marker_color=vol_colors,
        ),
        row=2,
        col=1,
    )

    last_close = float(df_c["Close"].iloc[-1])
    last_vwap = float(df_c["VWAP"].iloc[-1])
    fig.update_layout(
        title=(
            f"📈 {symbol_clean} — 15m Chart, VWAP/Anchor (₹{last_vwap:,.2f})"
            f" & 20 EMA | Last Price: ₹{last_close:,.2f}"
        ),
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=50, t=45, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


df_pulse = fetch_smart_money_pulse()

if not df_pulse.empty:
    inflow = df_pulse[df_pulse["Est. Flow (Cr)"] > 0]["Est. Flow (Cr)"].sum()
    outflow = abs(df_pulse[df_pulse["Est. Flow (Cr)"] < 0]["Est. Flow (Cr)"].sum())
    net_bias = inflow - outflow

    m1, m2, m3 = st.columns(3)
    m1.metric("🟢 Total Est. Inflow", f"₹{inflow:,.0f} Cr", "Positive Volume Bias")
    m2.metric("🔴 Total Est. Outflow", f"₹{outflow:,.0f} Cr", "Negative Volume Bias")
    m3.metric(
        "⚖️ Net Est. Bias",
        f"₹{net_bias:+,.0f} Cr",
        "Bullish Edge" if net_bias >= 0 else "Bearish Pressure",
    )

    st.markdown("---")

    # 1. CARRY-FORWARD WATCHLIST RADAR
    st.subheader("🔮 Carry-Forward Watchlist Radar")
    top_carry = df_pulse.sort_values(by="Carry Score", ascending=False).head(2)
    c1, c2 = st.columns(2)
    with c1:
        r1 = top_carry.iloc[0]
        st.success(
            f"**#1 TOP WATCHLIST: {r1['Symbol']} ({r1['Sector']})**\n\n"
            f"• **Est. Flow:** ₹{r1['Est. Flow (Cr)']:+.2f} Cr | **Score:** {r1['Carry Score']}/100\n"
            f"• **Close Strength:** {r1['Close Strength %']}% | **RVOL:** {r1['RVOL']}x"
        )
    if len(top_carry) > 1:
        with c2:
            r2 = top_carry.iloc[1]
            st.info(
                f"**#2 RUNNER-UP WATCHLIST: {r2['Symbol']} ({r2['Sector']})**\n\n"
                f"• **Est. Flow:** ₹{r2['Est. Flow (Cr)']:+.2f} Cr | **Score:** {r2['Carry Score']}/100\n"
                f"• **Close Strength:** {r2['Close Strength %']}% | **RVOL:** {r2['RVOL']}x"
            )

    st.markdown("---")

    # 2. INTERACTIVE SANKEY FLOW STREAM
    st.subheader("🌊 Sector-to-Stock Estimated Flow Stream (Sankey)")
    sectors = list(df_pulse["Sector"].unique())
    symbols = list(df_pulse["Symbol"].unique())
    nodes = sectors + symbols
    node_idx = {name: i for i, name in enumerate(nodes)}

    sources = [node_idx[s] for s in df_pulse["Sector"]]
    targets = [node_idx[sym] for sym in df_pulse["Symbol"]]
    values = [max(abs(v), 0.5) for v in df_pulse["Est. Flow (Cr)"]]
    link_colors = [
        "rgba(0, 230, 118, 0.45)" if v >= 0 else "rgba(255, 82, 82, 0.45)"
        for v in df_pulse["Est. Flow (Cr)"]
    ]

    fig_sankey = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=18,
                    line=dict(color="black", width=0.5),
                    label=nodes,
                    color=["#29B6F6"] * len(sectors)
                    + [
                        "#00E676" if v >= 0 else "#FF5252"
                        for v in df_pulse["Est. Flow (Cr)"]
                    ],
                ),
                link=dict(
                    source=sources, target=targets, value=values, color=link_colors
                ),
            )
        ]
    )
    fig_sankey.update_layout(
        template="plotly_dark", height=430, margin=dict(l=10, r=10, t=15, b=15)
    )
    st.plotly_chart(fig_sankey, use_container_width=True)

    st.markdown("---")

    # 3. SECTOR FILTER + CLICKABLE LEDGER + INLINE SMC CHART LAUNCHER
    st.subheader("📋 Flow & Momentum Ledger (Click Any Row for 15m Chart)")
    sector_options = ["All Sectors"] + sorted(df_pulse["Sector"].unique().tolist())
    chosen_sector = st.selectbox("Filter Ledger by Sector:", sector_options, index=0)

    df_view = (
        df_pulse
        if chosen_sector == "All Sectors"
        else df_pulse[df_pulse["Sector"] == chosen_sector].reset_index(drop=True)
    )

    st.caption("Select a stock row to inspect its 15-minute candlesticks, VWAP/anchor, and 20 EMA below.")

    event = st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Carry Score": st.column_config.ProgressColumn(
                "Carry Score", format="%.1f", min_value=0, max_value=100
            ),
            "Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Est. Flow (Cr)": st.column_config.NumberColumn(format="₹%+.2f Cr"),
            "RVOL": st.column_config.NumberColumn(format="%.2fx"),
        },
    )

    selected_rows = event.selection.rows if event and event.selection else []
    active_symbol = (
        df_view.iloc[selected_rows[0]]["Symbol"]
        if selected_rows
        else df_view.iloc[0]["Symbol"]
    )

    st.markdown("---")
    render_inline_smc_chart(active_symbol)
else:
    st.warning("⚠️ Unable to load flow data right now. Click **Refresh Smart Money Flows** to retry.")
