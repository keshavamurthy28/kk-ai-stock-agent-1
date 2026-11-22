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

with st.expander("📘 Beginner Guide: Key-Factor Stock Search, SMC Zones & TradingView Controls", expanded=False):
    st.markdown(
        "- **Key-Factor Stock Search:** Filter NSE stocks by **Sector**, **Price Band**, or **Name/Symbol** (e.g., typing `data` or selecting `Defence & Aerospace` brings up `DATAPATTNS — Data Patterns (India) Ltd`).\n"
        "- **Connected TradingView Toolbars:** Switch candle intervals (`1m` to `12M`) directly from the top chart bar and zoom date ranges (`1D` to `All`) from the bottom chart bar.\n"
        "- **Institutional SMC & VWAP Bands:** Combines **4H Fair Value Gaps (FVG)**, **Bullish & Bearish Order Blocks**, **BOS / CHoCH**, **Liquidity Sweeps (RVOL >= 1.5x)**, and **VWAP Standard Deviation Bands**.\n"
        "- **Risk & Profit Reminder:** Always verify live prices on your broker before trading and respect stop-loss levels—no setup guarantees profit. Not financial advice."
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

PRIMARY_INTERVALS = ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"]

INDICATOR_OPTIONS = [
    "VWAP",
    "VWAP Bands (±1.5σ)",
    "20 EMA",
    "50 EMA",
    "200 EMA",
    "Bollinger Bands",
    "RSI (14)",
]

SMC_LAYER_OPTIONS = [
    "4H FVG",
    "Order Blocks (Bull & Bear)",
    "BOS / CHoCH",
    "Liquidity (BSL/SSL)",
    "Liquidity Sweeps (RVOL)",
    "Discount/Premium 50%",
]

# Isolated Session State Keys
_state_defaults = {
    "adv_smc_tf": "5m",
    "adv_smc_range": "1d",
    "adv_smc_indicators": ["VWAP", "20 EMA", "50 EMA"],
    "adv_smc_layers": [
        "4H FVG",
        "Order Blocks (Bull & Bear)",
        "BOS / CHoCH",
        "Liquidity (BSL/SSL)",
        "Liquidity Sweeps (RVOL)",
    ],
    "adv_smc_volume": True,
    "adv_smc_spikes": True,
    "adv_smc_trade_lines": True,
    "adv_smc_fit_far": False,
    "adv_smc_jump_date": None,
}
for k, v in _state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _switch_timeframe(tf_label: str):
    st.session_state.adv_smc_tf = tf_label
    st.session_state.adv_smc_jump_date = None
    if tf_label in ["1D", "1W", "1M", "3M", "6M", "12M"] and st.session_state.adv_smc_range in ["1d", "5d"]:
        st.session_state.adv_smc_range = "1Y" if tf_label in ["1D", "1W", "1M"] else "5Y"
    elif tf_label not in ["1D", "1W", "1M", "3M", "6M", "12M"] and st.session_state.adv_smc_range in ["1Y", "5Y", "All"]:
        st.session_state.adv_smc_range = "1d"


# --- TOP FILTER & SYMBOL SELECTION BAR ---
kf1, kf2, kf3, kf4 = st.columns([1.4, 1.3, 1.5, 2.0])
selected_sector = kf1.selectbox("🏷️ Filter by Sector", SECTOR_OPTIONS, index=0)
selected_price_band = kf2.selectbox("💰 Filter by Price Tier", PRICE_BAND_OPTIONS, index=0)
typed_query = (
    kf3.text_input(
        "🔍 NSE Symbol or Name",
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

with kf4:
    if filtered_stocks:
        options_list = [f"{sym} — {name} [{sec}]" for sym, name, sec, _ in filtered_stocks]
        if q_clean and q_clean not in [s for s, _, _, _ in filtered_stocks]:
            options_list.insert(0, f"{q_clean} — Custom NSE Symbol ({q_clean}.NS)")
        selected_entry = st.selectbox(
            f"📋 Matching NSE Stocks ({len(options_list)} shown)",
            options_list,
            index=0,
            key="adv_smc_nse_select",
        )
        raw_sym = selected_entry.split(" — ")[0].strip().upper()
    else:
        raw_sym = q_clean or "LICHSGFIN"

ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"
tf_choice = st.session_state.adv_smc_tf


@st.cache_data(ttl=15)
def fetch_clean_smc(sym, tf):
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

    t_obj = yf.Ticker(sym)
    df = t_obj.history(period=p_map[tf], interval=i_map[tf], auto_adjust=True)
    df4 = t_obj.history(period="60d", interval="1h", auto_adjust=True)

    req = {"Open", "High", "Low", "Close", "Volume"}
    if df is None or df.empty or not req.issubset(set(df.columns)):
        return pd.DataFrame(), pd.DataFrame()

    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is not None:
        df["Time"] = df["Time"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)

    if tf in ["2m", "3m", "10m", "45m", "2h", "3h", "4h", "6M", "12M"]:
        rule_map = {
            "2m": ("2min", "0min"),
            "3m": ("3min", "0min"),
            "10m": ("10min", "0min"),
            "45m": ("45min", "15min"),
            "2h": ("2h", "15min"),
            "3h": ("3h", "15min"),
            "4h": ("4h", "15min"),
            "6M": ("6ME", None),
            "12M": ("12ME", None),
        }
        rule, offset = rule_map[tf]
        resampler = df.set_index("Time").resample(rule, offset=offset) if offset else df.set_index("Time").resample(rule)
        df = (
            resampler.agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
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

    return df, df4


df, df_4h = fetch_clean_smc(ticker, tf_choice)

if df.empty:
    st.error(
        f"No data returned for {ticker} on `{tf_choice}` interval. Check the exact NSE ticker (e.g., `DATAPATTNS`)."
    )
else:
    df = df.reset_index(drop=True)
    ltp = float(df["Close"].iloc[-1])
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

    # Calculate Technical & Institutional Quant Indicators
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # Session VWAP + Standard Deviation Bands
    typical_p = (df["High"] + df["Low"] + df["Close"]) / 3.0
    if df["Volume"].sum() > 0:
        grp_date = df["Time"].dt.date
        cum_pv = (typical_p * df["Volume"]).groupby(grp_date).cumsum()
        cum_v = df["Volume"].groupby(grp_date).cumsum().replace(0, np.nan)
        df["VWAP"] = (cum_pv / cum_v).fillna(df["EMA20"])
        sq_diff = ((typical_p - df["VWAP"]) ** 2) * df["Volume"]
        vwap_var = (sq_diff.groupby(grp_date).cumsum() / cum_v).fillna(0.0)
        vwap_std = np.sqrt(vwap_var)
        df["VWAP_Upper"] = df["VWAP"] + (1.5 * vwap_std)
        df["VWAP_Lower"] = df["VWAP"] - (1.5 * vwap_std)
    else:
        df["VWAP"] = df["EMA20"]
        df["VWAP_Upper"] = df["EMA20"]
        df["VWAP_Lower"] = df["EMA20"]

    # ATR (14)
    prev_close = df["Close"].shift(1).fillna(df["Close"])
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR14"] = tr.ewm(span=14, adjust=False).mean().bfill()

    # Bollinger Bands
    bb_mid = df["Close"].rolling(20, min_periods=1).mean()
    bb_std = df["Close"].rolling(20, min_periods=1).std().fillna(0.0)
    df["BB_Upper"] = bb_mid + (2.0 * bb_std)
    df["BB_Lower"] = bb_mid - (2.0 * bb_std)

    # Wilder's RSI (14)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    # Relative Volume (RVOL) & Liquidity Sweep Detection
    v_avg = df["Volume"].rolling(20, min_periods=1).mean().replace(0, np.nan)
    df["RVOL"] = (df["Volume"] / v_avg).fillna(1.0)

    prior_high_15 = df["High"].shift(1).rolling(15, min_periods=3).max()
    prior_low_15 = df["Low"].shift(1).rolling(15, min_periods=3).min()
    df["BSL_Sweep"] = (df["High"] > prior_high_15) & (df["Close"] < prior_high_15) & (df["RVOL"] >= 1.5)
    df["SSL_Sweep"] = (df["Low"] < prior_low_15) & (df["Close"] > prior_low_15) & (df["RVOL"] >= 1.5)

    latest_vwap = float(df["VWAP"].iloc[-1])
    latest_atr = float(df["ATR14"].iloc[-1])
    latest_rvol = float(df["RVOL"].iloc[-1])
    latest_rsi = float(df["RSI14"].iloc[-1])

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

    # 2. Institutional Bullish & Bearish Order Blocks
    bull_ob, bear_ob = None, None
    for i in range(len(df) - 2, 1, -1):
        if bull_ob is None:
            is_red = df["Close"].iloc[i] < df["Open"].iloc[i]
            next_strong_green = (df["Close"].iloc[i + 1] > df["Open"].iloc[i + 1]) and (df["RVOL"].iloc[i + 1] >= 1.4)
            if is_red and next_strong_green:
                bull_ob = (df["Axis_Str"].iloc[i], float(df["Low"].iloc[i]), float(df["High"].iloc[i]))
        if bear_ob is None:
            is_green = df["Close"].iloc[i] > df["Open"].iloc[i]
            next_strong_red = (df["Close"].iloc[i + 1] < df["Open"].iloc[i + 1]) and (df["RVOL"].iloc[i + 1] >= 1.4)
            if is_green and next_strong_red:
                bear_ob = (df["Axis_Str"].iloc[i], float(df["Low"].iloc[i]), float(df["High"].iloc[i]))
        if bull_ob and bear_ob:
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
    ssl_level = round(float(df["Low"].iloc[-lookback:].min()), 2)
    eq_level = round((bsl_level + ssl_level) / 2.0, 2)
    zone_tag = (
        "DISCOUNT ZONE (Good Value) 🟢"
        if ltp <= eq_level
        else "PREMIUM ZONE (Wait Pullback) 🟠"
    )

    # 5. ATR-Validated Execution Levels & Risk-Reward Ratio
    if bull_ob and bull_ob[1] <= ltp <= bull_ob[2] * 1.02:
        entry_p = round(bull_ob[2], 2)
    elif bull_fvg and bull_fvg[1] <= ltp <= bull_fvg[2] * 1.02:
        entry_p = round(bull_fvg[2], 2)
    elif sigs:
        entry_p = round(max(sigs[-1]["y"], latest_vwap), 2)
    else:
        entry_p = round(max(latest_vwap, ltp * 0.995), 2)

    raw_sl = (
        bull_ob[1] - (0.3 * latest_atr)
        if bull_ob
        else (bull_fvg[1] - (0.3 * latest_atr) if bull_fvg else entry_p - (1.5 * latest_atr))
    )
    sl_p = round(min(raw_sl, entry_p - (0.8 * latest_atr)), 2)
    risk = max(entry_p - sl_p, latest_atr * 0.5, entry_p * 0.005)
    t1_p = round(entry_p + risk * 1.5, 2)
    t2_p = round(max(bsl_level, entry_p + risk * 2.5), 2)
    rr_ratio = round((t2_p - entry_p) / risk, 2)

    # Push SMC Blueprint to Session State
    st.session_state.setdefault("live_scanner_picks", {})["SMC Terminal Blueprint"] = [
        {
            "symbol": ticker,
            "side": "BUY",
            "entry": float(entry_p),
            "sl": float(sl_p),
            "t1": float(t1_p),
            "t2": float(t2_p),
            "notes": f"SMC {tf_choice} | R:R 1:{rr_ratio} | {'Discount' if ltp <= eq_level else 'Premium'}",
        }
    ]

    # --- INSTITUTIONAL EXECUTION BLUEPRINT METRICS ---
    st.subheader(f"📊 Institutional SMC Execution Blueprint: {raw_sym} ({tf_choice})")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Last Price", f"₹{ltp:,.2f}", f"RVOL {latest_rvol:.2f}x | RSI {latest_rsi:.0f}")
    m2.metric("🟡 Reference Buy", f"₹{entry_p:,.2f}", zone_tag)
    m3.metric("🛑 ATR Stop-Loss", f"₹{sl_p:,.2f}", f"ATR(14): ₹{latest_atr:,.2f}")
    m4.metric("🎯 Target 1 (1.5R)", f"₹{t1_p:,.2f}", "Book Partial Profit")
    m5.metric("🚀 Target 2 (BSL)", f"₹{t2_p:,.2f}", f"R:R 1:{rr_ratio}")
    m6.metric("⚖️ Equilibrium (50%)", f"₹{eq_level:,.2f}", f"VWAP ₹{latest_vwap:,.2f}")

    # Build Multi-Panel Plotly Figure
    selected_indicators = st.session_state.adv_smc_indicators
    show_layers = st.session_state.adv_smc_layers
    show_volume = st.session_state.adv_smc_volume
    show_spikes = st.session_state.adv_smc_spikes
    show_trade_lines = st.session_state.adv_smc_trade_lines
    fit_far_smc_yaxis = st.session_state.adv_smc_fit_far

    show_rsi = "RSI (14)" in selected_indicators
    panels = ["price"] + (["volume"] if show_volume else []) + (["rsi"] if show_rsi else [])
    n_rows = len(panels)
    vol_row = panels.index("volume") + 1 if "volume" in panels else None
    rsi_row = panels.index("rsi") + 1 if "rsi" in panels else None

    if n_rows == 3:
        row_heights = [0.64, 0.18, 0.18]
    elif n_rows == 2:
        row_heights = [0.78, 0.22]
    else:
        row_heights = [1.0]

    end_str = df["Axis_Str"].iloc[-1]

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025 if n_rows > 1 else 0.01,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Axis_Str"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )

    if "VWAP" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["VWAP"],
                mode="lines",
                name="VWAP",
                line=dict(color="#FFD700", width=1.5),
            ),
            row=1,
            col=1,
        )
    if "VWAP Bands (±1.5σ)" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["VWAP_Upper"],
                mode="lines",
                name="VWAP +1.5σ",
                line=dict(color="rgba(255, 215, 0, 0.45)", width=1.0, dash="dot"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["VWAP_Lower"],
                mode="lines",
                name="VWAP -1.5σ",
                fill="tonexty",
                fillcolor="rgba(255, 215, 0, 0.05)",
                line=dict(color="rgba(255, 215, 0, 0.45)", width=1.0, dash="dot"),
            ),
            row=1,
            col=1,
        )
    if "20 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA20"],
                mode="lines",
                name="20 EMA",
                line=dict(color="#29B6F6", width=1.2),
            ),
            row=1,
            col=1,
        )
    if "50 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA50"],
                mode="lines",
                name="50 EMA",
                line=dict(color="#FFA726", width=1.3),
            ),
            row=1,
            col=1,
        )
    if "200 EMA" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["EMA200"],
                mode="lines",
                name="200 EMA",
                line=dict(color="#EC407A", width=1.4),
            ),
            row=1,
            col=1,
        )
    if "Bollinger Bands" in selected_indicators:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["BB_Upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="rgba(179, 157, 219, 0.7)", width=1.1, dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["BB_Lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="rgba(179, 157, 219, 0.7)", width=1.1, dash="dash"),
            ),
            row=1,
            col=1,
        )

    if vol_row is not None:
        fig.add_trace(
            go.Bar(x=df["Axis_Str"], y=df["Volume"], name="Volume (RVOL Colored)", marker_color=v_col),
            row=vol_row,
            col=1,
        )

    if rsi_row is not None:
        fig.add_trace(
            go.Scatter(
                x=df["Axis_Str"],
                y=df["RSI14"],
                mode="lines",
                name="RSI (14)",
                line=dict(color="#CE93D8", width=1.5),
            ),
            row=rsi_row,
            col=1,
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#FF5252", line_width=1, row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00E676", line_width=1, row=rsi_row, col=1)

    if "4H FVG" in show_layers:
        if bull_fvg:
            xs_str = map_time_to_str(bull_fvg[0])
            fig.add_shape(
                type="rect",
                x0=xs_str,
                x1=end_str,
                y0=bull_fvg[1],
                y1=bull_fvg[2],
                fillcolor="rgba(0, 230, 118, 0.14)",
                line=dict(color="rgba(0, 230, 118, 0.4)", width=1),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=xs_str,
                y=bull_fvg[2],
                text=f"4H Demand FVG (₹{bull_fvg[1]:,.1f}–₹{bull_fvg[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=10,
                font=dict(size=10, color="#00E676"),
                row=1,
                col=1,
            )
        if bear_fvg:
            xs_b_str = map_time_to_str(bear_fvg[0])
            fig.add_shape(
                type="rect",
                x0=xs_b_str,
                x1=end_str,
                y0=bear_fvg[1],
                y1=bear_fvg[2],
                fillcolor="rgba(255, 82, 82, 0.12)",
                line=dict(color="rgba(255, 82, 82, 0.4)", width=1),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=xs_b_str,
                y=bear_fvg[1],
                text=f"4H Supply FVG (₹{bear_fvg[1]:,.1f}–₹{bear_fvg[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=-12,
                font=dict(size=10, color="#FF5252"),
                row=1,
                col=1,
            )

    if "Order Blocks (Bull & Bear)" in show_layers:
        if bull_ob:
            fig.add_shape(
                type="rect",
                x0=bull_ob[0],
                x1=end_str,
                y0=bull_ob[1],
                y1=bull_ob[2],
                fillcolor="rgba(41, 182, 246, 0.16)",
                line=dict(color="#29B6F6", width=1, dash="dot"),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=bull_ob[0],
                y=bull_ob[1],
                text=f"🏦 Bullish OB (₹{bull_ob[1]:,.1f}–₹{bull_ob[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=-12,
                font=dict(size=10, color="#29B6F6"),
                row=1,
                col=1,
            )
        if bear_ob:
            fig.add_shape(
                type="rect",
                x0=bear_ob[0],
                x1=end_str,
                y0=bear_ob[1],
                y1=bear_ob[2],
                fillcolor="rgba(255, 112, 67, 0.14)",
                line=dict(color="#FF7043", width=1, dash="dot"),
                layer="below",
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=bear_ob[0],
                y=bear_ob[2],
                text=f"🏦 Bearish OB (₹{bear_ob[1]:,.1f}–₹{bear_ob[2]:,.1f})",
                showarrow=False,
                xanchor="left",
                yshift=10,
                font=dict(size=10, color="#FF8A65"),
                row=1,
                col=1,
            )

    if "BOS / CHoCH" in show_layers:
        for idx_s, s in enumerate(sigs[-3:]):
            is_latest = idx_s == len(sigs[-3:]) - 1
            fig.add_shape(
                type="line",
                x0=s["x0_str"],
                x1=s["t_str"],
                y0=s["y"],
                y1=s["y"],
                line=dict(color="#00E676", width=1.4, dash="dot"),
                row=1,
                col=1,
            )
            fig.add_annotation(
                x=s["t_str"],
                y=s["y"],
                text=f"CHoCH ▲ @ ₹{s['y']}" if is_latest else f"BOS ▲ @ ₹{s['y']}",
                showarrow=False,
                yshift=12,
                font=dict(size=10, color="#00E676"),
                row=1,
                col=1,
            )

    if "Liquidity Sweeps (RVOL)" in show_layers:
        for _, r_row in df[df["BSL_Sweep"]].tail(3).iterrows():
            fig.add_annotation(
                x=r_row["Axis_Str"],
                y=r_row["High"],
                text=f"⚡ BSL Sweep ({r_row['RVOL']:.1f}x)",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#FF5252",
                ay=-24,
                font=dict(size=10, color="#FF8A80"),
                bgcolor="rgba(30,0,0,0.7)",
                row=1,
                col=1,
            )
        for _, s_row in df[df["SSL_Sweep"]].tail(3).iterrows():
            fig.add_annotation(
                x=s_row["Axis_Str"],
                y=s_row["Low"],
                text=f"⚡ SSL Sweep ({s_row['RVOL']:.1f}x)",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#00E676",
                ay=24,
                font=dict(size=10, color="#69F0AE"),
                bgcolor="rgba(0,30,10,0.7)",
                row=1,
                col=1,
            )

    if "Liquidity (BSL/SSL)" in show_layers:
        fig.add_hline(
            y=bsl_level,
            line_dash="dot",
            line_color="#AB47BC",
            line_width=1.2,
            annotation_text=f"💧 BSL: ₹{bsl_level:,.2f}",
            annotation_position="top left",
            annotation_font_color="#CE93D8",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=ssl_level,
            line_dash="dot",
            line_color="#FF7043",
            line_width=1.2,
            annotation_text=f"💧 SSL: ₹{ssl_level:,.2f}",
            annotation_position="bottom left",
            annotation_font_color="#FFAB91",
            row=1,
            col=1,
        )

    if "Discount/Premium 50%" in show_layers:
        fig.add_hline(
            y=eq_level,
            line_dash="dashdot",
            line_color="#9E9E9E",
            line_width=1.0,
            annotation_text=f"⚖️ 50% EQ: ₹{eq_level:,.2f}",
            annotation_position="top right",
            annotation_font_color="#BDBDBD",
            row=1,
            col=1,
        )

    if show_trade_lines:
        fig.add_hline(
            y=entry_p,
            line_dash="solid",
            line_color="#FFD700",
            line_width=1.6,
            annotation_text=f"🟡 BUY: ₹{entry_p:,.2f}",
            annotation_position="bottom left",
            annotation_font_color="#FFD700",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=sl_p,
            line_dash="solid",
            line_color="#FF5252",
            line_width=1.6,
            annotation_text=f"🛑 SL: ₹{sl_p:,.2f}",
            annotation_position="bottom right",
            annotation_font_color="#FF5252",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=t1_p,
            line_dash="dash",
            line_color="#29B6F6",
            line_width=1.4,
            annotation_text=f"🎯 T1: ₹{t1_p:,.2f}",
            annotation_position="top left",
            annotation_font_color="#29B6F6",
            row=1,
            col=1,
        )
        fig.add_hline(
            y=t2_p,
            line_dash="dash",
            line_color="#00E676",
            line_width=1.4,
            annotation_text=f"🚀 T2: ₹{t2_p:,.2f}",
            annotation_position="top right",
            annotation_font_color="#00E676",
            row=1,
            col=1,
        )

    # Compute Start Index from Bottom Range Selector or Jump Date
    last_ts = df["Time"].iloc[-1]
    r_sel = st.session_state.adv_smc_range

    if st.session_state.adv_smc_jump_date is not None:
        target_dt = pd.Timestamp(st.session_state.adv_smc_jump_date)
        start_idx = max(0, int((df["Time"] - target_dt).abs().idxmin()))
    elif r_sel == "1d":
        if is_intraday_tf:
            last_date = df["Time"].dt.date.iloc[-1]
            start_idx = max(0, int(df[df["Time"].dt.date == last_date].index[0]) - 3)
        else:
            start_idx = max(0, len(df) - 2)
    elif r_sel == "5d":
        if is_intraday_tf:
            matches = df[df["Time"] >= last_ts - timedelta(days=5)]
            start_idx = int(matches.index[0]) if not matches.empty else 0
        else:
            start_idx = max(0, len(df) - 5)
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

    # Focused Y-Axis Range so Far SMC Zones Don't Squash Recent Candles
    vis_df = df.iloc[start_idx:] if not df.iloc[start_idx:].empty else df
    y_vals = [float(vis_df["Low"].min()), float(vis_df["High"].max()), ltp]
    if "VWAP" in selected_indicators and not vis_df["VWAP"].isna().all():
        y_vals.extend([float(vis_df["VWAP"].min()), float(vis_df["VWAP"].max())])
    if "20 EMA" in selected_indicators and not vis_df["EMA20"].isna().all():
        y_vals.extend([float(vis_df["EMA20"].min()), float(vis_df["EMA20"].max())])
    if show_trade_lines:
        y_vals.extend([entry_p, sl_p, t1_p])
    if fit_far_smc_yaxis:
        if bull_fvg:
            y_vals.extend([bull_fvg[1], bull_fvg[2]])
        if bear_fvg:
            y_vals.extend([bear_fvg[1], bear_fvg[2]])
        if bull_ob:
            y_vals.extend([bull_ob[1], bull_ob[2]])
        if bear_ob:
            y_vals.extend([bear_ob[1], bear_ob[2]])

    y_min_raw, y_max_raw = min(y_vals), max(y_vals)
    y_pad = max((y_max_raw - y_min_raw) * 0.08, y_max_raw * 0.005)

    active_ind_text = ", ".join(selected_indicators) if selected_indicators else "None"
    ist_now_str = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M:%S")

    fig.update_layout(
        title=dict(
            text=f"{raw_sym} ({tf_choice}) | LTP: ₹{ltp:,.2f} | R:R 1:{rr_ratio} | Ind: {active_ind_text}",
            x=0.01,
            y=0.985,
            font=dict(size=13, color="#E0E3EB"),
        ),
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        height=720 if show_rsi else 650,
        dragmode="pan",
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=10, r=65, t=34, b=24),
        yaxis=dict(
            side="right",
            title="Price (₹)",
            range=[y_min_raw - y_pad, y_max_raw + y_pad],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            showspikes=show_spikes,
            spikemode="across",
            spikesnap="cursor",
            spikecolor="#78909C",
            spikethickness=1,
            spikedash="dash",
        ),
    )

    if vol_row is not None:
        fig.update_yaxes(side="right", title="Volume", showgrid=False, row=vol_row, col=1)
    if rsi_row is not None:
        fig.update_yaxes(side="right", title="RSI", range=[0, 100], row=rsi_row, col=1)

    for r_idx in range(1, n_rows + 1):
        axis_kwargs = dict(
            type="category",
            rangeslider_visible=False,
            range=[start_idx, len(df) + 3],
            showspikes=show_spikes,
            spikemode="across",
            spikesnap="cursor",
            spikecolor="#78909C",
            spikethickness=1,
            spikedash="dash",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
        )
        if r_idx == n_rows:
            axis_kwargs.update(
                tickmode="auto",
                nticks=15,
                tickangle=0,
                tickfont=dict(size=11, color="#B0BEC5"),
            )
        fig.update_xaxes(axis_kwargs, row=r_idx, col=1)

    # TradingView Connected Top Bar + Connected Bottom Bar CSS
    st.markdown(
        """
        <style>
        /* Connected TradingView TOP Interval & Indicator Bar (Flush above chart title) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-top-marker),
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-top-marker) {
            background-color: #131722 !important;
            border: 1px solid #2A2E39 !important;
            border-bottom: 1px solid #2A2E39 !important;
            border-radius: 4px 4px 0px 0px !important;
            padding: 3px 8px !important;
            margin-bottom: -16px !important;
            position: relative !important;
            z-index: 2 !important;
        }
        /* Flush Plotly Chart Frame */
        div[data-testid="stPlotlyChart"] {
            margin-top: 0px !important;
            margin-bottom: -18px !important;
            border-left: 1px solid #2A2E39 !important;
            border-right: 1px solid #2A2E39 !important;
        }
        /* Connected TradingView BOTTOM Range Bar */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-bottom-marker),
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-bottom-marker) {
            background-color: #131722 !important;
            border: 1px solid #2A2E39 !important;
            border-radius: 0px 0px 4px 4px !important;
            padding: 2px 10px !important;
            margin-top: 0px !important;
        }
        /* Flat Single-Line TradingView Labels for Both Connected Bars */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-top-marker) button,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-top-marker) button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-bottom-marker) button,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-bottom-marker) button {
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
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-top-marker) button p,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-top-marker) button p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-bottom-marker) button p,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-bottom-marker) button p {
            white-space: nowrap !important;
            font-size: 12px !important;
            margin: 0px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-top-marker) button:hover,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-top-marker) button:hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-bottom-marker) button:hover,
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-bottom-marker) button:hover {
            background-color: #2A2E39 !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-top-marker) button[kind="primary"],
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-top-marker) button[kind="primary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.adv-tv-bottom-marker) button[kind="primary"],
        div[data-testid="stVerticalBlock"]:has(> div > .adv-tv-bottom-marker) button[kind="primary"] {
            color: #2962FF !important;
            background-color: rgba(41, 98, 255, 0.16) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- CONNECTED TOP TRADINGVIEW BAR (Right above Symbol & LTP header) ---
    with st.container(border=True):
        st.markdown('<div class="adv-tv-top-marker" style="display:none;"></div>', unsafe_allow_html=True)
        top_weights = [0.46] * len(PRIMARY_INTERVALS) + [0.10, 0.65, 0.10, 1.35, 1.35, 1.05, 0.45]
        top_cols = st.columns(top_weights, gap="small")

        for idx_tf, tf_label in enumerate(PRIMARY_INTERVALS):
            is_active = st.session_state.adv_smc_tf == tf_label
            if top_cols[idx_tf].button(
                tf_label,
                key=f"adv_tv_top_tf_{tf_label}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                _switch_timeframe(tf_label)
                st.rerun()

        with top_cols[len(PRIMARY_INTERVALS)]:
            st.markdown("<div style='border-left:1px solid #2A2E39; height:20px; margin:3px auto;'></div>", unsafe_allow_html=True)

        # Categorized TradingView Interval Menu (Minutes / Hours / Days & Months)
        with top_cols[len(PRIMARY_INTERVALS) + 1]:
            extra_active = tf_choice not in PRIMARY_INTERVALS
            more_label = f"⏱️ {tf_choice}" if extra_active else "⏱️ More"
            with st.popover(more_label, use_container_width=True):
                st.caption("MINUTES")
                m_cols = st.columns(4)
                for i_m, m_tf in enumerate(["1m", "2m", "3m", "5m", "10m", "15m", "30m", "45m"]):
                    if m_cols[i_m % 4].button(m_tf, key=f"adv_pop_tf_{m_tf}", type="primary" if tf_choice == m_tf else "secondary", use_container_width=True):
                        _switch_timeframe(m_tf)
                        st.rerun()
                st.caption("HOURS")
                h_cols = st.columns(4)
                for i_h, h_tf in enumerate(["1h", "2h", "3h", "4h"]):
                    if h_cols[i_h].button(h_tf, key=f"adv_pop_tf_{h_tf}", type="primary" if tf_choice == h_tf else "secondary", use_container_width=True):
                        _switch_timeframe(h_tf)
                        st.rerun()
                st.caption("DAYS / WEEKS / MONTHS")
                d_cols = st.columns(3)
                for i_d, d_tf in enumerate(["1D", "1W", "1M", "3M", "6M", "12M"]):
                    if d_cols[i_d % 3].button(d_tf, key=f"adv_pop_tf_{d_tf}", type="primary" if tf_choice == d_tf else "secondary", use_container_width=True):
                        _switch_timeframe(d_tf)
                        st.rerun()

        with top_cols[len(PRIMARY_INTERVALS) + 2]:
            st.markdown("<div style='border-left:1px solid #2A2E39; height:20px; margin:3px auto;'></div>", unsafe_allow_html=True)

        with top_cols[len(PRIMARY_INTERVALS) + 3]:
            with st.popover("📈 Indicators", use_container_width=True):
                st.session_state.adv_smc_indicators = st.multiselect(
                    "Select Indicators",
                    INDICATOR_OPTIONS,
                    default=st.session_state.adv_smc_indicators,
                    key="adv_ind_ms",
                )

        with top_cols[len(PRIMARY_INTERVALS) + 4]:
            with st.popover("🧱 SMC Layers", use_container_width=True):
                st.session_state.adv_smc_layers = st.multiselect(
                    "Select SMC Overlays",
                    SMC_LAYER_OPTIONS,
                    default=st.session_state.adv_smc_layers,
                    key="adv_smc_ms",
                )

        with top_cols[len(PRIMARY_INTERVALS) + 5]:
            with st.popover("⚙️ Settings", use_container_width=True):
                st.session_state.adv_smc_volume = st.checkbox(
                    "Show Volume Panel", value=st.session_state.adv_smc_volume, key="adv_chk_vol"
                )
                st.session_state.adv_smc_spikes = st.checkbox(
                    "Crosshair / Spikes", value=st.session_state.adv_smc_spikes, key="adv_chk_spk"
                )
                st.session_state.adv_smc_trade_lines = st.checkbox(
                    "BUY / SL / T1 / T2 Lines", value=st.session_state.adv_smc_trade_lines, key="adv_chk_trd"
                )
                st.session_state.adv_smc_fit_far = st.checkbox(
                    "Fit Far SMC Zones on Y-Axis", value=st.session_state.adv_smc_fit_far, key="adv_chk_fit"
                )

        with top_cols[len(PRIMARY_INTERVALS) + 6]:
            if st.button("🔄", key="adv_tv_top_refresh", help="Refresh Live Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

    # --- MAIN CHART CANVAS ---
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    # --- CONNECTED BOTTOM TRADINGVIEW BAR (1D 5D 1M 3M 6M YTD 1Y 5Y All | 📅  <--->  HH:MM:SS UTC+5:30 RTH | ADJ) ---
    TV_RANGE_LABELS = ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "All"]
    TV_COL_WEIGHTS = [0.55, 0.55, 0.58, 0.58, 0.58, 0.72, 0.55, 0.55, 0.65, 0.12, 0.62, 3.2, 2.3]
    with st.container(border=True):
        st.markdown('<div class="adv-tv-bottom-marker" style="display:none;"></div>', unsafe_allow_html=True)
        bar_cols = st.columns(TV_COL_WEIGHTS, gap="small")

        for idx_r, r_disp in enumerate(TV_RANGE_LABELS):
            r_key = r_disp.lower() if r_disp in ["1D", "5D", "1M", "3M", "6M"] else r_disp
            is_r_active = (st.session_state.adv_smc_range == r_key) and (st.session_state.adv_smc_jump_date is None)
            if bar_cols[idx_r].button(
                r_disp,
                key=f"adv_tv_range_{r_disp}",
                type="primary" if is_r_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.adv_smc_range = r_key
                st.session_state.adv_smc_jump_date = None
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
                    value=st.session_state.adv_smc_jump_date or df["Time"].dt.date.iloc[-1],
                    min_value=df["Time"].dt.date.iloc[0],
                    max_value=df["Time"].dt.date.iloc[-1],
                    key="adv_jump_date_input",
                )
                if st.button("Apply Date", key="adv_apply_date", use_container_width=True):
                    st.session_state.adv_smc_jump_date = picked
                    st.rerun()
                if st.session_state.adv_smc_jump_date is not None and st.button("Clear Jump", key="adv_clear_date", use_container_width=True):
                    st.session_state.adv_smc_jump_date = None
                    st.rerun()

        with bar_cols[-1]:
            st.markdown(
                f"<div style='text-align:right; color:#D1D4DC; font-size:12px; font-family:monospace; padding-top:4px; white-space:nowrap;'>"
                f"{ist_now_str} UTC+5:30   RTH "
                f"<span style='color:#2A2E39;'>|</span> "
                f"<span style='color:#2962FF; font-weight:600;'>ADJ</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
