from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import os
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

try:
    from kiteconnect import KiteConnect
    KITE_SDK_AVAILABLE = True
except ImportError:
    KiteConnect = None
    KITE_SDK_AVAILABLE = False

st.set_page_config(page_title="AI/ML Advanced SMC & Profit-Booking Terminal", layout="wide")
st.title("🧠 AI/ML Adaptive SMC, Liquidity Sweep & Profit-Booking Terminal")

with st.expander("📘 AI/ML Upgrade Guide: How These Algorithms Predict Profit-Booking Zones", expanded=False):
    st.markdown(
        "- **ML Adaptive SuperTrend (Volatility Clustering):** Clusters rolling ATR into Low/Med/High volatility regimes to adjust trailing stops dynamically without getting wicked out early.\n"
        "- **Chandelier Profit-Lock Exit:** Tracks `Highest High - (2.4 × ATR)` to signal exact trailing profit-booking exits when momentum stalls.\n"
        "- **Neural-Transformed RSI (NN-RSI):** Applies a `tanh` neural activation curve on smoothed RSI + momentum slope to catch exhaustion peaks before sharp reversals.\n"
        "- **Liquidity Rush & RVOL Trap Detector:** Flags candles that sweep Buy-Side Liquidity (BSL) on `>= 1.5x` Relative Volume (`RVOL`) and close weak—prime institutional profit-booking alerts.\n"
        "- **Advance Profit-Booking Radar:** Scans the NSE catalog in advance to rank stocks nearing Target 1 / Target 2 / BSL profit-booking zones."
    )

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
PRICE_BAND_OPTIONS = ["All Prices", "Under ₹500", "₹500 – ₹2,000", "Above ₹2,000"]

PRIMARY_INTERVALS = ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"]

INDICATOR_OPTIONS = [
    "VWAP",
    "ML Adaptive SuperTrend",
    "Chandelier Profit Exit",
    "Keltner Channel",
    "Trend Dots (Momentum Flip)",
    "20 EMA",
    "50 EMA",
    "200 EMA",
    "Bollinger Bands",
    "Neural RSI (NN-RSI)",
]

SMC_LAYER_OPTIONS = [
    "4H FVG",
    "Order Blocks",
    "BOS / CHoCH",
    "Liquidity (BSL/SSL)",
    "Liquidity Rush & Profit Alerts",
    "Discount/Premium 50%",
]

defaults = {
    "tf_choice": "5m",
    "range_choice": "1d",
    "selected_indicators": [
        "VWAP",
        "ML Adaptive SuperTrend",
        "Chandelier Profit Exit",
        "Trend Dots (Momentum Flip)",
        "Neural RSI (NN-RSI)",
    ],
    "show_layers": [
        "4H FVG",
        "Order Blocks",
        "BOS / CHoCH",
        "Liquidity (BSL/SSL)",
        "Liquidity Rush & Profit Alerts",
    ],
    "show_volume": True,
    "show_spikes": True,
    "show_trade_lines": True,
    "fit_far_smc_yaxis": False,
    "auto_refresh": False,
    "refresh_interval_sec": 5,
    "jump_date": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _get_kite_credentials():
    api_key = os.getenv("KITE_API_KEY", "").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip()
    try:
        if not api_key and "kite" in st.secrets:
            api_key = str(st.secrets["kite"].get("api_key", "")).strip()
        if not access_token and "kite" in st.secrets:
            access_token = str(st.secrets["kite"].get("access_token", "")).strip()
    except Exception:
        pass
    return api_key, access_token


@st.cache_resource
def get_kite_client():
    if not KITE_SDK_AVAILABLE:
        return None
    api_key, access_token = _get_kite_credentials()
    if not api_key or not access_token:
        return None
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        return kite
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_nse_token_map() -> dict:
    kite = get_kite_client()
    if kite is None:
        return {}
    try:
        insts = kite.instruments("NSE")
        return {
            str(item["tradingsymbol"]).upper(): int(item["instrument_token"])
            for item in insts
            if item.get("tradingsymbol") and item.get("instrument_token")
        }
    except Exception:
        return {}


def _switch_timeframe(tf_label: str):
    st.session_state.tf_choice = tf_label
    st.session_state.jump_date = None
    if tf_label in ["1D", "1W", "1M", "3M", "6M", "12M"] and st.session_state.range_choice in ["1d", "5d"]:
        st.session_state.range_choice = "1Y" if tf_label in ["1D", "1W", "1M"] else "5Y"
    elif tf_label not in ["1D", "1W", "1M", "3M", "6M", "12M"] and st.session_state.range_choice in ["1Y", "5Y", "All"]:
        st.session_state.range_choice = "1d"


# --- AI / ML QUANT ENGINE ---
def compute_ai_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    df["EMA200"] = close.ewm(span=200, adjust=False).mean()

    if vol.sum() > 0:
        df["VWAP"] = (
            (((high + low + close) / 3.0) * vol).groupby(df["Time"].dt.date).cumsum()
            / vol.groupby(df["Time"].dt.date).cumsum().replace(0, np.nan)
        ).fillna(df["EMA20"])
    else:
        df["VWAP"] = df["EMA20"]

    prev_close = close.shift(1).fillna(close)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    df["ATR14"] = tr.ewm(span=14, adjust=False).mean().bfill()

    # 1. Volatility Clustering -> ML Adaptive SuperTrend
    atr_pct = (df["ATR14"] / close.replace(0, np.nan)).fillna(0.005)
    q33 = atr_pct.rolling(50, min_periods=5).quantile(0.33).fillna(atr_pct.median())
    q66 = atr_pct.rolling(50, min_periods=5).quantile(0.66).fillna(atr_pct.median())

    adaptive_mult = np.where(atr_pct > q66, 3.2, np.where(atr_pct < q33, 1.8, 2.4))
    df["Vol_Regime"] = np.where(atr_pct > q66, "HIGH VOL", np.where(atr_pct < q33, "LOW VOL", "NORMAL"))

    hl2 = (high + low) / 2.0
    upper_basic = hl2 + adaptive_mult * df["ATR14"]
    lower_basic = hl2 - adaptive_mult * df["ATR14"]

    st_line = np.zeros(len(df), dtype=float)
    st_dir = np.ones(len(df), dtype=int)
    ub = np.array(upper_basic, dtype=float, copy=True)
    lb = np.array(lower_basic, dtype=float, copy=True)
    c_arr = np.array(close, dtype=float, copy=True)

    st_line[0] = lb[0]
    for i in range(1, len(df)):
        if c_arr[i] > ub[i - 1]:
            st_dir[i] = 1
        elif c_arr[i] < lb[i - 1]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i - 1]
            if st_dir[i] == 1 and lb[i] < lb[i - 1]:
                lb[i] = lb[i - 1]
            if st_dir[i] == -1 and ub[i] > ub[i - 1]:
                ub[i] = ub[i - 1]
        st_line[i] = lb[i] if st_dir[i] == 1 else ub[i]

    df["ML_ST"] = st_line
    df["ML_ST_Dir"] = st_dir

    # 2. Chandelier Profit-Lock Exit
    roll_high_22 = high.rolling(22, min_periods=1).max()
    df["Chandelier_Exit"] = roll_high_22 - (2.4 * df["ATR14"])

    # 3. Keltner Channel
    df["KC_Upper"] = df["EMA20"] + (1.8 * df["ATR14"])
    df["KC_Lower"] = df["EMA20"] - (1.8 * df["ATR14"])

    # Bollinger Bands
    bb_mid = close.rolling(20, min_periods=1).mean()
    bb_std = close.rolling(20, min_periods=1).std().fillna(0.0)
    df["BB_Upper"] = bb_mid + (2.0 * bb_std)
    df["BB_Lower"] = bb_mid - (2.0 * bb_std)

    # 4. Neural Network Transformed RSI (tanh activation + velocity blend)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    raw_rsi = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)
    rsi_norm = (raw_rsi - 50.0) / 25.0
    rsi_vel = rsi_norm.diff().fillna(0.0) * 1.5
    nn_act = np.tanh(0.85 * rsi_norm + 0.35 * rsi_vel)
    df["NN_RSI"] = 50.0 + (nn_act * 50.0)
    df["NN_RSI_Signal"] = df["NN_RSI"].ewm(span=5, adjust=False).mean()

    # 5. Relative Volume (RVOL) & Liquidity Rush / Sweep Profit-Booking Trap
    v_avg = vol.rolling(20, min_periods=1).mean().replace(0, np.nan)
    df["RVOL"] = (vol / v_avg).fillna(1.0)

    prior_swing_high = high.shift(1).rolling(15, min_periods=3).max()
    prior_swing_low = low.shift(1).rolling(15, min_periods=3).min()

    df["Liq_Rush_Top"] = (
        (high > prior_swing_high)
        & (close < prior_swing_high)
        & (df["RVOL"] >= 1.5)
    )
    df["Liq_Sweep_Bot"] = (
        (low < prior_swing_low)
        & (close > prior_swing_low)
        & (df["RVOL"] >= 1.5)
    )

    # 6. Purple / Green Trend-Flip Dots
    df["Bull_Dot"] = (df["ML_ST_Dir"] == 1) & (df["ML_ST_Dir"].shift(1) == -1)
    df["Bear_Profit_Dot"] = (
        ((df["ML_ST_Dir"] == -1) & (df["ML_ST_Dir"].shift(1) == 1))
        | ((df["NN_RSI"] > 78) & (df["NN_RSI"] < df["NN_RSI_Signal"]))
        | df["Liq_Rush_Top"]
    )

    # 7. Composite AI Profit-Booking Urgency Score (0 to 100)
    z_vwap = ((close - df["VWAP"]) / df["ATR14"].replace(0, np.nan)).fillna(0.0)
    score = (
        0.35 * np.clip(df["NN_RSI"], 0, 100)
        + 0.25 * np.clip(50 + z_vwap * 15, 0, 100)
        + 0.20 * np.clip(df["RVOL"] * 25, 0, 100)
        + 0.20 * np.where(close < df["Chandelier_Exit"], 85, 25)
    )
    df["Profit_Book_Score"] = np.round(np.clip(score, 0, 100), 1)

    return df


def _normalize_ist_naive(series_or_idx):
    dt = pd.to_datetime(series_or_idx)
    if getattr(dt, "tz", None) is not None:
        return dt.tz_convert("Asia/Kolkata").tz_localize(None)
    return dt


def _fetch_kite_candles(raw_sym: str, tf: str) -> pd.DataFrame:
    kite = get_kite_client()
    token_map = get_nse_token_map()
    token = token_map.get(raw_sym.upper())
    if kite is None or not token:
        return pd.DataFrame()

    days_map = {
        "1m": 5, "2m": 5, "3m": 5, "5m": 10, "10m": 10,
        "15m": 15, "30m": 30, "45m": 30,
        "1h": 60, "2h": 60, "3h": 60, "4h": 60,
        "1D": 730, "1W": 1460, "1M": 1825, "3M": 1825, "6M": 1825, "12M": 1825,
    }
    kite_iv_map = {
        "1m": "minute", "2m": "minute", "3m": "3minute", "5m": "5minute", "10m": "5minute",
        "15m": "15minute", "30m": "30minute", "45m": "15minute",
        "1h": "60minute", "2h": "60minute", "3h": "60minute", "4h": "60minute",
        "1D": "day", "1W": "day", "1M": "day", "3M": "day", "6M": "day", "12M": "day",
    }

    ist = pytz.timezone("Asia/Kolkata")
    to_dt = datetime.now(ist)
    from_dt = to_dt - timedelta(days=days_map.get(tf, 10))
    raw = kite.historical_data(
        instrument_token=token,
        from_date=from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        to_date=to_dt.strftime("%Y-%m-%d %H:%M:%S"),
        interval=kite_iv_map.get(tf, "5minute"),
        continuous=False,
        oi=False,
    )
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    df.rename(columns={"date": "Time", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
    df["Time"] = _normalize_ist_naive(df["Time"])
    df["Volume"] = df.get("Volume", 0).fillna(0)
    return df[["Time", "Open", "High", "Low", "Close", "Volume"]]


def _resample_df(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    rule_map = {
        "2m": ("2min", "0min"),
        "10m": ("10min", "0min"),
        "45m": ("45min", "15min"),
        "2h": ("2h", "15min"),
        "3h": ("3h", "15min"),
        "4h": ("4h", "15min"),
        "1W": ("1W-FRI", None),
        "1M": ("ME", None),
        "3M": ("3ME", None),
        "6M": ("6ME", None),
        "12M": ("12ME", None),
    }
    if tf not in rule_map:
        return df
    rule, offset = rule_map[tf]
    resampler = df.set_index("Time").resample(rule, offset=offset) if offset else df.set_index("Time").resample(rule)
    return (
        resampler.agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna(subset=["Open", "High", "Low", "Close"])
        .reset_index()
    )


@st.cache_data(ttl=60)
def fetch_4h_context(raw_sym: str, yf_sym: str) -> pd.DataFrame:
    kite_1h = _fetch_kite_candles(raw_sym, "1h")
    if not kite_1h.empty:
        return (
            kite_1h.set_index("Time")
            .resample("4h", offset="15min")
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
            .dropna()
        )
    df4 = yf.Ticker(yf_sym).history(period="60d", interval="1h", auto_adjust=False)
    if df4 is None or df4.empty or not {"Open", "High", "Low", "Close"}.issubset(set(df4.columns)):
        return pd.DataFrame()
    df4 = df4.copy()
    df4.index = _normalize_ist_naive(df4.index)
    return (
        df4.resample("4h", offset="15min")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
        .dropna()
    )


@st.cache_data(ttl=2)
def fetch_live_ltp(raw_sym: str, yf_sym: str, fallback_close: float):
    kite = get_kite_client()
    if kite is not None:
        key = f"NSE:{raw_sym.upper()}"
        try:
            q = kite.quote([key])
            if isinstance(q, dict) and key in q and q[key].get("last_price"):
                return float(q[key]["last_price"]), "Kite Live"
        except Exception:
            pass
    try:
        info = yf.Ticker(yf_sym).fast_info
        for attr in ("last_price", "regularMarketPrice"):
            val = getattr(info, attr, None)
            if val is not None and float(val) > 0:
                return float(val), "yfinance Quote"
    except Exception:
        pass
    return float(fallback_close), "Bar Close"


@st.cache_data(ttl=5)
def fetch_clean_smc(raw_sym: str, yf_sym: str, tf: str):
    df4 = fetch_4h_context(raw_sym, yf_sym)
    kite_df = _fetch_kite_candles(raw_sym, tf)
    if not kite_df.empty:
        return _resample_df(kite_df, tf), df4

    p_map = {
        "1m": "5d", "2m": "5d", "3m": "5d", "5m": "10d", "10m": "10d",
        "15m": "15d", "30m": "30d", "45m": "30d",
        "1h": "60d", "2h": "60d", "3h": "60d", "4h": "60d",
        "1D": "5y", "1W": "5y", "1M": "10y", "3M": "10y", "6M": "10y", "12M": "10y",
    }
    i_map = {
        "1m": "1m", "2m": "1m", "3m": "1m", "5m": "5m", "10m": "5m",
        "15m": "15m", "30m": "30m", "45m": "15m",
        "1h": "1h", "2h": "1h", "3h": "1h", "4h": "1h",
        "1D": "1d", "1W": "1wk", "1M": "1mo", "3M": "3mo", "6M": "1mo", "12M": "1mo",
    }
    df = yf.Ticker(yf_sym).history(period=p_map[tf], interval=i_map[tf], auto_adjust=False)
    req = {"Open", "High", "Low", "Close", "Volume"}
    if df is None or df.empty or not req.issubset(set(df.columns)):
        return pd.DataFrame(), df4

    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = _normalize_ist_naive(df["Time"])
    return _resample_df(df, tf), df4


def _scan_single_stock(item):
    sym, _, sec, _ = item
    try:
        d = _fetch_kite_candles(sym, "15m")
        if d.empty:
            d = yf.Ticker(f"{sym}.NS").history(period="15d", interval="15m", auto_adjust=False)
            if d is None or d.empty:
                return None
            d = d.reset_index()
            d.rename(columns={d.columns[0]: "Time"}, inplace=True)
            d["Time"] = _normalize_ist_naive(d["Time"])
        if len(d) < 30:
            return None
        d = compute_ai_ml_features(d)

        ltp = float(d["Close"].iloc[-1])
        bsl = float(d["High"].iloc[-60:].max())
        chand = float(d["Chandelier_Exit"].iloc[-1])
        nn_rsi = float(d["NN_RSI"].iloc[-1])
        rvol = float(d["RVOL"].iloc[-1])
        pb_score = float(d["Profit_Book_Score"].iloc[-1])
        dist_bsl_pct = ((bsl - ltp) / ltp) * 100.0 if ltp else 0.0

        if pb_score >= 72 or dist_bsl_pct <= 0.6 or ltp < chand:
            action = "💰 BOOK / TRAIL PROFIT"
        elif pb_score <= 35 and d["ML_ST_Dir"].iloc[-1] == 1:
            action = "🟢 ACCUMULATE (DISCOUNT)"
        else:
            action = "⏳ HOLD / RIDE TREND"

        return {
            "Symbol": sym,
            "Sector": sec,
            "LTP (₹)": round(ltp, 2),
            "AI Profit Score": pb_score,
            "NN-RSI": round(nn_rsi, 1),
            "RVOL": f"{rvol:.2f}x",
            "BSL Target (₹)": round(bsl, 2),
            "Dist to BSL": f"{dist_bsl_pct:.2f}%",
            "Chandelier Exit (₹)": round(chand, 2),
            "Advance AI Action": action,
        }
    except Exception:
        return None


@st.cache_data(ttl=30)
def scan_advance_profit_bookings(catalog_subset):
    """Pre-scans stocks concurrently to highlight where to book profits or enter early."""
    subset = list(catalog_subset)[:18]
    rows = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_scan_single_stock, item) for item in subset]
        for fut in as_completed(futures):
            res = fut.result()
            if res is not None:
                rows.append(res)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(by="AI Profit Score", ascending=False)


# --- TOP FILTER & SYMBOL BAR ---
kf1, kf2, kf3, kf4 = st.columns([1.4, 1.3, 1.5, 2.0])
selected_sector = kf1.selectbox("🏷️ Filter by Sector", SECTOR_OPTIONS, index=0)
selected_price_band = kf2.selectbox("💰 Filter by Price Tier", PRICE_BAND_OPTIONS, index=0)
typed_query = (
    kf3.text_input("🔍 NSE Symbol / Name", value="LICHSGFIN", placeholder="e.g., HAL, INFY, DATAPATTNS")
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
    and ((not q_clean) or (q_clean in sym) or (q_clean in name.upper()) or (q_clean in sec.upper()))
]

with kf4:
    if filtered_stocks:
        options_list = [f"{sym} — {name} [{sec}]" for sym, name, sec, _ in filtered_stocks]
        if q_clean and q_clean not in [s for s, _, _, _ in filtered_stocks]:
            options_list.insert(0, f"{q_clean} — Custom NSE Symbol ({q_clean}.NS)")
        selected_entry = st.selectbox(f"📋 Matching NSE Stocks ({len(options_list)})", options_list, index=0)
        raw_sym = selected_entry.split(" — ")[0].strip().upper()
    else:
        raw_sym = q_clean or "LICHSGFIN"

raw_sym = raw_sym.replace(".NS", "").strip().upper()
yf_ticker = f"{raw_sym}.NS"
tf_choice = st.session_state.tf_choice
df, df_4h = fetch_clean_smc(raw_sym, yf_ticker, tf_choice)

if df.empty:
    st.error(f"No data returned for {raw_sym} on {tf_choice} interval. Try switching interval or check NSE symbol.")
else:
    df = df.reset_index(drop=True)
    df = compute_ai_ml_features(df)

    bar_close = float(df["Close"].iloc[-1])
    ltp, price_source = fetch_live_ltp(raw_sym, yf_ticker, bar_close)

    latest_vwap = float(df["VWAP"].iloc[-1])
    latest_chand = float(df["Chandelier_Exit"].iloc[-1])
    latest_ml_st = float(df["ML_ST"].iloc[-1])
    latest_st_dir = int(df["ML_ST_Dir"].iloc[-1])
    latest_nn_rsi = float(df["NN_RSI"].iloc[-1])
    latest_rvol = float(df["RVOL"].iloc[-1])
    latest_pb_score = float(df["Profit_Book_Score"].iloc[-1])
    vol_regime = df["Vol_Regime"].iloc[-1]

    is_intraday_tf = tf_choice in ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "45m", "1h", "2h", "3h", "4h"]
    if not is_intraday_tf:
        df["Axis_Str"] = df["Time"].dt.strftime("%d %b '%y")
    else:
        is_new_day = df["Time"].dt.date != df["Time"].dt.date.shift(1)
        df["Axis_Str"] = np.where(
            is_new_day,
            df["Time"].dt.strftime("%d %b '%y  %H:%M"),
            df["Time"].dt.strftime("%H:%M  (%d %b)"),
        )

    v_col = [
        "#00E676" if (c >= o and rv >= 1.5) else (
            "#FF5252" if (c < o and rv >= 1.5) else (
                "rgba(0,230,118,0.38)" if c >= o else "rgba(255,82,82,0.38)"
            )
        )
        for o, c, rv in zip(df["Open"], df["Close"], df["RVOL"])
    ]

    def map_time_to_str(ts):
        idx = int((df["Time"] - ts).abs().idxmin())
        return df["Axis_Str"].iloc[idx]

    # 4H FVG
    bull_fvg, bear_fvg = None, None
    if df_4h is not None and len(df_4h) >= 3:
        for i in range(len(df_4h) - 1, 1, -1):
            if bull_fvg is None and (df_4h["Low"].iloc[i] - df_4h["High"].iloc[i - 2]) > 0.05:
                bull_fvg = (df_4h.index[i - 2], float(df_4h["High"].iloc[i - 2]), float(df_4h["Low"].iloc[i]))
            if bear_fvg is None and (df_4h["Low"].iloc[i - 2] - df_4h["High"].iloc[i]) > 0.05:
                bear_fvg = (df_4h.index[i - 2], float(df_4h["High"].iloc[i]), float(df_4h["Low"].iloc[i - 2]))
            if bull_fvg and bear_fvg:
                break

    # Bullish Order Block
    bull_ob = None
    for i in range(len(df) - 2, 1, -1):
        if df["Close"].iloc[i] < df["Open"].iloc[i] and df["Close"].iloc[i + 1] > df["Open"].iloc[i + 1] and df["RVOL"].iloc[i + 1] >= 1.4:
            bull_ob = (df["Axis_Str"].iloc[i], float(df["Low"].iloc[i]), float(df["High"].iloc[i]))
            break

    # BOS / CHoCH
    df["SH"] = df["High"] == df["High"].rolling(9, center=True).max()
    sigs, last_sh = [], None
    for i in range(4, len(df)):
        if df["SH"].iloc[i - 4]:
            last_sh = (df["Axis_Str"].iloc[i - 4], float(df["High"].iloc[i - 4]))
        if last_sh and float(df["Close"].iloc[i - 1]) <= last_sh[1] and float(df["Close"].iloc[i]) > last_sh[1]:
            sigs.append({"t_str": df["Axis_Str"].iloc[i], "x0_str": last_sh[0], "y": round(last_sh[1], 2)})
            last_sh = None

    # BSL / SSL / Equilibrium
    lookback = min(len(df), 80)
    bsl_level = round(float(df["High"].iloc[-lookback:].max()), 2)
    ssl_level = round(float(df["Low"].iloc[-lookback:].min()), 2)
    eq_level = round((bsl_level + ssl_level) / 2.0, 2)
    zone_tag = "DISCOUNT (Accumulate) 🟢" if ltp <= eq_level else "PREMIUM (Profit Zone) 🟠"

    # Execution & AI Trailing Levels
    if bull_ob and bull_ob[1] <= ltp <= bull_ob[2] * 1.02:
        entry_p = round(bull_ob[2], 2)
    elif bull_fvg and bull_fvg[1] <= ltp <= bull_fvg[2] * 1.02:
        entry_p = round(bull_fvg[2], 2)
    else:
        entry_p = round(max(latest_vwap, latest_ml_st), 2)

    sl_p = round(min(latest_ml_st * 0.997, entry_p * 0.99), 2)
    risk = max(entry_p - sl_p, entry_p * 0.008)
    t1_p = round(entry_p + risk * 1.5, 2)
    t2_p = round(max(bsl_level, entry_p + risk * 2.5), 2)

    # Push to Session State
    st.session_state.setdefault("live_scanner_picks", {})["SMC Terminal Blueprint"] = [{
        "symbol": raw_sym,
        "side": "BUY",
        "entry": float(entry_p),
        "sl": float(sl_p),
        "t1": float(t1_p),
        "t2": float(t2_p),
        "notes": f"AI Score {latest_pb_score}% | Chandelier ₹{latest_chand:,.2f}",
    }]

    # --- AI PROFIT-BOOKING & EXECUTION METRICS ---
    st.subheader(f"🧠 AI/ML Institutional Blueprint & Profit-Booking Radar: {raw_sym} ({tf_choice}) · {price_source}")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Last Price", f"₹{ltp:,.2f}", f"Close ₹{bar_close:,.2f} | RVOL {latest_rvol:.2f}x")
    m2.metric("🤖 ML SuperTrend", f"₹{latest_ml_st:,.2f}", "BULLISH 🟢" if latest_st_dir == 1 else "BEARISH 🔴")
    m3.metric("🔔 Chandelier Exit", f"₹{latest_chand:,.2f}", "Trail Stop / Book Profit")
    m4.metric("🎯 T1 / T2 Profit Zones", f"₹{t1_p:,.1f} / ₹{t2_p:,.1f}", zone_tag)
    m5.metric("🧬 Neural RSI (NN-RSI)", f"{latest_nn_rsi:.1f}", "Overbought Exhaustion ⚠️" if latest_nn_rsi >= 75 else "Healthy Momentum")
    m6.metric(
        "💰 AI Profit-Book Score",
        f"{latest_pb_score:.0f} / 100",
        "BOOK PROFITS NOW 🔥" if latest_pb_score >= 72 else ("HOLD / TRAIL 📈" if latest_pb_score >= 45 else "ENTRY ZONE 🟢"),
    )

    # Build Plotly Figure
    selected_indicators = st.session_state.selected_indicators
    show_layers = st.session_state.show_layers
    show_nn_rsi = "Neural RSI (NN-RSI)" in selected_indicators

    panels = ["price"] + (["volume"] if st.session_state.show_volume else []) + (["rsi"] if show_nn_rsi else [])
    n_rows = len(panels)
    vol_row = panels.index("volume") + 1 if "volume" in panels else None
    rsi_row = panels.index("rsi") + 1 if "rsi" in panels else None
    row_heights = [0.64, 0.18, 0.18] if n_rows == 3 else ([0.78, 0.22] if n_rows == 2 else [1.0])

    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.025 if n_rows > 1 else 0.01,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Axis_Str"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name=raw_sym, increasing_line_color="#00E676", decreasing_line_color="#FF5252",
        ),
        row=1, col=1,
    )

    if "ML Adaptive SuperTrend" in selected_indicators:
        bull_st = np.where(df["ML_ST_Dir"] == 1, df["ML_ST"], np.nan)
        bear_st = np.where(df["ML_ST_Dir"] == -1, df["ML_ST"], np.nan)
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=bull_st, mode="lines", name="ML SuperTrend (Bull)",
                       line=dict(color="#00E676", width=2.2)),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=bear_st, mode="lines", name="ML SuperTrend (Bear)",
                       line=dict(color="#FF5252", width=2.2)),
            row=1, col=1,
        )

    if "Chandelier Profit Exit" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["Chandelier_Exit"], mode="lines", name="Chandelier Exit",
                       line=dict(color="#FFAB00", width=1.6, dash="dashdot")),
            row=1, col=1,
        )

    if "Keltner Channel" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["KC_Upper"], mode="lines", name="KC Upper",
                       line=dict(color="rgba(38, 198, 218, 0.55)", width=1.1, dash="dot")),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["KC_Lower"], mode="lines", name="KC Lower",
                       fill="tonexty", fillcolor="rgba(38, 198, 218, 0.06)",
                       line=dict(color="rgba(38, 198, 218, 0.55)", width=1.1, dash="dot")),
            row=1, col=1,
        )

    if "Trend Dots (Momentum Flip)" in selected_indicators:
        b_dots = df[df["Bull_Dot"]]
        p_dots = df[df["Bear_Profit_Dot"]]
        if not b_dots.empty:
            fig.add_trace(
                go.Scatter(
                    x=b_dots["Axis_Str"], y=b_dots["Low"] * 0.9985, mode="markers", name="AI Buy Flip",
                    marker=dict(color="#00E676", size=9, symbol="circle", line=dict(color="#111", width=1)),
                ),
                row=1, col=1,
            )
        if not p_dots.empty:
            fig.add_trace(
                go.Scatter(
                    x=p_dots["Axis_Str"], y=p_dots["High"] * 1.0015, mode="markers", name="Book Profit / Exhaustion",
                    marker=dict(color="#E040FB", size=10, symbol="diamond", line=dict(color="#FFF", width=1)),
                ),
                row=1, col=1,
            )

    if "VWAP" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["VWAP"], mode="lines", name="VWAP",
                       line=dict(color="#FFD700", width=1.4)),
            row=1, col=1,
        )
    if "20 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["EMA20"], mode="lines", name="20 EMA",
                       line=dict(color="#29B6F6", width=1.2)),
            row=1, col=1,
        )
    if "50 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["EMA50"], mode="lines", name="50 EMA",
                       line=dict(color="#FFA726", width=1.3)),
            row=1, col=1,
        )
    if "200 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["EMA200"], mode="lines", name="200 EMA",
                       line=dict(color="#EC407A", width=1.4)),
            row=1, col=1,
        )
    if "Bollinger Bands" in selected_indicators:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["BB_Upper"], mode="lines", name="BB Upper",
                       line=dict(color="rgba(179,157,219,0.7)", width=1.1, dash="dash")),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["BB_Lower"], mode="lines", name="BB Lower",
                       line=dict(color="rgba(179,157,219,0.7)", width=1.1, dash="dash")),
            row=1, col=1,
        )

    if vol_row is not None:
        fig.add_trace(
            go.Bar(x=df["Axis_Str"], y=df["Volume"], name="Volume (RVOL Colored)", marker_color=v_col),
            row=vol_row, col=1,
        )

    if rsi_row is not None:
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["NN_RSI"], mode="lines", name="Neural RSI",
                       line=dict(color="#E040FB", width=1.8)),
            row=rsi_row, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Axis_Str"], y=df["NN_RSI_Signal"], mode="lines", name="NN Signal",
                       line=dict(color="#29B6F6", width=1.2, dash="dot")),
            row=rsi_row, col=1,
        )
        fig.add_hline(y=78, line_dash="dot", line_color="#FF5252", line_width=1, row=rsi_row, col=1)
        fig.add_hline(y=22, line_dash="dot", line_color="#00E676", line_width=1, row=rsi_row, col=1)

    end_str = df["Axis_Str"].iloc[-1]

    if "4H FVG" in show_layers:
        if bull_fvg:
            xs_str = map_time_to_str(bull_fvg[0])
            fig.add_shape(type="rect", x0=xs_str, x1=end_str, y0=bull_fvg[1], y1=bull_fvg[2],
                          fillcolor="rgba(0, 230, 118, 0.14)", line=dict(color="rgba(0, 230, 118, 0.4)", width=1),
                          layer="below", row=1, col=1)
        if bear_fvg:
            xs_b_str = map_time_to_str(bear_fvg[0])
            fig.add_shape(type="rect", x0=xs_b_str, x1=end_str, y0=bear_fvg[1], y1=bear_fvg[2],
                          fillcolor="rgba(255, 82, 82, 0.12)", line=dict(color="rgba(255, 82, 82, 0.4)", width=1),
                          layer="below", row=1, col=1)

    if "Order Blocks" in show_layers and bull_ob:
        fig.add_shape(type="rect", x0=bull_ob[0], x1=end_str, y0=bull_ob[1], y1=bull_ob[2],
                      fillcolor="rgba(41, 182, 246, 0.16)", line=dict(color="#29B6F6", width=1, dash="dot"),
                      layer="below", row=1, col=1)

    if "BOS / CHoCH" in show_layers:
        for idx_s, s in enumerate(sigs[-3:]):
            is_latest = idx_s == len(sigs[-3:]) - 1
            fig.add_shape(type="line", x0=s["x0_str"], x1=s["t_str"], y0=s["y"], y1=s["y"],
                          line=dict(color="#00E676", width=1.4, dash="dot"), row=1, col=1)
            fig.add_annotation(x=s["t_str"], y=s["y"],
                               text=f"CHoCH ▲ @ ₹{s['y']}" if is_latest else f"BOS ▲ @ ₹{s['y']}",
                               showarrow=False, yshift=12, font=dict(size=10, color="#00E676"), row=1, col=1)

    if "Liquidity Rush & Profit Alerts" in show_layers:
        for _, r_row in df[df["Liq_Rush_Top"]].tail(4).iterrows():
            fig.add_annotation(
                x=r_row["Axis_Str"], y=r_row["High"],
                text=f"🚨 Liq Rush ({r_row['RVOL']:.1f}x) Book Profit",
                showarrow=True, arrowhead=2, arrowcolor="#FF5252", ay=-26,
                font=dict(size=10, color="#FF8A80"), bgcolor="rgba(30,0,0,0.7)",
                row=1, col=1,
            )

    if "Liquidity (BSL/SSL)" in show_layers:
        fig.add_hline(y=bsl_level, line_dash="dot", line_color="#AB47BC", line_width=1.2,
                      annotation_text=f"💧 BSL: ₹{bsl_level:,.2f}", annotation_position="top left",
                      annotation_font_color="#CE93D8", row=1, col=1)
        fig.add_hline(y=ssl_level, line_dash="dot", line_color="#FF7043", line_width=1.2,
                      annotation_text=f"💧 SSL: ₹{ssl_level:,.2f}", annotation_position="bottom left",
                      annotation_font_color="#FFAB91", row=1, col=1)

    if "Discount/Premium 50%" in show_layers:
        fig.add_hline(y=eq_level, line_dash="dashdot", line_color="#9E9E9E", line_width=1.0,
                      annotation_text=f"⚖️ 50% EQ: ₹{eq_level:,.2f}", annotation_position="top right",
                      annotation_font_color="#BDBDBD", row=1, col=1)

    if st.session_state.show_trade_lines:
        fig.add_hline(y=entry_p, line_dash="solid", line_color="#FFD700", line_width=1.5,
                      annotation_text=f"🟡 BUY: ₹{entry_p:,.2f}", annotation_position="bottom left",
                      annotation_font_color="#FFD700", row=1, col=1)
        fig.add_hline(y=t1_p, line_dash="dash", line_color="#29B6F6", line_width=1.4,
                      annotation_text=f"🎯 T1: ₹{t1_p:,.2f}", annotation_position="top left",
                      annotation_font_color="#29B6F6", row=1, col=1)
        fig.add_hline(y=t2_p, line_dash="dash", line_color="#00E676", line_width=1.4,
                      annotation_text=f"🚀 T2: ₹{t2_p:,.2f}", annotation_position="top right",
                      annotation_font_color="#00E676", row=1, col=1)

    # Range Bounds
    last_ts = df["Time"].iloc[-1]
    r_sel = st.session_state.range_choice
    if st.session_state.jump_date is not None:
        start_idx = max(0, int((df["Time"] - pd.Timestamp(st.session_state.jump_date)).abs().idxmin()))
    elif r_sel == "1d":
        last_date = df["Time"].dt.date.iloc[-1]
        start_idx = max(0, int(df[df["Time"].dt.date == last_date].index[0]) - 3) if is_intraday_tf else max(0, len(df) - 2)
    elif r_sel == "5d":
        matches = df[df["Time"] >= last_ts - timedelta(days=5)]
        start_idx = int(matches.index[0]) if (is_intraday_tf and not matches.empty) else max(0, len(df) - 5)
    elif r_sel == "1m":
        matches = df[df["Time"] >= last_ts - timedelta(days=30)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    elif r_sel == "3m":
        matches = df[df["Time"] >= last_ts - timedelta(days=90)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    elif r_sel == "6m":
        matches = df[df["Time"] >= last_ts - timedelta(days=180)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    elif r_sel == "YTD":
        matches = df[df["Time"] >= datetime(last_ts.year, 1, 1)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    elif r_sel == "1Y":
        matches = df[df["Time"] >= last_ts - timedelta(days=365)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    elif r_sel == "5Y":
        matches = df[df["Time"] >= last_ts - timedelta(days=365 * 5)]
        start_idx = int(matches.index[0]) if not matches.empty else 0
    else:
        start_idx = 0

    vis_df = df.iloc[start_idx:] if not df.iloc[start_idx:].empty else df
    y_vals = [float(vis_df["Low"].min()), float(vis_df["High"].max()), ltp, latest_chand]
    if st.session_state.show_trade_lines:
        y_vals.extend([entry_p, t1_p])
    if st.session_state.fit_far_smc_yaxis:
        if bull_fvg:
            y_vals.extend([bull_fvg[1], bull_fvg[2]])
        if bear_fvg:
            y_vals.extend([bear_fvg[1], bear_fvg[2]])
        if bull_ob:
            y_vals.extend([bull_ob[1], bull_ob[2]])

    y_min_raw, y_max_raw = min(y_vals), max(y_vals)
    y_pad = max((y_max_raw - y_min_raw) * 0.08, y_max_raw * 0.005)

    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    ist_now_str = ist_now.strftime("%H:%M:%S")
    market_open_minutes = 9 * 60 + 15
    market_close_minutes = 15 * 60 + 30
    now_minutes = ist_now.hour * 60 + ist_now.minute
    session_tag = "RTH" if (ist_now.weekday() < 5 and market_open_minutes <= now_minutes <= market_close_minutes) else "CLOSED"

    fig.update_layout(
        title=dict(
            text=f"{raw_sym} ({tf_choice}) | LTP: ₹{ltp:,.2f} | AI Profit Score: {latest_pb_score:.0f}/100 | Chandelier: ₹{latest_chand:,.2f}",
            x=0.01,
            y=0.985,
            font=dict(size=13, color="#E0E3EB"),
        ),
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        height=740 if show_nn_rsi else 650,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=34, b=24),
        yaxis=dict(
            side="right", title="Price (₹)", range=[y_min_raw - y_pad, y_max_raw + y_pad],
            showgrid=True, gridcolor="rgba(255,255,255,0.06)",
            showspikes=st.session_state.show_spikes, spikemode="across", spikesnap="cursor",
        ),
    )

    if vol_row is not None:
        fig.update_yaxes(side="right", title="Volume", showgrid=False, row=vol_row, col=1)
    if rsi_row is not None:
        fig.update_yaxes(side="right", title="NN-RSI", range=[0, 100], row=rsi_row, col=1)

    for r_idx in range(1, n_rows + 1):
        axis_kwargs = dict(
            type="category", rangeslider_visible=False, range=[start_idx, len(df) + 3],
            showspikes=st.session_state.show_spikes, spikemode="across", spikesnap="cursor",
            showgrid=True, gridcolor="rgba(255,255,255,0.06)",
        )
        if r_idx == n_rows:
            axis_kwargs.update(tickmode="auto", nticks=15, tickangle=0, tickfont=dict(size=11, color="#B0BEC5"))
        fig.update_xaxes(axis_kwargs, row=r_idx, col=1)

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-top-bar-marker),
        div[data-testid="stVerticalBlock"]:has(> div > .tv-top-bar-marker) {
            background-color: #131722 !important;
            border: 1px solid #2A2E39 !important;
            border-bottom: 1px solid #2A2E39 !important;
            border-radius: 4px 4px 0px 0px !important;
            padding: 3px 8px !important;
            margin-bottom: -16px !important;
            position: relative !important;
            z-index: 2 !important;
        }
        div[data-testid="stPlotlyChart"] {
            margin-top: 0px !important;
            margin-bottom: -18px !important;
            border-left: 1px solid #2A2E39 !important;
            border-right: 1px solid #2A2E39 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-bottom-bar-marker),
        div[data-testid="stVerticalBlock"]:has(> div > .tv-bottom-bar-marker) {
            background-color: #131722 !important;
            border: 1px solid #2A2E39 !important;
            border-radius: 0px 0px 4px 4px !important;
            padding: 2px 10px !important;
            margin-top: 0px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-top-bar-marker) button,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-top-bar-marker) button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-bottom-bar-marker) button,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-bottom-bar-marker) button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0px 4px !important;
            min-height: 26px !important;
            height: 26px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #D1D4DC !important;
            border-radius: 3px !important;
            white-space: nowrap !important;
            overflow: visible !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-top-bar-marker) button p,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-top-bar-marker) button p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-bottom-bar-marker) button p,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-bottom-bar-marker) button p {
            white-space: nowrap !important;
            font-size: 12px !important;
            margin: 0px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-top-bar-marker) button:hover,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-top-bar-marker) button:hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-bottom-bar-marker) button:hover,
        div[data-testid="stVerticalBlock"]:has(> div > .tv-bottom-bar-marker) button:hover {
            background-color: #2A2E39 !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-top-bar-marker) button[kind="primary"],
        div[data-testid="stVerticalBlock"]:has(> div > .tv-top-bar-marker) button[kind="primary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.tv-bottom-bar-marker) button[kind="primary"],
        div[data-testid="stVerticalBlock"]:has(> div > .tv-bottom-bar-marker) button[kind="primary"] {
            color: #2962FF !important;
            background-color: rgba(41, 98, 255, 0.16) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="tv-top-bar-marker" style="display:none;"></div>', unsafe_allow_html=True)
        top_weights = [0.46] * len(PRIMARY_INTERVALS) + [0.10, 0.65, 0.10, 1.35, 1.35, 1.05, 0.45]
        top_cols = st.columns(top_weights, gap="small")

        for idx_tf, tf_label in enumerate(PRIMARY_INTERVALS):
            is_active = st.session_state.tf_choice == tf_label
            if top_cols[idx_tf].button(
                tf_label,
                key=f"tv_top_tf_{tf_label}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                _switch_timeframe(tf_label)
                st.rerun()

        with top_cols[len(PRIMARY_INTERVALS)]:
            st.markdown("<div style='border-left:1px solid #2A2E39; height:20px; margin:3px auto;'></div>", unsafe_allow_html=True)

        with top_cols[len(PRIMARY_INTERVALS) + 1]:
            extra_active = tf_choice not in PRIMARY_INTERVALS
            more_label = f"⏱️ {tf_choice}" if extra_active else "⏱️ More"
            with st.popover(more_label, use_container_width=True):
                st.caption("MINUTES")
                m_cols = st.columns(4)
                for i_m, m_tf in enumerate(["1m", "2m", "3m", "5m", "10m", "15m", "30m", "45m"]):
                    if m_cols[i_m % 4].button(m_tf, key=f"pop_tf_{m_tf}", type="primary" if tf_choice == m_tf else "secondary", use_container_width=True):
                        _switch_timeframe(m_tf)
                        st.rerun()
                st.caption("HOURS")
                h_cols = st.columns(4)
                for i_h, h_tf in enumerate(["1h", "2h", "3h", "4h"]):
                    if h_cols[i_h].button(h_tf, key=f"pop_tf_{h_tf}", type="primary" if tf_choice == h_tf else "secondary", use_container_width=True):
                        _switch_timeframe(h_tf)
                        st.rerun()
                st.caption("DAYS / WEEKS / MONTHS")
                d_cols = st.columns(3)
                for i_d, d_tf in enumerate(["1D", "1W", "1M", "3M", "6M", "12M"]):
                    if d_cols[i_d % 3].button(d_tf, key=f"pop_tf_{d_tf}", type="primary" if tf_choice == d_tf else "secondary", use_container_width=True):
                        _switch_timeframe(d_tf)
                        st.rerun()

        with top_cols[len(PRIMARY_INTERVALS) + 2]:
            st.markdown("<div style='border-left:1px solid #2A2E39; height:20px; margin:3px auto;'></div>", unsafe_allow_html=True)

        with top_cols[len(PRIMARY_INTERVALS) + 3]:
            with st.popover("📈 Indicators", use_container_width=True):
                st.session_state.selected_indicators = st.multiselect(
                    "Select AI/ML Indicators", INDICATOR_OPTIONS, default=st.session_state.selected_indicators
                )

        with top_cols[len(PRIMARY_INTERVALS) + 4]:
            with st.popover("🧱 SMC Layers", use_container_width=True):
                st.session_state.show_layers = st.multiselect(
                    "Select SMC & Profit Alerts", SMC_LAYER_OPTIONS, default=st.session_state.show_layers
                )

        with top_cols[len(PRIMARY_INTERVALS) + 5]:
            with st.popover("⚙️ Settings", use_container_width=True):
                st.session_state.show_volume = st.checkbox("Show Volume / RVOL", value=st.session_state.show_volume)
                st.session_state.show_spikes = st.checkbox("Crosshair / Spikes", value=st.session_state.show_spikes)
                st.session_state.show_trade_lines = st.checkbox("BUY / SL / T1 / T2 Lines", value=st.session_state.show_trade_lines)
                st.session_state.fit_far_smc_yaxis = st.checkbox("Fit Far SMC Zones", value=st.session_state.fit_far_smc_yaxis)
                st.divider()
                st.session_state.auto_refresh = st.checkbox("Auto-Refresh Poll", value=st.session_state.auto_refresh)
                st.session_state.refresh_interval_sec = st.slider(
                    "Poll Interval (sec)", min_value=3, max_value=60, value=int(st.session_state.refresh_interval_sec), step=1
                )

        with top_cols[len(PRIMARY_INTERVALS) + 6]:
            if st.button("🔄", key="tv_top_refresh", help="Refresh Live Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    TV_RANGE_LABELS = ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "All"]
    TV_COL_WEIGHTS = [0.55, 0.55, 0.58, 0.58, 0.58, 0.72, 0.55, 0.55, 0.65, 0.12, 0.62, 3.2, 2.3]
    with st.container(border=True):
        st.markdown('<div class="tv-bottom-bar-marker" style="display:none;"></div>', unsafe_allow_html=True)
        bar_cols = st.columns(TV_COL_WEIGHTS, gap="small")

        for idx_r, r_disp in enumerate(TV_RANGE_LABELS):
            r_key = r_disp.lower() if r_disp in ["1D", "5D", "1M", "3M", "6M"] else r_disp
            is_r_active = (st.session_state.range_choice == r_key) and (st.session_state.jump_date is None)
            if bar_cols[idx_r].button(
                r_disp,
                key=f"tv_range_{r_disp}",
                type="primary" if is_r_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.range_choice = r_key
                st.session_state.jump_date = None
                st.rerun()

        with bar_cols[len(TV_RANGE_LABELS)]:
            st.markdown(
                "<div style='border-left:1px solid #2A2E39; height:20px; margin:3px auto;'></div>",
                unsafe_allow_html=True,
            )

        with bar_cols[len(TV_RANGE_LABELS) + 1]:
            with st.popover("📅", use_container_width=True):
                picked = st.date_input(
                    "Go to date",
                    value=st.session_state.jump_date or df["Time"].dt.date.iloc[-1],
                    min_value=df["Time"].dt.date.iloc[0],
                    max_value=df["Time"].dt.date.iloc[-1],
                )
                if st.button("Apply Date", use_container_width=True):
                    st.session_state.jump_date = picked
                    st.rerun()
                if st.session_state.jump_date is not None and st.button("Clear Jump", use_container_width=True):
                    st.session_state.jump_date = None
                    st.rerun()

        with bar_cols[-1]:
            st.markdown(
                f"<div style='text-align:right; color:#D1D4DC; font-size:12px; font-family:monospace; padding-top:4px; white-space:nowrap;'>"
                f"{ist_now_str} UTC+5:30 &nbsp; {session_tag} "
                f"<span style='color:#2A2E39;'>|</span> "
                f"<span style='color:#2962FF; font-weight:600;'>{price_source}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("📡 Advance AI Profit-Booking & Entry Radar (Multi-Stock Pre-Scanner)")
    scan_col1, scan_col2 = st.columns([1.5, 4.5])
    run_scan = scan_col1.button("🚀 Scan Filtered Stocks for Profit-Booking", use_container_width=True)
    scan_col2.caption("Ranks stocks in advance by AI Profit Score, Chandelier Trailing Exit, NN-RSI Exhaustion & BSL Proximity.")

    if run_scan:
        with st.spinner("Running AI/ML Volatility & Liquidity Sweep Scan across NSE stocks..."):
            radar_df = scan_advance_profit_bookings(filtered_stocks or NSE_STOCK_CATALOG)
            if not radar_df.empty:
                st.dataframe(radar_df, use_container_width=True, hide_index=True)
            else:
                st.info("No intraday bars returned right now (market closed or ticker limit). Try again during market hours.")

    if st.session_state.auto_refresh:
        time.sleep(int(st.session_state.refresh_interval_sec))
        st.rerun()
