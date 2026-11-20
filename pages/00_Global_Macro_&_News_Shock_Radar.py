from datetime import datetime, time as dt_time
import hashlib
import html
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Global Macro, News Shock & Market Regime Radar | MU₹A Rendezvous",
    page_icon="🌍",
    layout="wide",
)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
is_market_open = (
    now_ist.weekday() < 5
    and dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utils.pick_ledger import record_picks as _ledger_record_picks
except Exception:
    _ledger_record_picks = None


def _save_macro_picks_to_ledger(
    picks: list[dict], module_label: str = "Macro Radar Top Picks"
) -> int:
    if not picks:
        return 0
    if callable(_ledger_record_picks):
        try:
            return int(_ledger_record_picks(module_label, picks))
        except Exception:
            pass

    ledger_dir = REPO_ROOT / "data_ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_file = ledger_dir / "pick_click_ledger.csv"
    cols = [
        "pick_id",
        "logged_at_ist",
        "session_date",
        "iso_week",
        "module",
        "symbol",
        "side",
        "entry_price",
        "stop_loss",
        "target_1",
        "target_2",
        "notes",
    ]
    ts_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    s_date = now_ist.strftime("%Y-%m-%d")
    i_week = f"{now_ist.isocalendar().year}-W{now_ist.isocalendar().week:02d}"
    bucket = now_ist.strftime("%Y-%m-%d %H:%M")

    existing = pd.read_csv(ledger_file) if ledger_file.exists() else pd.DataFrame(columns=cols)
    seen = set(existing["pick_id"].dropna().astype(str)) if not existing.empty else set()
    new_rows = []
    for p in picks:
        sym = str(p["symbol"]).strip().upper()
        if not sym.endswith(".NS"):
            sym = f"{sym}.NS"
        side = str(p.get("side", "BUY")).upper()
        entry = float(p["entry"])
        pid = hashlib.sha1(
            f"{bucket}|{module_label}|{sym}|{side}|{entry:.4f}".encode("utf-8")
        ).hexdigest()[:12]
        if pid in seen:
            continue
        seen.add(pid)
        new_rows.append({
            "pick_id": pid,
            "logged_at_ist": ts_str,
            "session_date": s_date,
            "iso_week": i_week,
            "module": module_label,
            "symbol": sym,
            "side": side,
            "entry_price": round(entry, 2),
            "stop_loss": round(float(p["sl"]), 2),
            "target_1": round(float(p["t1"]), 2),
            "target_2": round(float(p["t2"]), 2),
            "notes": str(p.get("notes", "")),
        })
    if not new_rows:
        return 0
    out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True).drop_duplicates(
        subset=["pick_id"], keep="first"
    )
    out.to_csv(ledger_file, index=False)
    return len(new_rows)


# ---------------------------------------------------------
# 1. HEADER & LIVE CONTROLS
# ---------------------------------------------------------
st.title("🌍 Global Macro, News Shock & Market Regime Radar")

c_top1, c_top2 = st.columns([4.2, 1.0])
with c_top1:
    session_badge = (
        "🟢 LIVE NSE SESSION (9:15 AM – 3:30 PM IST)"
        if is_market_open
        else "🟡 PRE-MARKET / POST-CLOSE BRIEFING"
    )
    st.caption(f"{session_badge} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")
with c_top2:
    if st.button("🔄 Refresh Macro & Picks", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# 2. LIVE GLOBAL MACRO & INDIA PULSE FETCHER
# ---------------------------------------------------------
MACRO_TICKERS = {
    "🇮🇳 Nifty 50": {"ticker": "^NSEI", "group": "India"},
    "🏦 Nifty Bank": {"ticker": "^NSEBANK", "group": "India"},
    "⚡ India VIX": {"ticker": "^INDIAVIX", "group": "India"},
    "🇺🇸 S&P 500": {"ticker": "^GSPC", "group": "US"},
    "💻 Nasdaq 100": {"ticker": "^IXIC", "group": "US"},
    "🏛️ Dow Jones": {"ticker": "^DJI", "group": "US"},
    "🛢️ Brent Crude ($)": {"ticker": "BZ=F", "group": "Commodities & FX"},
    "🥇 Gold ($)": {"ticker": "GC=F", "group": "Commodities & FX"},
    "💵 USD / INR (₹)": {"ticker": "INR=X", "group": "Commodities & FX"},
    "📈 US 10Y Yield (%)": {"ticker": "^TNX", "group": "Commodities & FX"},
    "🌐 US Dollar Index": {"ticker": "DX-Y.NYB", "group": "Commodities & FX"},
}

LIQUID_INSTITUTIONAL_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL",
    "ITC", "LT", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "M&M", "MARUTI",
    "TATAMOTORS", "SUNPHARMA", "NTPC", "POWERGRID", "TATASTEEL", "HINDALCO",
    "JSWSTEEL", "HAL", "BEL", "TRENT", "TITAN", "ADANIPORTS", "ONGC",
    "COALINDIA", "DLF", "SIEMENS", "ABB", "POLYCAB", "PERSISTENT", "COFORGE",
]


@st.cache_data(ttl=120)
def fetch_global_macro_snapshot():
    tickers = [v["ticker"] for v in MACRO_TICKERS.values()]
    data = {}
    try:
        raw = yf.download(
            tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
        for label, meta in MACRO_TICKERS.items():
            sym = meta["ticker"]
            sub = pd.DataFrame()
            if isinstance(raw.columns, pd.MultiIndex) and sym in raw.columns.get_level_values(0):
                sub = raw[sym].dropna(subset=["Close"])
            if len(sub) >= 2:
                last_c = float(sub["Close"].iloc[-1])
                prev_c = float(sub["Close"].iloc[-2])
                chg_pct = ((last_c - prev_c) / prev_c) * 100.0 if prev_c > 0 else 0.0
                data[label] = {
                    "price": last_c,
                    "chg_pct": chg_pct,
                    "group": meta["group"],
                }
            elif len(sub) == 1:
                data[label] = {
                    "price": float(sub["Close"].iloc[-1]),
                    "chg_pct": 0.0,
                    "group": meta["group"],
                }
    except Exception:
        pass
    return data


@st.cache_data(ttl=120)
def scan_institutional_vs_trap_stocks(tickers: list[str]) -> pd.DataFrame:
    syms = [f"{t}.NS" for t in tickers]
    try:
        raw = yf.download(
            syms,
            period="1mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    rows = []
    for t in tickers:
        sym = f"{t}.NS"
        sub = pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex) and sym in raw.columns.get_level_values(0):
            sub = raw[sym].dropna(subset=["Open", "High", "Low", "Close"])
        if len(sub) < 10:
            continue

        c_now = float(sub["Close"].iloc[-1])
        o_now = float(sub["Open"].iloc[-1])
        h_now = float(sub["High"].iloc[-1])
        l_now = float(sub["Low"].iloc[-1])
        c_prev = float(sub["Close"].iloc[-2])
        if c_prev <= 0:
            continue

        chg_pct = ((c_now - c_prev) / c_prev) * 100.0
        vol_now = float(sub["Volume"].iloc[-1]) if "Volume" in sub.columns else 0.0
        vol_avg = float(sub["Volume"].iloc[-11:-1].mean()) if "Volume" in sub.columns else 0.0
        rvol = round(vol_now / vol_avg, 2) if vol_avg > 0 else 1.0

        ema20 = float(sub["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        rng = max(h_now - l_now, 0.01)
        close_pos = ((c_now - l_now) / rng) * 100.0
        turnover_cr = (c_now * vol_now) / 1e7

        # Detect Pump-and-Dump / Chasing Traps vs. Clean Institutional Accumulation
        if abs(chg_pct) > 9.5 or (chg_pct > 4.0 and close_pos < 35.0):
            quality = "🚫 TRAP / PUMP-DUMP RISK"
            bias = "AVOID"
            score = -50.0
        elif chg_pct >= 1.0 and rvol >= 1.25 and c_now > ema20 and close_pos >= 65.0 and turnover_cr >= 40.0:
            quality = "🟢 INSTITUTIONAL BUY"
            bias = "BUY"
            score = (chg_pct * 8.0) + (rvol * 12.0) + (close_pos * 0.3)
        elif chg_pct <= -1.0 and rvol >= 1.25 and c_now < ema20 and close_pos <= 35.0 and turnover_cr >= 40.0:
            quality = "🔴 INSTITUTIONAL SELL"
            bias = "SHORT"
            score = (abs(chg_pct) * 8.0) + (rvol * 12.0) + ((100.0 - close_pos) * 0.3)
        else:
            quality = "⚪ NEUTRAL / WAIT"
            bias = "WAIT"
            score = 0.0

        if bias == "SHORT":
            entry = round(c_now * 1.003, 2)
            sl = round(c_now * 1.015, 2)
            t1 = round(c_now * 0.981, 2)
            t2 = round(c_now * 0.964, 2)
        else:
            entry = round(c_now * 0.996, 2)
            sl = round(c_now * 0.983, 2)
            t1 = round(c_now * 1.020, 2)
            t2 = round(c_now * 1.036, 2)

        rows.append({
            "Stock": t,
            "Signal": quality,
            "Bias": bias,
            "LTP": round(c_now, 2),
            "Change %": round(chg_pct, 2),
            "RVOL": rvol,
            "Close Strength %": round(close_pos, 1),
            "Turnover (Cr)": round(turnover_cr, 1),
            "Entry": entry,
            "Stop_Loss": sl,
            "Target_1": t1,
            "Target_2": t2,
            "Score": round(score, 1),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(by="Score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------
# 3. LIVE GLOBAL & INDIA FINANCIAL NEWS RSS PARSER
# ---------------------------------------------------------
NEWS_FEEDS = [
    ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol Business", "https://www.moneycontrol.com/rss/business.xml"),
    ("CNBC TV18 Market", "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/market.xml"),
    ("Yahoo Finance Top News", "https://finance.yahoo.com/news/rssindex"),
]


def _classify_headline(title: str) -> tuple[str, str]:
    t = title.lower()
    shock_words = ["crash", "plunge", "tumble", "slump", "war", "tariff", "sanction", "sell-off", "selloff", "rout", "fear", "crisis", "downgrade", "ban", "probe", "fraud"]
    rate_words = ["fed", "rbi", "inflation", "cpi", "interest rate", "yield", "powell", "mpc", "gdp", "jobs"]
    oil_words = ["oil", "crude", "brent", "opec", "gas", "rupee", "inr", "dollar"]
    flow_words = ["fii", "fpi", "dii", "block deal", "bulk deal", "outflow", "inflow", "buyback", "ipo"]
    bull_words = ["surge", "rally", "soar", "record high", "jump", "gain", "order win", "profit jumps", "upgrade"]

    if any(w in t for w in shock_words):
        return "🚨 SHOCK / RISK ALERT", "Watch for sudden volatility, gap-downs, or stop-loss sweeps in affected stocks."
    if any(w in t for w in oil_words):
        return "🛢️ CRUDE / CURRENCY", "Impacts OMCs, aviation, paints, chemicals (crude) or IT/pharma/FII flows (Rupee)."
    if any(w in t for w in rate_words):
        return "🏦 CENTRAL BANK / MACRO", "Moves Banks, NBFCs, Realty, Auto, and global risk appetite."
    if any(w in t for w in flow_words):
        return "💰 INSTITUTIONAL FLOW", "Signals heavy FII/DII buying or block-deal supply/demand overhang."
    if any(w in t for w in bull_words):
        return "📈 POSITIVE CATALYST", "Supports momentum continuation if confirmed by price above VWAP & RVOL."
    return "📰 MARKET UPDATE", "Monitor sector reaction during active NSE hours (9:15 AM – 3:30 PM IST)."


@st.cache_data(ttl=180)
def fetch_live_market_headlines(max_per_feed: int = 5) -> pd.DataFrame:
    items = []
    seen_titles = set()
    headers = {"User-Agent": "Mozilla/5.0"}

    for source_name, url in NEWS_FEEDS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            count = 0
            for item in root.findall(".//item"):
                raw_title = item.findtext("title") or ""
                clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                if not clean_title or clean_title.lower() in seen_titles:
                    continue
                seen_titles.add(clean_title.lower())
                pub_date = (item.findtext("pubDate") or "").strip()
                link = (item.findtext("link") or "").strip()
                tag, impact_note = _classify_headline(clean_title)
                items.append({
                    "Impact Tag": tag,
                    "Headline": clean_title,
                    "How It Affects Market": impact_note,
                    "Source": source_name,
                    "Published": pub_date[:25] if pub_date else "Recent",
                    "Link": link,
                })
                count += 1
                if count >= max_per_feed:
                    break
        except Exception:
            continue

    return pd.DataFrame(items)


# ---------------------------------------------------------
# 4. SIMPLE ONE-LINE ADVANCE SIGNAL BANNER (GREEN OR RED)
# ---------------------------------------------------------
macro = fetch_global_macro_snapshot()

sp_chg = macro.get("🇺🇸 S&P 500", {}).get("chg_pct", 0.0)
nq_chg = macro.get("💻 Nasdaq 100", {}).get("chg_pct", 0.0)
oil_chg = macro.get("🛢️ Brent Crude ($)", {}).get("chg_pct", 0.0)
vix_px = macro.get("⚡ India VIX", {}).get("price", 14.0)
inr_chg = macro.get("💵 USD / INR (₹)", {}).get("chg_pct", 0.0)

macro_score = 0
if sp_chg >= 0.35:
    macro_score += 1
elif sp_chg <= -0.5:
    macro_score -= 1

if nq_chg >= 0.45:
    macro_score += 1
elif nq_chg <= -0.6:
    macro_score -= 1

if oil_chg <= -0.5:
    macro_score += 1
elif oil_chg >= 1.5:
    macro_score -= 1

if inr_chg <= -0.05:
    macro_score += 1
elif inr_chg >= 0.25:
    macro_score -= 1

if vix_px < 15.0:
    macro_score += 1
elif vix_px >= 17.5:
    macro_score -= 2

is_green_line = macro_score >= 0

if is_green_line:
    st.success(
        f"🟢 **SIMPLE ADVANCE LINE: GREEN (INSTITUTIONAL RISK APPETITE EXPANDING — BUY QUALITY BREAKOUTS)** | "
        f"US S&P {sp_chg:+.2f}%, Nasdaq {nq_chg:+.2f}%, Crude {oil_chg:+.2f}%, USD/INR {inr_chg:+.2f}%, India VIX {vix_px:.2f} → "
        f"**Focus on Institutional Longs after 9:15 AM IST & book gains at Target 1.**"
    )
else:
    st.error(
        f"🔴 **SIMPLE ADVANCE LINE: RED (INSTITUTIONAL RISK APPETITE SHRINKING — DEFENSIVE / SHORT BIAS)** | "
        f"US S&P {sp_chg:+.2f}%, Nasdaq {nq_chg:+.2f}%, Crude {oil_chg:+.2f}%, USD/INR {inr_chg:+.2f}%, India VIX {vix_px:.2f} → "
        f"**Avoid chasing gap-ups; focus on Weak Breakdown Shorts or stay small with strict Stop-Loss.**"
    )

# ---------------------------------------------------------
# 5. TABBED VIEW: TOP INSTITUTIONAL PICKS & ANTI-PUMP-DUMP | MACRO DETAILS | NEWS WIRE
# ---------------------------------------------------------
tab_picks, tab_macro, tab_news = st.tabs([
    "🎯 Top Institutional Picks & Trap Filter",
    "📊 Global Macro Details (US, Crude, INR, VIX)",
    "📰 Live Breaking News & Shock Wire",
])

with tab_picks:
    st.subheader("🎯 High-Liquidity Institutional Picks (Filtered Against Pump-and-Dump Traps)")
    st.caption(
        "Automatically filters out penny/manipulated pump-and-dump spikes and surfaces only liquid NSE stocks "
        "with real institutional volume (`RVOL ≥ 1.25x`), high turnover (`≥ ₹40 Cr`), and strong closing conviction."
    )

    df_inst = scan_institutional_vs_trap_stocks(LIQUID_INSTITUTIONAL_UNIVERSE)

    if df_inst.empty:
        st.warning("Unable to load live stock data right now. Click **Refresh Macro & Picks** above.")
    else:
        buy_picks = df_inst[df_inst["Bias"] == "BUY"].head(3).reset_index(drop=True)
        short_picks = df_inst[df_inst["Bias"] == "SHORT"].head(3).reset_index(drop=True)
        trap_stocks = df_inst[df_inst["Bias"] == "AVOID"].reset_index(drop=True)

        c_buy, c_short = st.columns(2)
        ledger_batch = []

        with c_buy:
            st.markdown("#### 🟢 Top Institutional Longs (Buy Above Support)")
            if buy_picks.empty:
                st.info("No strict institutional buy setups met all filters right now.")
            else:
                for i, r in buy_picks.iterrows():
                    st.success(
                        f"**#{i + 1} {r['Stock']}** — LTP ₹{r['LTP']:,.2f} ({r['Change %']:+.2f}%) | **RVOL:** {r['RVOL']}x | **Turnover:** ₹{r['Turnover (Cr)']:,.0f} Cr\n\n"
                        f"• **Watch Buy:** ₹{r['Entry']:,.2f} | **Strict SL:** ₹{r['Stop_Loss']:,.2f} | **Target 1:** ₹{r['Target_1']:,.2f} | **Target 2:** ₹{r['Target_2']:,.2f}"
                    )
                    if is_green_line and i < 2:
                        ledger_batch.append({
                            "symbol": r["Stock"],
                            "side": "BUY",
                            "entry": float(r["Entry"]),
                            "sl": float(r["Stop_Loss"]),
                            "t1": float(r["Target_1"]),
                            "t2": float(r["Target_2"]),
                            "notes": f"Macro Green Top #{i + 1} | RVOL {r['RVOL']}x",
                        })

        with c_short:
            st.markdown("#### 🔴 Top Institutional Shorts (Intraday Breakdown Only)")
            if short_picks.empty:
                st.info("No strict institutional breakdown shorts met all filters right now.")
            else:
                for i, r in short_picks.iterrows():
                    st.error(
                        f"**#{i + 1} {r['Stock']}** — LTP ₹{r['LTP']:,.2f} ({r['Change %']:+.2f}%) | **RVOL:** {r['RVOL']}x | **Turnover:** ₹{r['Turnover (Cr)']:,.0f} Cr\n\n"
                        f"• **Watch Short:** ₹{r['Entry']:,.2f} | **Strict SL:** ₹{r['Stop_Loss']:,.2f} | **Target 1:** ₹{r['Target_1']:,.2f} | **Target 2:** ₹{r['Target_2']:,.2f}"
                    )
                    if (not is_green_line) and i < 2:
                        ledger_batch.append({
                            "symbol": r["Stock"],
                            "side": "SHORT",
                            "entry": float(r["Entry"]),
                            "sl": float(r["Stop_Loss"]),
                            "t1": float(r["Target_1"]),
                            "t2": float(r["Target_2"]),
                            "notes": f"Macro Red Top #{i + 1} | RVOL {r['RVOL']}x",
                        })

        # --- PUSH MACRO-ALIGNED PICKS TO ANALYSER SESSION STATE ---
        st.session_state.setdefault("live_scanner_picks", {})[
            "Macro Radar Top Picks"
        ] = ledger_batch

        if ledger_batch and st.button("📌 Log Top 2 Macro-Aligned Picks to History Ledger", type="primary"):
            saved_n = _save_macro_picks_to_ledger(ledger_batch, "Macro Radar Top Picks")
            st.success(f"Recorded {saved_n} macro-aligned Top 2 pick(s) to your history ledger.")

        if not trap_stocks.empty:
            st.warning(
                f"🚫 **Pump-and-Dump / Overextended Trap Warning:** {', '.join(trap_stocks['Stock'].tolist())} "
                "showed erratic spikes or weak closes—avoid chasing."
            )

        st.markdown("---")
        st.subheader("🛡️ Social Media / Telegram Tip Stress-Tester (Check Any Stock Before Buying)")
        tip_col1, tip_col2 = st.columns([2.0, 3.0])
        with tip_col1:
            custom_sym = st.text_input(
                "Enter any NSE stock symbol from a tip/channel (e.g. SUZLON, IRFC, TATAPOWER):",
                value="",
            ).strip().upper()
        with tip_col2:
            if custom_sym:
                clean_sym = custom_sym.replace(".NS", "")
                try:
                    t_df = yf.Ticker(f"{clean_sym}.NS").history(period="1mo", interval="1d", auto_adjust=True)
                    if t_df is None or len(t_df) < 5:
                        st.error(f"Could not find NSE data for **{clean_sym}**.")
                    else:
                        tc_now = float(t_df["Close"].iloc[-1])
                        tc_prev = float(t_df["Close"].iloc[-2])
                        th_now = float(t_df["High"].iloc[-1])
                        tl_now = float(t_df["Low"].iloc[-1])
                        t_chg = ((tc_now - tc_prev) / tc_prev) * 100.0
                        t_vol = float(t_df["Volume"].iloc[-1])
                        t_vavg = float(t_df["Volume"].iloc[:-1].mean())
                        t_rvol = round(t_vol / max(t_vavg, 1.0), 2)
                        t_turn_cr = (tc_now * t_vol) / 1e7
                        t_cpos = ((tc_now - tl_now) / max(th_now - tl_now, 0.01)) * 100.0

                        if t_turn_cr < 15.0 or abs(t_chg) > 9.5 or (t_chg > 3.0 and t_cpos < 35.0):
                            st.error(
                                f"🚨 **HIGH TRAP / PUMP-DUMP WARNING on {clean_sym}:** "
                                f"LTP ₹{tc_now:,.2f} ({t_chg:+.2f}%), Turnover ₹{t_turn_cr:.1f} Cr, Close Strength {t_cpos:.0f}%. "
                                "Low liquidity or late-stage dump pattern—do NOT enter blindly!"
                            )
                        elif t_rvol >= 1.25 and t_cpos >= 60.0 and t_chg > 0:
                            st.success(
                                f"✅ **REAL INSTITUTIONAL FOOTPRINT on {clean_sym}:** "
                                f"LTP ₹{tc_now:,.2f} ({t_chg:+.2f}%), RVOL {t_rvol}x, Turnover ₹{t_turn_cr:.1f} Cr, Close Strength {t_cpos:.0f}%. "
                                "Healthy institutional participation—wait for VWAP hold & use strict Stop-Loss."
                            )
                        else:
                            st.warning(
                                f"⚠️ **UNCONFIRMED / WEAK SETUP on {clean_sym}:** "
                                f"LTP ₹{tc_now:,.2f} ({t_chg:+.2f}%), RVOL {t_rvol}x, Close Strength {t_cpos:.0f}%. "
                                "Lacks strong institutional volume confirmation right now."
                            )
                except Exception:
                    st.error("Unable to verify symbol right now.")

        with st.expander("📋 View Full Institutional vs. Trap Scan Table", expanded=False):
            st.dataframe(
                df_inst[["Stock", "Signal", "LTP", "Change %", "RVOL", "Close Strength %", "Turnover (Cr)", "Entry", "Stop_Loss", "Target_1", "Target_2"]],
                use_container_width=True,
                hide_index=True,
            )

with tab_macro:
    st.subheader("📊 Global Cues & India Pulse (US Indices, Crude Oil, USD/INR & India VIX)")
    if not macro:
        st.warning("⚠️ Live global quotes temporarily unavailable.")
    else:
        st.markdown("**🇮🇳 Indian Market & Volatility**")
        c_in = st.columns(3)
        for idx, key in enumerate(["🇮🇳 Nifty 50", "🏦 Nifty Bank", "⚡ India VIX"]):
            if key in macro:
                inv = "inverse" if "VIX" in key else "normal"
                c_in[idx].metric(key, f"{macro[key]['price']:,.2f}", f"{macro[key]['chg_pct']:+.2f}%", delta_color=inv)

        st.markdown("**🇺🇸 Overnight US Cues**")
        c_us = st.columns(3)
        for idx, key in enumerate(["🇺🇸 S&P 500", "💻 Nasdaq 100", "🏛️ Dow Jones"]):
            if key in macro:
                c_us[idx].metric(key, f"{macro[key]['price']:,.2f}", f"{macro[key]['chg_pct']:+.2f}%")

        st.markdown("**🛢️ Commodities, Rupee & Global Yields**")
        c_cm = st.columns(5)
        for idx, key in enumerate(["🛢️ Brent Crude ($)", "🥇 Gold ($)", "💵 USD / INR (₹)", "📈 US 10Y Yield (%)", "🌐 US Dollar Index"]):
            if key in macro:
                inv = "inverse" if any(x in key for x in ["Crude", "USD / INR", "Yield", "Dollar"]) else "normal"
                c_cm[idx].metric(key, f"{macro[key]['price']:,.2f}", f"{macro[key]['chg_pct']:+.2f}%", delta_color=inv)

        st.markdown("---")
        st.markdown(
            "- **Overnight US Indices (S&P 500 & Nasdaq):** Green = global risk appetite expanding; Red = potential gap-down or IT/high-beta pressure.\n"
            "- **Brent Crude Oil:** Rising crude hurts Indian OMCs, aviation, paints, and tyres; falling crude supports Indian margins.\n"
            "- **USD/INR & US 10Y Yield:** Rising USD/INR (weak Rupee) often coincides with FII outflows in Nifty heavyweights.\n"
            "- **India VIX:** Below **15** supports smooth trends; above **18** signals wide swings—reduce position size."
        )

with tab_news:
    st.subheader("📰 Live Global & Indian Market News Wire")
    df_news = fetch_live_market_headlines(max_per_feed=5)
    if df_news.empty:
        st.info("Unable to fetch live RSS headlines right now. Click **Refresh Macro & Picks** to retry.")
    else:
        tag_options = ["All Headlines"] + sorted(df_news["Impact Tag"].unique().tolist())
        chosen_tag = st.selectbox("Filter News by Market Impact:", tag_options, index=0)
        news_view = (
            df_news
            if chosen_tag == "All Headlines"
            else df_news[df_news["Impact Tag"] == chosen_tag].reset_index(drop=True)
        )
        st.dataframe(
            news_view[["Impact Tag", "Headline", "How It Affects Market", "Source", "Published"]],
            use_container_width=True,
            hide_index=True,
        )
