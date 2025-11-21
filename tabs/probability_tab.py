import streamlit as st 
import pandas as pd  # Pandas structures JSON prediction data into a DataFrame for visualization
import altair as alt  # Altair builds declarative charts with precise aesthetic control
import os  # OS locates the JSON file
from utils.data_loaders import load_predictions

# Provide a single entry point to render probability tab
def render_probability_tab(include_up: bool = True,
                           include_down: bool = True,
                           prob_range = (0.0, 1.0),
                           limit_option = 10,
                           sort_option: str = "ProbUp descending"):

    st.subheader("Prediction Probabilities Overview")
    st.write("This section presents the latest model probability outputs per ticker along with the predicted signal.")

    # Resolve JSON file path relative to project root
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results_stock_prediction.json')
    df = load_predictions(json_path)

    if df.empty:
        st.warning("Prediction data file missing or empty (results_stock_prediction.json).")
        return

    # Show which predictions file was loaded
    st.markdown(f"**Loaded predictions:** `{os.path.basename(json_path)}`")

    # Apply filters and sorting
    work_df = df.copy()
    work_df["Signal_u"] = work_df["Signal"].astype(str).str.upper()
    signals = []
    if include_up:
        signals.append("UP")
    if include_down:
        signals.append("DOWN")
    if not signals:
        signals = ["UP", "DOWN"]
    work_df = work_df[work_df["Signal_u"].isin(signals)]
    # Apply probability range filter
    _p = pd.to_numeric(work_df["ProbUp"], errors="coerce").fillna(-1)
    pmin, pmax = prob_range if isinstance(prob_range, (list, tuple)) and len(prob_range) == 2 else (0.0, 1.0)
    work_df = work_df[(_p >= float(pmin)) & (_p <= float(pmax))]
    if sort_option == "ProbUp descending":
        result_df = work_df.sort_values('ProbUp', ascending=False)
    elif sort_option == "ProbUp ascending":
        result_df = work_df.sort_values('ProbUp', ascending=True)
    else:  # Alphabetical
        result_df = work_df.sort_values('Ticker', ascending=True)
    if isinstance(limit_option, int):
        result_df = result_df.head(limit_option)

    # Display raw structured data table
    st.markdown("### Predictions Table")
    # Prepare a display copy with formatted date and emoji-enhanced signal column
    df_display = result_df[['Ticker', 'Date', 'ProbUp', 'Signal']].copy()
    # Format date as day.month.year without time for readability
    df_display['Date'] = df_display['Date'].dt.strftime('%d.%m.%Y').fillna('')
    # Map signal to colored arrow emoji for quick visual parsing
    def _sig_to_emoji(s):
        if isinstance(s, str):
            s_up = s.upper()
            if s_up == 'UP':
                return '🟢⬆ UP'
            if s_up == 'DOWN':
                return '🔴⬇ DOWN'
        return s if s is not None else ''
    df_display['Signal'] = df_display['Signal'].apply(_sig_to_emoji)
    st.dataframe(df_display.reset_index(drop=True), use_container_width=True)

    # Build a color scale mapping signals to consistent colors
    signal_scale = alt.Scale(domain=['UP', 'DOWN'], range=['#2ca02c', '#d7301f'])

    # Probability bar chart for the filtered/sorted subset (top-N if limited)
    st.markdown("### Probability Bar Chart")
    chart_df = result_df
    chart_order = chart_df['Ticker'].tolist()

    # Create bar chart showing probability per ticker with color representing signal
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X('Ticker:N', sort=chart_order, title='Ticker'),
            y=alt.Y('ProbUp:Q', title='Probability Up'),
            color=alt.Color('Signal:N', scale=signal_scale, title='Signal'),
            tooltip=[
                alt.Tooltip('Ticker:N', title='Ticker'),
                alt.Tooltip('ProbUp:Q', title='Prob Up', format='.3f'),
                alt.Tooltip('Signal:N', title='Signal'),
            ],
        )
        .properties(height=500)
    )
    st.altair_chart(chart, use_container_width=True)

    # Provide a CSV download of the displayed dataset
    csv_bytes = result_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download filtered predictions CSV",
        data=csv_bytes,
        file_name="predictions_filtered.csv",
        mime="text/csv",
        help="Download the currently filtered probability prediction list as a CSV file.",
    )
