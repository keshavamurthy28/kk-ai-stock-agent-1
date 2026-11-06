import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Zerodha Portfolio Analysis", layout="wide")

st.title("📊 Zerodha Portfolio Trend & Action Agent")
st.write(
    "Upload your Zerodha Console holdings `.xlsx` file for customized rules,"
    " date filtering, and visual charts."
)

# Sidebar Parameters for Customizable Rules & Dates
st.sidebar.header("⚙️ Customize Trading Rules")
rsi_overbought = st.sidebar.slider("RSI Overbought (Sell Limit)", 60, 80, 70)
rsi_oversold = st.sidebar.slider("RSI Oversold (Dip Limit)", 20, 40, 30)
ema_fast_p = st.sidebar.number_input("Fast EMA Period", value=20)
ema_slow_p = st.sidebar.number_input("Slow EMA Period", value=50)

st.sidebar.markdown("---")
st.sidebar.header("📅 Date Range Selector")
default_start = datetime.date.today() - datetime.timedelta(days=180)
default_end = datetime.date.today()
start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date", value=default_end)


def clean_symbol(symbol):
  s = str(symbol).strip().upper()
  s = s.replace("-EQ", "").replace("-E", "").replace(".NS", "")
  return f"{s}.NS"


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = delta.where(delta > 0, 0).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def fetch_and_analyze(symbol, start_d, end_d):
  ticker_symbol = clean_symbol(symbol)
  # Fetch data dynamically using explicit start and end dates to avoid static fallbacks
  df = yf.download(
      ticker_symbol,
      start=start_d.strftime("%Y-%m-%d"),
      end=end_d.strftime("%Y-%m-%d"),
      progress=False,
  )

  # Handle multi-index columns if returned by newer yfinance versions
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

  if df.empty or len(df) < min(ema_slow_p, 10):
    return None, "NO DATA", 0, 0, 0

  df[f"EMA_{ema_fast_p}"] = (
      df["Close"].ewm(span=ema_fast_p, adjust=False).mean()
  )
  df[f"EMA_{ema_slow_p}"] = (
      df["Close"].ewm(span=ema_slow_p, adjust=False).mean()
  )
  df["RSI"] = calculate_rsi(df["Close"], period=14)

  latest = df.iloc[-1]
  ltp = float(latest["Close"])
  rsi_val = float(latest["RSI"])
  ema_fast_val = float(latest[f"EMA_{ema_fast_p}"])
  ema_slow_val = float(latest[f"EMA_{ema_slow_p}"])

  if ltp < ema_slow_val or rsi_val >= rsi_overbought:
    signal = "SELL / TRIM"
  elif (
      ltp > ema_slow_val
      and ema_fast_val > ema_slow_val
      and 45 <= rsi_val < rsi_overbought
  ):
    signal = "BUY / ACCUMULATE"
  elif (
      abs(ltp - ema_slow_val) / ema_slow_val <= 0.02
      and rsi_val <= (rsi_oversold + 10)
  ):
    signal = "DIP BUY"
  else:
    signal = "HOLD"

  return df, signal, ltp, rsi_val, ema_slow_val


def build_plotly_chart(df, symbol, signal):
  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.08,
      subplot_titles=(
          f"{symbol} — Daily Candlestick with {ema_fast_p} & {ema_slow_p} EMA",
          "14-Day RSI Indicator",
      ),
      row_width=[0.3, 0.7],
  )

  # Candlestick
  fig.add_trace(
      go.Candlestick(
          x=df.index,
          open=df["Open"],
          high=df["High"],
          low=df["Low"],
          close=df["Close"],
          name="OHLC Price",
      ),
      row=1,
      col=1,
  )

  # Fast & Slow EMA
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df[f"EMA_{ema_fast_p}"],
          line=dict(color="orange", width=1.5),
          name=f"{ema_fast_p} EMA",
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df[f"EMA_{ema_slow_p}"],
          line=dict(color="blue", width=2),
          name=f"{ema_slow_p} EMA",
      ),
      row=1,
      col=1,
  )

  # RSI Line
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["RSI"],
          line=dict(color="purple", width=2),
          name="RSI (14)",
      ),
      row=2,
      col=1,
  )

  # RSI Reference Lines
  fig.add_hline(
      y=rsi_overbought,
      line_dash="dash",
      line_color="red",
      row=2,
      col=1,
      annotation_text="Overbought Zone",
  )
  fig.add_hline(
      y=rsi_oversold,
      line_dash="dash",
      line_color="green",
      row=2,
      col=1,
      annotation_text="Oversold Zone",
  )
  fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)

  fig.update_layout(
      height=550, xaxis_rangeslider_visible=False, template="plotly_white"
  )
  return fig


# Upload Section
uploaded_file = st.file_uploader(
    "Upload Holdings (.xlsx or .csv)", type=["xlsx", "csv"]
)

if uploaded_file:
  df_raw = (
      pd.read_excel(uploaded_file)
      if uploaded_file.name.endswith(".xlsx")
      else pd.read_csv(uploaded_file)
  )
  symbol_col = [
      c
      for c in df_raw.columns
      if "symbol" in c.lower()
      or "instrument" in c.lower()
      or "stock" in c.lower()
  ][0]

  results = []
  stock_data_map = {}

  with st.spinner("Analyzing portfolio against custom trading rules & dates..."):
    for sym in df_raw[symbol_col].dropna().unique():
      hist_df, signal, ltp, rsi_val, ema_val = fetch_and_analyze(
          sym, start_date, end_date
      )
      results.append({
          "Stock": sym,
          "LTP": round(ltp, 2),
          "RSI (14)": round(rsi_val, 2),
          f"{ema_slow_p} EMA": round(ema_val, 2),
          "Action Signal": signal,
      })
      if hist_df is not None:
        stock_data_map[sym] = (hist_df, signal)

  res_df = pd.DataFrame(results)
  st.subheader("📋 Analysis Results")
  st.dataframe(res_df, use_container_width=True)

  # Interactive Visual Graph Inspector
  st.markdown("---")
  st.subheader("📈 Pictured Technical Graph Inspector")
  selected_stock = st.selectbox(
      "Select a stock to view technical chart & indicator lines:",
      list(stock_data_map.keys()),
  )

  if selected_stock:
    chart_df, stock_signal = stock_data_map[selected_stock]
    st.info(f"**Current Signal for {selected_stock}:** `{stock_signal}`")
    fig = build_plotly_chart(chart_df, selected_stock, stock_signal)
    st.plotly_chart(fig, use_container_width=True)
