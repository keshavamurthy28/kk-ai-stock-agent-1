import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Institutional & Orderflow Delta Scanner",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ NSE Market Scanner + Orderflow Delta & Trading Levels")
st.markdown(
    "Scans NSE equities for **Institutional Deals**, **Orderflow Delta**, **Buy/Sell Signals**, and **Automated Stop-Loss Levels**."
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
        symbols = tables[2]["Symbol"].tolist()
        clean_symbols = sorted(
            list(set([str(sym).strip() for sym in symbols if str(sym).strip()]))
        )
        if len(clean_symbols) > 0:
            return clean_symbols
    except Exception:
        pass

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
# 2. ORDERFLOW DELTA, TRADING SIGNALS & STOP LOSS ENGINE
# -------------------------------------------------------------------


def calculate_indicators_and_levels(df_hist, df_intraday):
    if df_intraday.empty or len(df_intraday) < 10:
        return df_intraday, 0, 0, "HOLD", 0, 0

    # Orderflow Delta Proxy calculation
    high_low_range = (df_intraday["High"] - df_intraday["Low"]).replace(
        0, 0.01
    )
    clv = (
        2 * df_intraday["Close"] - df_intraday["High"] - df_intraday["Low"]
    ) / high_low_range

    df_intraday["Buy Volume"] = (
        df_intraday["Volume"] * (0.5 + (0.5 * clv))
    ).fillna(0)
    df_intraday["Sell Volume"] = (
        df_intraday["Volume"] * (0.5 - (0.5 * clv))
    ).fillna(0)
    df_intraday["Delta"] = df_intraday["Buy Volume"] - df_intraday["Sell Volume"]
    df_intraday["Cumulative Delta"] = df_intraday["Delta"].cumsum()

    latest_close = float(df_hist["Close"].iloc[-1])
    recent_low = float(df_intraday["Low"].tail(15).min())
    recent_high = float(df_intraday["High"].tail(15).max())

    # Stop Loss and Targets (Risk-Reward 1:2)
    stop_loss = round(recent_low * 0.992, 2)  # slightly below recent swing low
    target_price = round(latest_close + (2 * (latest_close - stop_loss)), 2)

    latest_delta = float(df_intraday["Delta"].iloc[-1])
    net_delta_sum = float(df_intraday["Delta"].tail(5).sum())

    avg_vol = df_intraday["Volume"].rolling(20).mean().iloc[-1]
    current_vol = df_intraday["Volume"].iloc[-1]
    vol_surge = (
        (current_vol / avg_vol) if pd.notnull(avg_vol) and avg_vol > 0 else 1.0
    )

    ema_20 = float(df_hist["Close"].ewm(span=20, adjust=False).mean().iloc[-1])

    # Trigger logic
    if latest_close > ema_20 and net_delta_sum > 0 and vol_surge >= 1.2:
        action = "🟢 BUY / LONG ENTRY"
    elif latest_close < ema_20 and net_delta_sum < 0:
        action = "🔴 SELL / SHORT EXIT"
    else:
        action = "⚪ HOLD / WATCH"

    return (
        df_intraday,
        stop_loss,
        target_price,
        action,
        latest_delta,
        vol_surge,
    )


@st.cache_data(ttl=900)
def scan_nse_market(symbols_list, bulk_deals, scan_limit):
    data_records = []
    active_symbols = symbols_list[:scan_limit]

    progress_bar = st.progress(0)
    status_msg = st.empty()

    for idx, sym in enumerate(active_symbols):
        status_msg.text(
            f"Scanning Market & Computing Indicators [{idx+1}/{len(active_symbols)}]: {sym}..."
        )
        ticker_str = f"{sym}.NS" if not sym.endswith(".NS") else sym

        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period="3m", interval="1d")
            intraday = t.history(period="5d", interval="15m")

            if hist.empty or len(hist) < 30:
                progress_bar.progress((idx + 1) / len(active_symbols))
                continue

            latest_price = float(hist["Close"].iloc[-1])
            prev_price = float(hist["Close"].iloc[-2])
            day_change_pct = ((latest_price - prev_price) / prev_price) * 100

            (
                processed_intraday,
                stop_loss,
                target_price,
                action_signal,
                latest_delta,
                vol_surge,
            ) = calculate_indicators_and_levels(hist, intraday)

            try:
                info = t.info
                mcap = info.get("marketCap", 0) / 1e7
                pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
                sector = info.get("sector", "N/A")
                company_name = info.get("shortName", sym)
            except Exception:
                mcap, pe, sector, company_name = 0, 0, "N/A", sym

            is_institutional = sym.upper() in [b.upper() for b in bulk_deals]

            score = 0
            if is_institutional:
                score += 4
            if "BUY" in action_signal:
                score += 3
            if vol_surge >= 1.5:
                score += 2
            if day_change_pct > 0:
                score += 1

            data_records.append(
                {
                    "Symbol": sym,
                    "Company": company_name,
                    "Sector": sector,
                    "Price (₹)": round(latest_price, 2),
                    "Change (%)": round(day_change_pct, 2),
                    "Action Signal": action_signal,
                    "Stop Loss (₹)": stop_loss,
                    "Target (₹)": target_price,
                    "Inst. Deal": "Yes 🏛️" if is_institutional else "No",
                    "Net Delta": f"{latest_delta:+,.0f}",
                    "Vol Surge": f"{vol_surge:.2f}x",
                    "P/E Ratio": round(pe, 1) if pe else "N/A",
                    "Market Cap (Cr)": (
                        f"₹{mcap:,.0f} Cr" if mcap > 0 else "N/A"
                    ),
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
# 3. STREAMLIT INTERFACE
# -------------------------------------------------------------------

st.sidebar.header("⚙️ Scanner Settings")
all_equities = get_all_nse_equities()
total_equities_len = len(all_equities)

max_slider_val = max(20, total_equities_len)
default_val = min(40, max_slider_val)

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
    "Scanning NSE exchange, computing orderflow delta, volume surge, and trade triggers..."
):
    bulk_list = get_nse_bulk_block_deals()
    results_df = scan_nse_market(all_equities, bulk_list, scan_count)

if results_df.empty:
    st.warning(
        "No market data returned. Click **'Force Refresh Scanner'** in the sidebar."
    )
else:
    df_sorted = results_df.sort_values(
        by="Score", ascending=False
    ).reset_index(drop=True)
    st.subheader(f"⭐ Top {top_picks_count} Stock Action Triggers & Levels")

    top_results = df_sorted.head(top_picks_count)

    for idx, row in top_results.iterrows():
        with st.expander(
            f"#{idx+1} {row['Symbol']} — {row['Company']} | Signal: {row['Action Signal']}",
            expanded=(idx == 0),
        ):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(
                "Price", f"₹{row['Price (₹)']}", f"{row['Change (%)']}%"
            )
            c2.metric("Action Trigger", f"{row['Action Signal']}")
            c3.metric("Stop Loss", f"₹{row['Stop Loss (₹)']}")
            c4.metric("Target Price", f"₹{row['Target (₹)']}")
            c5.metric("Volume Surge", f"{row['Vol_Surge'] if 'Vol_Surge' in row else row['Vol Surge']}")

            st.markdown("---")

            # Unified Master Chart (Price Candle top pane + Volume/Delta bottom pane)
            intraday_df = row["IntradayDF"]
            if not intraday_df.empty and "Delta" in intraday_df.columns:
                fig = make_subplots(
                    rows=2,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    row_heights=[0.65, 0.35],
                    subplot_titles=(
                        f"{row['Symbol']} Intraday Price Action",
                        "Orderflow Delta & Volume Breakdown",
                    ),
                )

                # Row 1: Price Candlestick
                fig.add_trace(
                    go.Candlestick(
                        x=intraday_df.index,
                        open=intraday_df["Open"],
                        high=intraday_df["High"],
                        low=intraday_df["Low"],
                        close=intraday_df["Close"],
                        name="Price",
                    ),
                    row=1,
                    col=1,
                )

                # Row 2: Delta Volume Bars
                bar_colors = [
                    "#26a69a" if val >= 0 else "#ef5350"
                    for val in intraday_df["Delta"]
                ]
                fig.add_trace(
                    go.Bar(
                        x=intraday_df.index,
                        y=intraday_df["Delta"],
                        name="Orderflow Delta",
                        marker_color=bar_colors,
                    ),
                    row=2,
                    col=1,
                )

                fig.update_layout(
                    height=450,
                    margin=dict(l=10, r=10, t=30, b=10),
                    template="plotly_white",
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                )
                fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
                fig.update_yaxes(title_text="Delta Volume", row=2, col=1)

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Intraday chart data unavailable for this ticker.")

    st.markdown("---")
    st.subheader("📋 Complete Scanned Market Overview Table")
    final_table_df = df_sorted.drop(columns=["HistDF", "IntradayDF"])
    st.dataframe(final_table_df, use_container_width=True)
