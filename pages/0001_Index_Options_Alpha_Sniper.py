from datetime import date, datetime, time as dt_time, timedelta
import os
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Index Options Alpha Sniper | Simple Advance Guide",
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
LOT_SIZE = 65  # Current Nifty 50 lot size

# NSE Equity & Equity Derivatives Trading Holidays (weekday closures)
NSE_TRADING_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 15),   # Municipal Corporation Election - Maharashtra
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi
    date(2026, 3, 26),   # Shri Ram Navami
    date(2026, 3, 31),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 6, 26),   # Muharram
    date(2026, 9, 14),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali-Balipratipada
    date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
    date(2026, 12, 25),  # Christmas
}


def _is_nse_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in NSE_TRADING_HOLIDAYS_2026


def _shift_expiry_for_nse_holidays(scheduled_date: date) -> date:
    """If scheduled expiry falls on a weekend or NSE holiday, shift to prior trading day."""
    shifted = scheduled_date
    while not _is_nse_trading_day(shifted):
        shifted -= timedelta(days=1)
    return shifted


def _next_weekday_on_or_after(start_date: date, target_weekday: int) -> date:
    days_ahead = (target_weekday - start_date.weekday()) % 7
    return start_date + timedelta(days=days_ahead)


def _last_weekday_of_month(year: int, month: int, target_weekday: int) -> date:
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    offset = (last_day.weekday() - target_weekday) % 7
    return last_day - timedelta(days=offset)


def _format_expiry_label(exp_date: date, today_date: date, is_monthly: bool = False) -> str:
    delta_days = (exp_date - today_date).days
    date_str = exp_date.strftime("%d %b").lstrip("0")
    if delta_days == 0:
        rel = "Today"
    elif delta_days == 1:
        rel = "1 day"
    elif delta_days < 14:
        rel = f"{delta_days} days"
    elif delta_days < 60:
        weeks = max(2, round(delta_days / 7))
        rel = f"{weeks} weeks"
    else:
        months = max(1, round(delta_days / 30))
        rel = f"{months} months"
    suffix = " Monthly" if is_monthly else ""
    return f"{date_str} ({rel}{suffix})"


@st.cache_data(ttl=300)
def get_active_nifty_expiries(today_iso: str) -> list[dict]:
    """Generates active Nifty expiries >= today with NSE holiday shifts applied."""
    today_date = date.fromisoformat(today_iso)
    candidate_map: dict[date, bool] = {}

    cursor = _next_weekday_on_or_after(today_date, 1)
    for _ in range(8):
        last_tue = _last_weekday_of_month(cursor.year, cursor.month, 1)
        effective_exp = _shift_expiry_for_nse_holidays(cursor)
        effective_last_tue = _shift_expiry_for_nse_holidays(last_tue)
        is_m = cursor == last_tue
        candidate_map[effective_exp] = candidate_map.get(effective_exp, False) or is_m
        candidate_map[effective_last_tue] = True
        cursor += timedelta(days=7)

    for m_offset in range(1, 13):
        yr = today_date.year + (today_date.month - 1 + m_offset) // 12
        mo = (today_date.month - 1 + m_offset) % 12 + 1
        last_tue = _last_weekday_of_month(yr, mo, 1)
        effective_last_tue = _shift_expiry_for_nse_holidays(last_tue)
        if effective_last_tue >= today_date:
            candidate_map[effective_last_tue] = True

    active_dates = sorted(d for d in candidate_map.keys() if d >= today_date)[:8]
    return [
        {
            "date": d,
            "iso": d.isoformat(),
            "label": _format_expiry_label(d, today_date, is_monthly=candidate_map[d]),
        }
        for d in active_dates
    ]


def _get_kite_credentials() -> tuple[str, str]:
    sec = {}
    try:
        if "kite" in st.secrets:
            sec = dict(st.secrets["kite"])
    except Exception:
        sec = {}

    api_key = (
        st.session_state.get("kite_api_key")
        or sec.get("api_key")
        or os.getenv("KITE_API_KEY", "")
    ).strip()
    access_token = (
        st.session_state.get("kite_access_token")
        or sec.get("access_token")
        or os.getenv("KITE_ACCESS_TOKEN", "")
    ).strip()
    return api_key, access_token


@st.cache_data(ttl=3600)
def _fetch_kite_nifty_instruments(api_key: str, access_token: str) -> pd.DataFrame:
    if not api_key or not access_token:
        return pd.DataFrame()
    try:
        from kiteconnect import KiteConnect

        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        inst = pd.DataFrame(kite.instruments("NFO"))
        if inst.empty:
            return pd.DataFrame()
        nifty_opts = inst[
            (inst["name"] == "NIFTY") & (inst["instrument_type"].isin(["CE", "PE"]))
        ].copy()
        if nifty_opts.empty:
            return pd.DataFrame()
        nifty_opts["expiry_date"] = pd.to_datetime(nifty_opts["expiry"]).dt.date
        nifty_opts["strike"] = nifty_opts["strike"].astype(float)
        return nifty_opts
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_kite_option_chain_data(spot_ltp: float, expiry_iso: str, api_key: str, access_token: str):
    """Matches Index page's Kite option chain source (PCR, Max Pain, ATM LTP)."""
    opts_df = _fetch_kite_nifty_instruments(api_key, access_token)
    if opts_df.empty:
        return None

    target_date = date.fromisoformat(expiry_iso)
    available_dates = sorted(opts_df["expiry_date"].dropna().unique())
    if not available_dates:
        return None

    future_or_eq = [d for d in available_dates if d >= target_date]
    matched_date = future_or_eq[0] if future_or_eq else available_dates[-1]

    exp_df = opts_df[
        (opts_df["expiry_date"] == matched_date)
        & ((opts_df["strike"] - spot_ltp).abs() <= 400.0)
    ].copy()
    if exp_df.empty:
        return None

    try:
        from kiteconnect import KiteConnect

        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        symbols = exp_df["tradingsymbol"].tolist()
        quote_map: dict = {}
        for i in range(0, len(symbols), 200):
            batch = [f"NFO:{s}" for s in symbols[i : i + 200]]
            q = kite.quote(batch)
            if isinstance(q, dict):
                quote_map.update(q)

        by_strike: dict[float, dict] = {}
        total_ce_oi = 0.0
        total_pe_oi = 0.0

        for _, row in exp_df.iterrows():
            tsym = row["tradingsymbol"]
            strike = float(row["strike"])
            otype = row["instrument_type"]
            q_item = quote_map.get(f"NFO:{tsym}", {})

            ltp = float(q_item.get("last_price", 0.0) or 0.0)
            oi = float(q_item.get("oi", 0.0) or 0.0)

            entry = by_strike.setdefault(
                strike, {"strike": strike, "ce_oi": 0.0, "pe_oi": 0.0, "ce_ltp": 0.0, "pe_ltp": 0.0}
            )
            if otype == "CE":
                entry["ce_oi"] = oi
                entry["ce_ltp"] = ltp
                total_ce_oi += oi
            elif otype == "PE":
                entry["pe_oi"] = oi
                entry["pe_ltp"] = ltp
                total_pe_oi += oi

        chain_rows = [by_strike[k] for k in sorted(by_strike.keys())]
        if not chain_rows:
            return None

        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
        min_pain = float("inf")
        max_pain_strike = float(round(spot_ltp / 50) * 50)
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
        return {
            "ExpiryUsed": matched_date.strftime("%d %b %Y"),
            "PCR": pcr,
            "MaxPain": float(max_pain_strike),
            "ATMStrike": int(round(atm_row["strike"])),
            "CE_LTP": atm_row["ce_ltp"] if atm_row["ce_ltp"] > 0 else 132.0,
            "PE_LTP": atm_row["pe_ltp"] if atm_row["pe_ltp"] > 0 else 135.0,
            "Source": f"Live Kite ({matched_date.strftime('%d %b %Y')})",
        }
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_live_nse_option_chain(spot_ltp: float, expiry_iso: str):
    """Fallback NSE option chain lookup aligned to selected expiry_iso."""
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
        oc_data, _, _, _ = nse_oc_fn("NIFTY")
        if not isinstance(oc_data, dict):
            return None

        records = oc_data.get("records", {}).get("data", [])
        expiries = oc_data.get("records", {}).get("expiryDates", [])
        if not records or not expiries:
            return None

        target_dt = date.fromisoformat(expiry_iso)
        parsed_exps: list[tuple[date, str]] = []
        for exp_str in expiries:
            for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
                try:
                    parsed_exps.append((datetime.strptime(str(exp_str), fmt).date(), str(exp_str)))
                    break
                except ValueError:
                    continue

        if parsed_exps:
            parsed_exps.sort(key=lambda x: x[0])
            future_or_eq = [item for item in parsed_exps if item[0] >= target_dt]
            target_expiry = future_or_eq[0][1] if future_or_eq else parsed_exps[-1][1]
        else:
            target_expiry = expiries[0]

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

            total_ce_oi += ce_oi
            total_pe_oi += pe_oi
            chain_rows.append(
                {"strike": float(strike), "ce_oi": ce_oi, "pe_oi": pe_oi, "ce_ltp": ce_ltp, "pe_ltp": pe_ltp}
            )

        if not chain_rows:
            return None

        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
        min_pain = float("inf")
        max_pain_strike = float(round(spot_ltp / 50) * 50)
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
        return {
            "ExpiryUsed": target_expiry,
            "PCR": pcr,
            "MaxPain": float(max_pain_strike),
            "ATMStrike": int(round(atm_row["strike"])),
            "CE_LTP": atm_row["ce_ltp"] if atm_row["ce_ltp"] > 0 else 132.0,
            "PE_LTP": atm_row["pe_ltp"] if atm_row["pe_ltp"] > 0 else 135.0,
            "Source": f"Live NSE ({target_expiry})",
        }
    except Exception:
        return None


active_expiries = get_active_nifty_expiries(now_ist.date().isoformat())
expiry_labels = [item["label"] for item in active_expiries]
label_to_iso = {item["label"]: item["iso"] for item in active_expiries}
kite_api_key, kite_access_token = _get_kite_credentials()

# ---------------------------------------------------------
# HEADER & TOP REFRESH BAR
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("⚡ Nifty Options Quick Guide (Advance Signal)")
    st.markdown(
        "Simple view for **buying Nifty CE (Call) or PE (Put)**—shows the exact **40-point trigger** "
        "from your ceiling/floor fences, clear **Skip Trade** status, and exact ₹ risk/reward."
    )

with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    r_col1, r_col2 = st.columns([1.2, 1])
    with r_col1:
        if st.button("🔄 Refresh Now", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.toast("Updating Nifty & Option Chain...", icon="⚡")
            st.rerun()
    with r_col2:
        auto_refresh = st.toggle("Auto (60s)", value=False)
    market_badge = "🟢 Market Open" if is_market_open else "🟡 Market Closed"
    st.caption(f"{market_badge} • **{now_ist.strftime('%I:%M:%S %p IST')}**")

st.markdown("---")

# ---------------------------------------------------------
# 1. SIMPLE CONTROLS (ACTIVE EXPIRY, LOTS, SPEED)
# ---------------------------------------------------------
col_c1, col_c2, col_c3 = st.columns([2, 1.5, 1.5])

with col_c1:
    expiry_choice = st.selectbox(
        "📅 Expiry Date",
        expiry_labels,
        index=0,
    )

with col_c2:
    lot_multiplier = st.selectbox(
        f"📦 How Many Lots? (1 Lot = {LOT_SIZE} Qty)",
        [
            f"1 Lot ({LOT_SIZE} Qty)",
            f"2 Lots ({LOT_SIZE * 2} Qty)",
            f"4 Lots ({LOT_SIZE * 4} Qty)",
            f"8 Lots ({LOT_SIZE * 8} Qty)",
        ],
        index=0,
    )

with col_c3:
    timeframe_choice = st.selectbox(
        "⏱️ Chart Speed",
        ["15m (Intraday)", "5m (Quick Scalp)", "1h (Broader Move)"],
        index=0,
    )

qty_map = {
    f"1 Lot ({LOT_SIZE} Qty)": LOT_SIZE,
    f"2 Lots ({LOT_SIZE * 2} Qty)": LOT_SIZE * 2,
    f"4 Lots ({LOT_SIZE * 4} Qty)": LOT_SIZE * 4,
    f"8 Lots ({LOT_SIZE * 8} Qty)": LOT_SIZE * 8,
}
selected_qty = qty_map[lot_multiplier]
selected_expiry_iso = label_to_iso[expiry_choice]

tf_map = {
    "15m (Intraday)": ("5d", "15m"),
    "5m (Quick Scalp)": ("2d", "5m"),
    "1h (Broader Move)": ("1mo", "1h"),
}
period_val, interval_val = tf_map[timeframe_choice]


# ---------------------------------------------------------
# 2. PREDICTIVE TREND & OPTION ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_predictive_nifty_engine(
    expiry_label: str,
    expiry_iso: str,
    period: str,
    interval: str,
    api_key: str,
    access_token: str,
):
    nifty = yf.Ticker("^NSEI")
    vix = yf.Ticker("^INDIAVIX")

    df = nifty.history(period=period, interval=interval, auto_adjust=True)
    df_vix = vix.history(period="2d", interval="1d", auto_adjust=True)

    if df is None or df.empty or len(df) < 30:
        return None

    spot_ltp = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    spot_chg = round(((spot_ltp - prev_close) / prev_close) * 100, 2)
    current_vix = round(float(df_vix["Close"].iloc[-1]), 2) if not df_vix.empty else 15.57

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
    plain_reasons = []

    if df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        score += 30
        plain_reasons.append("Short-term trend lines point UP")
    elif df["EMA9"].iloc[-1] < df["EMA20"].iloc[-1] < df["EMA50"].iloc[-1]:
        score -= 30
        plain_reasons.append("Short-term trend lines point DOWN")
    elif df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1]:
        score += 15
        plain_reasons.append("Fast trend is turning slightly UP")
    else:
        score -= 15
        plain_reasons.append("Fast trend is turning slightly DOWN")

    if spot_ltp > df["VWAP"].iloc[-1]:
        score += 20
        plain_reasons.append("Price is ABOVE average intraday price")
    else:
        score -= 20
        plain_reasons.append("Price is BELOW average intraday price")

    if latest_rsi > 55 and rsi_slope > 0:
        score += 25
        plain_reasons.append("Buying energy is RISING")
    elif latest_rsi < 45 and rsi_slope < 0:
        score -= 25
        plain_reasons.append("Selling pressure is RISING")
    elif rsi_slope > 3:
        score += 15
        plain_reasons.append("Momentum is bouncing UP")
    elif rsi_slope < -3:
        score -= 15
        plain_reasons.append("Momentum is slipping DOWN")

    if hist_now > 0 and hist_now > hist_prev:
        score += 25
        plain_reasons.append("Upside speed is picking up")
    elif hist_now < 0 and hist_now < hist_prev:
        score -= 25
        plain_reasons.append("Downside speed is picking up")
    elif hist_now > hist_prev:
        score += 10
        plain_reasons.append("Downward push is slowing")
    else:
        score -= 10
        plain_reasons.append("Upward push is slowing")

    atm_strike = int(round(spot_ltp / 50) * 50)
    kite_oc = fetch_kite_option_chain_data(spot_ltp, expiry_iso, api_key, access_token)
    nse_oc = None if kite_oc else fetch_live_nse_option_chain(spot_ltp, expiry_iso)
    oc_data = kite_oc or nse_oc

    if oc_data:
        pcr = oc_data["PCR"]
        max_pain = oc_data["MaxPain"]
        rec_strike = oc_data["ATMStrike"]
        live_ce_prem = oc_data["CE_LTP"]
        live_pe_prem = oc_data["PE_LTP"]
        oc_source = oc_data["Source"]

        if pcr >= 1.15:
            score += 10
            plain_reasons.append(f"Put support looks healthy (PCR {pcr})")
        elif pcr <= 0.70:
            score -= 10
            plain_reasons.append(f"Call pressure is heavy (PCR {pcr})")
    else:
        pcr = 0.86
        max_pain = float(round((support_level + resistance_level) / 100) * 50)
        rec_strike = atm_strike
        live_ce_prem = 132.0
        live_pe_prem = 132.0
        oc_source = "Estimated (Live option chain unavailable)"

    score = max(-100, min(100, score))

    dist_up_pts = round(resistance_level - spot_ltp, 1)
    dist_down_pts = round(spot_ltp - support_level, 1)
    ce_40pt_trigger = round(resistance_level - ADVANCE_ALERT_POINTS, 2)
    pe_40pt_trigger = round(support_level + ADVANCE_ALERT_POINTS, 2)
    pts_to_ce_40 = round(max(ce_40pt_trigger - spot_ltp, 0.0), 1)
    pts_to_pe_40 = round(max(spot_ltp - pe_40pt_trigger, 0.0), 1)

    if score >= 35:
        simple_verdict = "BUY CALL (CE)"
        strength_label = "Strong Upward Move"
        opt_type = "CE"
        entry_prem = round(live_ce_prem, 2)
    elif 10 <= score < 35:
        simple_verdict = "CAUTIOUS BUY CALL (CE)"
        strength_label = "Weak / Early Upward Move"
        opt_type = "CE"
        entry_prem = round(live_ce_prem, 2)
    elif -35 < score <= -10:
        simple_verdict = "CAUTIOUS BUY PUT (PE)"
        strength_label = "Weak / Early Downward Move"
        opt_type = "PE"
        entry_prem = round(live_pe_prem, 2)
    elif score <= -35:
        simple_verdict = "BUY PUT (PE)"
        strength_label = "Strong Downward Move"
        opt_type = "PE"
        entry_prem = round(live_pe_prem, 2)
    else:
        simple_verdict = "SKIP TRADE (WAIT)"
        strength_label = "Choppy / No Clear Direction"
        opt_type = "WAIT"
        entry_prem = round(min(live_ce_prem, live_pe_prem), 2)

    if dist_up_pts <= 0:
        trigger_status = f"CE 40-Pt Trigger Reached (Above ₹{resistance_level:,.0f} ceiling)"
    elif dist_down_pts <= 0:
        trigger_status = f"PE 40-Pt Trigger Reached (Below ₹{support_level:,.0f} floor)"
    elif dist_up_pts <= ADVANCE_ALERT_POINTS:
        trigger_status = f"CE 40-Pt Trigger ACTIVE (Within {dist_up_pts:.0f} pts of ₹{resistance_level:,.0f} ceiling)"
    elif dist_down_pts <= ADVANCE_ALERT_POINTS:
        trigger_status = f"PE 40-Pt Trigger ACTIVE (Within {dist_down_pts:.0f} pts of ₹{support_level:,.0f} floor)"
    else:
        trigger_status = (
            f"Waiting for 40-Pt Trigger — CE Watch at ₹{ce_40pt_trigger:,.0f} ({pts_to_ce_40:.0f} pts away) "
            f"| PE Watch at ₹{pe_40pt_trigger:,.0f} ({pts_to_pe_40:.0f} pts away)"
        )

    if not is_market_open:
        skip_reason = "Market is closed—skip live buying right now and watch the 40-pt trigger levels below."
    elif abs(score) < 10:
        skip_reason = "Direction score is near zero—market is choppy, so skip buying until a 40-pt trigger is reached."
    elif dist_up_pts > ADVANCE_ALERT_POINTS and dist_down_pts > ADVANCE_ALERT_POINTS:
        skip_reason = (
            f"Nifty is in the middle ({dist_up_pts:.0f} pts below ceiling ₹{resistance_level:,.0f}, "
            f"{dist_down_pts:.0f} pts above floor ₹{support_level:,.0f})—skip until within 40 pts of ceiling or floor."
        )
    else:
        skip_reason = ""

    sl_prem = round(entry_prem * 0.75, 2)
    t1_prem = round(entry_prem * 1.35, 2)
    t2_prem = round(entry_prem * 1.80, 2)

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
        "Reasons": plain_reasons,
        "SimpleVerdict": simple_verdict,
        "StrengthLabel": strength_label,
        "OptType": opt_type,
        "Strike": rec_strike,
        "Resistance": resistance_level,
        "Support": support_level,
        "DistUp": dist_up_pts,
        "DistDown": dist_down_pts,
        "CE40Trigger": ce_40pt_trigger,
        "PE40Trigger": pe_40pt_trigger,
        "PtsToCE40": pts_to_ce_40,
        "PtsToPE40": pts_to_pe_40,
        "TriggerStatus": trigger_status,
        "SkipReason": skip_reason,
        "Expiry": expiry_label,
        "Entry": entry_prem,
        "SL": sl_prem,
        "T1": t1_prem,
        "T2": t2_prem,
        "DataFrame": df,
    }


intel = fetch_predictive_nifty_engine(
    expiry_choice,
    selected_expiry_iso,
    period_val,
    interval_val,
    kite_api_key,
    kite_access_token,
)

if not intel:
    st.error("⚠️ Could not load Nifty data right now. Click **Refresh Now** to try again.")
else:
    is_skip_now = bool(intel["SkipReason"]) or intel["OptType"] == "WAIT"

    if not is_skip_now and intel["OptType"] in ("CE", "PE"):
        st.session_state.setdefault("live_scanner_picks", {})[
            "Index Options Alpha Sniper"
        ] = [
            {
                "symbol": f"NIFTY_{intel['Strike']}_{intel['OptType']}",
                "side": "BUY",
                "entry": float(intel["Entry"]),
                "sl": float(intel["SL"]),
                "t1": float(intel["T1"]),
                "t2": float(intel["T2"]),
                "notes": f"{intel['SimpleVerdict']} | {intel['Expiry']} | Score {intel['Score']:+d}",
            }
        ]
    else:
        st.session_state.setdefault("live_scanner_picks", {})[
            "Index Options Alpha Sniper"
        ] = []

    # Single clear decision banner (no conflicting CE/PE banner when Skip Trade applies)
    if is_skip_now:
        st.warning(
            f"### 🛑 SKIP TRADE FOR NOW — {intel['TriggerStatus']}\n"
            f"{intel['SkipReason'] or 'Wait for a clear 40-pt trigger near ceiling or floor.'}"
        )
    elif intel["OptType"] == "CE":
        st.success(
            f"### 👉 ACTION: {intel['SimpleVerdict']} — Strike: **{intel['Strike']} CE** ({intel['TriggerStatus']})"
        )
    else:
        st.error(
            f"### 👉 ACTION: {intel['SimpleVerdict']} — Strike: **{intel['Strike']} PE** ({intel['TriggerStatus']})"
        )

    if intel["Score"] >= 35:
        score_plain = "Strong Up"
    elif intel["Score"] > 0:
        score_plain = "Slightly Up (Weak)"
    elif intel["Score"] <= -35:
        score_plain = "Strong Down"
    elif intel["Score"] < 0:
        score_plain = "Slightly Down (Weak)"
    else:
        score_plain = "Flat / No Direction"

    rsi_plain = "Rising" if intel["RSISlope"] > 1 else ("Falling" if intel["RSISlope"] < -1 else "Flat")
    pcr_plain = "More Put Support" if intel["PCR"] >= 1.15 else ("More Call Pressure" if intel["PCR"] <= 0.70 else "Balanced / Mixed")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Nifty Now", f"₹{intel['Spot']:,.2f}", f"{intel['Change']:+.2f}% today")
    m2.metric("Direction Strength", f"{intel['Score']:+d} / 100", score_plain)
    m3.metric("Speed Gauge (RSI)", f"{intel['RSI']}", f"{rsi_plain} ({intel['RSISlope']:+.1f})")
    m4.metric(
        "40-Pt Triggers (CE / PE)",
        f"₹{intel['CE40Trigger']:,.0f} / ₹{intel['PE40Trigger']:,.0f}",
        f"Fences ₹{intel['Resistance']:,.0f} / ₹{intel['Support']:,.0f}",
    )
    m5.metric("PCR / Pin Zone", f"{intel['PCR']} / ₹{intel['MaxPain']:,.0f}", f"{pcr_plain} · {intel['OCSource']}")

    st.caption("Why the app leans this way: " + " • ".join(intel["Reasons"]))

    st.markdown("---")

    total_investment = round(intel["Entry"] * selected_qty, 2)
    total_risk_amt = round((intel["Entry"] - intel["SL"]) * selected_qty, 2)
    potential_profit_t1 = round((intel["T1"] - intel["Entry"]) * selected_qty, 2)
    potential_profit_t2 = round((intel["T2"] - intel["Entry"]) * selected_qty, 2)

    st.markdown(f"### ✅ Simple Action Plan ({lot_multiplier} = {selected_qty} Qty)")
    pb1, pb2, pb3 = st.columns(3)

    with pb1:
        st.markdown("#### 1. When to Enter")
        if not is_market_open:
            st.write(
                "• **Market is closed right now.** Do not place a live buy.\n"
                f"• Watch **CE 40-Pt Trigger @ ₹{intel['CE40Trigger']:,.0f}** (ceiling ₹{intel['Resistance']:,.0f}) "
                f"and **PE 40-Pt Trigger @ ₹{intel['PE40Trigger']:,.0f}** (floor ₹{intel['Support']:,.0f}) after **9:15 AM IST**."
            )
        elif is_skip_now:
            st.write(
                "• **Skip this trade right now.** Price is outside the 40-pt trigger zone or direction is unclear.\n"
                f"• **40-Pt CE Trigger:** Nifty reaches **₹{intel['CE40Trigger']:,.0f}** ({intel['PtsToCE40']:.0f} pts away toward ₹{intel['Resistance']:,.0f}).\n"
                f"• **40-Pt PE Trigger:** Nifty reaches **₹{intel['PE40Trigger']:,.0f}** ({intel['PtsToPE40']:.0f} pts away toward ₹{intel['Support']:,.0f})."
            )
        else:
            st.write(
                f"• Look at **{intel['Strike']} {intel['OptType']}** (~₹{intel['Entry']:.2f} est. premium).\n"
                f"• **Cost for {selected_qty} qty:** ~**₹{total_investment:,.0f}**.\n"
                f"• **Cancel plan** if Nifty crosses the opposite fence (**₹{intel['Support']:,.0f}** for CE / **₹{intel['Resistance']:,.0f}** for PE)."
            )

    with pb2:
        st.markdown("#### 2. When to Take Profit")
        st.write(
            f"• **First Profit (₹{intel['T1']:.2f}):** ~**+₹{potential_profit_t1:,.0f}** on {selected_qty} qty — take most or all profit here.\n"
            f"• **Second Profit (₹{intel['T2']:.2f}):** ~**+₹{potential_profit_t2:,.0f}** only if the move stays strong.\n"
            "• **Exit early** if the speed gauge turns against you or on weekly expiry afternoon when time decay speeds up."
        )

    with pb3:
        st.markdown("#### 3. Stop-Loss & Safety")
        st.write(
            f"• **Hard Stop-Loss (₹{intel['SL']:.2f}):** Max loss ~**₹{total_risk_amt:,.0f}** on {selected_qty} qty. Exit immediately if hit.\n"
            "• **Skip when choppy:** Do not force trades when price is stuck between the 40-pt triggers.\n"
            "• **Stick to 1 Lot** while learning and verify live option prices in your broker app."
        )

    st.markdown("---")

    st.subheader(f"📊 Price & Speed Chart ({timeframe_choice})")

    df_c = intel["DataFrame"].tail(80)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.75, 0.25],
    )

    fig.add_trace(
        go.Candlestick(
            x=df_c.index,
            open=df_c["Open"],
            high=df_c["High"],
            low=df_c["Low"],
            close=df_c["Close"],
            name="Nifty 50",
            increasing_line_color="#00E676",
            decreasing_line_color="#FF5252",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["EMA9"],
            mode="lines",
            name="Fast Line (9 EMA)",
            line=dict(color="#00E5FF", width=1.5),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["EMA20"],
            mode="lines",
            name="Trend Line (20 EMA)",
            line=dict(color="#FFD700", width=1.6),
        ),
        row=1,
        col=1,
    )

    fig.add_hline(
        y=intel["Resistance"],
        line_dash="dot",
        line_color="#00E676",
        annotation_text=f"Upside Ceiling: ₹{intel['Resistance']:,.0f}",
        annotation_position="top left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=intel["CE40Trigger"],
        line_dash="dash",
        line_color="rgba(0, 230, 118, 0.55)",
        annotation_text=f"CE 40-Pt Trigger: ₹{intel['CE40Trigger']:,.0f}",
        annotation_position="top right",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=intel["PE40Trigger"],
        line_dash="dash",
        line_color="rgba(255, 82, 82, 0.55)",
        annotation_text=f"PE 40-Pt Trigger: ₹{intel['PE40Trigger']:,.0f}",
        annotation_position="bottom right",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=intel["Support"],
        line_dash="dot",
        line_color="#FF5252",
        annotation_text=f"Downside Floor: ₹{intel['Support']:,.0f}",
        annotation_position="bottom left",
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["RSI"],
            mode="lines",
            name="Speed Gauge (RSI)",
            line=dict(color="#BB86FC", width=1.6),
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=60, line_dash="dash", line_color="rgba(0,230,118,0.4)", row=2, col=1)
    fig.add_hline(y=40, line_dash="dash", line_color="rgba(255,82,82,0.4)", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=520,
        margin=dict(l=10, r=65, t=25, b=25),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        yaxis=dict(side="right", title="Nifty (₹)", showgrid=True),
        yaxis2=dict(side="right", title="Speed (RSI)", range=[15, 85], showgrid=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
