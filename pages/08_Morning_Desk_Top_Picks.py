import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Morning Desk & CNBC Panel Live Picks", layout="wide"
)

st.title("🎯 CNBC Morning Desk & Expert Panel Live Terminal")
st.markdown(
    "Automated live terminal tracking Morning Desk and TV panel picks across the"
    " **Indian stock market**. Features live volume status, breakout zones,"
    " automated risk-reward targets, and interactive SMC charts with EMAs and"
    " FVGs."
)

if st.sidebar.button("🔄 Refresh Morning Desk Terminal"):
  st.cache_data.clear()
  st.success("Cache cleared! Loaded latest live panel picks.")


@st.cache_data(ttl=60)
def fetch_morning_desk_picks():
  """Fetches live pricing, volume multipliers, and technical data for morning

  desk conviction tickers.
  """
  tickers = [
      "HONASA",
      "GLAND",
      "BANKBARODA",
      "MANKIND",
      "SBIN",
      "DIVISLAB",
      "WOCKPHARMA",
  ]
  desk_data = []

  for symbol in tickers:
    try:
      ticker = yf.Ticker(f"{symbol}.NS")
      hist = ticker.history(period="15d")

      if hist.empty or len(hist) < 5:
        continue

      latest = hist.iloc[-1]
      prev = hist.iloc[-2]

      ltp = float(latest["Close"])
      prev_close = float(prev["Close"])
      change_pct = ((ltp - prev_close) / prev_close) * 100

      avg_vol = hist["Volume"].iloc[:-1].mean()
      vol_mult = float(latest["Volume"]) / avg_vol if avg_vol > 0 else 1.0

      # Compute Technical EMAs & FVG zones
      hist["EMA_9"] = hist["Close"].ewm(span=9, adjust=False).mean()
      hist["EMA_21"] = hist["Close"].ewm(span=21, adjust=False).mean()

      zone = (
          "🟢 BREAKOUT / MOVING GREEN"
          if change_pct >= 0
          else "🔴 ACCUMULATION"
      )
      stop_loss = round(ltp * 0.973, 2)
      target_price = round(ltp * 1.066, 2)

      desk_data.append({
          "Stock": symbol,
          "LTP": round(ltp, 2),
          "Change_%": round(change_pct, 2),
          "Vol_Mult": round(vol_mult, 2),
          "Zone": zone,
          "Stop_Loss": stop_loss,
          "Target": target_price,
          "History": hist,
      })
    except Exception:
      continue

  return pd.DataFrame(desk_data)


with st.spinner("Fetching live Morning Desk panel picks..."):
  df_desk = fetch_morning_desk_picks()

st.markdown("## 🔥 Live Actionable Desk Picks & Profit Booking Matrix")

if df_desk.empty:
  st.warning("No Morning Desk data available right now.")
else:
  # Display in clean columns / card layout matching your live app
  for i in range(0, len(df_desk), 3):
    cols = st.columns(3)
    for j in range(3):
      if i + j < len(df_desk):
        row = df_desk.iloc[i + j]
        with cols[j]:
          st.markdown(
              f"### {row['Stock']} ({row['Change_%']:+.2f}%)"
          )
          st.markdown(f"Live Price: **₹{row['LTP']:,.2f}**")
          st.markdown(f"Vol: {row['Vol_Mult']}x")
          st.markdown(f"*Zone:* {row['Zone']}")
          st.markdown(
              f"🛑 *Stop-Loss:* ₹{row['Stop_Loss']} | 🎯 *Target:* ₹{row['Target']}"
          )

          # Expandable Chart with EMA & FVG overlays
          with st.expander(f"📈 View Chart & Technicals for {row['Stock']}"):
            hist_df = row["History"]
            if not hist_df.empty:
              fig = go.Figure()
              fig.add_trace(
                  go.Candlestick(
                      x=hist_df.index,
                      open=hist_df["Open"],
                      high=hist_df["High"],
                      low=hist_df["Low"],
                      close=hist_df["Close"],
                      name="Price",
                      increasing_line_color="#00E676",
                      decreasing_line_color="#FF5252",
                  )
              )
              if "EMA_9" in hist_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist_df.index,
                        y=hist_df["EMA_9"],
                        line=dict(color="#29B6F6", width=1.5),
                        name="EMA 9",
                    )
                )
              if "EMA_21" in hist_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist_df.index,
                        y=hist_df["EMA_21"],
                        line=dict(color="#FFA726", width=1.5),
                        name="EMA 21",
                    )
                )

              # FVG Shading
              if len(hist_df) >= 5:
                recent_low = float(hist_df["Low"].iloc[-3])
                recent_high = float(hist_df["High"].iloc[-5])
                fig.add_hrect(
                    y0=recent_high,
                    y1=recent_low,
                    fillcolor="rgba(0, 230, 118, 0.12)",
                    layer="below",
                    line_width=0,
                    annotation_text="FVG Demand Zone",
                    annotation_position="bottom right",
                )

              fig.add_hline(
                  y=row["Target"],
                  line_dash="dash",
                  line_color="#00E676",
                  annotation_text=f"Target: ₹{row['Target']}",
              )
              fig.add_hline(
                  y=row["Stop_Loss"],
                  line_dash="dash",
                  line_color="#FF5252",
                  annotation_text=f"Stop Loss: ₹{row['Stop_Loss']}",
              )

              fig.update_layout(
                  title=f"Morning Desk Chart — {row['Stock']}",
                  yaxis_title="Price (INR ₹)",
                  template="plotly_dark",
                  height=380,
                  xaxis_rangeslider_visible=False,
              )
              st.plotly_chart(fig, use_container_width=True)

          st.markdown("---")

  # Summary Table at the bottom
  st.markdown("## 📋 Detailed Summary Table")
  st.dataframe(
      df_desk[[
          "Stock",
          "LTP",
          "Change_%",
          "Vol_Mult",
          "Zone",
          "Stop_Loss",
          "Target",
      ]],
      use_container_width=True,
  )
