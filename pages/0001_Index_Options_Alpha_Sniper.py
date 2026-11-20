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
    page_title="Index Options Alpha Sniper | Predictive Trend & SMC Engine",
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
    st.title("⚡ Index Options Alpha Sniper: Predictive Trend & Expiry Engine")
    st.markdown(
        "**Expert Derivatives Analyst Guide:** Combines multi-timeframe EMA structure, RSI momentum slope, "
        "MACD acceleration, breakout trigger zones, and NSE option chain data to guide entries, "
        "profit-booking, and risk control."
    )

with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    r_col1, r_col2 = st.columns([1.2, 1])
    with r_col1:
        if st.button("🔄 Refresh Now", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.toast("Fetching latest Nifty, VIX & Option Chain data...", icon="⚡")
            st.rerun()
    with r_col2:
        auto_refresh = st.toggle("Auto (60s)", value=False)
    market_badge = "🟢 NSE Live Hours" if is_market_open else "🟡 Pre-Market / Closed"
    st.caption(f"{market_badge} • Last Sync: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")

st.markdown("---")

# ---------------------------------------------------------
# 1. LIVE CONTROLS, EXPIRY & LOT SELECTOR
# ---------------------------------------------------------
col_c1, col_c2, col_c3 = st.columns([2, 1.5, 1.5])

with col_c1:
    expiry_choice = st.selectbox(
        "📅 Select Active Contract Expiry:",
        ["23 Nov (Weekly)", "1 Dec (Next Weekly)", "29 Dec (Monthly)"],
        index=0,
    )

with col_c2:
    lot_multiplier = st.selectbox(
        "📦 Select Quantity / Lots (Nifty: 25/lot):",
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
        "⏱️ Predictive Chart Timeframe:",
        ["15m (Intraday Sniper)", "5m (Scalp Momentum)", "1h (Swing Trend)"],
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
    "15m (Intraday Sniper)": ("5d", "15m"),
    "5m (Scalp Momentum)": ("2d", "5m"),
    "1h (Swing Trend)": ("1mo", "1h"),
}
period_val, interval_val = tf_map[timeframe_choice]


# ---------------------------------------------------------
# 2. FREE NSE OPTION CHAIN CONNECTOR (PCR, MAX PAIN, LTP)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_live_nse_option_chain(spot_ltp: float, expiry_label: str):
    """
    Attempts to fetch live NIFTY option chain data via nsepython / nsepythonserver.
    Computes live PCR, Max Pain strike, and ATM CE/PE LTPs.
    Returns None if NSE blocks cloud IPs or data is unavailable.
    """
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
# 3. PREDICTIVE TREND & OPTION INTELLIGENCE ENGINE
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

    # 1. Multi-EMA Trend Structure (9, 20, 50)
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # Safe VWAP (handles ^NSEI zero-volume limitation gracefully)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    if df["Volume"].sum() > 0:
        df["VWAP"] = (
            (typical_price * df["Volume"]).groupby(df.index.date).cumsum()
            / df["Volume"].groupby(df.index.date).cumsum().replace(0, np.nan)
        ).fillna(df["EMA20"])
    else:
        df["VWAP"] = typical_price.rolling(20, min_periods=1).mean()

    # 2. Leading RSI (14) & Momentum Slope
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    latest_rsi = float(df["RSI"].iloc[-1])
    prev_rsi = float(df["RSI"].iloc[-4])
    rsi_slope = round(latest_rsi - prev_rsi, 2)

    # 3. MACD Acceleration (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    hist_now = float(df["MACD_Hist"].iloc[-1])
    hist_prev = float(df["MACD_Hist"].iloc[-2])

    # 4. Swing Breakout / Breakdown Levels (Last 20 candles)
    recent_window = df.tail(20)
    resistance_level = round(float(recent_window["High"].max()), 2)
    support_level = round(float(recent_window["Low"].min()), 2)

    # 5. Predictive Trend Score (-100 to +100)
    score = 0
    signals = []

    if df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
        score += 30
        signals.append("Bullish EMA Ribbon (9 > 20 > 50)")
    elif df["EMA9"].iloc[-1] < df["EMA20"].iloc[-1] < df["EMA50"].iloc[-1]:
        score -= 30
        signals.append("Bearish EMA Ribbon (9 < 20 < 50)")
    elif df["EMA9"].iloc[-1] > df["EMA20"].iloc[-1]:
        score += 15
        signals.append("Early Bullish 9/20 EMA Crossover")
    else:
        score -= 15
        signals.append("Early Bearish 9/20 EMA Crossover")

    if spot_ltp > df["VWAP"].iloc[-1]:
        score += 20
        signals.append("Trading Above Intraday Value Anchor")
    else:
        score -= 20
        signals.append("Trading Below Intraday Value Anchor")

    if latest_rsi > 55 and rsi_slope > 0:
        score += 25
        signals.append(f"Rising Bullish RSI ({latest_rsi:.1f}, +{rsi_slope})")
    elif latest_rsi < 45 and rsi_slope < 0:
        score -= 25
        signals.append(f"Accelerating Bearish RSI ({latest_rsi:.1f}, {rsi_slope})")
    elif rsi_slope > 3:
        score += 15
        signals.append(f"Early RSI Reversal Upward (+{rsi_slope})")
    elif rsi_slope < -3:
        score -= 15
        signals.append(f"Early RSI Reversal Downward ({rsi_slope})")

    if hist_now > 0 and hist_now > hist_prev:
        score += 25
        signals.append("MACD Bullish Expansion")
    elif hist_now < 0 and hist_now < hist_prev:
        score -= 25
        signals.append("MACD Bearish Expansion")
    elif hist_now > hist_prev:
        score += 10
        signals.append("MACD Bearish Exhaustion (Turning Up)")
    else:
        score -= 10
        signals.append("MACD Bullish Exhaustion (Turning Down)")

    # 6. Live NSE Option Chain Integration (with Fallback)
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
            signals.append(f"Bullish PCR ({pcr})")
        elif pcr <= 0.70:
            score -= 10
            signals.append(f"Bearish PCR ({pcr})")
    else:
        pcr = 0.86
        max_pain = float(round((support_level + resistance_level) / 100) * 50)
        rec_strike = atm_strike
        live_ce_prem = 132.0
        live_pe_prem = 132.0
        oc_source = "Fallback Est. (NSE blocked/closed)"

    score = max(-100, min(100, score))

    # 7. Advance Market Outlook & Option Levels
    if score >= 35:
        outlook = "STRONG UPTREND (HIGH CONVICTION)"
        action = "BUY CE (CALL OPTION)"
        opt_type = "CE"
        trigger_note = (
            f"Breakout Confirmed above ₹{resistance_level:,.2f}"
            if spot_ltp >= resistance_level
            else f"Anticipating Breakout toward ₹{resistance_level:,.2f}"
        )
        entry_prem = round(live_ce_prem, 2)
    elif 10 <= score < 35:
        outlook = "EARLY UPTREND / ACCUMULATION"
        action = "BUY CE ON DIPS (CALL OPTION)"
        opt_type = "CE"
        trigger_note = (
            f"Watch Breakout Trigger: ₹{resistance_level:,.2f} "
            f"(Invalidated below ₹{support_level:,.2f})"
        )
        entry_prem = round(live_ce_prem, 2)
    elif -35 < score <= -10:
        outlook = "EARLY DOWNTREND / DISTRIBUTION"
        action = "BUY PE ON RALLIES (PUT OPTION)"
        opt_type = "PE"
        trigger_note = (
            f"Watch Breakdown Trigger: ₹{support_level:,.2f} "
            f"(Invalidated above ₹{resistance_level:,.2f})"
        )
        entry_prem = round(live_pe_prem, 2)
    elif score <= -35:
        outlook = "STRONG DOWNTREND (HIGH CONVICTION)"
        action = "BUY PE (PUT OPTION)"
        opt_type = "PE"
        trigger_note = (
            f"Breakdown Confirmed below ₹{support_level:,.2f}"
            if spot_ltp <= support_level
            else f"Anticipating Breakdown toward ₹{support_level:,.2f}"
        )
        entry_prem = round(live_pe_prem, 2)
    else:
        outlook = "SIDEWAYS / CHOPPY CONSOLIDATION"
        action = "WAIT FOR BREAKOUT (NO TRADE)"
        opt_type = "WAIT"
        trigger_note = (
            f"Range-Bound: Buy CE > ₹{resistance_level:,.2f} | "
            f"Buy PE < ₹{support_level:,.2f}"
        )
        entry_prem = round(min(live_ce_prem, live_pe_prem), 2)

    sl_prem = round(entry_prem * 0.75, 2)
    t1_prem = round(entry_prem * 1.35, 2)
    t2_prem = round(entry_prem * 1.80, 2)

    theta_warning = (
        "⚠️ **Weekly Expiry Caution:** High time-decay (Theta). Exit intraday before expiry day!"
        if "Weekly" in expiry_str
        else "✅ **Positional Expiry:** Lower theta decay risk."
    )

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
        "Signals": signals,
        "Outlook": outlook,
        "Action": action,
        "OptType": opt_type,
        "Strike": rec_strike,
        "Resistance": resistance_level,
        "Support": support_level,
        "TriggerNote": trigger_note,
        "Expiry": expiry_str,
        "ThetaNote": theta_warning,
        "Entry": entry_prem,
        "SL": sl_prem,
        "T1": t1_prem,
        "T2": t2_prem,
        "DataFrame": df,
    }


intel = fetch_predictive_nifty_engine(expiry_choice, period_val, interval_val)

if not intel:
    st.error("⚠️ Unable to fetch live Nifty data. Click **Refresh Now** to retry.")
else:
    # --- PUSH ACTIVE INDEX OPTIONS SIGNAL TO ANALYSER SESSION STATE ---
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
                "notes": f"{intel['Action']} | {intel['Expiry']} | Score {intel['Score']:+d}",
            }
        ]
    else:
        st.session_state.setdefault("live_scanner_picks", {})[
            "Index Options Alpha Sniper"
        ] = []

    # ---------------------------------------------------------
    # 4. ADVANCE TREND PREDICTOR DASHBOARD
    # ---------------------------------------------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Nifty Spot LTP", f"₹{intel['Spot']:,.2f}", f"{intel['Change']:+.2f}%")
    m2.metric("Trend Prediction Score", f"{intel['Score']:+d} / 100", intel["Outlook"].split(" (")[0])
    m3.metric("Momentum RSI (14)", f"{intel['RSI']}", f"{intel['RSISlope']:+.1f} Slope")
    m4.metric("Breakout / Breakdown", f"₹{intel['Resistance']:,.0f} / ₹{intel['Support']:,.0f}", "Key Trigger Zone")
    m5.metric("PCR / Max Pain", f"{intel['PCR']} / ₹{intel['MaxPain']:,.0f}", intel["OCSource"])

    st.markdown("---")

    # Predictive Directive Banner
    if "BUY CE" in intel["Action"]:
        st.success(
            f"🟢 **ADVANCE SIGNAL ({intel['Outlook']}): {intel['Action']}** — "
            f"Strike: **{intel['Strike']} CE** | 🎯 {intel['TriggerNote']}"
        )
    elif "BUY PE" in intel["Action"]:
        st.error(
            f"🔴 **ADVANCE SIGNAL ({intel['Outlook']}): {intel['Action']}** — "
            f"Strike: **{intel['Strike']} PE** | 🎯 {intel['TriggerNote']}"
        )
    else:
        st.warning(
            f"🟡 **ADVANCE SIGNAL ({intel['Outlook']}): {intel['Action']}** — "
            f"🎯 {intel['TriggerNote']}"
        )

    st.info(
        f"🧠 **Leading Confluence Factors:** {'  •  '.join(intel['Signals'])}  \n"
        f"{intel['ThetaNote']}"
    )

    # ---------------------------------------------------------
    # 5. EXPERT ANALYST PLAYBOOK (WHEN TO BUY & BOOK PROFIT)
    # ---------------------------------------------------------
    st.markdown("### 👨‍🏫 Expert Analyst Action Plan (Beginner Rules)")
    pb1, pb2, pb3 = st.columns(3)

    with pb1:
        st.markdown("#### 1️⃣ When to Buy (Entry Rule)")
        if not is_market_open:
            st.write(
                "• **Market is currently closed/pre-market.** Treat this as a **watch-only plan**, "
                "not an instant buy at 9:15 AM.\n"
                "• Wait for live candles after **9:15 AM IST** and click **🔄 Refresh Now**."
            )
        elif intel["OptType"] == "WAIT":
            st.write(
                "• **Do NOT buy yet.** Momentum score is neutral/choppy.\n"
                f"• Wait for a clean spot move above **₹{intel['Resistance']:,.2f}** (for CE) "
                f"or below **₹{intel['Support']:,.2f}** (for PE)."
            )
        elif intel["OptType"] == "PE":
            st.write(
                f"• Consider **{intel['Strike']} PE** only when spot shows weakness/rejection "
                f"toward breakdown support **₹{intel['Support']:,.2f}**.\n"
                f"• **Cancel/Invalidate** if Nifty breaks and holds above **₹{intel['Resistance']:,.2f}**.\n"
                f"• **Hard Stop-Loss:** Exit immediately if premium drops to **₹{intel['SL']:,.2f}**."
            )
        else:
            st.write(
                f"• Consider **{intel['Strike']} CE** on pullbacks/strength while holding above "
                f"support and moving toward resistance **₹{intel['Resistance']:,.2f}**.\n"
                f"• **Cancel/Invalidate** if Nifty drops below **₹{intel['Support']:,.2f}**.\n"
                f"• **Hard Stop-Loss:** Exit immediately if premium drops to **₹{intel['SL']:,.2f}**."
            )

    with pb2:
        st.markdown("#### 2️⃣ When to Book Profit (Exit Rule)")
        st.write(
            f"• **Target 1 (+35% @ ₹{intel['T1']:,.2f}):** Book partial or full profit first—don't get greedy.\n"
            f"• **Target 2 (+80% @ ₹{intel['T2']:,.2f}):** Only hold a small runner if momentum stays strong.\n"
            "• **Early Profit Lock:** Book profit early if Nifty reaches a major resistance/support level, "
            "if **RSI** turns sharply against your trade, or if **MACD** loses steam.\n"
            "• **Time Rule:** Avoid holding risky weekly option buys into late-day time decay."
        )

    with pb3:
        st.markdown("#### 3️⃣ Beginner Safety Guardrails")
        st.write(
            "• **1 Lot Discipline:** Start with **1 Lot (25 Qty)** while learning.\n"
            "• **Never Average Down:** If a buy hits stop-loss, take the small loss and step back.\n"
            "• **Check Data Source:** If PCR/Max Pain says *Fallback Est.*, verify live option chain "
            "prices before placing real orders.\n"
            "• **Not Financial Advice:** Use for education and disciplined risk planning."
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. POSITION SIZING & EXECUTION LEVELS
    # ---------------------------------------------------------
    total_investment = round(intel["Entry"] * selected_qty, 2)
    total_risk_amt = round((intel["Entry"] - intel["SL"]) * selected_qty, 2)
    potential_profit_t1 = round((intel["T1"] - intel["Entry"]) * selected_qty, 2)

    st.markdown(f"### 💰 Position Sizing & Capital Outlay ({lot_multiplier})")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("📦 Selected Quantity", f"{selected_qty} Qty", lot_multiplier)
    sc2.metric("💵 Total Capital Required", f"₹{total_investment:,.2f}", f"@ ₹{intel['Entry']} prem")
    sc3.metric("🛡️ Total Max Risk (SL)", f"₹{total_risk_amt:,.2f}", f"@ ₹{intel['SL']} stop-loss")
    sc4.metric("🎯 Target 1 Profit (+35%)", f"₹{potential_profit_t1:,.2f}", f"@ ₹{intel['T1']}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 7. PREDICTIVE MULTI-PANE CHART (PRICE + EMA RIBBON + RSI)
    # ---------------------------------------------------------
    st.subheader(f"📊 Predictive Trend & Trigger Chart ({timeframe_choice})")

    df_c = intel["DataFrame"].tail(90)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.74, 0.26],
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
            name="9 EMA (Fast)",
            line=dict(color="#00E5FF", width=1.4),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["EMA20"],
            mode="lines",
            name="20 EMA (Trend)",
            line=dict(color="#FFD700", width=1.6),
        ),
        row=1,
        col=1,
    )

    fig.add_hline(
        y=intel["Resistance"],
        line_dash="dot",
        line_color="#00E676",
        annotation_text=f"🚀 Breakout Trigger: ₹{intel['Resistance']:,.2f}",
        annotation_position="top left",
        row=1,
        col=1,
    )
    fig.add_hline(
        y=intel["Support"],
        line_dash="dot",
        line_color="#FF5252",
        annotation_text=f"🔻 Breakdown Trigger: ₹{intel['Support']:,.2f}",
        annotation_position="bottom left",
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_c.index,
            y=df_c["RSI"],
            mode="lines",
            name="RSI (14)",
            line=dict(color="#BB86FC", width=1.6),
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=60, line_dash="dash", line_color="rgba(0,230,118,0.4)", row=2, col=1)
    fig.add_hline(y=40, line_dash="dash", line_color="rgba(255,82,82,0.4)", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=580,
        margin=dict(l=10, r=65, t=30, b=25),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        yaxis=dict(side="right", title="Nifty Spot (₹)", showgrid=True),
        yaxis2=dict(side="right", title="RSI (14)", range=[15, 85], showgrid=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

# Optional Auto-Refresh Loop (Every 60 seconds)
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
