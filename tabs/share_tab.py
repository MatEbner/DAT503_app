import streamlit as st 
import pandas as pd  # Pandas loads and prepares price and prediction data
import altair as alt  # Altair draws the line chart for closing prices
import os  # OS builds file paths; 
from utils.data_loaders import load_predictions

# Cache price CSV parsing for quicker interactions
@st.cache_data(show_spinner=False)
def _load_prices(csv_path: str) -> pd.DataFrame:
    dfp = pd.read_csv(csv_path)
    # Expect columns Date, Open, High, Low, Close, Volume; convert and sort by date
    dfp["Date"] = pd.to_datetime(dfp["Date"], errors="coerce")
    dfp = dfp.sort_values("Date").dropna(subset=["Date"])  # Keep valid dates only
    # Ensure OHLCV numeric for plotting and derived metrics
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in dfp.columns:
            dfp[col] = pd.to_numeric(dfp[col], errors="coerce")
    return dfp

# Build a fast lookup for price files by normalized ticker names
def _build_price_index(prices_dir: str):
    idx = {}
    if not os.path.isdir(prices_dir):
        return idx
    for fname in os.listdir(prices_dir):
        if not fname.lower().endswith(".csv"):
            continue
        stem = os.path.splitext(fname)[0]  # e.g., "AAPL_US"
        prefix = stem.split("_")[0]  # Use name part before first underscore as ticker key
        path = os.path.join(prices_dir, fname)
        # Register multiple normalization variants to improve match success
        candidates = {
            stem.lower(),
            prefix.lower(),
            prefix.replace("-", "_").lower(),
            prefix.replace("-", "").lower(),
            prefix.replace(".", "-").lower(),
            prefix.replace(".", "").lower(),
        }
        for key in candidates:
            # Only set if not already present to keep first-seen (or later add preference logic)
            idx.setdefault(key, path)
    return idx

# Resolve a ticker to its price CSV path using a few robust normalization strategies
def _resolve_price_path(ticker: str, price_idx: dict):
    # Try exact ticker and common normalizations to find a CSV by index keys
    candidates = [
        ticker,
        ticker.replace("-", "_"),
        ticker.replace("-", ""),
        ticker.replace(".", "-"),
        ticker.replace(".", ""),
    ]
    for c in candidates:
        p = price_idx.get(c.lower())
        if p:
            return p
    return None

# mapping from ticker to company display name
_TICKER_NAME = {
    "V": "Visa",
    "MA": "Mastercard",
    "NVDA": "NVIDIA",
    "CAT": "Caterpillar",
    "META": "Meta Platforms",
    "UNH": "UnitedHealth",
    "SAP": "SAP",
    "MSFT": "Microsoft",
    "AMD": "AMD",
    "HD": "Home Depot",
    "BRK-A": "Berkshire Hathaway Class A",
    "NVO": "Novo Nordisk",
    "CRM": "Salesforce",
    "GOOGL": "Alphabet",
    "NVS": "Novartis",
    "PG": "Procter & Gamble",
    "CVX": "Chevron",
    "RTX": "RTX",
    "TSM": "TSMC",
    "AAPL": "Apple",
    "KO": "Coca-Cola",
    "TMUS": "T-Mobile US",
    "ASML": "ASML",
    "PM": "Philip Morris",
    "TSLA": "Tesla",
    "BAC": "Bank of America",
    "AMZN": "Amazon",
    "AZN": "AstraZeneca",
    "XOM": "ExxonMobil",
    "BABA": "Alibaba",
    "JNJ": "Johnson & Johnson",
    "CSCO": "Cisco",
    "TM": "Toyota",
    "WFC": "Wells Fargo",
    "MS": "Morgan Stanley",
    "LLY": "Eli Lilly",
}

# Encapsulate share information logic here so app.py remains lean
def render_share_tab(include_up: bool = True,
                     include_down: bool = True,
                     prob_range = (0.0, 1.0),
                     limit_option = 10,
                     sort_option: str = "ProbUp descending"):
    
    st.subheader("Share Information Overview")
    st.write("This section loads the latest stored share trends, prediction probability  and presents charts based on the selected filters.")

    # Establish base paths relative to the project for robust file access
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prices_dir = os.path.join(base_dir, "data", "prices")
    preds_path = os.path.join(base_dir, "results_stock_prediction.json")

    # Load predictions and index available price files once
    pred_df = load_predictions(preds_path)
    price_idx = _build_price_index(prices_dir)

    rel_prices = os.path.relpath(prices_dir, base_dir).replace(os.sep, '/')
    if not rel_prices.endswith('/'):
        rel_prices += '/'

    st.markdown(f"**Loaded files:** `{os.path.basename(preds_path)}` with price data from `{rel_prices}`") 

    # Abort if no predictions are available
    if pred_df.empty:
        st.warning("No predictions found. Please ensure 'results_stock_prediction.json' exists.")
        return

    # Reduce to the latest prediction per ticker (in case of multiple dates)
    latest_df = (
        pred_df.sort_values(["Ticker", "Date"]).dropna(subset=["Ticker"])\
               .groupby("Ticker", as_index=False).tail(1)
    )

    # Apply sidebar filters (signals, minimum probability) then sort and limit
    signals_selected = []
    if include_up:
        signals_selected.append("UP")
    if include_down:
        signals_selected.append("DOWN")
    if not signals_selected:  # safety fallback
        signals_selected = ["UP", "DOWN"]
    work_df = latest_df.copy()
    work_df['Signal_u'] = work_df['Signal'].astype(str).str.upper()
    work_df = work_df[work_df['Signal_u'].isin(signals_selected)]
    # Apply probability range filter (inclusive)
    _p = pd.to_numeric(work_df['ProbUp'], errors='coerce').fillna(-1)
    pmin, pmax = prob_range if isinstance(prob_range, (list, tuple)) and len(prob_range) == 2 else (0.0, 1.0)
    work_df = work_df[(_p >= float(pmin)) & (_p <= float(pmax))]
    if sort_option == "ProbUp descending":
        work_df = work_df.sort_values('ProbUp', ascending=False)
    elif sort_option == "ProbUp ascending":
        work_df = work_df.sort_values('ProbUp', ascending=True)
    else:
        work_df = work_df.sort_values('Ticker', ascending=True)
    if isinstance(limit_option, int):
        work_df = work_df.head(limit_option)

    # Summary of how many results are shown based on filters
    total_cnt = len(latest_df)
    shown_cnt = len(work_df)
    st.markdown(f"🔍 **Showing {shown_cnt} of {total_cnt} shares based on current filters.**")

    # Iterate each filtered ticker and render its section.
    for _, row in work_df.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        if not ticker:
            continue
        company = _TICKER_NAME.get(ticker, ticker)  # Fall back to ticker if name unknown

        st.subheader(f"{company} ({ticker})")

        # A compact prediction summary with colored arrow and formatted probability
        prob = row.get("ProbUp")
        signal = str(row.get("Signal", "")).upper() if pd.notna(row.get("Signal")) else ""
        date_val = row.get("Date")
        date_str = pd.to_datetime(date_val).strftime("%d.%m.%Y") if pd.notna(date_val) else ""
        if signal == "UP":
            arrow = "🟢⬆"
            sig_label = "UP"
        elif signal == "DOWN":
            arrow = "🔴⬇"
            sig_label = "DOWN"
        else:
            arrow = ""  # Unknown signal; no emoji
            sig_label = signal or ""
        prob_pct = f"{(float(prob) * 100):.1f}%" if pd.notna(prob) else "N/A"
        st.markdown(
            f"**Prediction:** {arrow} {sig_label} — {prob_pct} with last update on {date_str} (prediction horizon: 5 days)"
        )

        # Details toggle: hide/show slider, charts and data source
        show_details = st.toggle("Show details", value=False, key=f"share_show_details_{ticker}")
        if not show_details:
            st.markdown("---")
            continue

        # Resolve price CSV path; warn and skip chart if not found
        price_path = _resolve_price_path(ticker, price_idx)
        if not price_path:
            st.warning("No price data found for this ticker in 'data/prices/'.")
            st.markdown("---")
            continue

        # Load and prepare price data
        prices = _load_prices(price_path)
        if prices.empty or prices["Date"].isna().all():
            st.warning("Price data is empty or invalid for this ticker.")
            st.markdown("---")
            continue

        # Build preset timeframe quick picks
        min_d = prices["Date"].min()
        max_d = prices["Date"].max()
        preset_options = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "Max"]
        preset_value_key = f"{ticker}_preset_value"
        preset_radio_key = f"{ticker}_preset_radio"
        if preset_value_key not in st.session_state:
            st.session_state[preset_value_key] = "1M"

        preset = st.radio(
            "Select Timeframe:",
            options=preset_options,
            index=preset_options.index(st.session_state[preset_value_key]),
            horizontal=True,
            key=preset_radio_key,
        )

        # Sync selected radio back to value key
        if st.session_state.get(preset_radio_key) != st.session_state.get(preset_value_key):
            st.session_state[preset_value_key] = st.session_state[preset_radio_key]
        preset = st.session_state[preset_value_key]

        # Compute window bounds based on preset
        if preset.endswith("M"):
            months = int(preset.replace("M", ""))
            win_start = max(max_d - pd.DateOffset(months=months), min_d)
        elif preset == "YTD":
            jan1 = pd.Timestamp(year=max_d.year, month=1, day=1, tz=max_d.tz)
            win_start = max(jan1, min_d)
        elif preset.endswith("Y"):
            years = int(preset.replace("Y", ""))
            win_start = max(max_d - pd.DateOffset(years=years), min_d)
        else:  # Max
            win_start = min_d

        # No manual slider; use the preset window directly
        start_d, end_d = win_start.to_pydatetime(), max_d.to_pydatetime()

        # Filter price data to the selected window
        mask = (prices["Date"] >= pd.to_datetime(start_d)) & (prices["Date"] <= pd.to_datetime(end_d))
        win_full = prices.loc[mask, ["Date", "Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Date"]) 
        win = win_full[["Date", "Close"]]

        # Render closing price line chart with a clear headline
        st.write("### Closing Price")
        brush = alt.selection_interval(bind='scales', encodings=['x'])
        chart = (
            alt.Chart(win)
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Close:Q", title="Close Price"),
                tooltip=["Date:T", alt.Tooltip("Close:Q", format=".2f")],
            )
            .add_selection(brush)
            .properties(height=420)
        )
        st.altair_chart(chart, use_container_width=True)

        # Add a candlestick chart to show OHLC structure over the selected window
        st.write("### Candlestick (OHLC)")
        # Compute a boolean for up-days to color bodies
        win_full = win_full.copy()
        win_full["is_up"] = (win_full["Close"] >= win_full["Open"])
        color_scale = alt.Scale(domain=[True, False], range=["#2ca02c", "#d62728"]) 
        base = alt.Chart(win_full).encode(x=alt.X("Date:T", title="Date"))
        wick = base.mark_rule(color="#999").encode(y="Low:Q", y2="High:Q") 
        body = base.mark_bar().encode(
            y="Open:Q",
            y2="Close:Q",
            color=alt.Color("is_up:N", scale=color_scale, title="Up day"),
            tooltip=[
                "Date:T",
                alt.Tooltip("Open:Q", format=".2f"),
                alt.Tooltip("High:Q", format=".2f"),
                alt.Tooltip("Low:Q", format=".2f"),
                alt.Tooltip("Close:Q", format=".2f"),
            ],
        )
        candle = (wick + body).add_selection(brush).properties(height=420)
        st.altair_chart(candle, use_container_width=True)

        # Add a volume bar chart below the candlesticks
        st.write("### Volume")
        vol_chart = (
            alt.Chart(win_full)
            .mark_bar()
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Volume:Q", title="Volume"),
                color=alt.Color("is_up:N", scale=color_scale, legend=None),
                tooltip=["Date:T", alt.Tooltip("Volume:Q", format=",.0f")],
            )
            .add_selection(brush)
            .properties(height=420)
        )
        st.altair_chart(vol_chart, use_container_width=True)

        # Show the matched CSV source file
        st.caption(f"Data source: {os.path.basename(price_path)}")
        st.markdown("---")
