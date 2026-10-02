import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="NSE Strategy Backtester", page_icon="🧪", layout="wide"
)

st.title("🧪 NSE Historical Strategy & Orderflow Backtester")
st.markdown(
    "Backtest custom setups on any NSE equity across **Minute, Hourly, or Daily** timeframes for any date range you desire."
)

# -------------------------------------------------------------------
# SIDEBAR CONTROLS FOR BACKTESTING
# -------------------------------------------------------------------
st.sidebar.header("⚙️ Backtest Parameters")

stock_symbol = st.sidebar.text_input(
    "Enter NSE Ticker Symbol", value="RELIANCE"
).upper()
ticker_string = (
    f"{stock_symbol}.NS"
    if not stock_symbol.endswith(".NS")
    else stock_symbol
)

timeframe_option = st.sidebar.selectbox(
    "Select Timeframe", ["1m", "5m", "15m", "1h", "1d"]
)

if timeframe_option == "1m":
    st.sidebar.warning(
        "⚠️ 1-minute data via free APIs is restricted to the last 7 days max."
    )
    default_days = 5
elif timeframe_option in ["5m", "15m", "1h"]:
    st.sidebar.warning(
        "⚠️ Intraday data (5m/15m/1h) is restricted to the last 60 days max."
    )
    default_days = 30
else:
    default_days = 365

col_d1, col_d2 = st.sidebar.columns(2)
end_date = pd.Timestamp.today().date()
start_date = end_date - pd.Timedelta(days=default_days)

user_start_date = st.sidebar.date_input("Start Date", value=start_date)
user_end_date = st.sidebar.date_input("End Date", value=end_date)

st.sidebar.subheader("Strategy Rules")
ema_period = st.sidebar.slider("EMA Trend Filter", 10, 50, 20)
vol_multiplier = st.sidebar.slider("Volume Surge Threshold", 1.0, 3.0, 1.5, 0.1)

run_backtest = st.sidebar.button("🚀 Run Backtest Simulation")

# -------------------------------------------------------------------
# BACKTEST EXECUTION ENGINE
# -------------------------------------------------------------------


@st.cache_data(ttl=600)
def fetch_backtest_data(ticker, interval, start, end):
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end + pd.Timedelta(days=1),
            interval=interval,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        return pd.DataFrame()


if run_backtest:
    with st.spinner(f"Running historical simulation for {ticker_string}..."):
        df_data = fetch_backtest_data(
            ticker_string, timeframe_option, user_start_date, user_end_date
        )

        if df_data.empty or len(df_data) < 20:
            st.error(
                f"No data returned for {ticker_string} on interval '{timeframe_option}'. "
                "Please shorten your date range or choose a larger timeframe (like 1d)."
            )
        else:
            df_data = df_data.dropna()

            df_data["EMA"] = (
                df_data["Close"].ewm(span=ema_period, adjust=False).mean()
            )
            df_data["Avg_Vol"] = (
                df_data["Volume"].rolling(window=20).mean().fillna(1)
            )
            df_data["Vol_Surge"] = df_data["Volume"] / df_data["Avg_Vol"]

            hl_range = (df_data["High"] - df_data["Low"]).replace(0, 0.01)
            clv = (
                2 * df_data["Close"] - df_data["High"] - df_data["Low"]
            ) / hl_range
            df_data["Delta"] = df_data["Volume"] * clv

            df_data["Signal"] = 0
            buy_condition = (
                (df_data["Close"] > df_data["EMA"])
                & (df_data["Vol_Surge"] >= vol_multiplier)
                & (df_data["Delta"] > 0)
            )
            df_data.loc[buy_condition, "Signal"] = 1

            df_data["Market_Return"] = df_data["Close"].pct_change()
            df_data["Strategy_Return"] = (
                df_data["Signal"].shift(1) * df_data["Market_Return"]
            )

            cumulative_market = (
                (1 + df_data["Market_Return"].fillna(0)).cumprod() - 1
            ) * 100
            cumulative_strategy = (
                (1 + df_data["Strategy_Return"].fillna(0)).cumprod() - 1
            ) * 100

            st.success("Backtest Completed Successfully!")

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Total Strategy Return",
                f"{cumulative_strategy.iloc[-1]:.2f}%",
            )
            m2.metric(
                "Benchmark Buy & Hold Return",
                f"{cumulative_market.iloc[-1]:.2f}%",
            )
            total_trades = int(df_data["Signal"].sum())
            m3.metric("Total Signals Generated", f"{total_trades}")

            st.subheader("📈 Cumulative Performance Comparison")
            fig_perf = go.Figure()
            fig_perf.add_trace(
                go.Scatter(
                    x=df_data.index,
                    y=cumulative_strategy,
                    name="Strategy Return",
                    line=dict(color="green", width=2),
                )
            )
            fig_perf.add_trace(
                go.Scatter(
                    x=df_data.index,
                    y=cumulative_market,
                    name="Benchmark (Buy & Hold)",
                    line=dict(color="gray", width=1.5, dash="dash"),
                )
            )
            fig_perf.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                template="plotly_white",
                yaxis_title="Return (%)",
            )
            st.plotly_chart(fig_perf, use_container_width=True)

            st.subheader("⚡ Minute/Hour Orderflow Delta & Volume Breakdown")
            fig_delta = go.Figure()

            bar_colors = [
                "#26a69a" if val >= 0 else "#ef5350"
                for val in df_data["Delta"]
            ]
            fig_delta.add_trace(
                go.Bar(
                    x=df_data.index,
                    y=df_data["Delta"],
                    name="Period Delta (Buy - Sell)",
                    marker_color=bar_colors,
                )
            )
            fig_delta.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                template="plotly_white",
                yaxis_title="Delta Volume",
                xaxis_title="Time / Date",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            )
            st.plotly_chart(fig_delta, use_container_width=True)

            st.subheader("📋 Signal Execution Logs")
            trades_df = df_data[df_data["Signal"] == 1][
                ["Close", "Volume", "Vol_Surge", "Delta", "EMA"]
            ]
            if not trades_df.empty:
                st.dataframe(trades_df, use_container_width=True)
            else:
                st.info(
                    "No trade signals met the exact criteria during this date range. Try relaxing the filters."
                )
else:
    st.info(
        "👈 Configure your stock symbol, date range, and timeframe in the sidebar, then click **Run Backtest Simulation**."
    )
