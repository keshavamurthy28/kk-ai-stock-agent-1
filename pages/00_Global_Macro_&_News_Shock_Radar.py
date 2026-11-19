from datetime import datetime, time as dt_time
import html
import re
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

# ---------------------------------------------------------
# 1. HEADER & LIVE CONTROLS
# ---------------------------------------------------------
st.title("🌍 Global Macro, News Shock & Market Regime Radar")
st.markdown(
    "**Check This Page FIRST Before Trading:** Explains **what happened** globally and in India, "
    "**why** it matters, **how** it impacts NSE stocks/sectors, and **what may happen next**—so you "
    "never get blindsided by overnight cues, crude spikes, or sudden news."
)

c_top1, c_top2 = st.columns([4.2, 1.0])
with c_top1:
    session_badge = (
        "🟢 LIVE NSE SESSION (9:15 AM – 3:30 PM IST)"
        if is_market_open
        else "🟡 PRE-MARKET / POST-CLOSE BRIEFING"
    )
    st.caption(f"{session_badge} • Synced: **{now_ist.strftime('%d %b %Y, %I:%M:%S %p IST')}**")
with c_top2:
    if st.button("🔄 Refresh Macro & News", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.expander("📘 Beginner Guide: How Global Cues & News Move Indian Stocks", expanded=False):
    st.markdown(
        "- **US Markets (S&P 500 & Nasdaq):** Set the overnight mood. A sharp US drop often causes a gap-down open in Nifty IT and broad Indian equities.\n"
        "- **Brent Crude Oil:** India imports over 80% of its oil. Rising crude hurts paints, aviation, tyres, and OMCs, while benefiting upstream producers like ONGC/Oil India.\n"
        "- **USD/INR & US 10Y Bond Yield:** A falling Rupee (`USD/INR` rising) or spiking US yields often triggers **FII (Foreign Institutional Investor) selling** in Indian large-caps.\n"
        "- **India VIX (Fear Gauge):** Below **14** = calm trending market; **15–19** = choppy swings (use smaller position sizes); **20+** = high shock risk (strict stop-losses mandatory). Not financial advice."
    )

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
# 4. RENDER LIVE MACRO SCORECARD & REGIME VERDICT
# ---------------------------------------------------------
macro = fetch_global_macro_snapshot()

st.subheader("1️⃣ Global Cues & India Pulse (What Is Moving Right Now)")

if not macro:
    st.warning("⚠️ Live global quotes temporarily unavailable. Click **Refresh Macro & News** above.")
else:
    # Group rows cleanly
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

    # ---------------------------------------------------------
    # 5. CRISP "WHAT HAPPENED, WHY, HOW & WHAT MAY HAPPEN NEXT"
    # ---------------------------------------------------------
    st.subheader("2️⃣ Crisp Intelligence Briefing: What Happened, Why, How & What May Happen Next")

    sp_chg = macro.get("🇺🇸 S&P 500", {}).get("chg_pct", 0.0)
    nq_chg = macro.get("💻 Nasdaq 100", {}).get("chg_pct", 0.0)
    oil_chg = macro.get("🛢️ Brent Crude ($)", {}).get("chg_pct", 0.0)
    oil_px = macro.get("🛢️ Brent Crude ($)", {}).get("price", 0.0)
    vix_px = macro.get("⚡ India VIX", {}).get("price", 14.0)
    inr_chg = macro.get("💵 USD / INR (₹)", {}).get("chg_pct", 0.0)
    us10y_chg = macro.get("📈 US 10Y Yield (%)", {}).get("chg_pct", 0.0)

    risk_flags = 0
    insights = []

    # US Tech & Broad Market Cue
    if sp_chg <= -1.0 or nq_chg <= -1.3:
        risk_flags += 2
        insights.append({
            "Factor": f"🇺🇸 US Sell-Off (S&P {sp_chg:+.2f}%, Nasdaq {nq_chg:+.2f}%)",
            "What & Why": "Global institutions reduced equity risk overnight on US growth/rate worries.",
            "How It Hits NSE": "Nifty IT & high-beta stocks often open weak; gap-up long breakouts face higher failure risk.",
            "What May Happen Next": "Wait for the first 15–30 mins (until 9:45 AM IST) to see if Nifty holds opening lows before buying.",
        })
    elif sp_chg >= 0.8 or nq_chg >= 1.0:
        insights.append({
            "Factor": f"🇺🇸 US Rally (S&P {sp_chg:+.2f}%, Nasdaq {nq_chg:+.2f}%)",
            "What & Why": "Strong overnight risk-on appetite across US equities and tech.",
            "How It Hits NSE": "Supports positive opening sentiment in Nifty IT, Financials, and momentum breakouts.",
            "What May Happen Next": "Watch if Nifty sustains above opening VWAP; avoid chasing huge gap-ups blindly.",
        })
    else:
        insights.append({
            "Factor": f"🇺🇸 US Cues Neutral/Mixed (S&P {sp_chg:+.2f}%, Nasdaq {nq_chg:+.2f}%)",
            "What & Why": "No major overnight shock from Wall Street; domestic flows will drive today's trend.",
            "How It Hits NSE": "Stock-specific earnings, sector rotation, and FII/DII flows take center stage.",
            "What May Happen Next": "Focus on top relative-strength sectors on the Sector Rotation & PRIME Sniper pages.",
        })

    # Crude Oil Cue
    if oil_chg >= 2.0 or oil_px >= 85.0:
        risk_flags += 1
        insights.append({
            "Factor": f"🛢️ Crude Oil Pressure (${oil_px:.2f}, {oil_chg:+.2f}%)",
            "What & Why": "Supply concerns or geopolitical tension pushed Brent crude higher.",
            "How It Hits NSE": "Pressures margins for Aviation, Paints, Tyres, Chemicals & OMCs; helps ONGC/Oil India.",
            "What May Happen Next": "Avoid aggressive longs in oil-sensitive sectors; check Bearish Terminal for weak setups.",
        })
    elif oil_chg <= -2.0:
        insights.append({
            "Factor": f"🛢️ Crude Oil Cooling (${oil_px:.2f}, {oil_chg:+.2f}%)",
            "What & Why": "Lower crude prices ease India's inflation and import bill pressure.",
            "How It Hits NSE": "Tailwind for Paints, Aviation, OMCs, Autos, and broader consumer sentiment.",
            "What May Happen Next": "Look for VWAP breakouts in Auto, FMCG, and Paint stocks if volume confirms.",
        })

    # Currency & Yield Cue
    if inr_chg >= 0.35 or us10y_chg >= 2.0:
        risk_flags += 1
        insights.append({
            "Factor": f"💵 Rupee Weakening / Yields Up (USD/INR {inr_chg:+.2f}%, US10Y {us10y_chg:+.2f}%)",
            "What & Why": "Stronger US Dollar and higher US bond yields pull foreign capital toward US assets.",
            "How It Hits NSE": "Increases probability of FII selling in heavyweight Nifty stocks (HDFCBANK, RELIANCE, ICICIBANK).",
            "What May Happen Next": "Expect intraday pullbacks near resistance; book profits faster at Target 1.",
        })

    # India VIX Regime
    if vix_px >= 18.0:
        risk_flags += 2
        insights.append({
            "Factor": f"⚡ Elevated India VIX ({vix_px:.2f})",
            "What & Why": "Option traders are pricing in wide daily swings and potential news shocks.",
            "How It Hits NSE": "Tight intraday stop-losses get swept easily by sudden 1–2% whipsaws.",
            "What May Happen Next": "Cut position size by 50%, avoid over-leveraging, and stick strictly to A+ setups.",
        })
    elif vix_px >= 15.0:
        risk_flags += 1
        insights.append({
            "Factor": f"⚡ Moderate-High India VIX ({vix_px:.2f})",
            "What & Why": "Volatility is slightly elevated above calm levels.",
            "How It Hits NSE": "Both bullish and bearish swings can move quickly during the session.",
            "What May Happen Next": "Respect your Stop-Loss strictly and book partial/full gains at Target 1.",
        })
    else:
        insights.append({
            "Factor": f"⚡ Calm India VIX ({vix_px:.2f})",
            "What & Why": "Low expected volatility indicates orderly institutional participation.",
            "How It Hits NSE": "VWAP and 20 EMA trend setups tend to hold cleaner without erratic spikes.",
            "What May Happen Next": "Standard disciplined intraday execution works well with normal risk rules.",
        })

    # Overall Pre-Trade Verdict Banner
    if risk_flags >= 3:
        st.error(
            "🔴 **REGIME VERDICT: HIGH SHOCK / DEFENSIVE MODE** — Multiple global/volatility headwinds active. "
            "Reduce trade size, wait until after **9:45 AM IST** for stability, and never trade without a Stop-Loss."
        )
    elif risk_flags >= 1:
        st.warning(
            "🟡 **REGIME VERDICT: SELECTIVE / CAUTIOUS MODE** — Mixed global cues or elevated VIX. "
            "Trade only top-ranked setups with strong `RVOL` and book profits promptly near **Target 1**."
        )
    else:
        st.success(
            "🟢 **REGIME VERDICT: CONSTRUCTIVE / TREND-FRIENDLY** — Global cues and India VIX are supportive. "
            "Follow your scanner levels after **9:15 AM IST** with strict Stop-Loss discipline."
        )

    st.dataframe(pd.DataFrame(insights), use_container_width=True, hide_index=True)

st.markdown("---")

# ---------------------------------------------------------
# 6. LIVE GLOBAL & INDIA BREAKING NEWS WIRE
# ---------------------------------------------------------
st.subheader("3️⃣ Live Global & Indian Market News Wire (Catalyst & Shock Scanner)")
st.caption(
    "Scans live business headlines for sudden shocks, RBI/Fed policy news, crude oil moves, and institutional deal flow."
)

df_news = fetch_live_market_headlines(max_per_feed=5)

if df_news.empty:
    st.info("Unable to fetch live RSS headlines right now (network/feed timeout). Click **Refresh Macro & News** to retry.")
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

    with st.expander("🔗 Open Direct Article Links", expanded=False):
        for _, nrow in news_view.head(10).iterrows():
            if nrow["Link"]:
                st.markdown(f"- **{nrow['Impact Tag']}** — [{nrow['Headline']}]({nrow['Link']}) *({nrow['Source']})*")
