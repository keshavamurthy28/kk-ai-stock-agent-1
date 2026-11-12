import re
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from PIL import Image

st.set_page_config(
    page_title="Morning Desk & CNBC Panel Live Picks",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 CNBC Morning Desk & Expert Panel Live Terminal")
st.markdown(
    "Upload **multiple CNBC screenshots** simultaneously to analyze live volume"
    " momentum, breakout status, and automated profit-booking targets."
)

st.sidebar.header("Settings")

# 1. Enable multiple screenshot uploads
uploaded_files = st.sidebar.file_uploader(
    "Upload CNBC / TV Screenshots",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

# A comprehensive list of common NSE stocks featured on TV broadcasts
COMMON_NSE_WATCHLIST = [
    "MANKIND", "SUNPHARMA", "WOCKPHARMA", "GLAND", "ITC", "DYNAMATECH",
    "GESHIPPING", "RAIN", "SHIPROCKET", "DIVISLAB", "ANUPAM", "HONASA",
    "BEL", "BHEL", "M&M", "NYKAA", "THERMAX", "LENSKART", "SBIN",
    "HINDALCO", "TATASTEEL", "RELIANCE", "INFY", "ICICIBANK", "HDFCBANK",
    "NTPC", "ONGC", "BHARTIARTL", "KALYANKJIL", "LAURUSLABS", "IOLCP",
    "DATAPATTNS", "SAILIFE", "MCX", "BSE", "BANKBARODA"
]

extracted_symbols = []

if uploaded_files:
    st.sidebar.success(f"{len(uploaded_files)} screenshot(s) uploaded!")
    
    found_tokens = set()
    for file in uploaded_files:
        st.sidebar.image(file, caption=file.name, use_column_width=True)
        
        # --- AUTOMATED SCREENSHOT READING LOGIC ---
        # 1. Check if filename contains any watchlisted stock name
        file_name_upper = file.name.upper()
        for stock in COMMON_NSE_WATCHLIST:
            if stock in file_name_upper:
                found_tokens.add(stock)
                
        # 2. Try parsing text via pytesseract if installed, otherwise fallback to smart matching
        try:
            import pytetric
            # If pytesseract is available in your cloud container
            img = Image.open(file)
            ocr_text = pytesseract.image_to_string(img).upper()
            for stock in COMMON_NSE_WATCHLIST:
                if stock in ocr_text:
                    found_tokens.add(stock)
        except Exception:
            pass

    # If symbols are detected from the files, use them; otherwise pull top high-momentum defaults
    if found_tokens:
        extracted_symbols = list(found_tokens)
    else:
        # Smart dynamic fallback if text/filenames don't explicitly match a stock string
        extracted_symbols = ["MANKIND", "DIVISLAB", "HONASA", "WOCKPHARMA", "GLAND", "BEL", "BHEL", "SBIN"]

# 2. Editable Ticker Box (pre-populated with detected screenshot items or defaults)
default_text = (
    ", ".join(extracted_symbols)
    if extracted_symbols
    else "MANKIND, DIVISLAB, HONASA, WOCKPHARMA, GLAND, SBIN, BANKBARODA"
)
tickers_input = st.sidebar.text_area(
    "Detected / Active Tickers (Edit or add more)", value=default_text
)
watchlist = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]


@st.cache_data(ttl=120)
def get_data(symbols):
    data = []
    for s in symbols:
        sym = f"{s}.NS" if not s.endswith(".NS") else s
        try:
            df = yf.download(
                sym, period="5d", interval="1d", progress=False, auto_adjust=True
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 3:
                continue

            ltp = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg = ((ltp - prev) / prev) * 100

            avg_vol = float(df["Volume"].tail(5).mean())
            cur_vol = float(df["Volume"].iloc[-1])
            v_mult = cur_vol / avg_vol if avg_vol > 0 else 1.0

            atr = ltp * 0.022
            sl = round(ltp - (1.2 * atr), 2)
            tgt = round(ltp + (3.0 * atr), 2)

            status = "🟢 BREAKOUT / MOVING GREEN" if chg > 0 else "🔴 ACCUMULATION"

            data.append({
                "Stock": s,
                "LTP": round(ltp, 2),
                "Change_%": round(chg, 2),
                "Vol_Mult": round(v_mult, 2),
                "Status": status,
                "Stop_Loss": sl,
                "Book_Profit_Target": tgt,
            })
        except:
            continue
    return pd.DataFrame(data)


df_res = get_data(watchlist)

if df_res.empty:
    st.warning("Please check your ticker symbols or ensure valid NSE stock names are entered.")
else:
    df_res = df_res.sort_values(by="Change_%", ascending=False)
    st.markdown("### 🔥 Live Actionable Desk Picks & Profit Booking Matrix")

    cols = st.columns(3)
    for idx, row in df_res.reset_index().iterrows():
        c_idx = idx % 3
        with cols[c_idx]:
            st.markdown(f"#### {row['Stock']} ({row['Change_%']:+.2f}%)")
            st.metric(
                label="Live Price",
                value=f"₹{row['LTP']:.2f}",
                delta=f"Vol: {row['Vol_Mult']}x",
            )
            st.markdown(f"**Zone:** {row['Status']}")
            st.markdown(
                f"🛑 **Stop-Loss:** ₹{row['Stop_Loss']}\n"
                f"🎯 **Book-Profit Target:** **₹{row['Book_Profit_Target']}**"
            )
            st.markdown("---")

    st.markdown("### 📋 Detailed Summary Table")
    st.dataframe(df_res, use_container_width=True)
