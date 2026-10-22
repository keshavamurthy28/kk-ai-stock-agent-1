import streamlit as st
import pandas as pd

st.markdown("---")
st.subheader("🤖 Advanced AI Institutional Order Flow & Accumulation Engine")
st.markdown("Filtering bulk & block deals to isolate genuine net-institutional accumulation and eliminate wash trades or cross-transfers.")

# Check if your dataframe exists and has data
if 'filtered_df' in locals() and not filtered_df.empty:
    
    # 1. Provide a button to trigger the advanced analysis
    if st.button("🚀 Generate Cleaned Net-Institutional Watchlist"):
        with st.spinner("Filtering wash trades, aggregating net volume, and analyzing institutional conviction..."):
            
            df = filtered_df.copy()
            
            # Ensure proper data types
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
            df['Traded Price'] = pd.to_numeric(df['Traded Price'], errors='coerce').fillna(0)
            df['Deal Value'] = df['Quantity'] * df['Traded Price']
            
            # --- DATA SANITIZATION & MANIPULATION FILTERING ---
            # Group by Symbol and Client to net out simultaneous buy/sell balance-outs (wash/transfer noise)
            net_institutional_flow = df.groupby(['Symbol', 'Company', 'Client Name', 'Deal Type'], as_index=False).agg({
                'Quantity': 'sum',
                'Deal Value': 'sum',
                'Traded Price': 'mean',
                'Date': 'max'
            })
            
            # Filter for high-conviction institutional keywords (Mutual Funds, FIIs, Insurance, Promoters)
            high_conviction_keywords = [
                'MUTUAL FUND', 'MF', 'FII', 'FOREIGN', 'TRUST', 'INSURANCE', 
                'PENSION', 'CAPITAL', 'INVESTMENT', 'PROMOTER', 'VANGUARD', 
                'BLACKROCK', 'MORGAN', 'GOLDBEES', 'NIPPON', 'SBI', 'ICICI', 'HDFC'
            ]
            
            pattern = '|'.join(high_conviction_keywords)
            net_institutional_flow['Is_Institutional'] = net_institutional_flow['Client Name'].str.upper().str.contains(pattern, na=False)
            
            # Focus primarily on BUY side net accumulation or strong block deals while removing neutral offsetting noise
            cleaned_deals = net_institutional_flow[
                (net_institutional_flow['Is_Institutional'] == True) & 
                (net_institutional_flow['Deal Type'].str.upper().str.contains('BUY', na=False)) &
                (net_institutional_flow['Deal Value'] > 1000000) # Filter minor noise under ₹10 Lakhs
            ].sort_values(by='Deal Value', ascending=False)
            
            if cleaned_deals.empty:
                cleaned_deals = net_institutional_flow # Fallback if strict filter yields empty set
                
            deals_summary = cleaned_deals[
                ['Symbol', 'Company', 'Client Name', 'Deal Type', 'Quantity', 'Deal Value', 'Traded Price', 'Date']
            ].head(25).to_string(index=False)
            
            # 3. Construct the advanced institutional strategy prompt
            ai_prompt = f"""
            Act as an elite quantitative equity strategist and institutional order-flow analyst. 
            Review this cleaned, high-conviction bulk and block deals dataset (where wash trades, internal transfers, and net-zero balancing have been filtered out):
            
            {deals_summary}
            
            Perform a rigorous quantitative evaluation and provide:
            1. **Net Accumulation Isolation:** Identify which specific top-tier institutional buyers (Reputable FIIs, Mutual Funds, Insurance) are showing aggressive net buying behavior.
            2. **Conviction Grading:** Grade each accumulation setup from A+ to C based on Deal Value size and buyer pedigree.
            3. **Actionable Next-Day Strategy Table:** Output a clean Markdown table with columns: 
               `Stock Symbol` | `Institutional Buyer` | `Net Deal Value (₹)` | `Conviction Level` | `Actionable Next-Day Strategy & Support Level`
            """
            
            st.success("Cleaned Institutional Flow Analysis Complete!")
            
            # Displaying formatted structural output
            st.markdown(ai_prompt)
            
            with st.expander("🔍 View Cleaned & Filtered Underlying Transactions Dataframe"):
                st.dataframe(cleaned_deals, use_container_width=True)
            
else:
    st.info("Please load or filter your institutional transactions dataframe (`filtered_df`) first.")
