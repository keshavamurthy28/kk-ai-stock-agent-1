from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Advanced SMC & FVG Terminal", layout="wide")
st.title("📊 Advanced Smart Money Concepts (SMC) & Institutional FVG Terminal")

with st.expander("📘 Beginner Guide: Key-Factor Stock Search, Intervals & Range Controls", expanded=False):
    st.markdown(
        "- **Key-Factor Stock Search:** Filter NSE stocks by **Sector**, **Price Band**, or **Name/Symbol** (for example, typing `data` or selecting `Defence & Aerospace` brings up `DATAPATTNS — Data Patterns (India) Ltd`).\n"
        "- **Any NSE Symbol Support:** Even if a stock isn't in the built-in list, you can type its exact NSE ticker (like `DATAPATTNS`) and load its chart.\n"
        "- **Risk & Profit Reminder:** Always verify live prices on your broker before trading and use a stop-loss—no setup guarantees profit. Not financial advice."
    )

# Expanded NSE Catalog with Sector & Approx Price Tier for Key-Factor Filtering
NSE_STOCK_CATALOG = [
    ("DATAPATTNS", "Data Patterns (India) Ltd", "Defence & Aerospace", 2500.0),
    ("HAL", "Hindustan Aeronautics Ltd", "Defence & Aerospace", 4200.0),
    ("BEL", "Bharat Electronics Ltd", "Defence & Aerospace", 310.0),
    ("MAZDOCK", "Mazagon Dock Shipbuilders Ltd", "Defence & Aerospace", 2400.0),
    ("BDL", "Bharat Dynamics Ltd", "Defence & Aerospace", 1250.0),
    ("COCHINSHIP", "Cochin Shipyard Ltd", "Defence & Aerospace", 1500.0),
    ("INFY", "Infosys Ltd", "IT & Tech", 1850.0),
    ("TCS", "Tata Consultancy Services Ltd", "IT & Tech", 4100.0),
    ("WIPRO", "Wipro Ltd", "IT & Tech", 560.0),
    ("HCLTECH", "HCL Technologies Ltd", "IT & Tech", 1800.0),
    ("TECHM", "Tech Mahindra Ltd", "IT & Tech", 1650.0),
    ("INFOBEAN", "InfoBeans Technologies Ltd", "IT & Tech", 620.0),
    ("PERSISTENT", "Persistent Systems Ltd", "IT & Tech", 5400.0),
    ("LTIM", "LTIMindtree Ltd", "IT & Tech", 5900.0),
    ("HDFCBANK", "HDFC Bank Ltd", "Banking & Finance", 1720.0),
    ("ICICIBANK", "ICICI Bank Ltd", "Banking & Finance", 1280.0),
    ("SBIN", "State Bank of India", "Banking & Finance", 840.0),
    ("AXISBANK", "Axis Bank Ltd", "Banking & Finance", 1160.0),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "Banking & Finance", 1780.0),
    ("INDUSINDBK", "IndusInd Bank Ltd", "Banking & Finance", 1050.0),
    ("LICHSGFIN", "LIC Housing Finance Ltd", "Banking & Finance", 610.0),
    ("BAJFINANCE", "Bajaj Finance Ltd", "Banking & Finance", 6900.0),
    ("BAJAJFINSV", "Bajaj Finserv Ltd", "Banking & Finance", 1650.0),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd", "Pharma & Healthcare", 1820.0),
    ("CIPLA", "Cipla Ltd", "Pharma & Healthcare", 1520.0),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd", "Pharma & Healthcare", 1260.0),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise Ltd", "Pharma & Healthcare", 6850.0),
    ("MAXHEALTH", "Max Healthcare Institute Ltd", "Pharma & Healthcare", 1020.0),
    ("RELIANCE", "Reliance Industries Ltd", "Energy & Power", 1320.0),
    ("NTPC", "NTPC Ltd", "Energy & Power", 390.0),
    ("POWERGRID", "Power Grid Corporation of India Ltd", "Energy & Power", 325.0),
    ("ONGC", "Oil & Natural Gas Corporation Ltd", "Energy & Power", 265.0),
    ("COALINDIA", "Coal India Ltd", "Energy & Power", 440.0),
    ("TATAPOWER", "Tata Power Company Ltd", "Energy & Power", 445.0),
    ("GAIL", "GAIL (India) Ltd", "Energy & Power", 205.0),
    ("TATASTEEL", "Tata Steel Ltd", "Metals & Mining", 150.0),
    ("HINDALCO", "Hindalco Industries Ltd", "Metals & Mining", 670.0),
    ("VEDL", "Vedanta Ltd", "Metals & Mining", 460.0),
    ("JINDALSTEL", "Jindal Steel & Power Ltd", "Metals & Mining", 920.0),
    ("MARUTI", "Maruti Suzuki India Ltd", "Auto & EV", 11400.0),
    ("TATAMOTORS", "Tata Motors Ltd", "Auto & EV", 820.0),
    ("M&M", "Mahindra & Mahindra Ltd", "Auto & EV", 2950.0),
    ("ITC", "ITC Ltd", "FMCG & Consumer", 480.0),
    ("HINDUNILVR", "Hindustan Unilever Ltd", "FMCG & Consumer", 2480.0),
    ("TITAN", "Titan Company Ltd", "FMCG & Consumer", 3250.0),
    ("TRENT", "Trent Ltd", "FMCG & Consumer", 6600.0),
    ("ASIANPAINT", "Asian Paints Ltd", "FMCG & Consumer", 2520.0),
    ("BHARTIARTL", "Bharti Airtel Ltd", "Telecom & Infra", 1590.0),
    ("LT", "Larsen & Toubro Ltd", "Telecom & Infra", 3650.0),
    ("ADANIENT", "Adani Enterprises Ltd", "Telecom & Infra", 2850.0),
    ("ADANIPORTS", "Adani Ports & Special Economic Zone Ltd", "Telecom & Infra", 1320.0),
    ("IRCTC", "Indian Railway Catering & Tourism Corp Ltd", "Telecom & Infra", 840.0),
]

SECTOR_OPTIONS = [
    "All Sectors",
    "Defence & Aerospace",
    "IT & Tech",
    "Banking & Finance",
    "Pharma & Healthcare",
    "Energy & Power",
    "Metals & Mining",
    "Auto & EV",
    "FMCG & Consumer",
    "Telecom & Infra",
]
PRICE_BAND_OPTIONS = [
    "All Prices",
    "Under ₹500",
    "₹500 – ₹2,000",
    "Above ₹2,000",
]

INTERVAL_OPTIONS = [
    "1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"
]
INDICATOR_OPTIONS = [
    "VWAP",
    "20 EMA",
    "50 EMA",
    "200 EMA",
    "Bollinger Bands",
    "RSI (14)",
]
SMC_LAYER_OPTIONS = [
    "4H FVG",
    "Order Blocks",
    "BOS / CHoCH",
    "Liquidity (BSL/SSL)",
    "Discount/Premium 50%",
]
RANGE_BUTTONS = ["1d", "5d", "1m", "3m", "6m", "YTD", "1Y", "5Y", "All"]

if "tf_choice" not in st.session_state:
    st.session_state.tf_choice = "1m"
if "range_choice" not in st.session_state:
    st.session_state.range_choice = "1d"
if "selected_indicators" not in st.session_state:
    st.session_state.selected_indicators = ["VWAP", "20 EMA"]
if "show_layers" not in st.session_state:
    st.session_state.show_layers = [
        "4H FVG",
        "Order Blocks",
        "BOS / CHoCH",
        "Liquidity (BSL/SSL)",
    ]
if "show_volume" not in st.session_state:
    st.session_state.show_volume = True
if "show_spikes" not in st.session_state:
    st.session_state.show_spikes = True
if "show_trade_lines" not in st.session_state:
    st.session_state.show_trade_lines = True
if "fit_far_smc_yaxis" not in st.session_state:
    st.session_state.fit_far_smc_yaxis = False
if "jump_date" not in st.session_state:
    st.session_state.jump_date = None

# Key-Factor Filters (Sector & Price Band)
kf1, kf2, kf3 = st.columns([1.8, 1.5, 2.7])
selected_sector = kf1.selectbox("🏷️ Filter by Sector", SECTOR_OPTIONS, index=0)
selected_price_band = kf2.selectbox("💰 Filter by Price Tier", PRICE_BAND_OPTIONS, index=0)
kf3.caption(
    "💡 Tip: Filter by Sector or Price Tier, or type partial letters like `data` / `inf` to pick matching NSE stocks—or enter any NSE symbol directly."
)

# Type-to-Suggest NSE Stock Picker + Clickable Candle Interval Buttons Row
sym_col, tf_bar_col = st.columns([1.9, 4.1])
with sym_col:
    typed_query = (
        st.text_input(
            "Type NSE Symbol or Name (e.g., data, inf)",
            value="LICHSGFIN",
            placeholder="Type letters like data, inf, hal...",
        )
        .strip()
        .upper()
    )

    q_clean = typed_query.replace(".NS", "")

    def _matches_price_band(approx_p, band):
        if band == "Under ₹500":
            return approx_p < 500.0
        if band == "₹500 – ₹2,000":
            return 500.0 <= approx_p <= 2000.0
        if band == "Above ₹2,000":
            return approx_p > 2000.0
        return True

    filtered_stocks = [
        (sym, name, sec, approx_p)
        for sym, name, sec, approx_p in NSE_STOCK_CATALOG
        if (selected_sector == "All Sectors" or sec == selected_sector)
        and _matches_price_band(approx_p, selected_price_band)
        and (
            (not q_clean)
            or (q_clean in sym.upper())
            or (q_clean in name.upper())
            or (q_clean in sec.upper())
        )
    ]

    if filtered_stocks:
        options_list = [
            f"{sym} — {name} [{sec}]" for sym, name, sec, _ in filtered_stocks
        ]
        if q_clean and q_clean not in [s for s, _, _, _ in filtered_stocks]:
            options_list.insert(0, f"{q_clean} — Custom NSE Symbol ({q_clean}.NS)")
        selected_entry = st.selectbox(
            f"Matching NSE Stocks ({len(options_list)} shown)",
            options_list,
            index=0,
            key="nse_suggestion_select",
        )
        raw_sym = selected_entry.split(" — ")[0].strip().upper()
    else:
        st.caption("No catalog match under current filters—using typed NSE symbol directly.")
        raw_sym = q_clean or "LICHSGFIN"

ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"

with tf_bar_col:
    st.caption("Candle Interval (Click to Switch)")
    tf_cols = st.columns(len(INTERVAL_OPTIONS))
    for idx_tf, tf_label in enumerate(INTERVAL_OPTIONS):
        is_active = st.session_state.tf_choice == tf_label
        if tf_cols[idx_tf].button(
            tf_label,
            key=f"btn_tf_{tf_label}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state.tf_choice = tf_label
            st.session_state.jump_date = None
            if tf_label in ["1D", "1W", "1M"] and st.session_state.range_choice in ["1d", "5d"]:
                st.session_state.range_choice = "1Y"
            elif tf_label not in ["1D", "1W", "1M"] and st.session_state.range_choice in ["1Y", "5Y", "All"]:
                st.session_state.range_choice = "1d"
            st.rerun()

tf_choice = st.session_state.tf_choice


@st.cache_data(ttl=15)
def fetch_clean_smc(sym, tf):
    p_map = {
        "1m": "5d",
        "2m": "5d",
        "3m": "5d",
        "5m": "10d",
        "10m": "10d",
        "15m": "15d",
        "30m": "30d",
        "1h": "60d",
        "4h": "60d",
        "1D": "5y",
        "1W": "5y",
        "1M": "5y",
    }
    i_map = {
        "1m": "1m",
        "2m": "1m",
        "3m": "1m",
        "5m": "5m",
        "10m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "1h",
        "1D": "1d",
        "1W": "1wk",
        "1M": "1mo",
    }

    t_obj = yf.Ticker(sym)
    df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)
    df4 = t_obj.history(period="60d", interval="1h", auto_adjust=True)
    df1 = t_obj.history(period="6mo", interval="1d", auto_adjust=True)

    req = {"Open", "High", "Low", "Close", "Volume"}
    if df is None or df.empty or not req.issubset(set(df.columns)):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
        df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

    if tf in ["2m", "3m", "10m", "4h"]:
        rule_map = {
            "2m": ("2min", "0min"),
            "3m": ("3min", "0min"),
            "10m": ("10min", "0min"),
            "4h": ("4h", "15min"),
        }
        rule, offset = rule_map[tf]
        df = (
            df.set_index("Time")
            .resample(rule, offset=offset)
            .agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            })
            .dropna(subset=["Open", "High", "Low", "Close"])
            .reset_index()
        )

    if df4 is not None and not df4.empty and {"Open", "High", "Low", "Close"}.issubset(set(df4.columns)):
        df4.index = pd.to_datetime(df4.index)
        if df4.index.tz is not None:
            df4.index = df4.index.tz_convert("Asia/Kolkata").tz_localize(None)
        df4 = (
            df4.resample("4h", offset="15min")
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
            .dropna()
        )

    return df, df4, df1


df, df_4h, df_1d = fetch_clean_smc(ticker, tf_choice)

if df.empty:
    st.error(
        f"No data returned for {ticker}. Check the exact NSE ticker (for example, Data Patterns is `DATAPATTNS` -> `DATAPATTNS.NS`)."
    )
else:
    df = df.reset_index(drop=True)
    ltp = float(df["Close"].iloc[-1])
    is_intraday_tf = tf_choice in ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h"]

    if not is_intraday_tf:
        df["Axis_Str"] = df["Time"].dt.strftime("%d %b '%y")
    else:
        is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
        df["Axis_Str"] = np.where(
            is_new_day,
            df["Time"].dt.strftime("%d %b '%y  %H:%M"),
            df["Time"].dt.strftime("%H:%M  (%d %b)"),
        )

    # Calculate Technical Indicators
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    if df["Volume"].sum() > 0:
        df["VWAP"] = (
            (((df["High"] + df["Low"] + df["Close"]) / 3.0) * df["Volume"])
            .groupby(df["Time"].dt.date)
            .cumsum()
            / df["Volume"].groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
        ).fillna(df["EMA20"])
    else:
        df["VWAP"] = df["EMA20"]

    bb_mid = df["Close"].rolling(20, min_periods=1).mean()
    bb_std = df["Close"].rolling(20, min_periods=1).std().fillna(0.0)
    df["BB_Upper"] = bb_mid + (2.0 * bb_std)
    df["BB_Lower"] = bb_mid - (2.0 * bb_std)

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    latest_vwap = float(df["VWAP"].iloc[-1])

    v_avg = df["Volume"].rolling(20, min_periods=1).mean()
    v_col = [
        (
            "#00E676"
            if (c >= o and v >= 1.5 * va)
            else (
                "#FF5252"
                if (c < o and v >= 1.5 * va)
                else ("rgba(0,230,118,0.38)" if c >= o else "rgba(255,82,82,0.38)")
            )
        )
        for o, c, v, va in zip(df["Open"], df["Close"], df["Volume"], v_avg)
    ]

    def map_time_to_str(ts):
        idx = int((df["Time"] - ts).abs().idxmin())
        return df["Axis_Str"].iloc[idx]

    # 1. Higher-Timeframe (4H) Bullish & Bearish Fair Value Gaps (FVG)
    bull_fvg, bear_fvg = None, None
    if df_4h is not None and len(df_4h) >= 3:
        for i in range(len(df_4h) - 1, 1, -1):
            if bull_fvg is None and (df_4h["Low"].iloc[i] - df_4h["High"].iloc[i - 2]) > 0.05:
                bull_fvg = (
                    df_4h.index[i - 2],
                    float(df_4h["High"].iloc[i - 2]),
                    float(df_4h["Low"].iloc[i]),
                )
            if bear_fvg is None and (df_4h["Low"].iloc[i - 2] - df_4h["High"].iloc[i]) > 0.05:
                bear_fvg = (
                    df_4h.index[i - 2],
                    float(df_4h["High"].iloc[i]),
                    float(df_4h["Low"].iloc[i - 2]),
                )
            if bull_fvg and bear_fvg:
                break

    # 2. Institutional Bullish Order Block
    bull_ob = None
    for i in range(len(df) - 2, 1, -1):
        is_red = df["Close"].iloc[i] < df["Open"].iloc[i]
        next_strong_green = (df["Close"].iloc[i + 1] > df["Open"].iloc[i + 1]) and (
            df["Volume"].iloc[i + 1] >= 1.4 * v_avg.iloc[i + 1]
        )
        if is_red and next_strong_green:
            bull_ob = (
                df["Axis_Str"].iloc[i],
                float(df["Low"].iloc[i]),
                float(df["High"].iloc[i]),
            )
            break

    # 3. Market Structure: Swing Highs -> BOS & CHoCH
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df)):
        if df["SH"].iloc[i - 4]:
            last_sh = (df["Axis_Str"].iloc[i - 4], float(df["High"].iloc[i - 4]))
        if (
            last_sh
            and float(df["Close"].iloc[i - 1]) <= last_sh[1]
            and float(df["Close"].iloc[i]) > last_sh[1]
        ):
            sigs.append({
                "t_str": df["Axis_Str"].iloc[i],
                "x0_str": last_sh[0],
                "y": round(last_sh[1], 2),
            })
            last_sh = None

    # 4. Liquidity Pools (BSL / SSL) & Equilibrium (50%)
    lookback = min(len(df), 80)
    bsl_level = round(float(df["High"].iloc[-lookback:].max()), 2)
