import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Master Confluence Strategy Backtester", layout="wide")
st.title("📊 Master Confluence & Pullback Limit Backtester (6-Month Proof)")
st.markdown("Tests the exact **Night-Before VCP Coil + 20D Breakout + Pullback Limit Entry** strategy across top NSE stocks over the last **6 months** to verify historical win rate and net P&L.")

BACKTEST_UNIVERSE = ["ITC", "APOLLOHOSP", "KALYANKJIL", "DEEPAKFERT", "BELRISE", "BHARTIARTL", "PNB", "EICHERMOT", "SBIN", "HDFCBANK", "ICICIBANK", "BSE", "HINDALCO", "ABB", "RELIANCE", "TCS", "INFY", "AXISBANK", "BAJFINANCE", "SUNPHARMA", "MARUTI", "NTPC", "M&M", "TATASTEEL", "HAL", "BEL", "TRENT", "DIXON", "POLYCAB", "PFC", "RECLTD", "IRFC", "RVNL", "MAZDOCK", "TITAN", "DLF", "INDIGO", "MAXHEALTH"]

c_in1, c_in2, c_in3 = st.columns(3)
capital_per_trade = c_in1.number_input("Capital Allocated per Trade (₹)", min_value=10000, max_value=1000000, value=100000, step=10000)
rr_target = c_in2.selectbox("Profit Target Multiplier", [1.5, 2.0, 2.5, 3.0], index=1)
hold_days = c_in3.slider("Max Holding Days per Trade", min_value=2, max_value=15, value=7)

@st.cache_data(ttl=300)
def run_confluence_backtest(tickers, cap, rr, max_hold):
    raw = yf.download([f"{t}.NS" for t in tickers], period="6mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    trades = []
    for t in tickers:
        try:
            df = raw[f"{t}.NS"].dropna()
            if len(df) < 40: continue
            df["EMA21"] = df["Close"].ewm(span=21).mean()
            df["EMA50"] = df["Close"].ewm(span=50).mean()
            df["VolAvg"] = df["Volume"].rolling(20).mean()
            df["Res20"] = df["High"].rolling(20).max().shift(1)

            i = 25
            while i < len(df) - max_hold:
                prev_c, prev_ema21, prev_ema50, res20 = float(df["Close"].iloc[i-1]), float(df["EMA21"].iloc[i-1]), float(df["EMA50"].iloc[i-1]), float(df["Res20"].iloc[i])
                dist_coil = ((res20 - prev_c) / prev_c) * 100
                # Night-Before Coil Check on Day i-1
                is_coil = (prev_c > prev_ema21 > prev_ema50) and (-2.5 <= dist_coil <= 4.0)
                # Breakout + Volume Expansion Check on Day i
                day_c, day_o, day_h, day_l = float(df["Close"].iloc[i]), float(df["Open"].iloc[i]), float(df["High"].iloc[i]), float(df["Low"].iloc[i])
                rvol = float(df["Volume"].iloc[i]) / max(float(df["VolAvg"].iloc[i]), 1.0)
                if is_coil and day_c >= res20 and day_c > day_o and rvol >= 1.3:
                    limit_entry = round(max(res20, day_h - ((day_h - day_l) * 0.382)), 2)
                    sl = round(min(day_l, limit_entry * 0.985), 2)
                    risk = max(limit_entry - sl, limit_entry * 0.01)
                    target = round(limit_entry + (risk * rr), 2)
                    qty = max(int(cap // limit_entry), 1)

                    filled, exit_p, exit_dt, outcome = False, limit_entry, df.index[i], "Unfilled"
                    for j in range(i + 1, min(i + 1 + max_hold, len(df))):
                        fh, fl, fc = float(df["High"].iloc[j]), float(df["Low"].iloc[j]), float(df["Close"].iloc[j])
                        if not filled:
                            if fl <= limit_entry <= fh:
                                filled = True
                            continue
                        if fl <= sl:
                            exit_p, exit_dt, outcome = sl, df.index[j], "🛑 Stop-Loss Hit"
                            break
                        if fh >= target:
                            exit_p, exit_dt, outcome = target, df.index[j], "🎯 Target Hit"
                            break
                        exit_p, exit_dt, outcome = fc, df.index[j], "⏳ Time Exit"

                    if filled and outcome != "Unfilled":
                        pnl = round((exit_p - limit_entry) * qty, 2)
                        trades.append({"Stock": t, "Entry_Date": df.index[i].strftime("%Y-%m-%d"), "Exit_Date": exit_dt.strftime("%Y-%m-%d"), "Limit_Buy": limit_entry, "Stop_Loss": sl, "Target": target, "Exit_Price": round(exit_p, 2), "Result": outcome, "Net_PnL (₹)": pnl})
                        i += max_hold
                        continue
                i += 1
        except Exception: continue
    return pd.DataFrame(trades)

if st.button("🚀 Run 6-Month Confluence Backtest"):
    st.cache_data.clear()

df_bt = run_confluence_backtest(BACKTEST_UNIVERSE, capital_per_trade, rr_target, hold_days)

if df_bt.empty:
    st.warning("No completed historical trades matched the strict filter parameters.")
else:
    df_bt = df_bt.sort_values(by="Exit_Date").reset_index(drop=True)
    df_bt["Cumulative_PnL"] = df_bt["Net_PnL (₹)"].cumsum()
    total_trades = len(df_bt)
    wins = len(df_bt[df_bt["Net_PnL (₹)"] > 0])
    win_rate = round((wins / total_trades) * 100, 1)
    net_profit = round(df_bt["Net_PnL (₹)"].sum(), 2)
    gross_win = df_bt[df_bt["Net_PnL (₹)"] > 0]["Net_PnL (₹)"].sum()
    gross_loss = abs(df_bt[df_bt["Net_PnL (₹)"] < 0]["Net_PnL (₹)"].sum())
    profit_factor = round(gross_win / max(gross_loss, 1.0), 2)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Executed Trades", total_trades)
    m2.metric("Verified Win Rate", f"{win_rate}%", f"{wins} Wins / {total_trades - wins} Losses")
    m3.metric("Profit Factor", f"{profit_factor}x", "Gross Win / Gross Loss")
    m4.metric("6-Month Net P&L", f"₹{net_profit:,.2f}", f"₹{capital_per_trade:,}/trade")

    fig = go.Figure(go.Scatter(x=df_bt["Exit_Date"], y=df_bt["Cumulative_PnL"], mode="lines+markers", line=dict(color="#00E676", width=2.5), name="Equity Curve"))
    fig.update_layout(title="Cumulative Strategy Equity Curve (6 Months)", template="plotly_dark", height=360, yaxis_title="Cumulative Profit (₹)", margin=dict(l=10, r=20, t=40, b=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader("📋 Complete Historical Trade Log (Pullback Limit Orders Filled)")
    st.dataframe(df_bt.sort_values(by="Entry_Date", ascending=False), width="stretch", hide_index=True)
