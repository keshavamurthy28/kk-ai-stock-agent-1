# BEARISH SHORT SNIPER FILTER (For Negative Markets)
# 1. Negative intraday momentum (-0.5% to -5.0%)
# 2. Institutional breakdown: Price must be below VWAP & 20 EMA
# 3. Active volume participation on downward move (RVOL >= 1.1x)
if (
    -5.0 <= change_pct <= -0.5
    and ltp <= latest_vwap
    and ltp <= latest_ema
    and rvol >= 1.1
):
  # Short Entry & Target Calculation
  short_entry = round(ltp * 1.004, 2)  # Sell on minor bounce
  stop_loss = round(latest_vwap * 1.008, 2)  # Stop loss above VWAP
  target_1 = round(ltp * 0.975, 2)  # Target 1 (-2.5%)
  target_2 = round(ltp * 0.952, 2)  # Target 2 (-4.8%)
