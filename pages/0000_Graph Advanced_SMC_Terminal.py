NSE_STOCK_CATALOG = [
    ("RELIANCE", "Reliance Industries Ltd"),
    ("TCS", "Tata Consultancy Services Ltd"),
    ("HDFCBANK", "HDFC Bank Ltd"),
    ("ICICIBANK", "ICICI Bank Ltd"),
    ("INFY", "Infosys Ltd"),
    ("INFOBEAN", "InfoBeans Technologies Ltd"),
    ("SBIN", "State Bank of India"),
    ("ITC", "ITC Ltd"),
    ("BHARTIARTL", "Bharti Airtel Ltd"),
    ("AXISBANK", "Axis Bank Ltd"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd"),
    ("LT", "Larsen & Toubro Ltd"),
    ("BAJFINANCE", "Bajaj Finance Ltd"),
    ("BAJAJFINSV", "Bajaj Finserv Ltd"),
    ("MARUTI", "Maruti Suzuki India Ltd"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd"),
    ("TITAN", "Titan Company Ltd"),
    ("ADANIENT", "Adani Enterprises Ltd"),
    ("ADANIPORTS", "Adani Ports & Special Economic Zone Ltd"),
    ("TATASTEEL", "Tata Steel Ltd"),
    ("NTPC", "NTPC Ltd"),
    ("POWERGRID", "Power Grid Corporation of India Ltd"),
    ("COALINDIA", "Coal India Ltd"),
    ("ONGC", "Oil & Natural Gas Corporation Ltd"),
    ("WIPRO", "Wipro Ltd"),
    ("ASIANPAINT", "Asian Paints Ltd"),
    ("HCLTECH", "HCL Technologies Ltd"),
    ("TECHM", "Tech Mahindra Ltd"),
    ("INDUSINDBK", "IndusInd Bank Ltd"),
    ("LICHSGFIN", "LIC Housing Finance Ltd"),
    ("HAL", "Hindustan Aeronautics Ltd"),
    ("BEL", "Bharat Electronics Ltd"),
    ("TDPOWERSYS", "TD Power Systems Ltd"),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise Ltd"),
    ("CIPLA", "Cipla Ltd"),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd"),
    ("GAIL", "GAIL (India) Ltd"),
    ("JINDALSTEL", "Jindal Steel & Power Ltd"),
    ("HINDALCO", "Hindalco Industries Ltd"),
    ("VEDL", "Vedanta Ltd"),
    ("TRENT", "Trent Ltd"),
    ("ZOMATO", "Eternal / Zomato Ltd"),
    ("IRCTC", "Indian Railway Catering & Tourism Corp Ltd"),
    ("TATAPOWER", "Tata Power Company Ltd"),
]

# Type letters (e.g., "Inf") -> Instant matching NSE suggestions in dropdown below
sym_col, tf_bar_col = st.columns([1.6, 4.4])
with sym_col:
    typed_query = (
        st.text_input(
            "Type NSE Symbol or Name (e.g., Inf)",
            value="LICHSGFIN",
            placeholder="Type letters like Inf, Tata, Bank...",
        )
        .strip()
        .upper()
    )

    q_clean = typed_query.replace(".NS", "")
    matching_stocks = [
        (sym, name)
        for sym, name in NSE_STOCK_CATALOG
        if (not q_clean) or (q_clean in sym.upper()) or (q_clean in name.upper())
    ]

    if matching_stocks:
        options_list = [f"{sym} — {name}" for sym, name in matching_stocks]
        if q_clean and q_clean not in [s for s, _ in matching_stocks]:
            options_list.append(f"{q_clean} — Use Typed Symbol ({q_clean}.NS)")
        selected_entry = st.selectbox(
            f"Matching NSE Stocks ({len(options_list)} shown)",
            options_list,
            index=0,
            key="nse_suggestion_select",
        )
        raw_sym = selected_entry.split(" — ")[0].strip().upper()
    else:
        st.caption("No catalog match—using typed NSE symbol directly.")
        raw_sym = q_clean or "LICHSGFIN"

ticker = raw_sym if raw_sym.endswith(".NS") else f"{raw_sym}.NS"
