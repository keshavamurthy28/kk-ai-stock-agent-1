import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advanced SMC & FVG Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS: Push content safely below Streamlit's top header bar
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3.8rem !important;
            padding-bottom: 1rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- TOP BAR: SYMBOL INPUT & CANDLE INTERVALS (Clearly visible below header) ---
with st.container(border=True):
  top_col1, top_col2, top_col3 = st.columns([2, 6, 2])

  with top_col1:
    stock_input = (
        st.text_input(
            "NSE Symbol",
            value="RELIANCE",
            label_visibility="collapsed",
            placeholder="Symbol (e.g., AMBER, RELIANCE)",
        )
        .upper()
        .strip()
    )

  ticker_symbol = (
      f"{stock_input}.NS" if not stock_input.endswith(".NS") else stock_input
  )

  with top_col2:
    interval_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"]
    selected_tf = st.radio(
        "Candle Interval",
        options=interval_options,
        index=2,  # Default to 15m
        horizontal=True,
        label_visibility="collapsed",
    )

  with top_col3:
    show_mtf_zones = st.toggle("Show 1D & 4H Zones", value=True)
