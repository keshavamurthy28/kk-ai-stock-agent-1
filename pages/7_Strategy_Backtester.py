import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="NSE Strategy Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧪 NSE Historical Strategy & Orderflow Backtester")
st.markdown(
    "Backtest custom setups on any NSE equity across *Minute, Hourly, or Daily*"
    " timeframes for any date range you desire."
)

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Backtest Parameters")
ticker_input = st.sidebar.text_input(
    "Enter NSE Ticker Symbol", value="RELIANCE"
)
ticker_symbol = (
    ticker_input.strip().upper()
    if ticker_input.strip().upper().endswith(".NS")
    else ticker_input.strip().upper() + ".NS"
)

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=4
)

today_date = datetime.date.today()
default_start = today_date - datetime.timedelta(days=365)

start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date", value=today_date)

st.sidebar.markdown("### Strategy Rules")
ema_period = st.sidebar.slider("EMA Trend Filter", 10, 50, 20, 5)
vol_threshold = st.sidebar.slider(
    "Volume Surge Threshold", 1.0, 3.0, 1.5, 0.1
)


@st.cache_data(ttl=60)
def load_backtest_data(symbol, start, end, interval):
  df = yf.download(
      symbol, start=start, end=end, interval=interval, progress=False
  )
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  df.dropna(inplace=True)
  return df


if st.sidebar.button("🚀 Run Backtest Simulation", type="primary"):
  df = load_backtest_data(
      ticker_symbol, str(start_date), str(end_date), timeframe
  )

  if df.empty or len(df) < ema_period:
    st.error(
        "Insufficient data found for the selected ticker and date range."
        " Please adjust your filters."
    )
  else:
    # Strategy calculations
    df["EMA"] = df["Close"].ewm(span=ema_period, adjust=False).mean()
    df["Vol_SMA"] = df["Volume"].rolling(window=20).mean()
    df["Vol_Surge"] = df["Volume"] > (vol_threshold * df["Vol_SMA"])

    # Simulate Signals & Returns
    df["Signal"] = 0
    df.loc[(df["Close"] > df["EMA"]) & (df["Vol_Surge"]), "Signal"] = 1
    df.loc[(df["Close"] < df["EMA"]) & (df["Vol_Surge"]), "Signal"] = -1

    df["Market_Return"] = df["Close"].pct_change().fillna(0)
    df["Strategy_Return"] = df["Market_Return"] * df["Signal"].shift(1).fillna(0)

    df["Cumulative_Strategy"] = (1 + df["Strategy_Return"]).cumprod() - 1
    df["Cumulative_Benchmark"] = (1 + df["Market_Return"]).cumprod() - 1

    df["Delta_Return"] = (
        df["Cumulative_Strategy"] - df["Cumulative_Benchmark"]
    )
    df["Orderflow_Delta"] = (df["Close"] - df["Open"]) * df["Volume"]

    total_strat_ret = float(df["Cumulative_Strategy"].iloc[-1] * 100)
    total_bench_ret = float(df["Cumulative_Benchmark"].iloc[-1] * 100)
    total_signals = int((df["Signal"] != 0).sum())

    st.success("Backtest Completed Successfully!")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Strategy Return", f"{total_strat_ret:+.2f}%")
    col2.metric("Benchmark Buy & Hold Return", f"{total_bench_ret:+.2f}%")
    col3.metric("Total Signals Generated", f"{total_signals}")

    # --- INTERACTIVE 2-TIER SUBPLOT CHART ---
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
    )

    # 1. Cumulative Performance (Row 1)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Cumulative_Strategy"] * 100,
            line=dict(color="#00E676", width=2),
            name="Strategy Return (%)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Cumulative_Benchmark"] * 100,
            line=dict(color="#FF5252", width=1.5, dash="dash"),
            name="Benchmark (Buy & Hold)",
        ),
        row=1,
        col=1,
    )

    # 2. Orderflow Delta & Volume Breakdown (Row 2)
    bar_colors = [
        "#00E676" if val >= 0 else "#FF1744" for val in df["Orderflow_Delta"]
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker_color=bar_colors,
            name="Orderflow Delta & Volume Breakdown",
        ),
        row=2,
        col=1,
    )

    # TradingView-Like Global Layout with Adjusted Legend Position
    fig.update_layout(
        template="plotly_dark",
        height=680,
        xaxis_rangeslider_visible=False,
        dragmode="zoom",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,  # Pushes legend slightly above the top chart line boundary
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0.5)",
        ),
    )

    # Crosshair configuration
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="#888888",
        spikethickness=1,
    )
    fig.update_yaxes(
        side="right",
        showspikes=True,
        spikecolor="#888888",
        spikethickness=1,
    )

    # Display fully interactive chart
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
        },
    )

    # --- SIGNAL EXECUTION LOGS ---
    st.subheader("📋 Signal Execution Logs")
    exec_logs = df[df["Signal"] != 0][
        ["Close", "Volume", "Vol_Surge", "Orderflow_Delta", "EMA"]
    ].tail(50)
    st.dataframe(exec_logs, use_container_width=True)
else:
    st.info(
        "👈 Configure your parameters in the sidebar and click **Run Backtest"
        " Simulation** to load the interactive backtest."
    )
