import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# Configure page layout
st.set_page_config(
    page_title="NSE Dynamic Stock Scanner", page_icon="📅", layout="wide"
)

st.title("📅 NSE Top Stocks of the Day (Live Nifty 50 Fetch)")
st.markdown(
    "Automated dynamic scanner pulling live constituents directly from **Nifty 50** to evaluate Fundamental & Technical setups."
)

# -------------------------------------------------------------------
# DYNAMIC NIFTY 50 TICKER RETRIEVAL
# -------------------------------------------------------------------


@st.cache_data(ttl=86400)  # Cache index list for 24 hours
def get_nifty50_tickers():
    """Fetches the official Nifty 50 stock list dynamically with custom headers to prevent 403 blocks."""
    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(response.text)
        nifty_table = tables[2]  # Nifty 50 constituents table
        symbols = nifty_table["Symbol"].tolist()
        return [str(sym).strip() for sym in symbols if str(sym).strip()]
    except Exception:
        # Fallback list if external fetch fails
        return [
            "RELIANCE",
            "HDFCBANK",
            "BHARTIARTL",
            "ICICIBANK",
            "TCS",
            "TATAMOTORS",
            "SBIN",
            "INFY",
            "LT",
            "AXISBANK",
            "KOTAKBANK",
            "HINDUNILVR",
            "ITC",
            "BAJFINANCE",
            "MARUTI",
        ]


# -------------------------------------------------------------------
# STOCK DATA FETCH & TECHNICAL ANALYSIS
# -------------------------------------------------------------------


@st.cache_data(ttl=900)  # Cache analysis results for 15 minutes
def fetch_daily_stock_details(symbols):
    data_list = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sym in enumerate(symbols):
        status_text.text(
            f"Scanning Nifty 50 constituent [{idx+1}/{len(symbols)}]: {sym}..."
        )
        ticker_str = (
            f"{sym.upper()}.NS" if not sym.endswith(".NS") else sym.upper()
        )

        try:
            t = yf.Ticker(ticker_str)
            hist = t.history(period="6m", interval="1d")

            if hist.empty or len(hist) < 50:
                progress_bar.progress((idx + 1) / len(symbols))
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            # Technical Indicators
            latest_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            day_change_pct = ((latest_price - prev_price) / prev_price) * 100

            ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])

            # RSI Calculation
            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # Volume Surge Ratio
            avg_vol = volume.tail(20).mean()
            vol_surge = (
                (float(volume.iloc[-1]) / avg_vol) if avg_vol > 0 else 1.0
            )

            # Fundamental Data
            try:
                info = t.info
                mcap = info.get("marketCap", 0) / 1e7  # Cr INR
                pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
                div_yield = (info.get("dividendYield", 0.0) or 0.0) * 100
                sector = info.get("sector", "N/A")
                company_name = info.get("shortName", sym)
            except Exception:
                mcap, pe, div_yield, sector, company_name = 0, 0, 0, "N/A", sym

            # Scoring Logic
            score = 0
            if latest_price > ema_20:
                score += 1
            if ema_20 > ema_50:
                score += 1
            if 35 <= rsi <= 65:
                score += 1
            if vol_surge >= 1.2:
                score += 1
            if pe > 0 and pe < 35:
                score += 1

            if rsi < 32:
                signal = "🟢 OVERSOLD BUY (Reversal)"
            elif score >= 4:
                signal = "🔥 STRONG BUY (Trend + Vol)"
            elif score == 3:
                signal = "📈 ACCUMULATE (Positive)"
            elif latest_price < ema_50 or rsi > 70:
                signal = "🔴 TRIM / BEARISH"
            else:
                signal = "⚪ NEUTRAL / HOLD"

            data_list.append(
                {
                    "Symbol": sym,
                    "Company": company_name,
                    "Sector": sector,
                    "Price (₹)": round(latest_price, 2),
                    "Change (%)": round(day_change_pct, 2),
                    "RSI (14)": round(rsi, 1),
                    "20 EMA": round(ema_20, 2),
                    "50 EMA": round(ema_50, 2),
                    "P/E Ratio": round(pe, 1) if pe else "N/A",
                    "Market Cap (Cr)": (
                        f"₹{mcap:,.0f} Cr" if mcap > 0 else "N/A"
                    ),
                    "Div Yield (%)": f"{div_yield:.2f}%"
                    if div_yield
                    else "0.00%",
                    "Vol Surge": f"{vol_surge:.2f}x",
                    "Action Signal": signal,
                    "Score": score,
                    "HistDF": hist,
                }
            )
        except Exception:
            pass

        progress_bar.progress((idx + 1) / len(symbols))

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(data_list)


# -------------------------------------------------------------------
# APP CONTROLS & RENDER
# -------------------------------------------------------------------

st.sidebar.header("⚙️ Scanner Settings")

# Fetch full Nifty 50 list dynamically
nifty_symbols = get_nifty50_tickers()
st.sidebar.write(
    f"**Live Index:** Nifty 50 ({len(nifty_symbols)} Stocks Loaded)"
)

top_n_picks = st.sidebar.slider("Number of Top Picks to Display", 3, 10, 5)

if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Executing dynamic Nifty 50 market scan..."):
    df_results = fetch_daily_stock_details(nifty_symbols)

if df_results.empty:
    st.error(
        "Could not pull stock data. Please click 'Force Refresh Data' in the sidebar."
    )
else:
    df_sorted = df_results.sort_values(
        by="Score", ascending=False
    ).reset_index(drop=True)

    st.subheader(f"⭐ Top {top_n_picks} Stocks of the Day (Nifty 50)")

    top_picks_df = df_sorted.head(top_n_picks)

    for idx, row in top_picks_df.iterrows():
        with st.expander(
            f"#{idx+1} {row['Symbol']} — {row['Company']} ({row['Action Signal']})",
            expanded=(idx == 0),
        ):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Current Price", f"₹{row['Price (₹)']}", f"{row['Change (%)']}%"
            )
            col2.metric("P/E Ratio", f"{row['P/E Ratio']}")
            col3.metric("RSI (14)", f"{row['RSI (14)']}")
            col4.metric("Market Cap", f"{row['Market Cap (Cr)']}")

            c1, c2 = st.columns([1, 2])
            with c1:
                st.write(f"**Sector:** {row['Sector']}")
                st.write(f"**Dividend Yield:** {row['Div Yield (%)']}")
                st.write(f"**20 EMA:** ₹{row['20 EMA']}")
                st.write(f"**50 EMA:** ₹{row['50 EMA']}")
                st.write(f"**Volume Surge:** {row['Vol Surge']}")

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
    st.subheader("📋 Complete Nifty 50 Comparison Table")
    display_df = df_sorted.drop(columns=["HistDF"])
    st.dataframe(display_df, use_container_width=True)
