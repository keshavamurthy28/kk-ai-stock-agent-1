from datetime import datetime, time
import pytz
import streamlit as st

# 1. Define IST Timezone
ist = pytz.timezone("Asia/Kolkata")
current_time_ist = datetime.now(ist).time()

# 2. Define Market Gates
market_open = time(9, 15)
allowed_execution_time = time(9, 20)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Automated Execution Gate")

if current_time_ist < allowed_execution_time:
  st.warning(
      f"⏳ **Market Pre-Open / Opening Phase ({current_time_ist.strftime('%H:%M:%S')} IST):**"
      " Execution cards are locked until 09:20 AM to let opening range volatility"
      " settle."
  )
  # Optional: Blur or disable trading buttons until 9:20 AM
  lock_execution = True
else:
  st.success("✅ **Live Execution Window Active** (Post-09:20 AM IST)")
  lock_execution = False

# 3. Automated Gap-Up Rejection Filter for Rank #1 Stock
# Assuming 'open_price' and 'prev_close' are pulled from your live yfinance/kite feed
# Example check:
# gap_percentage = ((open_price - prev_close) / prev_close) * 0.100 # Adjusted logic

# if gap_percentage > 1.5 and lock_execution == False:
#     st.error(f"⛔ **AUTO-REJECT: Gap-Up is {gap_percentage:.2f}% (> 1.5%)**. High risk of morning trap. Skipping trade.")
#     # Disable order trigger
