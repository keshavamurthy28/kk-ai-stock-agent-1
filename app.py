import streamlit as st

st.set_page_config(
    page_title="Institutional Alpha & Catalyst Terminal", layout="wide"
)

st.title(
    "🚀 Institutional Alpha & Catalyst-Driven Execution Engine (Advanced)"
)
st.markdown(
    "Welcome to your centralized algorithmic trading terminal. Use the"
    " **sidebar navigation** on the left to switch between specialized"
    " modules:"
)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Market Scanners & Order Blocks")
  st.markdown(
      "- **Live Market Spurt Scanner**: Real-time volume surge & breakout"
      " detector.\n- **Multi Stock Breakout Scanner**: Scans top F&O stocks for"
      " institutional confluence.\n- **Advanced SMC Terminal**: Order Block &"
      " Fair Value Gap mapping."
  )

  st.subheader("💼 Institutional Intelligence")
  st.markdown(
      "- **Institutional Bulk Deals**: Upload and parse daily block deal"
      " reports.\n- **FII Stock Tracker**: Comprehensive FII/FPI accumulation"
      " monitor."
  )

with col2:
  st.subheader("📈 Portfolio & Backtesting")
  st.markdown(
      "- **Portfolio Analysis**: Upload Zerodha holdings and track technical"
      " signals.\n- **Strategy Backtester**: Simulate custom EMA and volume"
      " rules on historical data."
  )

  st.subheader("🎯 Active High-Conviction Focus")
  st.markdown(
      "- **DCXINDIA**: Institutional Block Deal & Defense Sector Order Win"
      " Confluence (+12.05%)\n- **KALYANKJIL**: Strong FII Accumulation & Retail"
      " Sales Expansion (+7.1%)"
  )
