"""
Intraday NSE Scanner (Streamlit)
Run:  pip install streamlit yfinance pandas numpy plotly
      streamlit run intraday_app.py

EDUCATIONAL TOOL. No indicator or strategy guarantees profit. Always check the
backtest tab before trusting any signal, and never risk money you can't lose.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Intraday Scanner", layout="wide")

DEFAULT_WATCHLIST = (
    "RELIANCE,HDFCBANK,ICICIBANK,KOTAKBANK,BAJFINANCE,BHARTIARTL,TITAN,BHEL,"
    "HEROMOTOCO,ADANIGREEN,BSE,INFY,TCS,SBIN,AXISBANK,LT,ITC,MARUTI,TATAMOTORS,SUNPHARMA"
)
COST_PCT = 0.05  # approx round-trip brokerage + taxes + slippage, in %


# ---------------------------------------------------------------- data
@st.cache_data(ttl=60, show_spinner=False)
def load(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(f"{symbol}.NS", period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


# ---------------------------------------------------------------- indicators
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["date"] = d.index.date
    d["ema9"] = d["Close"].ewm(span=9, adjust=False).mean()
    d["ema21"] = d["Close"].ewm(span=21, adjust=False).mean()

    delta = d["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    tr = pd.concat([
        d["High"] - d["Low"],
        (d["High"] - d["Close"].shift()).abs(),
        (d["Low"] - d["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()

    tp = (d["High"] + d["Low"] + d["Close"]) / 3
    d["vwap"] = (tp * d["Volume"]).groupby(d["date"]).cumsum() / d["Volume"].groupby(d["date"]).cumsum()

    d["vol_ratio"] = d["Volume"] / d["Volume"].rolling(20).mean()

    # Opening range = first 3 candles (9:15-9:30 on 5m)
    d["orh"] = d.groupby("date")["High"].transform(lambda s: s.iloc[:3].max())
    d["orl"] = d.groupby("date")["Low"].transform(lambda s: s.iloc[:3].min())
    d["bar_no"] = d.groupby("date").cumcount()

    # Score: +1 per bullish condition, -1 per bearish one (range -5..+5)
    bull = ((d["Close"] > d["vwap"]).astype(int)
            + (d["ema9"] > d["ema21"]).astype(int)
            + d["rsi"].between(55, 72).astype(int)
            + (d["vol_ratio"] > 1.5).astype(int)
            + (d["Close"] > d["orh"]).astype(int))
    bear = ((d["Close"] < d["vwap"]).astype(int)
            + (d["ema9"] < d["ema21"]).astype(int)
            + d["rsi"].between(28, 45).astype(int)
            + (d["vol_ratio"] > 1.5).astype(int)
            + (d["Close"] < d["orl"]).astype(int))
    d["score"] = np.where(bull >= bear, bull, -bear)
    return d


def levels(entry, atr, side, rr=2.0, atr_mult=1.5):
    risk = atr * atr_mult
    if side == "BUY":
        return entry - risk, entry + risk * rr
    return entry + risk, entry - risk * rr


def verdict(score, min_score):
    if score >= min_score:
        return "BUY"
    if score <= -min_score:
        return "SELL"
    return "WAIT"


# ---------------------------------------------------------------- backtest
def backtest(df: pd.DataFrame, min_score: int, rr: float, atr_mult: float) -> pd.DataFrame:
    d = add_indicators(df)
    trades = []
    for day, g in d.groupby("date"):
        g = g.reset_index()
        for i in range(3, len(g) - 2):
            row = g.iloc[i]
            side = verdict(row["score"], min_score)
            if side == "WAIT" or np.isnan(row["atr"]):
                continue
            entry = row["Close"]
            sl, tgt = levels(entry, row["atr"], side, rr, atr_mult)
            exit_px, why = g["Close"].iloc[-1], "EOD"
            for j in range(i + 1, len(g)):
                hi, lo = g["High"].iloc[j], g["Low"].iloc[j]
                if side == "BUY":
                    if lo <= sl: exit_px, why = sl, "SL"; break      # SL checked first (conservative)
                    if hi >= tgt: exit_px, why = tgt, "TARGET"; break
                else:
                    if hi >= sl: exit_px, why = sl, "SL"; break
                    if lo <= tgt: exit_px, why = tgt, "TARGET"; break
            pnl = (exit_px - entry) / entry * 100 * (1 if side == "BUY" else -1) - COST_PCT
            trades.append({"date": day, "side": side, "entry": round(entry, 2),
                           "exit": round(exit_px, 2), "result": why, "pnl_%": round(pnl, 3)})
            break  # one trade per day
    return pd.DataFrame(trades)


# ---------------------------------------------------------------- UI
st.title("📈 Intraday NSE Scanner")
st.caption("Rule-based signals + ATR stoploss. Not financial advice, and no signal is guaranteed.")

with st.sidebar:
    st.header("Settings")
    capital = st.number_input("Capital (₹)", 10000, 10_000_000, 100000, 5000)
    risk_pct = st.slider("Risk per trade (% of capital)", 0.25, 2.0, 0.5, 0.25)
    interval = st.selectbox("Candle", ["5m", "15m"], index=0)
    min_score = st.slider("Min score to act (out of 5)", 3, 5, 4)
    rr = st.slider("Reward : Risk", 1.0, 3.0, 2.0, 0.5)
    atr_mult = st.slider("Stoploss = ATR ×", 1.0, 3.0, 1.5, 0.25)
    watch = st.text_area("Watchlist (NSE symbols, comma separated)", DEFAULT_WATCHLIST, height=120)
    symbols = [s.strip().upper() for s in watch.split(",") if s.strip()]

tab_scan, tab_detail, tab_bt = st.tabs(["🔍 Scanner", "📊 Stock detail", "🧪 Backtest"])

# ---- Scanner
with tab_scan:
    if st.button("Scan now", type="primary"):
        rows, bar = [], st.progress(0.0)
        for k, sym in enumerate(symbols):
            bar.progress((k + 1) / len(symbols), text=f"Analysing {sym}")
            raw = load(sym, "5d", interval)
            if len(raw) < 40:
                continue
            d = add_indicators(raw)
            last = d.iloc[-1]
            side = verdict(last["score"], min_score)
            entry = last["Close"]
            sl, tgt = levels(entry, last["atr"], "BUY" if side != "SELL" else "SELL", rr, atr_mult)
            per_share_risk = abs(entry - sl)
            qty = int(min((capital * risk_pct / 100) / per_share_risk, capital / entry)) if per_share_risk else 0
            day = d[d["date"] == last["date"]]
            rows.append({
                "Symbol": sym, "Signal": side, "Score": int(last["score"]),
                "LTP": round(entry, 2),
                "Day %": round((entry / day["Open"].iloc[0] - 1) * 100, 2),
                "RSI": round(last["rsi"], 1),
                "Vol x": round(last["vol_ratio"], 2),
                "VWAP": round(last["vwap"], 2),
                "Entry": round(entry, 2), "Stoploss": round(sl, 2), "Target": round(tgt, 2),
                "Qty": qty, "Max loss ₹": round(qty * per_share_risk),
            })
        bar.empty()
        st.session_state["scan"] = pd.DataFrame(rows)

    scan = st.session_state.get("scan")
    if scan is not None and not scan.empty:
        scan = scan.reindex(scan["Score"].abs().sort_values(ascending=False).index)
        act = scan[scan["Signal"] != "WAIT"]
        st.subheader(f"{len(act)} actionable setups")
        color = lambda v: ("background-color:#d4f5dd" if v == "BUY"
                           else "background-color:#fbd5d5" if v == "SELL" else "")
        st.dataframe(scan.style.map(color, subset=["Signal"]), use_container_width=True, hide_index=True)
        st.info("Entry only on a fresh candle close. If price already ran past Entry by more than ~0.5 ATR, skip it. "
                "Exit everything by 3:15 PM. Stoploss is mandatory.")
    elif scan is not None:
        st.warning("No data returned. Market may be closed, or symbols are invalid.")

# ---- Detail
with tab_detail:
    sym = st.selectbox("Stock", symbols)
    raw = load(sym, "5d", interval)
    if len(raw) >= 40:
        d = add_indicators(raw)
        today = d[d["date"] == d["date"].iloc[-1]]
        last = d.iloc[-1]
        side = verdict(last["score"], min_score)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LTP", f"₹{last['Close']:.2f}")
        c2.metric("Signal", side, f"score {int(last['score'])}")
        c3.metric("RSI", f"{last['rsi']:.0f}")
        c4.metric("Volume vs avg", f"{last['vol_ratio']:.1f}x")

        fig = go.Figure(go.Candlestick(x=today.index, open=today["Open"], high=today["High"],
                                       low=today["Low"], close=today["Close"], name="Price"))
        fig.add_scatter(x=today.index, y=today["vwap"], name="VWAP", line=dict(color="orange"))
        fig.add_scatter(x=today.index, y=today["ema9"], name="EMA9", line=dict(width=1))
        fig.add_scatter(x=today.index, y=today["ema21"], name="EMA21", line=dict(width=1))
        if side != "WAIT":
            sl, tgt = levels(last["Close"], last["atr"], side, rr, atr_mult)
            fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="Stoploss")
            fig.add_hline(y=tgt, line_color="green", line_dash="dash", annotation_text="Target")
            fig.add_hline(y=last["Close"], line_color="gray", annotation_text="Entry")
        fig.update_layout(height=520, xaxis_rangeslider_visible=False, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Why this signal**")
        checks = {
            "Price vs VWAP": "above" if last["Close"] > last["vwap"] else "below",
            "EMA9 vs EMA21": "bullish" if last["ema9"] > last["ema21"] else "bearish",
            "RSI": f"{last['rsi']:.0f}",
            "Volume spike (>1.5x)": "yes" if last["vol_ratio"] > 1.5 else "no",
            "Opening range": ("broke up" if last["Close"] > last["orh"]
                              else "broke down" if last["Close"] < last["orl"] else "inside range"),
        }
        st.table(pd.DataFrame(checks.items(), columns=["Check", "Reading"]))
    else:
        st.warning("Not enough data for this symbol right now.")

# ---- Backtest
with tab_bt:
    st.write("Replays the same rules on the last ~30 days (one trade per day, SL checked first, "
             f"costs {COST_PCT}% per trade). Use this to see if the strategy has any edge **before** using real money.")
    if st.button("Run backtest on selected stock"):
        raw30 = load(sym, "30d", interval)
        if len(raw30) < 100:
            st.warning("Not enough history.")
        else:
            t = backtest(raw30, min_score, rr, atr_mult)
            if t.empty:
                st.info("No trades triggered with these settings.")
            else:
                wins = (t["pnl_%"] > 0).mean() * 100
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Trades", len(t))
                m2.metric("Win rate", f"{wins:.0f}%")
                m3.metric("Avg P&L / trade", f"{t['pnl_%'].mean():.2f}%")
                m4.metric("Total P&L", f"{t['pnl_%'].sum():.2f}%")
                st.line_chart(t.set_index("date")["pnl_%"].cumsum())
                st.dataframe(t, use_container_width=True, hide_index=True)
                st.caption("A small sample (≈20 trades) proves nothing. Paper-trade for a few weeks first.")
