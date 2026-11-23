from datetime import datetime, time as dt_time
import math
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Nifty Options Layman Guide | ₹5,000 Goal & Expiry Alert",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
current_time = now_ist.time()
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= current_time <= dt_time(15, 30)
)

ADVANCE_ALERT_POINTS = 40.0
LOT_SIZE = 65
EXPIRY_CHOICES = [
    "23 Nov (Today)",
    "1 Dec (8 days)",
    "8 Dec (2 weeks)",
    "15 Dec (3 weeks)",
    "22 Dec (4 weeks)",
    "29 Dec (1 month)",
    "25 Jan (2 months)",
    "30 Mar (4 months)",
    "29 Jun (7 months)",
    "28 Sep (10 months)",
    "28 Dec (1 year)",
]

# ---------------------------------------------------------
# HEADER & LIVE REFRESH BAR
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([3, 1.2])
with head_col1:
    st.title("⚡ Nifty Options Top Action & Expiry Guide")
    st.markdown(
        "Plain-English **Top Trade Table** for **NIFTY 50** options with a **₹5,000 profit goal**, "
        "**exact Buy / Sell / Stop-Loss prices**, **expiry exit warnings**, and a "
        "**Kite-colored Option Chain table** below the chart. "
        "*(Educational tool only — verify live prices on Kite.)*"
    )

with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    r_col1, r_col2, r_col3 = st.columns([1.2, 1, 1])
    with r_col1:
        if st.button("🔄 Refresh", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.toast("Refreshing Nifty & Option Chain...", icon="⚡")
            st.rerun()
    with r_col2:
        live_stream = st.toggle("Live (15s)", value=False)
    with r_col3:
        auto_refresh = st.toggle("Auto (60s)", value=False)
    market_badge = "🟢 Market Open" if is_market_open else "🟡 Market Closed"
    st.caption(f"{market_badge} • **{now_ist.strftime('%I:%M:%S %p IST')}**")

st.markdown("---")

# ---------------------------------------------------------
# 1. CONTROLS (EXPIRY DATES, LOTS, PROFIT GOAL, EXPECTED PT MOVE)
# ---------------------------------------------------------
col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([1.8, 1.3, 1.2, 1.2, 1.2])

with col_c1:
    expiry_choice = st.selectbox(
        "📅 Expiry Date",
        EXPIRY_CHOICES,
        index=0,
    )

with col_c2:
    lot_multiplier = st.selectbox(
        "📦 Selected Lots (1 Lot = 65)",
        [
            "1 Lot (65 Qty)",
            "2 Lots (130 Qty)",
            "4 Lots (260 Qty)",
            "8 Lots (520 Qty)",
        ],
        index=0,
    )

with col_c3:
    profit_goal_rs = st.number_input(
        "🎯 Profit Target (₹)",
        min_value=500,
        max_value=100000,
        value=5000,
        step=500,
    )

with col_c4:
    expected_pt_gain = st.number_input(
        "📈 Expected Pt Gain",
        min_value=1.0,
        max_value=500.0,
        value=15.0,
        step=1.0,
    )

with col_c5:
    timeframe_choice = st.selectbox(
        "⏱️ Chart Speed",
        ["15m (Intraday)", "5m (Quick Scalp)", "1h (Broader Move)"],
        index=0,
    )

qty_map = {
    "1 Lot (65 Qty)": 65,
    "2 Lots (130 Qty)": 130,
    "4 Lots (260 Qty)": 260,
    "8 Lots (520 Qty)": 520,
}
selected_qty = qty_map[lot_multiplier]

tf_map = {
    "15m (Intraday)": ("5d", "15m"),
    "5m (Quick Scalp)": ("2d", "5m"),
    "1h (Broader Move)": ("1mo", "1h"),
}
period_val, interval_val = tf_map[timeframe_choice]


def build_kite_style_reference_chain(spot_ltp: float, expiry_label: str):
    """Builds a Kite-style reference chain around ATM when live NSE chain rows are unavailable."""
    atm = int(round(spot_ltp / 50) * 50)
    strikes = [atm + offset * 50 for offset in range(-8, 12)]

    if "Today" in expiry_label:
        time_scale = 1.0
    elif "8 days" in expiry_label:
        time_scale = 2.6
    elif "2 weeks" in expiry_label:
        time_scale = 3.5
    elif "3 weeks" in expiry_label:
        time_scale = 4.2
    else:
        time_scale = 5.0

    rows = []
    for k in strikes:
        intrinsic_ce = max(0.0, spot_ltp - k)
        intrinsic_pe = max(0.0, k - spot_ltp)
        otm_dist = abs(spot_ltp - k)
        extrinsic = max(3.65, (75.0 * np.exp(-otm_dist / 320.0)) * time_scale)
        ce_ref = round(intrinsic_ce + extrinsic, 2)
        pe_ref = round(intrinsic_pe + extrinsic, 2)

        ce_oi_l = round(max(0.15, 180.0 * np.exp(-abs(k - (atm + 250)) / 350.0)), 2)
        pe_oi_l = round(max(0.15, 180.0 * np.exp(-abs(k - (atm - 250)) / 350.0)), 2)
        ce_chg_pct = round(-63.76 - ((k - atm) / 50.0) * 3.1, 2)
        pe_chg_pct = round(59.62 - ((k - atm) / 50.0) * 1.8, 2)
        ce_oi_chg_pct = round(180.0 - abs(k - (atm + 100)) * 0.25, 2)
        pe_oi_chg_pct = round(140.0 - abs(k - (atm - 100)) * 0.25, 2)

        rows.append({
            "Call OI Chg %": ce_oi_chg_pct,
            "OI (in lakhs)": ce_oi_l,
            "Call Chg %": ce_chg_pct,
            "Call LTP": ce_ref,
            "Strike": k,
            "Put LTP": pe_ref,
            "Put Chg %": pe_chg_pct,
            "Put OI (in lakhs)": pe_oi_l,
            "Put OI Chg %": pe_oi_chg_pct,
            "Is_ATM": k == atm,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 2. NSE OPTION CHAIN CONNECTOR
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def fetch_live_nse_option_chain(spot_ltp: float, expiry_label: str):
    nse_oc_fn = None
    try:
        from nsepython import nse_optionchain_scalar as _fn
        nse_oc_fn = _fn
    except ImportError:
        try:
            from nsepythonserver import nse_optionchain_scalar as _fn
            nse_oc_fn = _fn
        except ImportError:
            return None

    try:
        oc_data, _, timestamp, _ = nse_oc_fn("NIFTY")
        if not isinstance(oc_data, dict):
            return None

        records = oc_data.get("records", {}).get("data", [])
        expiries = oc_data.get("records", {}).get("expiryDates", [])
        if not records or not expiries:
            return None

        target_expiry = expiries[0]
        label_token = expiry_label.split()[0].lower()
        for exp in expiries:
            if label_token in str(exp).lower():
                target_expiry = exp
                break

        chain_rows = []
        total_ce_oi = 0.0
        total_pe_oi = 0.0

        for item in records:
            if item.get("expiryDate") != target_expiry:
                continue
            strike = item.get("strikePrice")
            if strike is None:
                continue

            ce = item.get("CE") or {}
            pe = item.get("PE") or {}
            ce_oi = float(ce.get("openInterest", 0) or 0)
            pe_oi = float(pe.get("openInterest", 0) or 0)
            ce_ltp = float(ce.get("lastPrice", 0) or 0)
            pe_ltp = float(pe.get("lastPrice", 0) or 0)
            ce_pchange = float(ce.get("pChange", 0) or 0)
            pe_pchange = float(pe.get("pChange", 0) or 0)
            ce_oi_chg_pct = float(ce.get("pchangeinOpenInterest", 0) or 0)
            pe_oi_chg_pct = float(pe.get("pchangeinOpenInterest", 0) or 0)

            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

            chain_rows.append({
                "strike": float(strike),
                "ce_oi": ce_oi,
                "pe_oi": pe_oi,
                "ce_ltp": ce_ltp,
                "pe_ltp": pe_ltp,
                "ce_pchange": ce_pchange,
                "pe_pchange": pe_pchange,
                "ce_oi_chg_pct": ce_oi_chg_pct,
                "pe_oi_chg_pct": pe_oi_chg_pct,
            })

        if not chain_rows:
            return None

        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
        min_pain = float("inf")
        max_pain_strike = round(spot_ltp / 50) * 50
        for pin_row in chain_rows:
            pin = pin_row["strike"]
            pain = 0.0
            for r in chain_rows:
                k = r["strike"]
                if pin > k:
                    pain += (pin - k) * r["pe_oi"]
                elif pin < k:
                    pain += (k - pin) * r["ce_oi"]
            if pain < min_pain:
                min_pain = pain
                max_pain_strike = pin

        atm_row = min(chain_rows, key=lambda r: abs(r["strike"] - spot_ltp))
        atm_int = int(round(atm_row["strike"]))

        table_df = pd.DataFrame([
            {
                "Call OI Chg %": round(r["ce_oi_chg_pct"], 2),
                "OI (in lakhs)": round(r["ce_oi"] / 100000.0, 2),
                "Call Chg %": round(r["ce_pchange"], 2),
                "Call LTP": round(r["ce_ltp"], 2),
                "Strike": int(round(r["strike"])),
                "Put LTP": round(r["pe_ltp"], 2),
                "Put Chg %": round(r["pe_pchange"], 2),
                "Put OI (in lakhs)": round(r["pe_oi"] / 100000.0, 2),
                "Put OI Chg %": round(r["pe_oi_chg_pct"], 2),
                "Is_ATM": int(round(r["strike"])) == atm_int,
            }
            for r in sorted(chain_rows, key=lambda x: x["strike"])
            if abs(r["strike"] - spot_ltp) <= 500
        ])

        return {
            "ExpiryUsed": target_expiry,
            "NSETime": timestamp,
            "PCR": pcr,
            "MaxPain": float(max_pain_strike),
            "ATMStrike": atm_int,
            "CE_LTP": atm_row["ce_ltp"] if atm_row["ce_ltp"] > 0 else 80.60,
            "PE_LTP": atm_row["pe_ltp"] if atm_row["pe_ltp"] > 0 else 83.40,
            "ChainDF": table_df,
        }
    except Exception:
        return None


# ---------------------------------------------------------
# 3. TREND & SIGNAL ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def fetch_predictive_nifty_engine(expiry_str, period, interval):
    nifty = yf.Ticker("^NSEI")
    vix = yf.Ticker("^INDIAVIX")

    df = nifty.history(period=period, interval=interval, auto_adjust=True)
    df_vix = vix.history(period="2d", interval="1d", auto_adjust=True)

    if df is None or df.empty or len(df) < 30:
        return None

    spot_ltp = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    spot_chg = round(((spot_ltp - prev_close) / prev_close) * 100, 2)
    current_vix = round(float(df_vix["Close"].iloc[-1]), 2) if not df_vix.empty else 18.37

    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    if df["Volume"].sum() > 0:
        df["VWAP"] = (
            (typical_price * df["Volume"]).groupby(df.index.date).cumsum()
            / df["Volume"].groupby(df.index.date).cumsum().replace(0, np.nan)
        ).fillna(df["EMA20"])
    else:
        df["VWAP"] = typical_price.rolling(20, min_periods=1).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    latest_rsi = float(df["RSI"].iloc[-1])
    prev_rsi = float(df["RSI"].iloc[-4])
    rsi_slope = round(latest_rsi - prev_rsi, 2)

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    hist_now = float(df["MACD_Hist"].iloc[-1])
    hist_prev = float(df["MACD_Hist"].iloc[-2])

    recent_window = df.tail(20)
    resistance_level = round(float(recent_window["High"].max()), 2)
    support_level = round(float(recent_window["Low"].min()), 2)

    score = 0
    if df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        score += 30
    elif df["EMA9"].iloc[-1] < df["EMA20"].iloc[-1] < df["EMA50"].iloc[-1]:
        score -= 30
    elif df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1]:
        score += 15
    else:
        score -= 15

    if spot_ltp > df["VWAP"].iloc[-1]:
        score += 20
    else:
        score -= 20

    if latest_rsi > 55 and rsi_slope > 0:
        score += 25
    elif latest_rsi < 45 and rsi_slope < 0:
        score -= 25
    elif rsi_slope > 3:
        score += 15
    elif rsi_slope < -3:
        score -= 15

    if hist_now > 0 and hist_now > hist_prev:
        score += 25
    elif hist_now < 0 and hist_now < hist_prev:
        score -= 25
    elif hist_now > hist_prev:
        score += 10
    else:
        score -= 10

    atm_strike = int(round(spot_ltp / 50) * 50)
    nse_oc = fetch_live_nse_option_chain(spot_ltp, expiry_str)

    if nse_oc:
        pcr = nse_oc["PCR"]
        max_pain = nse_oc["MaxPain"]
        rec_strike = nse_oc["ATMStrike"]
        live_ce_prem = nse_oc["CE_LTP"]
        live_pe_prem = nse_oc["PE_LTP"]
        oc_source = f"Live NSE ({nse_oc['ExpiryUsed']})"
        chain_df = nse_oc["ChainDF"]
        if pcr >= 1.15:
            score += 10
        elif pcr <= 0.70:
            score -= 10
    else:
        pcr = 0.82
        max_pain = float(round(spot_ltp / 100) * 100)
        rec_strike = atm_strike
        ref_df = build_kite_style_reference_chain(spot_ltp, expiry_str)
        atm_match = ref_df[ref_df["Strike"] == rec_strike]
        if not atm_match.empty:
            live_ce_prem = float(atm_match["Call LTP"].iloc[0])
            live_pe_prem = float(atm_match["Put LTP"].iloc[0])
        else:
            live_ce_prem = 80.60
            live_pe_prem = 83.40
        oc_source = "Reference Estimate (Verify live chain on Kite)"
        chain_df = ref_df

    score = max(-100, min(100, score))
    dist_up_pts = round(resistance_level - spot_ltp, 1)
    dist_down_pts = round(spot_ltp - support_level, 1)

    if score >= 10:
        opt_type = "CE"
        verdict = "BUY CALL (CE)" if score >= 35 else "CAUTIOUS BUY CALL (CE)"
        entry_prem = round(live_ce_prem, 2)
    elif score <= -10:
        opt_type = "PE"
        verdict = "BUY PUT (PE)" if score <= -35 else "CAUTIOUS BUY PUT (PE)"
        entry_prem = round(live_pe_prem, 2)
    else:
        opt_type = "WAIT"
        verdict = "SKIP TRADE (CHOPPY)"
        entry_prem = round(min(live_ce_prem, live_pe_prem), 2)

    sl_prem = round(entry_prem * 0.75, 2)

    return {
        "Spot": round(spot_ltp, 2),
        "Change": spot_chg,
        "VIX": current_vix,
        "PCR": pcr,
        "MaxPain": max_pain,
        "OCSource": oc_source,
        "RSI": round(latest_rsi, 1),
        "RSISlope": rsi_slope,
        "Score": score,
        "Verdict": verdict,
        "OptType": opt_type,
        "Strike": rec_strike,
        "Resistance": resistance_level,
        "Support": support_level,
        "DistUp": dist_up_pts,
        "DistDown": dist_down_pts,
        "Expiry": expiry_str,
        "Entry": entry_prem,
        "SL": sl_prem,
        "DataFrame": df,
        "ChainDF": chain_df,
    }


def render_kite_colored_chain(df: pd.DataFrame):
    """Renders a Kite-matched dark option chain with green/red % styling and ATM row highlight."""
    display_df = pd.DataFrame({
        "OI (in lakhs)": df.apply(
            lambda r: f"{r['Call OI Chg %']:+.2f}%  {r['OI (in lakhs)']:.2f}", axis=1
        ),
        "Call LTP": df.apply(
            lambda r: f"{r['Call Chg %']:+.2f}%  {r['Call LTP']:.2f}", axis=1
        ),
        "Strike": df["Strike"].astype(str),
        "Put LTP": df.apply(
            lambda r: f"{r['Put LTP']:.2f}  {r['Put Chg %']:+.2f}%", axis=1
        ),
        "Put OI (in lakhs)": df.apply(
            lambda r: f"{r['Put OI (in lakhs)']:.2f}  {r['Put OI Chg %']:+.2f}%", axis=1
        ),
    })

    atm_flags = df["Is_ATM"].tolist()
    ce_chg_list = df["Call Chg %"].tolist()
    pe_chg_list = df["Put Chg %"].tolist()

    def style_row(row):
        idx = row.name
        is_atm = atm_flags[idx] if idx < len(atm_flags) else False
        ce_chg = ce_chg_list[idx] if idx < len(ce_chg_list) else 0.0
        pe_chg = pe_chg_list[idx] if idx < len(pe_chg_list) else 0.0

        row_bg = "#2b2f36" if is_atm else "#171717"
        ce_tint = "#261f1d" if not is_atm else "#2b2f36"
        pe_tint = "#241e1c" if not is_atm else "#2b2f36"
        strike_bg = "#252629" if is_atm else "#1c1c1c"

        ce_color = "#ff5252" if ce_chg < 0 else "#00e676"
        pe_color = "#00e676" if pe_chg >= 0 else "#ff5252"

        return [
            f"background-color: {ce_tint}; color: #e6e6e6; border-bottom: 1px solid #262626;",
            f"background-color: {ce_tint}; color: {ce_color}; font-weight: 600; border-bottom: 1px solid #262626;",
            f"background-color: {strike_bg}; color: #ffffff; font-weight: {'700' if is_atm else '600'}; text-align: center; border-bottom: 1px solid #262626;",
            f"background-color: {pe_tint}; color: {pe_color}; font-weight: 600; border-bottom: 1px solid #262626;",
            f"background-color: {pe_tint}; color: #e6e6e6; border-bottom: 1px solid #262626;",
        ] if not is_atm else [
            f"background-color: {row_bg}; color: #ffffff; font-weight: 700; border-top: 1px solid #4a5568; border-bottom: 1px solid #4a5568;",
            f"background-color: {row_bg}; color: {ce_color}; font-weight: 700; border-top: 1px solid #4a5568; border-bottom: 1px solid #4a5568;",
            f"background-color: #2962ff; color: #ffffff; font-weight: 700; text-align: center; border-top: 1px solid #4a5568; border-bottom: 1px solid #4a5568;",
            f"background-color: {row_bg}; color: {pe_color}; font-weight: 700; border-top: 1px solid #4a5568; border-bottom: 1px solid #4a5568;",
            f"background-color: {row_bg}; color: #ffffff; font-weight: 700; border-top: 1px solid #4a5568; border-bottom: 1px solid #4a5568;",
        ]

    styled = display_df.style.apply(style_row, axis=1).set_table_styles([
        {
            "selector": "th",
            "props": [
                ("background-color", "#141414"),
                ("color", "#9e9e9e"),
                ("font-weight", "600"),
                ("font-size", "12px"),
                ("border-bottom", "1px solid #2c2c2c"),
                ("padding", "8px 10px"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("font-size", "12.5px"),
                ("padding", "6px 10px"),
            ],
        },
    ])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=540)


intel = fetch_predictive_nifty_engine(expiry_choice, period_val, interval_val)

if not intel:
    st.error("⚠️ Could not load Nifty data right now. Click **Refresh Now** to try again.")
else:
    profit_per_lot_at_exp_pts = expected_pt_gain * LOT_SIZE
    lots_needed_for_goal = max(1, math.ceil(profit_goal_rs / max(profit_per_lot_at_exp_pts, 1.0)))
    qty_needed_for_goal = lots_needed_for_goal * LOT_SIZE
    est_cost_for_goal_lots = round(intel["Entry"] * qty_needed_for_goal, 2)
    est_max_loss_for_goal_lots = round((intel["Entry"] - intel["SL"]) * qty_needed_for_goal, 2)
    est_profit_for_goal_lots = round(expected_pt_gain * qty_needed_for_goal, 2)

    pts_needed_for_selected_lots = round(profit_goal_rs / max(selected_qty, 1), 2)
    goal_exit_prem = round(intel["Entry"] + pts_needed_for_selected_lots, 2)
    selected_cost = round(intel["Entry"] * selected_qty, 2)
    selected_max_loss = round((intel["Entry"] - intel["SL"]) * selected_qty, 2)

    is_same_day_expiry = "Today" in expiry_choice
    exit_cutoff_time = "2:00 PM IST (before sharp expiry decay)" if is_same_day_expiry else "3:00 PM IST (intraday exit)"

    if intel["OptType"] in ("CE", "PE"):
        st.session_state.setdefault("live_scanner_picks", {})["Index Options Alpha Sniper"] = [
            {
                "symbol": f"NIFTY_{intel['Strike']}_{intel['OptType']}",
                "side": "BUY",
                "entry": float(intel["Entry"]),
                "sl": float(intel["SL"]),
                "t1": float(goal_exit_prem),
                "t2": float(round(goal_exit_prem * 1.15, 2)),
                "notes": f"{intel['Verdict']} | Lots needed: {lots_needed_for_goal} | Goal ₹{profit_goal_rs}",
            }
        ]
    else:
        st.session_state.setdefault("live_scanner_picks", {})["Index Options Alpha Sniper"] = []

    # 1. TOP ACTION TABLE
    st.markdown("### 🎯 Top Action Table: What to Trade, Lots Needed & How to Book Profit")
    strike_display = f"{intel['Strike']} {intel['OptType']}" if intel["OptType"] in ("CE", "PE") else "WAIT (Skip)"

    top_action_df = pd.DataFrame([
        {
            "Expiry": expiry_choice,
            "Suggested Setup": strike_display,
            "Lots Needed for ₹5k": f"{lots_needed_for_goal} lots ({qty_needed_for_goal} qty @ +{expected_pt_gain:.0f} pts)",
            "Est. Cost (Needed Lots)": f"~₹{est_cost_for_goal_lots:,.0f} (Max SL loss: -₹{est_max_loss_for_goal_lots:,.0f})",
            "Selected Lots Plan": f"{lot_multiplier}: need +{pts_needed_for_selected_lots:.2f} pts → ₹{goal_exit_prem:.2f}",
            "When to Sell / Exit": f"Sell at target OR stop-loss OR by {exit_cutoff_time}",
        }
    ])
    st.dataframe(top_action_df, use_container_width=True, hide_index=True)

    # 2. SEPARATE BUY / SELL TARGET / STOP-LOSS PRICE TABLE RIGHT BELOW
    st.markdown("#### 💵 Exact Buy, Sell Target & Stop-Loss Price Table")
    price_action_df = pd.DataFrame([
        {
            "Plan View": f"Selected Lots ({lot_multiplier})",
            "Contract": strike_display,
            "Buy Price (Entry)": f"₹{intel['Entry']:.2f} (Cost ~₹{selected_cost:,.0f})",
            "Sell Target Price": f"₹{goal_exit_prem:.2f} (+{pts_needed_for_selected_lots:.2f} pts → +₹{profit_goal_rs:,.0f})",
            "Stop-Loss Price (SL)": f"₹{intel['SL']:.2f} (Max Loss -₹{selected_max_loss:,.0f})",
            "Exit Rule": f"Sell at target / SL / {exit_cutoff_time}",
        },
        {
            "Plan View": f"₹5k Goal Lots ({lots_needed_for_goal} lots / {qty_needed_for_goal} qty)",
            "Contract": strike_display,
            "Buy Price (Entry)": f"₹{intel['Entry']:.2f} (Cost ~₹{est_cost_for_goal_lots:,.0f})",
            "Sell Target Price": f"₹{round(intel['Entry'] + expected_pt_gain, 2):.2f} (+{expected_pt_gain:.0f} pts → +₹{est_profit_for_goal_lots:,.0f})",
            "Stop-Loss Price (SL)": f"₹{intel['SL']:.2f} (Max Loss -₹{est_max_loss_for_goal_lots:,.0f})",
            "Exit Rule": f"Sell at target / SL / {exit_cutoff_time}",
        },
    ])
    st.dataframe(price_action_df, use_container_width=True, hide_index=True)

    # 3. EXPIRY & ADVANCE ALERT STRIP
    dist_up = intel["DistUp"]
    dist_dn = intel["DistDown"]
    if dist_up <= ADVANCE_ALERT_POINTS:
        st.info(f"⏳ **40-Pt Advance Alert:** Nifty is {max(dist_up, 0):.0f} pts from upside ceiling ₹{intel['Resistance']:,.0f}.")
    elif dist_dn <= ADVANCE_ALERT_POINTS:
        st.info(f"⏳ **40-Pt Advance Alert:** Nifty is {max(dist_dn, 0):.0f} pts from downside floor ₹{intel['Support']:,.0f}.")

    if is_same_day_expiry:
        st.error(
            f"⏰ **EXPIRY WARNING ({expiry_choice}):** Buying more lots increases both profit potential and loss risk. "
            f"**Sell by {exit_cutoff_time}** or book profit when your target is reached."
        )
    else:
        st.warning(
            f"⏰ **EXPIRY & PROFIT RULE ({expiry_choice}):** Even with more days to expiry, **sell by {exit_cutoff_time}** "
            f"or when profit hits **₹{profit_goal_rs:,.0f}** so gains do not reverse."
        )

    # 4. QUICK METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lots Needed for Goal", f"{lots_needed_for_goal} Lots", f"{qty_needed_for_goal} qty @ +{expected_pt_gain:.0f} pts")
    m2.metric("Nifty 50 Now", f"₹{intel['Spot']:,.2f}", f"{intel['Change']:+.2f}%")
    m3.metric("Ceiling / Floor", f"₹{intel['Resistance']:,.0f} / ₹{intel['Support']:,.0f}", f"+{dist_up:.0f} up | -{dist_dn:.0f} dn")
    m4.metric("PCR / Max Pain", f"{intel['PCR']}", f"Max Pain ₹{intel['MaxPain']:,.0f}")

    # 5. PRICE & RSI CHART
    st.markdown("### 📊 Nifty Price & Speed Chart")
    df_c = intel["DataFrame"].tail(80)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
    fig.add_trace(
        go.Candlestick(
            x=df_c.index, open=df_c["Open"], high=df_c["High"], low=df_c["Low"], close=df_c["Close"],
            name="Nifty 50", increasing_line_color="#00E676", decreasing_line_color="#FF5252",
        ),
        row=1, col=1,
    )
    fig.add_trace(go.Scatter(x=df_c.index, y=df_c["EMA9"], mode="lines", name="9 EMA", line=dict(color="#00E5FF", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_c.index, y=df_c["EMA20"], mode="lines", name="20 EMA", line=dict(color="#FFD700", width=1.6)), row=1, col=1)
    fig.add_hline(y=intel["Resistance"], line_dash="dot", line_color="#00E676", annotation_text=f"Ceiling: ₹{intel['Resistance']:,.0f}", annotation_position="top left", row=1, col=1)
    fig.add_hline(y=intel["Support"], line_dash="dot", line_color="#FF5252", annotation_text=f"Floor: ₹{intel['Support']:,.0f}", annotation_position="bottom left", row=1, col=1)
    fig.add_trace(go.Scatter(x=df_c.index, y=df_c["RSI"], mode="lines", name="RSI (14)", line=dict(color="#BB86FC", width=1.6)), row=2, col=1)
    fig.add_hline(y=60, line_dash="dash", line_color="rgba(0,230,118,0.4)", row=2, col=1)
    fig.add_hline(y=40, line_dash="dash", line_color="rgba(255,82,82,0.4)", row=2, col=1)
    fig.update_layout(
        template="plotly_dark", height=500, margin=dict(l=10, r=65, t=25, b=25),
        xaxis_rangeslider_visible=False, legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        yaxis=dict(side="right", title="Nifty (₹)"), yaxis2=dict(side="right", title="RSI", range=[15, 85]),
    )
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    # 6. KITE-COLORED OPTION CHAIN BELOW CHART
    st.markdown("---")
    st.markdown(f"### 📋 Option Chain — {expiry_choice}")
    st.caption(
        f"NIFTY 50 Spot: ₹{intel['Spot']:,.2f} ({intel['Change']:+.2f}%) • "
        f"PCR: {intel['PCR']} • Max Pain: ₹{intel['MaxPain']:,.0f} • Source: {intel['OCSource']}"
    )
    render_kite_colored_chain(intel["ChainDF"])

if live_stream and is_market_open:
    time.sleep(15)
    st.cache_data.clear()
    st.rerun()
elif auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
