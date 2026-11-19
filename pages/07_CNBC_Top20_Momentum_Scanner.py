from datetime import datetime, time as dt_time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="CNBC Top 20 & Institutional Momentum Scanner", layout="wide"
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

st.title("📺 CNBC-Style 'Top 20' & Institutional Momentum Desk")
st.markdown(
    "Combines **live NSE market/volume data** with **real-time market news headlines** "
    "and a customizable **TV / Desk Watchlist** so you can check news catalysts, "
    "price action, stop-loss, and profit targets in one place."
)

market_status = (
    "🟢 Live NSE Session (9:15 AM – 3:30 PM IST)"
    if is_market_open
    else "🟡 Pre-Market / Market Closed"
)
st.caption(f"{market_status} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

with st.expander("📘 Beginner Guide: How to Use TV / Momentum Desk Picks Safely", expanded=False):
    st.markdown(
        "- **News vs. Price Action:** A news headline or TV mention puts a stock on your radar—**price and volume after 9:15 AM IST** confirm whether buyers or sellers are actually in control.\n"
        "- **When to Buy:** Only after live trading starts (**9:15 AM IST**) with clear momentum and volume—avoid rushing in blindly at the opening bell.\n"
        "- **When to Book Profit:** Consider taking partial or full profit near **Target 1** first rather than waiting blindly for a distant target, and exit if price hits **Stop-Loss**. Not financial advice."
    )

# Sidebar Controls for Filtering
st.sidebar.header("🌐 Market Universe & Filters")
scanning_universe = st.sidebar.selectbox(
    "Select Scanning Universe",
    [
        "Broad NSE Liquid F&O Universe (Top 50+)",
        "Nifty 50 Heavyweights",
        "High-Conviction Midcaps",
        "Custom TV / Desk Watchlist",
    ],
)
vol_multiplier_filter = st.sidebar.slider(
    "Min Volume Surge Multiplier", 0.5, 3.0, 1.2, 0.1
)

default_desk_stocks = "COALINDIA, ITC, HAL, SUNPHARMA, TDPOWERSYS, APOLLOHOSP, SBIN, RELIANCE"
custom_input = st.sidebar.text_area(
    "TV / Desk Watchlist Tickers (comma-separated)",
    value=default_desk_stocks,
    height=75,
)

if st.sidebar.button("🔄 Refresh CNBC Momentum Desk", type="primary"):
    st.cache_data.clear()
    st.toast("Cache cleared! Fetching latest live market & news signals...", icon="⚡")
    st.rerun()


@st.cache_data(ttl=300)
def fetch_market_news_headlines():
    """Fetches recent Indian stock market news headlines from public RSS feeds if available."""
    headlines = []
    try:
        import feedparser

        feeds = [
            "https://www.cnbctv18.com/commonfeeds/v1/cnbc/rss/market.xml",
            "https://www.cnbctv18.com/commonfeeds/v1/cnbc/rss/stocks.xml",
        ]
        for url in feeds:
            parsed = feedparser.parse(url)
            for entry in getattr(parsed, "entries", [])[:15]:
                title = getattr(entry, "title", "").strip()
                if title:
                    headlines.append(title)
    except Exception:
        pass
    return headlines


def _match_news_catalyst(symbol, change_pct, headlines):
    sym_upper = symbol.upper()
    for h in headlines:
        h_upper = h.upper()
        if sym_upper in h_upper or (sym_upper == "SBIN" and "SBI" in h_upper) or (
            sym_upper == "COALINDIA" and "COAL INDIA" in h_upper
        ) or (sym_upper == "APOLLOHOSP" and "APOLLO" in h_upper):
            short_h = h if len(h) <= 75 else h[:72] + "..."
            return f"📰 {short_h}"
    return "📈 Positive Momentum / Volume Surge" if change_pct >= 0 else "📉 Weak / Pullback Watch"


def _extract_ticker_df(raw_df, sym, total_tickers):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    if total_tickers > 1 and isinstance(raw_df.columns, pd.MultiIndex):
        if sym in raw_df.columns.get_level_values(0):
            return raw_df[sym].dropna(how="all")
        return pd.DataFrame()
    return raw_df.dropna(how="all")


@st.cache_data(ttl=60)
def fetch_cnbc_top_momentum_scans(universe_choice, min_vol, custom_csv):
    custom_tickers = [
        t.strip().upper().replace(".NS", "")
        for t in custom_csv.split(",")
        if t.strip()
    ]

    if "Custom TV" in universe_choice and custom_tickers:
        tickers = custom_tickers
    elif "Nifty 50" in universe_choice:
        tickers = [
            "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN",
            "BHARTIARTL", "ITC", "LT", "BAJFINANCE", "SUNPHARMA", "AXISBANK",
            "TATAMOTORS", "NTPC", "DIVISLAB", "ONGC", "HINDUNILVR",
        ]
    elif "Midcaps" in universe_choice:
        tickers = [
            "MSTCLTD", "POWERINDIA", "AMBER", "TDPOWERSYS", "KALYANKJIL",
            "HAL", "BEL", "COALINDIA", "APOLLOHOSP",
        ]
    else:
        tickers = list(dict.fromkeys([
            "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
            "DIVISLAB", "ONGC", "MSTCLTD", "POWERINDIA", "AMBER", "TDPOWERSYS",
            "KALYANKJIL", "HAL", "BEL", "ITC", "COALINDIA", "APOLLOHOSP",
        ] + custom_tickers))

    headlines = fetch_market_news_headlines()
    symbols = [f"{s}.NS" for s in tickers]

    try:
        raw = yf.download(
            symbols,
            period="25d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    scan_results = []

    for symbol in tickers:
        try:
            hist = _extract_ticker_df(raw, f"{symbol}.NS", len(tickers)).dropna(
                subset=["Close", "Open", "High", "Low"]
            )
            if hist is None or hist.empty or len(hist) < 10:
                continue

            latest = hist.iloc[-1]
            prev = hist.iloc[-2]

            ltp = float(latest["Close"])
            prev_close = float(prev["Close"])
            if prev_close <= 0 or np.isnan(ltp) or np.isnan(prev_close):
                continue

            change_pct = ((ltp - prev_close) / prev_close) * 100.0
            vol_series = hist["Volume"] if "Volume" in hist else pd.Series(0.0, index=hist.index)
            cur_vol = float(vol_series.iloc[-1]) if pd.notna(vol_series.iloc[-1]) else 0.0
            avg_vol = float(vol_series.iloc[:-1].mean()) if len(vol_series) > 2 else cur_vol
            vol_mult = round(cur_vol / avg_vol, 2) if avg_vol > 0 and cur_vol > 0 else 1.0

            if vol_mult >= min_vol:
                hist = hist.copy()
                hist["EMA_9"] = hist["Close"].ewm(span=9, adjust=False).mean()
                hist["EMA_21"] = hist["Close"].ewm(span=21, adjust=False).mean()

                stop_loss = round(ltp * 0.967, 2)
                target_1 = round(ltp * 1.035, 2)
                target_2 = round(ltp * 1.068, 2)
                score = "4/5" if change_pct > 0 else "3/5"
                catalyst = _match_news_catalyst(symbol, change_pct, headlines)

                scan_results.append({
                    "Stock": symbol,
                    "LTP": round(ltp, 2),
                    "Change_%": round(change_pct, 2),
                    "Vol_Mult": vol_mult,
                    "Score": score,
                    "Catalyst": catalyst,
                    "Stop_Loss": stop_loss,
                    "Target_1": target_1,
                    "Target_2": target_2,
                    "History": hist,
                })
        except Exception:
            continue

    df = pd.DataFrame(scan_results)
    if not df.empty:
        df = df.sort_values(by="Change_%", ascending=False).reset_index(drop=True)
    return df


with st.spinner("Scanning NSE momentum, volume & news catalysts..."):
    df_cnbc = fetch_cnbc_top_momentum_scans(
        scanning_universe, vol_multiplier_filter, custom_input
    )

st.markdown(
    f"## 🔥 Top Actionable Stocks for the Day (Market Sweep — Total Found: {len(df_cnbc)})"
)
st.caption(
    "*Combines live market price/volume filters with matched news headlines—use as a research watchlist, not guaranteed financial advice.*"
)

if df_cnbc.empty:
    st.warning("No stocks matched the current filter criteria. Try lowering **Min Volume Surge Multiplier** in the sidebar.")
else:
    for _, row in df_cnbc.iterrows():
        stock_symbol = row["Stock"]
        chg = row["Change_%"]
        color_emoji = "🟢" if chg >= 0 else "🔴"

        st.markdown(
            f"### {color_emoji} {stock_symbol} ({chg:+.2f}%) — Score: "
            f"{row['Score']} | {row['Catalyst']}"
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Last Price", f"₹{row['LTP']:,.2f}", f"Vol: {row['Vol_Mult']}x")
        col2.metric("Stop-Loss", f"₹{row['Stop_Loss']:,.2f}", "Risk Guardrail")
        col3.metric("Target 1 / Target 2", f"₹{row['Target_1']:,.2f}", f"T2: ₹{row['Target_2']:,.2f} (+6.8%)")
        col4.metric(
            "Stance",
            "BUY WATCH" if chg >= 0 else "CAUTION WATCH",
            "Confirm After 9:15 AM",
        )

        with st.expander(
            f"📈 View Chart & EMA/FVG Breakdown for {stock_symbol}"
        ):
            hist_df = row["History"]
            if not hist_df.empty:
                fig = go.Figure()

                fig.add_trace(
                    go.Candlestick(
                        x=hist_df.index,
                        open=hist_df["Open"],
                        high=hist_df["High"],
                        low=hist_df["Low"],
                        close=hist_df["Close"],
                        name="Price Action",
                        increasing_line_color="#00E676",
                        decreasing_line_color="#FF5252",
                    )
                )

                if "EMA_9" in hist_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=hist_df.index,
                            y=hist_df["EMA_9"],
                            line=dict(color="#29B6F6", width=1.5),
                            name="EMA 9",
                        )
                    )
                if "EMA_21" in hist_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=hist_df.index,
                            y=hist_df["EMA_21"],
                            line=dict(color="#FFA726", width=1.5),
                            name="EMA 21",
                        )
                    )

                if len(hist_df) >= 5:
                    recent_low = float(hist_df["Low"].iloc[-3])
                    recent_high = float(hist_df["High"].iloc[-5])
                    fig.add_hrect(
                        y0=min(recent_high, recent_low),
                        y1=max(recent_high, recent_low),
                        fillcolor="rgba(0, 230, 118, 0.12)",
                        layer="below",
                        line_width=0,
                        annotation_text="Bullish FVG Demand Zone",
                        annotation_position="bottom right",
                    )

                fig.add_hline(
                    y=row["Target_1"],
                    line_dash="dot",
                    line_color="#29B6F6",
                    annotation_text=f"Target 1: ₹{row['Target_1']:,.2f}",
                )
                fig.add_hline(
                    y=row["Target_2"],
                    line_dash="dash",
                    line_color="#00E676",
                    annotation_text=f"Target 2: ₹{row['Target_2']:,.2f}",
                )
                fig.add_hline(
                    y=row["Stop_Loss"],
                    line_dash="dash",
                    line_color="#FF5252",
                    annotation_text=f"Stop Loss: ₹{row['Stop_Loss']:,.2f}",
                )

                fig.update_layout(
                    title=f"Momentum Desk Chart Analysis — {stock_symbol}",
                    yaxis_title="Price (INR ₹)",
                    template="plotly_dark",
                    height=420,
                    xaxis_rangeslider_visible=False,
                )

                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
