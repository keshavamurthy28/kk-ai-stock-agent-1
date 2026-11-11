import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Matched Super-Signal Watchlist", page_icon="🎯", layout="wide"
)

st.title("🎯 Matched Morning Super-Signal Watchlist")
st.markdown(
    "Automatically cross-references your Night-Before Homework with Live Morning"
    " Volume Spurts."
)

st.sidebar.header("Filters")
min_vol_surge = st.sidebar.slider("Min Volume Surge (x)", 1.2, 5.0, 2.0, 0.2)

MASTER_UNIVERSE = [
    "JYOTISTRUC",
    "ASHOKA",
    "KALYANKJIL",
    "APOLLO",
    "PCJEWELLER",
    "IRFC",
    "RVNL",
    "RPOWER",
    "GTLINFRA",
    "SUZLON",
    "YESBANK",
    "IDEA",
    "BANKBARODA",
    "PNB",
    "CANBK",
    "HDFCBANK",
    "ICICIBANK",
    "RELIANCE",
    "TATASTEEL",
    "INFY",
    "WOCKPHARMA",
    "HONASA",
    "BEL",
    "BHEL",
    "M&M",
    "THERMAX",
    "LENSKART",
    "RAIN",
    "DATAPATTNS",
    "GLAND",
    "AARTIDRUGS",
]


@st.cache_data(ttl=30)
def fetch_super_signals(symbols, vol_threshold):
  matched_setups = []
  for sym in symbols:
    ticker = f"{sym}.NS" if not sym.endswith(".NS") else sym
    try:
      df = yf.download(
          ticker, period="30d", interval="1d", progress=False,
