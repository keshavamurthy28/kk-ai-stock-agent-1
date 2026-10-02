import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Zerodha Portfolio Agent", page_icon="📊", layout="wide"
)

st.title("📊 Zerodha Portfolio Trend & Action Agent")
st.markdown(
    "Upload your downloaded Zerodha Console holdings **.xlsx** file to analyze actions."
)

uploaded_file = st.sidebar.file_uploader(
    "Upload Holdings (.xlsx or .csv)", type=["xlsx", "csv"]
)


def calculate_ema(series, span=50):
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze_stock(symbol):
    ticker = f"{symbol}.NS"
    df = yf.download(ticker, period="6m", interval="1d", progress=False)

    if df.empty or len(df) < 20:
        return "UNKNOWN", 0, 0, 0

    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"][ticker]
    else:
        close = df["Close"]

    rsi = calculate_rsi(close, 14).iloc[-1]
    ema_50 = calculate_ema(close, 50).iloc[-1]
    ltp = close.iloc[-1]

    if ltp > ema_50 and 45 < rsi < 65:
        signal = "ADD / BUY"
    elif ltp < ema_50 or rsi > 70:
        signal = "SELL / TRIM"
    else:
        signal = "HOLD"

    return (
        signal,
        round(float(ltp), 2),
        round(float(rsi), 2),
        round(float(ema_50), 2),
    )


if uploaded_file is not None:
    # Read raw Excel or CSV
    if uploaded_file.name.endswith(".xlsx"):
        df_raw = pd.read_excel(uploaded_file)
    else:
        df_raw = pd.read_csv(uploaded_file)

    # Detect header row automatically if title rows exist
    header_idx = None
    for idx, row in df_raw.iterrows():
        row_str = row.astype(str).str.lower().values
        if any(
            col in row_str
            for col in [
                "symbol",
                "instrument",
                "trading symbol",
                "tradingsymbol",
            ]
        ):
            header_idx = idx
            break

    if header_idx is not None and header_idx > 0:
        if uploaded_file.name.endswith(".xlsx"):
            holdings_df = pd.read_excel(uploaded_file, header=header_idx + 1)
        else:
            holdings_df = pd.read_csv(uploaded_file, header=header_idx + 1)
    else:
        holdings_df = df_raw

    holdings_df.columns = holdings_df.columns.astype(str).str.strip()

    st.subheader("📋 Portfolio Recommendations")

    results = []
    with st.spinner("Analyzing portfolio stocks..."):
        for idx, row in holdings_df.iterrows():
            # Find symbol from matching column names
            symbol = None
            for col in holdings_df.columns:
                if col.lower() in [
                    "symbol",
                    "instrument",
                    "trading symbol",
                    "tradingsymbol",
                    "stock",
                ]:
                    symbol = str(row[col]).strip()
                    break

            if (
                not symbol
                or symbol == "nan"
                or symbol.lower() in ["total", "subtotal", "none", ""]
            ):
                continue

            # Strip exchange prefix if present (e.g. NSE:INFY -> INFY)
            if ":" in symbol:
                symbol = symbol.split(":")[-1]

            qty = 0
            for col in holdings_df.columns:
                if "qty" in col.lower() or "quantity" in col.lower():
                    try:
                        qty = float(row[col])
                    except:
                        qty = 0
                    break

            avg_cost = 0
            for col in holdings_df.columns:
                if (
                    "avg" in col.lower()
                    or "cost" in col.lower()
                    or "buy" in col.lower()
                    or "price" in col.lower()
                ):
                    try:
                        avg_cost = float(row[col])
                    except:
                        avg_cost = 0
                    break

            try:
                signal, ltp, rsi, ema_50 = analyze_stock(symbol)
            except Exception:
                continue

            results.append(
                {
                    "Stock": symbol,
                    "Qty": qty,
                    "Buy Avg": avg_cost,
                    "LTP": ltp,
                    "RSI (14)": rsi,
                    "50 EMA": ema_50,
                    "Action Signal": signal,
                }
            )

    if results:
        res_df = pd.DataFrame(results)

        def color_signals(val):
            if "BUY" in str(val):
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif "SELL" in str(val):
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            return "background-color: #e2e3e5; color: #383d41;"

        st.dataframe(
            res_df.style.map(color_signals, subset=["Action Signal"]),
            use_container_width=True,
        )

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.success("🟢 **Stocks Recommended to ADD / BUY**")
            buys = res_df[res_df["Action Signal"] == "ADD / BUY"]
            if not buys.empty:
                st.table(buys[["Stock", "LTP", "RSI (14)", "50 EMA"]])
            else:
                st.write("No strong buy setups detected today.")

        with col2:
            st.error("🔴 **Stocks Recommended to SELL / TRIM**")
            sells = res_df[res_df["Action Signal"] == "SELL / TRIM"]
            if not sells.empty:
                st.table(sells[["Stock", "LTP", "RSI (14)", "50 EMA"]])
            else:
                st.write("No sell/breakdown alerts detected today.")
    else:
        st.error(
            "Could not parse stock symbols from the file. Please ensure the file contains valid holding symbols."
        )
else:
    st.info("👈 Upload your downloaded Zerodha `.xlsx` file in the sidebar.")
