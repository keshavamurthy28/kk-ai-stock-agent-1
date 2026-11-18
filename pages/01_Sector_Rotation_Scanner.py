from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Institutional Sector Rotation & Macro Pulse", layout="wide"
)

# --- CLEAN SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.markdown(
    "- 🗺️ **[Sector Rotation & Macro Pulse](Sector_Rotation_Scanner)**"
)
st.sidebar.markdown("- ⚡ **[Smart Money Flow Terminal](Smart_Money_Pulse)**")
st.sidebar.markdown(
    "- 🌙 **[Night-Before Prep & Coiling](Night_Before_Prep_Scanner)**"
)
st.sidebar.markdown(
    "- 🎯 **[Live Super-Signal Triggers](Matched_Super_Signal_Page)**"
)
st.sidebar.markdown("---")

if "nav_sector" not in st.session_state:
  st.session_state.nav_sector = None
if "nav_stock" not in st.session_state:
  st.session_state.nav_stock = None


def reset_to_all():
  st.session_state.nav_sector = None
  st.session_state.nav_stock = None


MACRO_INDICES = {
    "NIFTY 50": "^NSEI",
    "BSE SENSEX": "^BSESN",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
}

# Complete 31+ Sector Dictionary aligned with Trendlyne
TRENDLYNE_31_SECTORS = {
    "Telecommunications": ["BHARTIARTL.NS", "IDEA.NS", "TATACOMM.NS"],
    "Telecom Services": ["INDUSTOWER.NS", "NELCO.NS"],
    "Media": ["ZEEL.NS", "SUNTV.NS", "PVRINOX.NS"],
    "Textiles Apparels": ["PAGEIND.NS", "KPRMILL.NS", "TRIDENT.NS"],
    "Consumer Durables": ["TITAN.NS", "ASIANPAINT.NS", "DIXON.NS", "AMBER.NS"],
    "Hotels Restaurants": ["INDHOTEL.NS", "CHALET.NS", "EIHOTEL.NS"],
    "Commercial Services": ["CDSL.NS", "MCX.NS", "CAMS.NS"],
    "Retailing": ["DMART.NS", "TRENT.NS", "V2RETAIL.NS"],
    "Fertilizers": ["DEEPAKFERT.NS", "CHAMBLFERT.NS", "COROMANDEL.NS"],
    "Software & Services": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS"],
    "Metals & Mining": [
        "TATASTEEL.NS",
        "HINDALCO.NS",
        "JSWSTEEL.NS",
        "VEDL.NS",
    ],
    "Automobiles & Anc": [
        "MARUTI.NS",
        "TATAMOTORS.NS",
        "M&M.NS",
        "BAJAJ-AUTO.NS",
    ],
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
    ],
    "Energy & Oil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
    "Utilities": ["TATAPOWER.NS", "ADANIPOWER.NS", "NHPC.NS", "SJVN.NS"],
    "Healthcare": [
        "SUNPHARMA.NS",
        "CIPLA.NS",
        "DRREDDY.NS",
        "DIVISLAB.NS",
        "MAXHEALTH.NS",
    ],
    "Chemicals": ["UPL.NS", "PIIND.NS", "NAVINFLUOR.NS", "DEEPAKNITR.NS"],
    "Realty": ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS"],
    "Transportation": ["INDIGO.NS", "CONCOR.NS", "DELHIVERY.NS"],
    "FMCG": [
        "HINDUNILVR.NS",
        "ITC.NS",
        "BRITANNIA.NS",
        "NESTLEIND.NS",
        "DABUR.NS",
    ],
    "Cement & Construction": ["ULTRACEMCO.NS", "AMBUJACEM.NS", "GRASIM.NS"],
    "Hardware Technology": ["HFCL.NS", "VOLTAS.NS", "BLUESTARCO.NS"],
    "Forest Materials": ["CENTURYPLY.NS", "JKPAPER.NS"],
    "Diversified": ["ADANIENT.NS", "ITC.NS"],
    "Food Beverages": ["TATACONSUM.NS", "VBL.NS", "MCDOWELL-N.NS"],
    "General Industrials": ["SIEMENS.NS", "ABB.NS", "CUMMINSIND.NS"],
    "Defense & Aerospace": ["HAL.NS", "BEL.NS", "MAZDOCK.NS", "COCHINSHIP.NS"],
    "Capital Goods": ["LT.NS", "BHEL.NS", "BEL.NS"],
    "Packaging": ["Uflex.NS", "EPL.NS"],
    "Leather & Footwear": ["BATAINDIA.NS", "RELAXO.NS"],
    "Sugar": ["BALRAMCHIN.NS", "TRIVENI.NS", "RENUKA.NS"],
}


@st.cache_data(ttl=900)
def fetch_complete_sector_breadth():
  all_syms = list(MACRO_INDICES.values()) + [
      t for stocks in TRENDLYNE_31_SECTORS.values() for t in stocks
  ]
  raw = yf.download(
      all_syms,
      period="3mo",
      interval="1d",
      group_by="ticker",
      progress=False,
      threads=True,
  )

  index_metrics = {}
  for name, symbol in MACRO_INDICES.items():
    try:
      df = raw[symbol]["Close"].dropna()
      if not df.empty:
        ltp, prev = float(df.iloc[-1]), float(df.iloc[-2])
        chg = ((ltp - prev) / prev) * 100
        index_metrics[name] = {"LTP": round(ltp, 2), "Chg%": round(chg, 2)}
    except Exception:
      pass

  stock_records = []
  sector_summary_rows = []
  ohlcv_store = {}

  for sector, tickers in TRENDLYNE_31_SECTORS.items():
    sec_day_changes = []
    sec_advances = 0
    sec_declines = 0
    valid_stocks_count = 0

    for ticker in tickers:
      try:
        df = raw[ticker].dropna()
        if len(df) < 15:
          continue
        sym = ticker.replace(".NS", "")
        ohlcv_store[sym] = df

        close, vol = df["Close"], df["Volume"]
        ltp = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        day_chg = ((ltp - prev) / prev) * 100
        week_chg = (
            ((ltp / float(close.iloc[-6]) - 1) * 100)
            if len(close) >= 6
            else 0.0
        )
        rvol = (
            float(vol.iloc[-1] / vol.iloc[-21:-1].mean())
            if len(vol) >= 21
            else 1.0
        )

        sec_day_changes.append(day_chg)
        valid_stocks_count += 1
        if day_chg >= 0:
          sec_advances += 1
        else:
          sec_declines += 1

        stock_records.append({
            "Symbol": sym,
            "Sector": sector,
            "LTP": round(ltp, 2),
            "Day %": round(day_chg, 2),
            "Week %": round(week_chg, 2),
            "RVOL (x)": round(rvol, 2),
        })
      except Exception:
        continue

    if valid_stocks_count > 0:
      avg_day_chg = np.mean(sec_day_changes)
      adv_dec_ratio = (
          round(sec_advances / sec_declines, 2)
          if sec_declines > 0
          else float(sec_advances)
      )
      momentum_score = round(
          50 + (avg_day_chg * 5) + ((sec_advances - sec_declines) * 2), 2
      )

      sector_summary_rows.append({
          "Sector": sector,
          "No. of Companies": valid_stocks_count,
          "Advances": sec_advances,
          "Declines": sec_declines,
          "Advances/Declines Ratio": adv_dec_ratio,
          "Day Change %": round(avg_day_chg, 2),
          "Sector Momentum Score": max(0.0, min(100.0, momentum_score)),
      })

  return (
      index_metrics,
      pd.DataFrame(stock_records),
      pd.DataFrame(sector_summary_rows),
      ohlcv_store,
  )


with st.spinner("Syncing live 31+ sector performance metrics..."):
  (
      index_metrics,
      df_stocks,
      df_sector_table,
      ohlcv_store,
  ) = fetch_complete_sector_breadth()

# Render Top Macro Bar
macro_cols = st.columns(len(MACRO_INDICES))
for i, (name, _) in enumerate(MACRO_INDICES.items()):
  with macro_cols[i]:
    if name in index_metrics:
      st.metric(
          name,
          f"{index_metrics[name]['LTP']:,.2f}",
          f"{index_metrics[name]['Chg%']:+.2f}%",
      )

st.markdown("---")

b1, _ = st.columns([1.2, 4])
with b1:
  if st.button("🏠 All Sectors", use_container_width=True):
    reset_to_all()
    st.rerun()

st.divider()

# =========================================================
# LEVEL 3 VIEW: STOCK TECHNICAL CHART TERMINAL
# =========================================================
if st.session_state.nav_stock:
  sym = st.session_state.nav_stock
  row = df_stocks[df_stocks["Symbol"] == sym].iloc[0]
  hist = ohlcv_store[sym].copy()

  st.header(
      f"📈 {sym} — Technical Chart & Institutional Setup ({row['Sector']})"
  )

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("LTP", f"₹{row['LTP']}", f"{row['Day %']:+.2f}%")
  m2.metric("Week Return", f"{row['Week %']:+.2f}%")
  m3.metric("Volume Surge (RVOL)", f"{row['RVOL (x)']}x")
  m4.metric("Sector", row["Sector"])

  hist["EMA20"] = hist["Close"].ewm(span=20).mean()
  hist["VWAP"] = (
      (((hist["High"] + hist["Low"] + hist["Close"]) / 3.0) * hist["Volume"])
      .groupby(hist.index.date)
      .cumsum()
      / hist["Volume"].groupby(hist.index.date).cumsum().replace(0, np.nan)
  )

  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=[0.75, 0.25],
  )
  fig.add_trace(
      go.Candlestick(
          x=hist.index,
          open=hist["Open"],
          high=hist["High"],
          low=hist["Low"],
          close=hist["Close"],
          name=sym,
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=hist.index,
          y=hist["VWAP"],
          line=dict(color="#FFD700", width=1.3),
          name="VWAP",
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=hist.index,
          y=hist["EMA20"],
          line=dict(color="#29B6F6", width=1.3),
          name="20 EMA",
      ),
      row=1,
      col=1,
  )

  v_colors = [
      "#00E676" if c >= o else "#FF5252"
      for c, o in zip(hist["Close"], hist["Open"])
  ]
  fig.add_trace(
      go.Bar(
          x=hist.index,
          y=hist["Volume"],
          marker_color=v_colors,
          name="Volume",
      ),
      row=2,
      col=1,
  )

  fig.update_layout(
      height=520,
      template="plotly_dark",
      xaxis_rangeslider_visible=False,
      margin=dict(t=20, l=10, r=10, b=10),
  )
  st.plotly_chart(fig, use_container_width=True)

# =========================================================
# LEVEL 2 VIEW: SECTOR CONSTITUENTS TABLE
# =========================================================
elif st.session_state.nav_sector:
  sec = st.session_state.nav_sector
  sec_df = df_stocks[df_stocks["Sector"] == sec].reset_index(drop=True)

  st.header(f"📂 {sec} — Constituent Stocks")
  st.markdown("👆 **Click any row in the table below** to view its chart.")

  table_event = st.dataframe(
      sec_df[["Symbol", "LTP", "Day %", "Week %", "RVOL (x)"]],
      use_container_width=True,
      hide_index=True,
      on_select="rerun",
      selection_mode="single-row",
      key="sector_table",
  )
  if table_event and table_event.selection and table_event.selection.rows:
    row_idx = table_event.selection.rows[0]
    st.session_state.nav_stock = sec_df.iloc[row_idx]["Symbol"]
    st.rerun()

# =========================================================
# LEVEL 1 VIEW: 31+ SECTOR HEATMAP & TABLE
# =========================================================
else:
  st.subheader("🗺️ Sector Heatmap & Breadth Analysis (Over 31+ Sectors)")
  st.caption(
      "🟢 **Green Boxes:** Bullish Outperformers  |  🔴 **Red Boxes:** Correction"
      " / Distribution Sectors"
  )

  if not df_sector_table.empty:
    fig_tree = px.treemap(
        df_sector_table,
        path=["Sector"],
        values="No. of Companies",
        color="Day Change %",
        color_continuous_scale=[
            "#990000",
            "#d9534f",
            "#f5f5f5",
            "#5cb85c",
            "#006400",
        ],
        color_continuous_midpoint=0,
        custom_data=["Day Change %", "No. of Companies"],
    )
    fig_tree.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:+.2f}%",
        hovertemplate=(
            "<b>%{label}</b><br>Day Change: %{customdata[0]:+.2f}%<br>Companies:"
            " %{customdata[1]}<extra></extra>"
        ),
    )
    fig_tree.update_layout(height=520, margin=dict(t=10, l=10, r=10, b=10))

    sector_event = st.plotly_chart(
        fig_tree, use_container_width=True, on_select="rerun", key="main_heatmap"
    )
    if (
        sector_event
        and sector_event.selection
        and sector_event.selection.points
    ):
      clicked_sec = sector_event.selection.points[0].get("label")
      if clicked_sec in TRENDLYNE_31_SECTORS:
        st.session_state.nav_sector = clicked_sec
        st.rerun()

    st.markdown("---")
    st.subheader(
        "📊 Sector Analysis and Scores Table (Advances, Declines & Momentum)"
    )

    table_selection = st.dataframe(
        df_sector_table.sort_values(by="Day Change %", ascending=False),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="master_sector_table",
    )
    if (
        table_selection
        and table_selection.selection
        and table_selection.selection.rows
    ):
      row_idx = table_selection.selection.rows[0]
      selected_sector_name = df_sector_table.sort_values(
          by="Day Change %", ascending=False
      ).iloc[row_idx]["Sector"]
      st.session_state.nav_sector = selected_sector_name
      st.rerun()
