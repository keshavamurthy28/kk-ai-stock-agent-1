import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Morning Desk & CNBC Panel Live Picks",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 CNBC Morning Desk & Expert Panel Live Terminal")
st.markdown(
    "Upload a CNBC screenshot or enter tickers manually to track live volume"
    " momentum, breakout status, and automated profit-booking targets."
)

st.sidebar.header("Settings")

# 1. Added File Uploader for Screenshots
uploaded_image = st.sidebar.file_uploader(
    "Upload CNBC / TV Screenshot", type=["png", "jpg", "jpeg"]
)
if uploaded_image is not None:
  st.sidebar.image(
      uploaded_image, caption="Uploaded TV Screen", use_column_width=True
  )
  st.sidebar.info(
      "Screenshot received! (Tip: If OCR isn't active, use the text box below"
      " to type the stocks visible in your photo)."
  )

# 2. Ticker Input Box
tickers_input = st.sidebar.text_area(
    "Enter Tickers (comma separated)",
    value="MANKIND, DIVISLAB, HONASA, WOCKPHARMA, GLAND, SBIN",
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
  st.warning(
      "Please check your ticker symbols or enter valid NSE stock names (e.g.,"
      " MANKIND, DIVISLAB)."
  )
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
