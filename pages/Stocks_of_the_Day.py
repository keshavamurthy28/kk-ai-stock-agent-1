import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Institutional & Orderflow Delta Scanner",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ NSE Market Scanner + Orderflow Delta & Minute Volumes")
st.markdown(
    "Scans all NSE equities for **Institutional Bulk/Block Deals**, **Fundamentals**, and provides a **Minute-by-Minute Orderflow Delta & Volume Breakdown**."
)

# -------------------------------------------------------------------
# 1. UNIVERSE & INSTITUTIONAL BULK/BLOCK DEALS
# -------------------------------------------------------------------


@st.cache_data(ttl=86400)
def get_all_nse_equities():
    url = "https://en.wikipedia.org/wiki/NIFTY_500"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(response.text)
        df_nse = tables[2]
        symbols = df_nse["Symbol"].tolist()
        clean_symbols = sorted(
            list(set([str(sym).strip() for sym in symbols if str(sym).strip()]))
        )
        if len(clean_symbols) > 0:
            return clean_symbols
    except Exception:
        pass

    # Reliable Fallback List
    return [
        "RELIANCE",
        "TCS",
        "HDFCBANK",
        "INFY",
        "ICICIBANK",
        "BHARTIARTL",
        "SBIN",
        "LTIM",
        "ITC",
        "HINDUNILVR",
        "LT",
        "BAJFINANCE",
        "AXISBANK",
        "MARUTI",
        "SUNPHARMA",
        "TATAMOTORS",
        "TITAN",
        "ULTRACEMCO",
        "NTPC",
        "ONGC",
    ]


@st.cache_data(ttl=3600)
def get_nse_bulk_block_deals():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    session = requests.Session()
    session.headers.update(headers)
    bulk_symbols = set()
    try:
        session.get("https://www.nseindia.com", timeout=5)
        deal_url = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
        resp = session.get(deal_url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("bulkDeals", []):
                sym = item.get("symbol")
                if sym:
                    bulk_symbols.add(sym.strip().upper())
            for item in data.get("blockDeals", []):
                sym = item.get("symbol")
                if sym:
                    bulk_symbols.add(sym.strip().upper())
    except Exception:
        pass
    return list(bulk_symbols)


# -------------------------------------------------------------------
# 2. ORDERFLOW DELTA & MINUTE ENGINE
# -------------------------------------------------------------------


def calculate_orderflow_delta(df_intraday):
    if df_intraday.empty:
        return df_intraday

    high_low_range = df_intraday["High"] - df_intraday["Low"]
    high_low_range = high_low_range.replace(0, 0.01)

    clv = (
        (2 * df_intraday["Close"] - df_intraday["High"] - df_intraday["Low"])
        / high_low_range
    )

    df_intraday["Buy Volume"] = (
        df_intraday["Volume"] * (0.5 + (0.5 * clv))
    ).fillna(0)
    df_intraday["Sell Volume"] = (
        df_intraday["Volume"] * (0.5 - (0.5 * clv))
    ).fillna(0)
    df_intraday["Delta"] = df_intraday["Buy Volume"] - df_intraday["Sell Volume"]
    df_intraday["Cumulative Delta"] = df_intraday["Delta"].cumsum()
    return df_intraday


@st.cache_data(ttl=900)
def scan_nse_market_with_orderflow(symbols_list, bulk_deals, scan_limit):
    data_records = []
    active_symbols = symbols_list[:scan_limit]

    progress_bar = st.progress(0)
    status_msg = st.empty()

    for idx, sym in enumerate(active_symbols):
        status_msg.text(
            f"Scanning NSE & Orderflow [{idx+1}/{len(active_symbols)}]: {sym}..."
        )
        ticker_str = (
            f"{sym.upper()}.NS" if not sym.endswith(".NS") else sym.upper()
        )

        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period="3m", interval="1d")
            intraday = t.history(period="5d", interval="5m")

            if hist.empty or len(hist) < 30:
                progress_bar.progress((idx + 1) / len(active_symbols))
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            latest_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            day_change_pct = ((latest_price - prev_price) / prev_price) * 100

            ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            delta_series = close.diff()
            gain = delta_series.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
            loss = (-delta_series.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            avg_vol = volume.tail(20).mean()
            vol_surge = (
                (float(volume.iloc[-1]) / avg_vol) if avg_vol > 0 else 1.0
            )

            try:
                info = t.info
                mcap = info.get("marketCap", 0) / 1e7
                pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
                sector = info.get("sector", "N/A")
                company_name = info.get("shortName", sym)
            except Exception:
                mcap, pe, sector, company_name = 0, 0, "N/A", sym

            is_institutional = sym.upper() in [b.upper() for b in bulk_deals]

            processed_intraday = calculate_orderflow_delta(intraday)
            latest_delta_sum = (
                float(processed_intraday["Delta"].tail(10).sum())
                if not processed_intraday.empty
                else 0
            )

            score = 0
            if is_institutional:
                score += 4
            if latest_delta_sum > 0:
                score += 2
            if latest_price > ema_20:
                score += 1
            if 35 <= rsi <= 65:
                score += 1
            if vol_surge >= 1.5:
                score += 1

            if is_institutional:
                signal = "🏛️️ INSTITUTIONAL BULK ACCUMULATION"
            elif latest_delta_sum > 0 and vol_surge >= 1.3:
                signal = "⚡ HIGH DELTA BUY MOMENTUM"
            elif rsi < 32:
                signal = "🟢 OVERSOLD REVERSAL"
            else:
                signal = "⚪ NEUTRAL / WATCH"

            data_records.append(
                {
                    "Symbol": sym,
                    "Company": company_name,
                    "Sector": sector,
                    "Price (₹)": round(latest_price, 2),
                    "Change (%)": round(day_change_pct, 2),
                    "Inst. Deal": "Yes 🏛️" if is_institutional else "No",
                    "Net Delta (5m)": (
                        f"{latest_delta_sum:+,.0f}"
                        if latest_delta_sum != 0
                        else "0"
                    ),
                    "RSI (14)": round(rsi, 1),
                    "Vol Surge": f"{vol_surge:.2f}x",
                    "P/E Ratio": round(pe, 1) if pe else "N/A",
                    "Market Cap (Cr)": (
                        f"₹{mcap:,.0f} Cr" if mcap > 0 else "N/A"
                    ),
                    "Action Signal": signal,
                    "Score": score,
                    "HistDF": hist,
                    "IntradayDF": processed_intraday,
                }
            )
        except Exception:
            pass

        progress_bar.progress((idx + 1) / len(active_symbols))

    status_msg.empty()
    progress_bar.empty()
    return pd.DataFrame(data_records)


# -------------------------------------------------------------------
# 3. STREAMLIT INTERFACE (SAFE SLIDER BOUNDS)
# -------------------------------------------------------------------

st.sidebar.header("⚙️ Scanner Settings")
all_equities = get_all_nse_equities()
total_equities_len = len(all_equities)

# Safely handle slider boundaries to prevent MinMax errors
max_slider_val = max(20, total_equities_len)
default_val = min(50, max_slider_val)

scan_count = st.sidebar.slider(
    "Number of Stocks to Scan",
    min_value=10,
    max_value=max_slider_val,
    value=default_val,
    step=10,
)

top_picks_count = st.sidebar.slider(
    "Top Stocks to Display", min_value=3, max_value=15, value=5
)

if st.sidebar.button("🔄 Force Refresh Scanner"):
    st.cache_data.clear()
    st.rerun()

with st.spinner(
    "Scanning NSE exchange, bulk deals, and calculating orderflow delta matrices..."
):
    bulk_list = get_nse_bulk_block_deals()
    results_df = scan_nse_market_with_orderflow(
        all_equities, bulk_list, scan_count
    )

if results_df.empty:
    st.warning(
        "No market data returned. Click **'Force Refresh Scanner'** in the sidebar."
    )
else:
    df_sorted = results_df.sort_values(
        by="Score", ascending=False
    ).reset_index(drop=True)
    st.subheader(
        f"⭐ Top {top_picks_count} Stock Picks (Filtered by Orderflow & Bulk Orders)"
    )

    top_results = df_sorted.head(top_picks_count)

    for idx, row in top_results.iterrows():
        with st.expander(
            f"#{idx+1} {row['Symbol']} — {row['Company']} ({row['Action Signal']})",
            expanded=(idx == 0),
        ):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Current Price", f"₹{row['Price (₹)']}", f"{row['Change (%)']}%"
            )
            col2.metric("Institutional Deal", f"{row['Inst. Deal']}")
            col3.metric("Net Orderflow Delta", f"{row['Net Delta (5m)']}")
            col4.metric("Market Cap", f"{row['Market Cap (Cr)']}")

            tab_chart, tab_delta = st.tabs(
                ["📈 Price Action Chart", "⚡ Orderflow Delta & Minute Volumes"]
            )

            with tab_chart:
                hist_df = row["HistDF"]
                fig = go.Figure()
                fig.add_trace(
                    go.Candlestick(
                        x=hist_df.index,
                        open=hist_df["Open"],
                        high=hist_df["High"],
                        low=hist_df["Low"],
                        close=hist_df["Close"],
                        name="Price",
                    )
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_delta:
                intraday_df = row["IntradayDF"]
                if not intraday_df.empty and "Delta" in intraday_df.columns:
                    fig_delta = go.Figure()
                    colors = [
                        "green" if val >= 0 else "red"
                        for val in intraday_df["Delta"]
                    ]

                    fig_delta.add_trace(
                        go.Bar(
                            x=intraday_df.index,
                            y=intraday_df["Delta"],
                            name="Minute Delta (Buy-Sell)",
                            marker_color=colors,
                        )
                    )
                    fig_delta.add_trace(
                        go.Scatter(
                            x=intraday_df.index,
                            y=intraday_df["Cumulative Delta"],
                            name="Cumulative Delta Line",
                            yaxis="y2",
                            line=dict(color="blue", width=2),
                        )
                    )

                    fig_delta.update_layout(
                        title=f"{row['Symbol']} — Intraday Orderflow Delta & Volume Breakdown",
                        height=280,
                        margin=dict(l=10, r=10, t=30, b=10),
                        template="plotly_white",
                        yaxis=dict(title="Minute Delta Volume"),
                        yaxis2=dict(
                            title="Cumulative Delta",
                            overlaying="y",
                            side="right",
                        ),
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.02, x=0
                        ),
                    )
                    st.plotly_chart(fig_delta, use_container_width=True)
                else:
                    st.info(
                        "Intraday minute delta data currently unavailable for this ticker."
                    )

    st.markdown("---")
    st.subheader("📋 Complete Scanned Market Overview Table")
    final_table_df = df_sorted.drop(columns=["HistDF", "IntradayDF"])
    st.dataframe(final_table_df, use_container_width=True)
