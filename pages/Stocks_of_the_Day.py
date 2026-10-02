import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE All-Market & Institutional Scanner",
    page_icon="📈",
    layout="wide",
)

st.title("📈 NSE All-Market & Institutional Order Scanner")
st.markdown(
    "Scans across **all available NSE equities**, checking for **Institutional Bulk/Block Deals**, **Fundamental Valuations** (P/E, Market Cap), and **Technical Momentum** (RSI, EMAs, Volume Surge)."
)

# -------------------------------------------------------------------
# 1. FETCH ALL NSE STOCKS & LIVE BULK/BLOCK DEALS
# -------------------------------------------------------------------


@st.cache_data(ttl=86400)
def get_all_nse_equities():
    """Fetches the official comprehensive equity list from NSE/Wikipedia indices (Nifty Total Market / 500)."""
    url = "https://en.wikipedia.org/wiki/NIFTY_500"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(response.text)
        df_nse = tables[2]
        symbols = df_nse["Symbol"].tolist()
        return sorted(list(set([str(sym).strip() for sym in symbols if str(sym).strip()])))
    except Exception:
        # Core fallback equity list if network limits occur
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
            "ASIANPAINT",
            "HCLTECH",
            "WIPRO",
            "POWERGRID",
            "TATASTEEL",
        ]


@st.cache_data(ttl=3600)
def get_nse_bulk_block_deals():
    """Pulls recent institutional bulk and block deals directly from NSE API endpoints."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    session = requests.Session()
    session.headers.update(headers)
    bulk_symbols = set()

    try:
        # Establish session cookie handshake with NSE
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
# 2. SCANNING & ANALYSIS ENGINE
# -------------------------------------------------------------------


@st.cache_data(ttl=900)
def scan_nse_market(symbols_list, bulk_deals, scan_limit):
    data_records = []
    active_symbols = symbols_list[:scan_limit]

    progress_bar = st.progress(0)
    status_msg = st.empty()

    for idx, sym in enumerate(active_symbols):
        status_msg.text(
            f"Scanning NSE Market [{idx+1}/{len(active_symbols)}]: {sym}..."
        )
        ticker_str = (
            f"{sym.upper()}.NS" if not sym.endswith(".NS") else sym.upper()
        )

        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period="3m", interval="1d")

            if hist.empty or len(hist) < 30:
                progress_bar.progress((idx + 1) / len(active_symbols))
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            latest_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            day_change_pct = ((latest_price - prev_price) / prev_price) * 100

            # Technical indicators
            ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            ema_50 = (
                float(close.ewm(span=50, adjust=False).mean().iloc[-1])
                if len(close) >= 50
                else ema_20
            )

            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # Volume surge ratio
            avg_vol = volume.tail(20).mean()
            vol_surge = (
                (float(volume.iloc[-1]) / avg_vol) if avg_vol > 0 else 1.0
            )

            # Fundamentals
            try:
                info = t.info
                mcap = info.get("marketCap", 0) / 1e7  # Crores INR
                pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
                div_yield = (info.get("dividendYield", 0.0) or 0.0) * 100
                sector = info.get("sector", "N/A")
                company_name = info.get("shortName", sym)
            except Exception:
                mcap, pe, div_yield, sector, company_name = 0, 0, 0, "N/A", sym

            # Institutional Check
            is_institutional = sym.upper() in [b.upper() for b in bulk_deals]

            # Scoring algorithm combining institutional activity + technicals + fundamentals
            score = 0
            if is_institutional:
                score += 4  # Heavy weight for verified bulk/block institutional order presence
            if latest_price > ema_20:
                score += 1
            if ema_20 > ema_50:
                score += 1
            if 35 <= rsi <= 65:
                score += 1
            if vol_surge >= 1.5:
                score += 1  # High accumulation volume
            if pe > 0 and pe < 35:
                score += 1

            if is_institutional:
                signal = "🏛️ INSTITUTIONAL BULK ACCUMULATION"
            elif rsi < 32:
                signal = "🟢 OVERSOLD REVERSAL"
            elif score >= 5:
                signal = "🔥 STRONG TECHNICAL MOMENTUM"
            elif score >= 3:
                signal = "📈 POSITIVE SETUP"
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
                    "RSI (14)": round(rsi, 1),
                    "Vol Surge": f"{vol_surge:.2f}x",
                    "P/E Ratio": round(pe, 1) if pe else "N/A",
                    "Market Cap (Cr)": (
                        f"₹{mcap:,.0f} Cr" if mcap > 0 else "N/A"
                    ),
                    "Action Signal": signal,
                    "Score": score,
                    "HistDF": hist,
                }
            )
        except Exception:
            pass

        progress_bar.progress((idx + 1) / len(active_symbols))

    status_msg.empty()
    progress_bar.empty()
    return pd.DataFrame(data_records)


# -------------------------------------------------------------------
# 3. STREAMLIT APP CONTROLS & DASHBOARD VIEW
# -------------------------------------------------------------------

st.sidebar.header("⚙️ Scanner Settings")

all_equities = get_all_nse_equities()
st.sidebar.info(
    f"Loaded **{len(all_equities)}** total equities from NSE broader universe."
)

scan_count = st.sidebar.slider(
    "Number of Stocks to Scan in Session",
    min_value=20,
    max_value=len(all_equities),
    value=min(100, len(all_equities)),
    step=10,
    help="Increase this slider to scan more stocks across the exchange.",
)

top_picks_count = st.sidebar.slider(
    "Top Stocks to Display", min_value=3, max_value=15, value=5
)

if st.sidebar.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

with st.spinner(
    "Fetching live NSE bulk/block orders, fundamentals, and charting indicators..."
):
    bulk_list = get_nse_bulk_block_deals()
    results_df = scan_nse_market(all_equities, bulk_list, scan_count)

if results_df.empty:
    st.warning(
        "No market data returned. Please click **'Force Refresh All Data'** in the sidebar."
    )
else:
    df_sorted = results_df.sort_values(
        by="Score", ascending=False
    ).reset_index(drop=True)

    st.subheader(f"⭐ Top {top_picks_count} Stock Picks of the Day")

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
            col3.metric("RSI (14)", f"{row['RSI (14)']}")
            col4.metric("Market Cap", f"{row['Market Cap (Cr)']}")

            c1, c2 = st.columns([1, 2])
            with c1:
                st.write(f"**Sector:** {row['Sector']}")
                st.write(f"**P/E Ratio:** {row['P/E Ratio']}")
                st.write(f"**Volume Surge:** {row['Vol Surge']}")
                st.write(f"**Composite Score:** {row['Score']}")

            with c2:
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
                    height=220,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Complete Scanned Market Data Table")
    final_table_df = df_sorted.drop(columns=["HistDF"])
    st.dataframe(final_table_df, use_container_width=True)
