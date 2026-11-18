from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Smart Money Pulse & Institutional Flow", layout="wide"
)

# --- CLEAN SIDEBAR NAVIGATION ---
st.sidebar.markdown("### 🧭 Hedge Fund Navigation Workflow")
st.sidebar.markdown("- 🗺️ **[Sector Rotation & Macro Pulse](Sector_Rotation_Scanner)**")
st.sidebar.markdown("- ⚡ **[Smart Money Flow Terminal](Smart_Money_Pulse)**")
st.sidebar.markdown("- 🌙 **[Night-Before Prep & Coiling](Night_Before_Prep_Scanner)**")
st.sidebar.markdown("- 📈 **[Intraday Sniper Terminal](PRIME_2-5_INTRADAY_SNIPER)**")
st.sidebar.markdown("---")

st.title("⚡ Institutional Smart Money Flow & Pulse Terminal")
st.caption(
    "Live Sector-to-Stock Capital Flow Streams, Inflow/Outflow Aggregates in"
    " Crores."
)

SECTOR_MAPPING = {
    "Banking & Finance": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
    ],
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Automobiles": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS"],
    "Energy & Oil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
}


@st.cache_data(ttl=300)
def fetch_institutional_flows():
  all_syms = [
      sym for tickers in SECTOR_MAPPING.values() for sym in tickers
  ]
  raw = yf.download(
      all_syms, period="1mo", interval="1d", group_by="ticker", progress=False
  )

  records = []
  for sector, tickers in SECTOR_MAPPING.items():
    for ticker in tickers:
      try:
        df = raw[ticker].dropna()
        if len(df) < 10:
          continue
        close, vol = df["Close"], df["Volume"]
        ltp = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        pct_chg = ((ltp - prev) / prev) * 100
        turnover_cr = (ltp * float(vol.iloc[-1])) / 1e7
        net_flow_cr = round(
            turnover_cr
            * (pct_chg / 100)
            * (float(vol.iloc[-1]) / float(vol.rolling(10).mean().iloc[-1])),
            2,
        )

        records.append({
            "Symbol": ticker.replace(".NS", ""),
            "Sector": sector,
            "Price": round(ltp, 2),
            "Change %": round(pct_chg, 2),
            "Net Flow (Cr)": net_flow_cr,
        })
      except Exception:
        continue
  return pd.DataFrame(records)


with st.spinner("Streaming institutional order book capital flows..."):
  df_flow = fetch_institutional_flows()

if not df_flow.empty:
  total_in = df_flow[df_flow["Net Flow (Cr)"] > 0]["Net Flow (Cr)"].sum()
  total_out = abs(df_flow[df_flow["Net Flow (Cr)"] < 0]["Net Flow (Cr)"].sum())

  # Top Institutional Metrics Bar (Fixed invalid delta_value parameter)
  c1, c2, c3 = st.columns(3)
  c1.metric(
      "🟢 Total Institutional Inflow",
      f"₹{total_in:,.0f} Cr",
      delta="Accumulation",
  )
  c2.metric(
      "🔴 Total Institutional Outflow", f"₹{total_out:,.0f} Cr", delta="Distribution"
  )
  c3.metric(
      "⚖️ Net Market Institutional Bias",
      f"₹{total_in - total_out:,.0f} Cr",
      delta="Bullish Edge",
  )

  st.markdown("---")
  st.subheader("🌊 Institutional Sector-to-Stock Capital Flow (Sankey Stream)")
  st.caption(
      "Visualizing capital velocity from sectors into individual equities based"
      " on turnover and volume surge."
  )

  # Build Sankey Diagram Data Structures
  sectors = list(SECTOR_MAPPING.keys())
  stocks = df_flow["Symbol"].tolist()
  nodes = sectors + stocks
  node_indices = {node: i for i, node in enumerate(nodes)}

  sources, targets, values, link_colors = [], [], [], []

  for _, row in df_flow.iterrows():
    sec_idx = node_indices[row["Sector"]]
    stock_idx = node_indices[row["Symbol"]]
    flow_val = abs(row["Net Flow (Cr)"]) + 10

    sources.append(sec_idx)
    targets.append(stock_idx)
    values.append(flow_val)
    link_colors.append(
        "rgba(0, 230, 118, 0.5)"
        if row["Net Flow (Cr)"] >= 0
        else "rgba(255, 82, 82, 0.5)"
    )

  node_colors = ["#29B6F6"] * len(sectors) + [
      "#00E676" if c >= 0 else "#FF5252" for c in df_flow["Change %"]
  ]

  fig_sankey = go.Figure(
      go.Sankey(
          node=dict(
              pad=15,
              thickness=20,
              line=dict(color="black", width=0.5),
              label=nodes,
              color=node_colors,
          ),
          link=dict(
              source=sources,
              target=targets,
              value=values,
              color=link_colors,
          ),
      )
  )

  fig_sankey.update_layout(
      height=500,
      template="plotly_dark",
      margin=dict(t=10, l=10, r=10, b=10),
  )
  st.plotly_chart(fig_sankey, use_container_width=True)

  st.markdown("---")
  st.subheader("📋 Underlying Institutional Flow Ledger")
  st.dataframe(
      df_flow.sort_values(by="Net Flow (Cr)", ascending=False),
      use_container_width=True,
      hide_index=True,
  )
