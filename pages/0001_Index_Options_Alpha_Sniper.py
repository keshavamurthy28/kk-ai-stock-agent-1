from datetime import datetime, time as dt_time
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

# ---------------------------------------------------------
# HEADER & TOP REFRESH BAR
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("⚡ Nifty Options Quick Guide (Advance Signal)")
    st.markdown(
        "Simple view for **buying Nifty CE (Call) or PE (Put)**—shows early alerts, "
        "key trigger levels, and exact ₹ risk/reward at a glance."
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
# 1. SIMPLE CONTROLS (EXPIRY, LOTS, SPEED)
# ---------------------------------------------------------
col_c1, col_c2, col_c3 = st.columns([2, 1.5, 1.5])

with col_c1:
    expiry_choice = st.selectbox(
        "📅 Expiry Date",
        ["23 Nov (Weekly)", "1 Dec (Next Weekly)", "29 Dec (Monthly)"],
        index=0,
    )

with col_c2:
    lot_multiplier = st.selectbox(
        "📦 How Many Lots? (1 Lot = 25 Qty)",
        [
            "1 Lot (25 Qty)",
            "2 Lots (50 Qty)",
            "4 Lots (100 Qty)",
            "8 Lots (200 Qty)",
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
    "1 Lot (25 Qty)": 25,
    "2 Lots (50 Qty)": 50,
    "4 Lots (100 Qty)": 100,
    "8 Lots (200 Qty)": 200,
}
selected_qty = qty_map[lot_multiplier]

tf_map = {
    "15m (Intraday)": ("5d", "15m"),
    "5m (Quick Scalp)": ("2d", "5m"),
    "1h (Broader Move)": ("1mo", "1h"),
}
period_val, interval_val = tf_map[timeframe_choice]


# ---------------------------------------------------------
# 2. NSE OPTION CHAIN CONNECTOR (PCR, MAX PAIN, LTP)
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
            "CE_LTP": atm_row["ce_ltp"] if atm_row["ce_ltp"] > 0 else 132.0,
            "PE_LTP": atm_row["pe_ltp"] if atm_row["pe_ltp"] > 0 else 135.0,
        }
    except Exception:
        return None


# ---------------------------------------------------------
# 3. PREDICTIVE TREND & OPTION ENGINE
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
        oc_source = "Estimated (Live NSE chain unavailable)"

    score = max(-100, min(100, score))

    dist_up_pts = round(resistance_level - spot_ltp, 1)
    dist_down_pts = round(spot_ltp - support_level, 1)

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
        simple_verdict = "WAIT (NO TRADE)"
        strength_label = "Choppy / No Clear Direction"
        opt_type = "WAIT"
        entry_prem = round(min(live_ce_prem, live_pe_prem), 2)

    if dist_up_pts <= 0:
        advance_alert = f"🚨 Nifty is ABOVE upside ceiling ₹{resistance_level:,.0f} — watch for CE continuation or fakeout."
    elif dist_down_pts <= 0:
        advance_alert = f"🚨 Nifty is BELOW downside floor ₹{support_level:,.0f} — watch for PE continuation or bounce."
    elif dist_up_pts <= 60:
        advance_alert = f"⏳ EARLY ALERT: Nifty is only {dist_up_pts:.0f} pts below upside ceiling ₹{resistance_level:,.0f}. Get ready for CE breakout."
    elif dist_down_pts <= 60:
        advance_alert = f"⏳ EARLY ALERT: Nifty is only {dist_down_pts:.0f} pts above downside floor ₹{support_level:,.0f}. Get ready for PE breakdown."
    else:
        advance_alert = (
            f"👀 ADVANCE WATCH: Nifty is {dist_up_pts:.0f} pts below upside ceiling (₹{resistance_level:,.0f}) "
            f"and {dist_down_pts:.0f} pts above downside floor (₹{support_level:,.0f})."
        )

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
        "AdvanceAlert": advance_alert,
        "Expiry": expiry_str,
        "Entry": entry_prem,
        "SL": sl_prem,
        "T1": t1_prem,
        "T2": t2_prem,
        "DataFrame": df,
    }


intel = fetch_predictive_nifty_engine(expiry_choice, period_val, interval_val)

if not intel:
    st.error("⚠️ Could not load Nifty data right now. Click **Refresh Now** to try again.")
else:
    if intel["OptType"] in ("CE", "PE"):
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

    # ---------------------------------------------------------
    # 4. INSTANT VERDICT & ADVANCE ALERT
    # ---------------------------------------------------------
    strike_text = f"Strike: **{intel['Strike']} {intel['OptType']}**" if intel["OptType"] in ("CE", "PE") else "No trade yet"
    if intel["OptType"] == "CE":
        st.success(f"### 👉 TODAY'S LEAN: {intel['SimpleVerdict']} ({intel['StrengthLabel']}) — {strike_text}")
    elif intel["OptType"] == "PE":
        st.error(f"### 👉 TODAY'S LEAN: {intel['SimpleVerdict']} ({intel['StrengthLabel']}) — {strike_text}")
    else:
        st.warning(f"### 👉 TODAY'S LEAN: {intel['SimpleVerdict']} ({intel['StrengthLabel']})")

    st.info(intel["AdvanceAlert"])

    # ---------------------------------------------------------
    # 5. FIVE PLAIN-ENGLISH CARDS
    # ---------------------------------------------------------
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
    m4.metric("Up / Down Fences", f"₹{intel['Resistance']:,.0f} / ₹{intel['Support']:,.0f}", f"+{intel['DistUp']:.0f} up | -{intel['DistDown']:.0f} dn")
    m5.metric("PCR / Pin Zone", f"{intel['PCR']} / ₹{intel['MaxPain']:,.0f}", f"{pcr_plain} · {intel['OCSource']}")

    st.caption("Why the app leans this way: " + " • ".join(intel["Reasons"]))

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. THREE SIMPLE STEPS: ENTER, EXIT, PROTECT
    # ---------------------------------------------------------
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
                "• **Market is closed right now.** Use this as a watch list, not an instant buy.\n"
                "• After **9:15 AM IST**, click **Refresh Now** and wait for price to move toward the trigger level."
            )
        elif intel["OptType"] == "WAIT":
            st.write(
                "• **Stay out for now.** Direction is unclear.\n"
                f"• Only look for **CE** if Nifty crosses **₹{intel['Resistance']:,.0f}**, or **PE** if it drops below **₹{intel['Support']:,.0f}**."
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
            "• **Stick to 1 Lot** while learning.\n"
            "• **Double-check live option price** in your broker app before placing any order."
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 7. SIMPLE PRICE & SPEED CHART
    # ---------------------------------------------------------
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
