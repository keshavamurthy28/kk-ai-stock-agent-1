import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Deal Backtester & Screener",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ NSE Institutional Bulk/Block Deals & Fundamental Screener")
st.markdown(
    "Backtest and screen stocks backed by **Institutional Bulk & Block Deals**, combined with **Fundamental filters** (Market Cap, P/E) and **Technical Volume/Delta surges**."
)

# -------------------------------------------------------------------
# 1. UNIVERSE & INSTITUTIONAL DATA FETCHING
# -------------------------------------------------------------------


@st.cache_data(ttl=86400)
def get_nse_universe():
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

    # Reliable Fallback List if web fetch fails
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
def get_live_bulk_block_deals():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    session = requests.Session()
    session.headers.update(headers)
    deal_symbols = set()
    try:
        session.get("https://www.nseindia.com", timeout=5)
        deal_url = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
        resp = session.get(deal_url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("bulkDeals", []):
                sym = item.get("symbol")
                if sym:
                    deal_symbols.add(sym.strip().upper())
            for item in data.get("blockDeals", []):
                sym = item.get("symbol")
                if sym:
                    deal_symbols.add(sym.strip().upper())
    except Exception:
        pass
    return list(deal_symbols)


# -------------------------------------------------------------------
# 2. SIDEBAR CONFIGURATION CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("⚙️ Institutional Screener Filters")

universe_size = st.sidebar.slider(
    "Number of Stocks to Scan", min_value=10, max_value=200, value=50, step=10
)
min_mcap_cr = st.sidebar.number_input(
    "Minimum Market Cap (₹ Crores)", value=5000, step=1000
)
max_pe_ratio = st.sidebar.number_input(
    "Maximum P/E Ratio (0 for Any)", value=60.0, step=5.0
)
require_bulk_deal = st.sidebar.checkbox(
    "Require Recent Institutional Bulk/Block Deal", value=False
)

st.sidebar.subheader("Backtest Performance Horizon")
backtest_period = st.sidebar.selectbox(
    "Select Historical Lookback", ["1 Day", "1 Week", "1 Month", "3 Months"]
)

period_map = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
}
selected_period = period_map[backtest_period]

run_screening = st.sidebar.button("🚀 Run Institutional Screener & Backtest")

# -------------------------------------------------------------------
# 3. SCREENING & BACKTESTING ENGINE
# -------------------------------------------------------------------


def run_institutional_screener(
    symbols, bulk_deals, limit, min_mcap, max_pe, req_deal, period
):
    scanned_records = []
    active_pool = symbols[:limit]

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sym in enumerate(active_pool):
        status_text.text(
            f"Screening [{idx+1}/{len(active_pool)}]: Analyzing {sym}..."
        )
        ticker_str = f"{sym}.NS" if not sym.endswith(".NS") else sym

        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period=period, interval="1d")

            if hist.empty or len(hist) < 15:
                progress_bar.progress((idx + 1) / len(active_pool))
                continue

            # Fundamentals Check
            try:
                info = t.info
                mcap = info.get("marketCap", 0) / 1e7  // Crores
                pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
                sector = info.get("sector", "N/A")
                company_name = info.get("shortName", sym)
            except Exception:
                mcap, pe, sector, company_name = 0, 0, "N/A", sym

            # Apply Fundamental filters
            if mcap < min_mcap:
                progress_bar.progress((idx + 1) / len(active_pool))
                continue
            if max_pe > 0 and pe and pe > max_pe:
                progress_bar.progress((idx + 1) / len(active_pool))
                continue

            is_institutional = sym.upper() in [b.upper() for b in bulk_deals]
            if req_deal and not is_institutional:
                progress_bar.progress((idx + 1) / len(active_pool))
                continue

            # Technical & Backtest Calculations
            close = hist["Close"]
            volume = hist["Volume"]

            start_price = float(close.iloc[0])
            end_price = float(close.iloc[-1])
            stock_return_pct = ((end_price - start_price) / start_price) * 100

            # Volatility & Momentum score
            ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            avg_vol = volume.tail(20).mean()
            vol_surge = (
                (float(volume.iloc[-1]) / avg_vol) if avg_vol > 0 else 1.0
            )

            # Score Assignment
            score = 0
            if is_institutional:
                score += 5
            if stock_return_pct > 0:
                score += 2
            if end_price > ema_20:
                score += 2
            if vol_surge >= 1.3:
                score += 1

            scanned_records.append(
                {
                    "Symbol": sym,
                    "Company": company_name,
                    "Sector": sector,
                    "Current Price (₹)": round(end_price, 2),
                    f"Return ({backtest_period})": round(stock_return_pct, 2),
                    "Inst. Deal": "Yes 🏛️" if is_institutional else "No",
                    "Market Cap (Cr)": (
                        f"₹{mcap:,.0f} Cr" if mcap > 0 else "N/A"
                    ),
                    "P/E Ratio": round(pe, 1) if pe else "N/A",
                    "Vol Surge": f"{vol_surge:.2f}x",
                    "Score": score,
                    "PriceHistory": close,
                }
            )
        except Exception:
            pass

        progress_bar.progress((idx + 1) / len(active_pool))

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(scanned_records)


# -------------------------------------------------------------------
# 4. DASHBOARD RENDER LOGIC
# -------------------------------------------------------------------
if run_screening:
    with st.spinner("Executing fundamental filters and institutional backtest..."):
        all_symbols = get_nse_universe()
        bulk_list = get_live_bulk_block_deals()

        result_df = run_institutional_screener(
            all_symbols,
            bulk_list,
            universe_size,
            min_mcap_cr,
            max_pe_ratio,
            require_bulk_deal,
            selected_period,
        )

    if result_df.empty:
        st.warning(
            "No stocks matched your specific fundamental and institutional criteria. Try relaxing your filters."
        )
    else:
        df_sorted = result_df.sort_values(
            by="Score", ascending=False
        ).reset_index(drop=True)

        st.success(
            f"Successfully screened {len(df_sorted)} high-potential institutional stocks!"
        )

        # Top Picks Metrics Display
        st.subheader("⭐ Top Recommended Institutional Stock Picks")
        top_picks = df_sorted.head(5)

        cols = st.columns(len(top_picks) if len(top_picks) > 0 else 1)
        for i, (idx, row) in enumerate(top_picks.iterrows()):
            with cols[i]:
                st.metric(
                    label=f"#{i+1} {row['Symbol']}",
                    value=f"₹{row['Current Price (₹)']}",
                    delta=f"{row[f'Return ({backtest_period})']}%",
                )
                st.caption(
                    f"**Inst. Deal:** {row['Inst. Deal']} | **M-Cap:** {row['Market Cap (Cr)']}"
                )

        # Comparative Performance Chart of Top Picks
        st.subheader("📈 Cumulative Performance Comparison of Top Selected Stocks")
        fig_comp = go.Figure()
        for idx, row in top_picks.iterrows():
            p_series = row["PriceHistory"]
            norm_series = (p_series / p_series.iloc[0] - 1) * 100
            fig_comp.add_trace(
                go.Scatter(
                    x=norm_series.index,
                    y=norm_series,
                    name=row["Symbol"],
                    mode="lines",
                )
            )

        fig_comp.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            template="plotly_white",
            yaxis_title="Growth (%)",
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Detailed Scanned Data Table
        st.subheader("📋 Complete Scanned & Backtested Stock List")
        display_table = df_sorted.drop(columns=["PriceHistory"])
        st.dataframe(display_table, use_container_width=True)
else:
    st.info(
        "👈 Configure your institutional preferences, market cap limits, and lookback horizon in the sidebar, then click **Run Institutional Screener & Backtest**."
    )
