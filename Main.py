import streamlit as st

st.set_page_config(
    page_title="Market Intelligence Dashboard",
    layout="wide",
    page_icon="📊",
)

st.title("🚀 Market Intelligence & Institutional Trading Dashboard")
st.write(
    "Welcome to your advanced stock market terminal. Use the sidebar navigation"
    " to explore specialized trading tools:"
)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Institutional Bulk & Block Deals")
  st.write(
      "Track daily institutional transactions, block deals, and large volume"
      " accumulations with precise date filters."
  )

with col2:
  st.subheader("⚡ Volume Surge Scanner")
  st.write(
      "Scan watchlist equities for abnormal volume spikes, moving average"
      " breakouts, and momentum triggers."
  )
