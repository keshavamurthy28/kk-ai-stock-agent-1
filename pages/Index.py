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
]

# ---------------------------------------------------------
# HEADER & REFRESH BAR
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("⚡ Nifty Options Top Action & Expiry Guide")
    st.markdown(
        "Plain-English **Top Trade Table** for **NIFTY 50** options across expiry dates "
        "with a **₹5,000 profit goal**, **lots needed**, and **expiry exit warnings**. "
        "*(Educational tool only — no guaranteed profit; verify live prices on Kite.)*"
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
# 1. CONTROLS (EXPIRY DATES, LOTS, PROFIT GOAL, EXPECTED PT MOVE)
# ---------------------------------------------------------
col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([1.7, 1.3, 1.2, 1.2, 1.2])

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


# ---------------------------------------------------------
# 2. NSE OPTION CHAIN CONNECTOR
# ---------------------------------------------------------
@st.cache_data(ttl=60)
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

            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

            chain_rows.append({
                "strike": float(strike),
                "ce_oi": ce_oi,
                "pe_oi": pe_oi,
                "ce_ltp": ce_ltp,
                "pe_ltp": pe_ltp,
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
        return {
            "ExpiryUsed": target_expiry,
            "NSETime": timestamp,
            "PCR": pcr,
            "MaxPain": float(max_pain_strike),
            "ATMStrike": int(round(atm_row["strike"])),
            "CE_LTP": atm_row["ce_ltp"] if atm_row["ce_ltp"] > 0 else 85.0,
            "PE_LTP": atm_row["pe_ltp"] if atm_row["pe_ltp"] > 0 else 88.0,
        }
    except Exception:
        return None


# ---------------------------------------------------------
# 3. TREND & SIGNAL ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=60)
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
    current_vix = round(float(df_vix["Close"].iloc[-1]), 2) if not df_vix.empty else 18.25

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
        if pcr >= 1.15:
            score += 10
        elif pcr <= 0.70:
            score -= 10
    else:
        pcr = 0.90
        max_pain = float(round(spot_ltp / 100) * 100)
        rec_strike = atm_strike
        if "Today" in expiry_str:
            live_ce_prem = 88.00
            live_pe_prem = 87.65
        elif "8 days" in expiry_str:
            live_ce_prem = 270.45
            live_pe_prem = 289.60
        else:
            live_ce_prem = 367.35
            live_pe_prem = 351.65
        oc_source = "Estimated (Check live chain on Kite)"

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
    }


intel = fetch_predictive_nifty_engine(expiry_choice, period_val, interval_val)

if not intel:
    st.error("⚠️ Could not load Nifty data right now. Click **Refresh Now** to try again.")
else:
    profit_per_lot_at_exp_pts = expected_pt_gain * LOT_SIZE
    lots_needed_for_goal = max(1, math.ceil(profit_goal_rs / max(profit_per_lot_at_exp_pts, 1.0)))
    qty_needed_for_goal = lots_needed_for_goal * LOT_SIZE
    est_cost_for_goal_lots = round(intel["Entry"] * qty_needed_for_goal, 2)
    est_max_loss_for_goal_lots = round((intel["Entry"] - intel["SL"]) * qty_needed_for_goal, 2)

    pts_needed_for_selected_lots = round(profit_goal_rs / max(selected_qty, 1), 2)
    goal_exit_prem = round(intel["Entry"] + pts_needed_for_selected_lots, 2)
    investment_needed = round(intel["Entry"] * selected_qty, 2)
    max_loss_at_sl = round((intel["Entry"] - intel["SL"]) * selected_qty, 2)

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

    # 1. TOP ACTION TABLE WITH LOTS NEEDED FOR ₹5,000
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

    # 2. EXPIRY & ADVANCE ALERT STRIP
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

    # 3. QUICK METRICS & EXPIRY SNAPSHOT ACROSS DATES
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lots Needed for Goal", f"{lots_needed_for_goal} Lots", f"{qty_needed_for_goal} qty @ +{expected_pt_gain:.0f} pts")
    m2.metric("Nifty 50 Now", f"₹{intel['Spot']:,.2f}", f"{intel['Change']:+.2f}%")
    m3.metric("Ceiling / Floor", f"₹{intel['Resistance']:,.0f} / ₹{intel['Support']:,.0f}", f"+{dist_up:.0f} up | -{dist_dn:.0f} dn")
    m4.metric("Data Source", intel["OCSource"].split(" (")[0], f"PCR {intel['PCR']}")

    st.markdown("#### 📅 Expiry Dates Overview (Same Rule Applied)")
    expiry_overview = pd.DataFrame([
        {
            "Expiry Tab": exp_name,
            "Selected": "✅ Active" if exp_name == expiry_choice else "",
            "Lots Needed (Est.)": f"{lots_needed_for_goal} lots ({qty_needed_for_goal} qty)",
            "Time Decay Risk": "Very High (Same-Day)" if "Today" in exp_name else ("Moderate-High" if "8 days" in exp_name else "Lower (More Time)"),
            "Suggested Exit Cutoff": "2:00 PM IST" if "Today" in exp_name else "3:00 PM IST",
        }
        for exp_name in EXPIRY_CHOICES
    ])
    st.dataframe(expiry_overview, use_container_width=True, hide_index=True)

    # 4. SIMPLE PRICE & RSI CHART
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

if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
