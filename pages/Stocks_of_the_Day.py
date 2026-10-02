import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Daily Stock Scanner", page_icon="📅", layout="wide"
)

st.title("📅 NSE Top Stocks of the Day")
st.markdown(
    "Automated daily analysis combining **Fundamental Valuation** (P/E, Market Cap, Dividend Yield) with **Technical Indicators** (RSI, 20/50 EMA, Volume Surge)."
)

# Core Watchlist of major liquid NSE stocks
DEFAULT_SYMBOLS = [
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
]


@st.cache_data(ttl=900)  # Cache results for 15 minutes to speed up loading
def fetch_daily_stock_details(symbols):
    data_list = []

    for sym in symbols:
        ticker_str = (
            f"{sym.upper()}.NS" if not sym.endswith(".NS") else sym.upper()
        )
        t = yf.Ticker(ticker_str)

        # Download 6 months of daily historical price data
        hist = t.history(period="6m", interval="1d")
        if hist.empty or len(hist) < 50:
            continue

        close = hist["Close"]
        volume = hist["Volume"]

        # Technical Calculations
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

        # Fundamentals Retrieval
        try:
            info = t.info
            mcap = info.get("marketCap", 0) / 1e7  # Convert to Cr (INR)
            pe = info.get("trailingPE", 0.0) or info.get("forwardPE", 0.0)
            div_yield = (info.get("dividendYield", 0.0) or 0.0) * 100
            sector = info.get("sector", "N/A")
            company_name = info.get("shortName", sym)
        except Exception:
            mcap, pe, div_yield, sector, company_name = 0, 0, 0, "N/A", sym

        # Scoring & Signal Allocation
        score = 0
        if latest_price > ema_20:
            score += 1
        if ema_20 > ema_50:
            score += 1
        if 30 <= rsi <= 65:
            score += 1
        if vol_surge >= 1.2:
            score += 1
        if pe > 0 and pe < 35:
            score += 1

        if rsi < 35:
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
                "Div Yield (%)": f"{div_yield:.2f}%" if div_yield else "0.00%",
                "Vol Surge": f"{vol_surge:.2f}x",
                "Action Signal": signal,
                "Score": score,
                "HistDF": hist,
            }
        )

    return pd.DataFrame(data_list)


# Sidebar Options
st.sidebar.header("🔍 Stock Selection Filters")
selected_symbols = st.sidebar.multiselect(
    "Select Stocks to Analyze:",
    options=[
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
    ],
    default=DEFAULT_SYMBOLS[:5],  # Top 5 by default
)

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()

with st.spinner("Fetching fundamentals & technicals from NSE..."):
    df_results = fetch_daily_stock_details(selected_symbols)

if df_results.empty:
    st.warning("No stock data returned. Please select symbols from the sidebar.")
else:
    # Sort by highest setup score
    df_sorted = df_results.sort_values(
        by="Score", ascending=False
    ).reset_index(drop=True)

    st.subheader("⭐ Top 5 Stocks of the Day")

    # Display Top 5 Stock Cards
    top_5 = df_sorted.head(5)

    for idx, row in top_5.iterrows():
        with st.expander(
            f"#{idx+1} {row['Symbol']} — {row['Company']} ({row['Action Signal']})",
            expanded=(idx == 0),
        ):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Price", f"₹{row['Price (₹)']}", f"{row['Change (%)']}%")
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
                # Mini chart
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

    # Complete Summary Data Table
    st.subheader("📋 Overview Comparison Table")
    display_df = df_sorted.drop(columns=["HistDF"])
    st.dataframe(display_df, use_container_width=True)
