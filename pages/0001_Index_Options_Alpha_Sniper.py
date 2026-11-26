from datetime import date, datetime, time as dt_time, timedelta
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
import streamlit as st
import yfinance as yf

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
    """Returns only active Nifty 50 expiries >= today (never includes expired dates)."""
    today_date = date.fromisoformat(today_iso)
    candidate_map: dict[date, bool] = {}

    cursor = _next_weekday_on_or_after(today_date, 1)
    for _ in range(8):
        last_tue = _last_weekday_of_month(cursor.year, cursor.month, 1)
        candidate_map[cursor] = candidate_map.get(cursor, False) or (cursor == last_tue)
        candidate_map[last_tue] = True
        cursor += timedelta(days=7)

    for m_offset in range(1, 13):
        yr = today_date.year + (today_date.month - 1 + m_offset) // 12
        mo = (today_date.month - 1 + m_offset) % 12 + 1
        last_tue = _last_weekday_of_month(yr, mo, 1)
        if last_tue >= today_date:
            candidate_map[last_tue] = True

    active_dates = sorted(d for d in candidate_map.keys() if d >= today_date)[:8]
    return [
        {
            "date": d,
            "iso": d.isoformat(),
            "label": _format_expiry_label(d, today_date, is_monthly=candidate_map[d]),
        }
        for d in active_dates
    ]


active_expiries = get_active_nifty_expiries(now_ist.date().isoformat())
expiry_labels = [item["label"] for item in active_expiries]
label_to_iso = {item["label"]: item["iso"] for item in active_expiries}

# HEADER & TOP REFRESH BAR
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("⚡ Nifty Options Quick Guide (Advance Signal)")
    st.markdown(
        "Simple view for **buying Nifty CE (Call) or PE (Put)**—gives early "
        "**40-point alerts**, clear **Skip Trade** warnings, and exact ₹ risk/reward."
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

# 1. SIMPLE CONTROLS (ACTIVE EXPIRY, LOTS, SPEED)
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
