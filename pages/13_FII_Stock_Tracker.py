import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Comprehensive FII / FPI Institutional Tracker", layout="wide"
)

st.title("🌐 Comprehensive FII / FPI & Institutional Stock Tracker")
st.caption(
    "Track Foreign Institutional Investor (FII/FPI) bulk/block deal anchors,"
    " tomorrow's advance breakout setups & inline SMC charts."
)

# Sidebar Ingestion & Filters
st.sidebar.header("⚙️ FII Data Ingestion & Filters")
uploaded_file = st.sidebar.file_uploader(
    "Upload Daily NSE Bulk/Block Deal CSV/Excel", type=["csv", "xlsx"]
)

default_data = [
    {"Date": "2026-11-13", "Symbol": "ETERNAL", "Client_Name": "VANGUARD FUNDS", "Deal_Type": "BUY", "Quantity": 3200000, "Price": 245.80, "Category": "FII"},
    {"Date": "2026-11-13", "Symbol": "TCS", "Client_Name": "GOLDMAN SACHS INVESTMENTS", "Deal_Type": "SELL", "Quantity": 450000, "Price": 2410.50, "Category": "FII"},
    {"Date": "2026-11-12", "Symbol": "RELIANCE", "Client_Name": "GOVERNMENT OF SINGAPORE", "Deal_Type": "BUY", "Quantity": 1500000, "Price": 1274.00, "Category": "FII"},
    {"Date": "2026-11-11", "Symbol": "INFY", "Client_Name": "NOMURA SINGAPORE LIMITED", "Deal_Type": "BUY", "Quantity": 900000, "Price": 1520.00, "Category": "FII"},
    {"Date": "2026-11-10", "Symbol": "HDFCBANK", "Client_Name": "BLACKROCK GLOBAL FUNDS", "Deal_Type": "BUY", "Quantity": 2100000, "Price": 805.00, "Category": "FII"},
    {"Date": "2026-11-09", "Symbol": "ICICIBANK", "Client_Name": "MORGAN STANLEY ASIA SINGAPORE", "Deal_Type": "BUY", "Quantity": 1800000, "Price": 1590.00, "Category": "FII"},
    {"Date": "2026-11-08", "Symbol": "SBIN", "Client_Name": "JP MORGAN FUNDS", "Deal_Type": "BUY", "Quantity": 1200000, "Price": 1115.00, "Category": "FII"},
    {"Date": "2026-11-07", "Symbol": "BHARTIARTL", "Client_Name": "ABERDEEN ASSET MANAGEMENT", "Deal_Type": "BUY", "Quantity": 850000, "Price": 1580.00, "Category": "FII"},
]

if uploaded_file is not None:
  if uploaded_file.name.endswith(".csv"):
    df_fii = pd.read_csv(uploaded_file)
  else:
    df_fii = pd.read_excel(uploaded_file)
else:
  df_fii = pd.DataFrame(default_data)

fii_clients = ["All Foreign Investors"] + sorted(
    df_fii["Client_Name"].unique().tolist()
)
selected_client = st.sidebar.selectbox(
    "🎯 Specific FII / Client Filter", fii_clients
)

if selected_client != "All Foreign Investors":
  df_fii = df_fii[df_fii["Client_Name"] == selected_client].reset_index(
      drop=True
  )


@st.cache_data(ttl=300)
def enrich_with_live_prices(df_in):
  symbols = [f"{s}.NS" for s in df_in["Symbol"].unique()]
  raw = yf.download(
      symbols, period="2d", interval="1d", group_by="ticker", progress=False
  )
  ltp_map = {}
  for sym in df_in["Symbol"].unique():
    t = f"{sym}.NS"
    try:
      if len(symbols) == 1:
        ltp_map[sym] = round(float(raw["Close"].dropna().iloc[-1]), 2)
      elif t in raw and not raw[t]["Close"].dropna().empty:
        ltp_map[sym] = round(float(raw[t]["Close"].dropna().iloc[-1]), 2)
      else:
        ltp_map[sym] = None
    except Exception:
      ltp_map[sym] = None

  df_enriched = df_in.copy()
  df_enriched["Live LTP"] = df_enriched["Symbol"].map(ltp_map)
  df_enriched["vs FII Anchor %"] = np.where(
      df_enriched["Live LTP"].notna(),
      ((df_enriched["Live LTP"] - df_enriched["Price"]) / df_enriched["Price"])
      * 100,
      0.0,
  ).round(2)
  df_enriched["Deal Value (Cr)"] = (
      (df_enriched["Quantity"] * df_enriched["Price"]) / 1e7
  ).round(2)
  df_enriched["Tomorrow Setup"] = np.where(
      (df_enriched["Deal_Type"] == "BUY")
      & (df_enriched["vs FII Anchor %"] >= -1.5)
      & (df_enriched["vs FII Anchor %"] <= 4.0),
      "🔥 FII SUPPORT ZONE (Ready for Bounce)",
      np.where(
          df_enriched["Deal_Type"] == "SELL",
          "🔴 FII DISTRIBUTION OVERHEAD",
          "🟢 FII IN PROFIT / TRENDING",
      ),
  )
  return df_enriched


def render_fii_anchor_chart(symbol_clean, fii_anchor_price, deal_type):
  ticker = f"{symbol_clean}.NS"
  df_c = yf.Ticker(ticker).history(period="5d", interval="15m", auto_adjust=True)
  if df_c is None or df_c.empty:
    st.warning(f"Intraday chart unavailable for {symbol_clean}.")
    return

  df_c["EMA20"] = df_c["Close"].ewm(span=20, adjust=False).mean()
  df_c["VWAP"] = (
      (((df_c["High"] + df_c["Low"] + df_c["Close"]) / 3.0) * df_c["Volume"])
      .groupby(df_c.index.date)
      .cumsum()
      / df_c["Volume"].groupby(df_c.index.date).cumsum().replace(0, np.nan)
  )
  df_c = df_c.tail(85)

  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=[0.76, 0.24],
  )
  fig.add_trace(
      go.Candlestick(
          x=df_c.index,
          open=df_c["Open"],
          high=df_c["High"],
          low=df_c["Low"],
          close=df_c["Close"],
          name=symbol_clean,
          increasing_line_color="#00E676",
          decreasing_line_color="#FF5252",
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df_c.index,
          y=df_c["VWAP"],
          mode="lines",
          name="VWAP",
          line=dict(color="#FFD700", width=1.5),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df_c.index,
          y=df_c["EMA20"],
          mode="lines",
          name="20 EMA",
          line=dict(color="#29B6F6", width=1.2),
      ),
      row=1,
      col=1,
  )

  # Plot Institutional FII Deal Price Anchor Line
  anchor_color = "#00E676" if deal_type == "BUY" else "#FF5252"
  fig.add_hline(
      y=fii_anchor_price,
      line_dash="dash",
      line_color=anchor_color,
      annotation_text=f"🏦 FII {deal_type} Anchor: ₹{fii_anchor_price:,.2f}",
      annotation_position="top left",
      row=1,
      col=1,
  )

  vol_colors = [
      "#00E676" if c >= o else "#FF5252"
      for o, c in zip(df_c["Open"], df_c["Close"])
  ]
  fig.add_trace(
      go.Bar(
          x=df_c.index,
          y=df_c["Volume"],
          name="Volume",
          marker_color=vol_colors,
      ),
      row=2,
      col=1,
  )

  fig.update_layout(
      title=(
          f"📈 {symbol_clean} — Live SMC Chart with FII Institutional Price"
          f" Anchor (₹{fii_anchor_price:,.2f})"
      ),
      template="plotly_dark",
      height=500,
      xaxis_rangeslider_visible=False,
      margin=dict(l=10, r=50, t=45, b=20),
  )
  st.plotly_chart(fig, use_container_width=True)


df_view = enrich_with_live_prices(df_fii)

# KPI Metrics
k1, k2, k3 = st.columns(3)
k1.metric("Total Filtered Deals", len(df_view))
k2.metric("FII Buy Signals", len(df_view[df_view["Deal_Type"] == "BUY"]))
k3.metric("Unique FII Entities", df_view["Client_Name"].nunique())

st.markdown("---")

# Tomorrow's Advance FII Anchor Radar
st.subheader("🔮 Tomorrow's Advance FII Price-Anchor Radar")
fii_buys = df_view[df_view["Deal_Type"] == "BUY"].sort_values(
    by="Deal Value (Cr)", ascending=False
)
if not fii_buys.empty:
  b1 = fii_buys.iloc[0]
  st.success(
      f"**#1 HIGHEST CONVICTION FII ACCUMULATION: {b1['Symbol']} ({b1['Client_Name']})**\n\n"
      f"• **Deal Size:** ₹{b1['Deal Value (Cr)']:,.2f} Cr @ **FII Anchor Price:** ₹{b1['Price']:,.2f}\n"
      f"• **Current Live LTP:** ₹{b1['Live LTP']} ({b1['vs FII Anchor %']:+.2f}% from FII cost) → **{b1['Tomorrow Setup']}**"
  )

st.markdown("---")

# Clickable FII Deal Feed Table
st.subheader("📄 FII / FPI Deal Feed & Live Anchor Comparison (Click Any Row for Graph)")
st.caption("Select any row on the left checkbox to inspect its candlestick chart plotted directly against the FII institutional deal price.")

deal_event = st.dataframe(
    df_view,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Price": st.column_config.NumberColumn("FII Anchor ₹", format="₹%.2f"),
        "Live LTP": st.column_config.NumberColumn("Live LTP ₹", format="₹%.2f"),
        "vs FII Anchor %": st.column_config.NumberColumn(format="%+.2f%%"),
        "Deal Value (Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
    },
)

sel = deal_event.selection.rows
chosen_row = df_view.iloc[sel[0]] if sel else df_view.iloc[0]

st.markdown("---")
render_fii_anchor_chart(
    chosen_row["Symbol"], chosen_row["Price"], chosen_row["Deal_Type"]
)
