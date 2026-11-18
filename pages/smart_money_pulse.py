import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Smart Money Pulse & Flow Terminal", layout="wide")

st.title("⚡ Smart Money Pulse & Institutional Flow Terminal")
st.caption("Real-time Sector-to-Stock Capital Flow, Fastest Inflow/Outflow Bubbles & 10-15% Swing Breakout Screener")

# Sector-wise liquid NSE Universe
SECTOR_STOCKS = {
    "Bank & PSU": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "BANKBARODA.NS", "PNB.NS"],
    "IT & Tech": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "PERSISTENT.NS", "COFORGE.NS"],
    "Pharma & Health": ["SUNPHARMA.NS", "DIVISLAB.NS", "CIPLA.NS", "DRREDDY.NS", "LUPIN.NS", "LAURUSLABS.NS", "GLAXO.NS"],
    "Defence & CapGoods": ["HAL.NS", "BEL.NS", "MAZDOCK.NS", "DATAPATTNS.NS", "LT.NS", "SIEMENS.NS", "POWERINDIA.NS"],
    "Auto & EV": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "TVSMOTOR.NS"],
    "NBFC & Finance": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "CHOLAFIN.NS", "SHRIRAMFIN.NS", "JIOFIN.NS", "IREDA.NS"],
    "Metals & Energy": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "RELIANCE.NS", "NTPC.NS", "ONGC.NS", "TATAPOWER.NS"],
    "Consumer & FMCG": ["ITC.NS", "HINDUNILVR.NS", "TRENT.NS", "TITAN.NS", "JUBLFOOD.NS", "VBL.NS"]
}

def analyze_stock(symbol, sector):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 25:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        high = df['High'].iloc[-1]
        low = df['Low'].iloc[-1]
        vol = df['Volume'].iloc[-1]
        avg_vol_20 = df['Volume'].iloc[-21:-1].mean()

        pct_chg = ((close - prev_close) / prev_close) * 100
        vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

        hl_range = (high - low) if (high - low) > 0 else 0.01
        clv = ((close - low) - (high - close)) / hl_range
        turnover_cr = (close * vol) / 1e7
        net_flow_cr = round(turnover_cr * clv, 2)

        high_20d = df['High'].iloc[-21:-1].max()
        low_20d = df['Low'].iloc[-21:-1].min()
        range_20d_pct = ((high_20d - low_20d) / low_20d) * 100

        is_breakout = (close >= high_20d * 0.985) and (vol_ratio >= 1.3) and (pct_chg > 1.0)
        is_tight_base = (range_20d_pct <= 14.0) and (close > df['Close'].rolling(20).mean().iloc[-1])

        setup_tag = "🔥 Breakout + Vol" if is_breakout else ("📦 Tight Smart Base" if is_tight_base else "Watchlist")

        return {
            "Symbol": symbol.replace(".NS", ""),
            "Sector": sector,
            "Price": round(close, 2),
            "Change %": round(pct_chg, 2),
            "Turnover (Cr)": round(turnover_cr, 1),
            "Net Flow (Cr)": net_flow_cr,
            "Vol Surge (x)": round(vol_ratio, 2),
            "20D Range %": round(range_20d_pct, 1),
            "Swing Setup": setup_tag
        }
    except Exception:
        return None

@st.cache_data(ttl=300)
def fetch_market_flow():
    tasks = [(sym, sec) for sec, syms in SECTOR_STOCKS.items() for sym in syms]
    results = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(analyze_stock, sym, sec) for sym, sec in tasks]
        for f in futures:
            res = f.result()
            if res:
                results.append(res)
    return pd.DataFrame(results)

if st.button("🔄 Refresh Live Smart Money Flow"):
    st.cache_data.clear()

with st.spinner("Scanning Institutional Sector & Stock Money Flows..."):
    df_flow = fetch_market_flow()

if df_flow.empty:
    st.error("Unable to fetch market data right now. Please try refreshing.")
    st.stop()

inflows_df = df_flow[df_flow["Net Flow (Cr)"] > 0].sort_values(by="Net Flow (Cr)", ascending=False)
outflows_df = df_flow[df_flow["Net Flow (Cr)"] < 0].sort_values(by="Net Flow (Cr)", ascending=True)

total_inflow = inflows_df["Net Flow (Cr)"].sum()
total_outflow = abs(outflows_df["Net Flow (Cr)"].sum())
net_market_flow = total_inflow - total_outflow

c1, c2, c3, c4 = st.columns(4)
c1.metric("🟢 Total Smart Inflow", f"₹{total_inflow:,.0f} Cr")
c2.metric("🔴 Total Smart Outflow", f"₹{total_outflow:,.0f} Cr")
c3.metric("⚖️ Net Institutional Flow", f"₹{net_market_flow:,.0f} Cr", delta=f"{'Bullish' if net_market_flow > 0 else 'Bearish'}")
c4.metric("🚀 Swing Breakout Candidates", len(df_flow[df_flow["Swing Setup"] != "Watchlist"]))

st.divider()

# ==========================================
# SECTION 1: TREDYE-STYLE SANKEY MONEY FLOW
# ==========================================
st.subheader("🌊 Sector-to-Stock Institutional Money Flow Stream")

top_in = inflows_df.head(8)
top_out = outflows_df.head(8).copy()
top_out["Abs Flow"] = top_out["Net Flow (Cr)"].abs()

sectors = list(SECTOR_STOCKS.keys())
in_stocks = [f"{r['Symbol']} (+₹{r['Net Flow (Cr)']:.0f}Cr)" for _, r in top_in.iterrows()]
out_stocks = [f"{r['Symbol']} (-₹{r['Abs Flow']:.0f}Cr)" for _, r in top_out.iterrows()]

labels = sectors + ["🟢 INSTITUTIONAL INFLOW", "🔴 INSTITUTIONAL OUTFLOW"] + in_stocks + out_stocks
node_colors = (
    ["#3b82f6"] * len(sectors) +
    ["#10b981", "#ef4444"] +
    ["#10b981"] * len(in_stocks) +
    ["#ef4444"] * len(out_stocks)
)

sources, targets, values, link_colors = [], [], [], []
inflow_hub_idx = len(sectors)
outflow_hub_idx = len(sectors) + 1

for i, sec in enumerate(sectors):
    sec_in = inflows_df[inflows_df["Sector"] == sec]["Net Flow (Cr)"].sum()
    sec_out = abs(outflows_df[outflows_df["Sector"] == sec]["Net Flow (Cr)"].sum())
    if sec_in > 0:
        sources.append(i)
        targets.append(inflow_hub_idx)
        values.append(sec_in)
        link_colors.append("rgba(16, 185, 129, 0.35)")
    if sec_out > 0:
        sources.append(i)
        targets.append(outflow_hub_idx)
        values.append(sec_out)
        link_colors.append("rgba(239, 68, 68, 0.35)")

for idx, (_, row) in enumerate(top_in.iterrows()):
    sources.append(inflow_hub_idx)
    targets.append(outflow_hub_idx + 1 + idx)
    values.append(row["Net Flow (Cr)"])
    link_colors.append("rgba(16, 185, 129, 0.55)")

for idx, (_, row) in enumerate(top_out.iterrows()):
    sources.append(outflow_hub_idx)
    targets.append(outflow_hub_idx + 1 + len(in_stocks) + idx)
    values.append(row["Abs Flow"])
    link_colors.append("rgba(239, 68, 68, 0.55)")

fig_sankey = go.Figure(data=[go.Sankey(
    node=dict(pad=18, thickness=18, line=dict(color="#111827", width=0.5), label=labels, color=node_colors),
    link=dict(source=sources, target=targets, value=values, color=link_colors)
)])
fig_sankey.update_layout(height=560, margin=dict(l=10, r=10, t=20, b=20), paper_bgcolor="#0e1117", font=dict(color="white", size=12))
st.plotly_chart(fig_sankey, use_container_width=True)

# ==========================================
# SECTION 2: FASTEST INFLOWS / OUTFLOWS BUBBLES
# ==========================================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🟢 Fastest Inflows (Volume + Price Expansion)")
    fast_in = inflows_df.sort_values(by="Vol Surge (x)", ascending=False).head(8)
    fig_in = px.scatter(fast_in, x="Vol Surge (x)", y="Change %", size="Net Flow (Cr)", text="Symbol", color_discrete_sequence=["#10b981"], size_max=55)
    fig_in.update_traces(textposition="middle center", textfont=dict(color="white", size=11))
    fig_in.update_layout(height=360, paper_bgcolor="#0e1117", plot_bgcolor="#111827", showlegend=False)
    st.plotly_chart(fig_in, use_container_width=True)

with col_right:
    st.subheader("🔴 Fastest Outflows (Distribution Pressure)")
    fast_out = outflows_df.copy()
    fast_out["Abs Flow"] = fast_out["Net Flow (Cr)"].abs()
    fast_out = fast_out.sort_values(by="Vol Surge (x)", ascending=False).head(8)
    fig_out = px.scatter(fast_out, x="Vol Surge (x)", y="Change %", size="Abs Flow", text="Symbol", color_discrete_sequence=["#ef4444"], size_max=55)
    fig_out.update_traces(textposition="middle center", textfont=dict(color="white", size=11))
    fig_out.update_layout(height=360, paper_bgcolor="#0e1117", plot_bgcolor="#111827", showlegend=False)
    st.plotly_chart(fig_out, use_container_width=True)

# ==========================================
# SECTION 3: SMART MONEY SWING BREAKOUT SCREENER
# ==========================================
st.divider()
st.subheader("🎯 Smart Money Swing Trade Screener (10–15% Rally Setups)")
st.caption("Filters stocks with positive institutional inflow + tight base / 20-day range breakout + volume surge.")

swing_df = df_flow[df_flow["Net Flow (Cr)"] > 0].sort_values(by=["Swing Setup", "Vol Surge (x)"], ascending=[True, False])

# Replaced pandas style gradient with direct dataframe rendering to avoid matplotlib dependency error
st.dataframe(swing_df, use_container_width=True, hide_index=True)
