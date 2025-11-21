import os  # OS enables filesystem navigation for locating report files
import re  # Regex extracts timestamp and numeric metrics from report content and filenames
from io import StringIO  # StringIO wraps table text for pandas fixed-width parsing
import pandas as pd  # Pandas structures classification and feature importance data
import altair as alt  # Altair renders ordered bar charts for feature importances
import streamlit as st 

# Provide a single entry point to render classification tab
def render_classification_tab():

    st.subheader("Model Classification Reports")
    st.write("This section loads the latest stored classification report, parses its metrics and presents them in a structured way.")

    # Build reports directory path relative to this module for reliability across run contexts
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
    reports_dir = os.path.normpath(reports_dir)

    # List candidate report files; handle missing directory
    try:
        report_files = [f for f in os.listdir(reports_dir) if f.startswith("Klassifikationsreport_") and f.endswith(".txt")]
    except FileNotFoundError:
        st.warning("Reports folder not found. Expected a 'reports/' directory.")
        return

    if not report_files:
        st.warning("No classification report files found.")
        return

    # Extract timestamp string from filename for chronological sorting
    def extract_timestamp(fname: str):
        m = re.search(r"Klassifikationsreport_(\d{8}_\d{6})\.txt", fname)
        return m.group(1) if m else ""

    # Sort files by parsed timestamp to select the most recent report
    sorted_files = sorted(report_files, key=lambda f: pd.to_datetime(extract_timestamp(f), format="%Y%m%d_%H%M%S"))
    latest_file = sorted_files[-1]
    latest_path = os.path.join(reports_dir, latest_file)

    # Read full report text for subsequent regex and structural parsing
    with open(latest_path, "r", encoding="utf-8") as fh:
        raw_report = fh.read()

    st.markdown(f"**Loaded report:** `{latest_file}`")

    # Break report into lines to identify table and sections by scanning
    lines = raw_report.splitlines()

    # Locate classification metrics table header by matching column names pattern
    table_start_idx = next((i for i, ln in enumerate(lines) if re.search(r"\bprecision\s+recall\s+f1-score\s+support\b", ln)), None)

    # Collect table lines until scalar metrics (ROC-AUC) line appears
    df_class = None
    if table_start_idx is not None:
        collected = []  # Accumulates table lines including accuracy/macro/weighted rows
        for j in range(table_start_idx, len(lines)):
            if lines[j].startswith("ROC-AUC:"):
                break
            collected.append(lines[j])
    # Remove leading/trailing empty lines to ensure clean fixed-width parsing
        while collected and collected[0].strip() == "":
            collected.pop(0)
        while collected and collected[-1].strip() == "":
            collected.pop()
        table_block = "\n".join(collected)
        df_class = pd.read_fwf(StringIO(table_block))  # Parse fixed-width table into DataFrame
        df_class.columns = [c.strip() for c in df_class.columns]  # Normalize column names spacing
        st.write("### Detailed Class Metrics")
        st.dataframe(df_class, use_container_width=True)
    else:
        st.info("Classification metrics table not detected in report text.")

    # Define regex patterns for scalar metrics extraction
    metric_patterns = {
        "ROC-AUC": r"ROC-AUC:\s*([0-9]*\.?[0-9]+)",
        "Accuracy": r"Accuracy\s*:\s*([0-9]*\.?[0-9]+)",
        "Precision": r"Precision:\s*([0-9]*\.?[0-9]+)",
        "Recall": r"Recall\s*: *([0-9]*\.?[0-9]+)",
    }
    extracted_metrics = {}
    for label, pattern in metric_patterns.items():  # Iterate each metric pattern to find matches
        m = re.search(pattern, raw_report)
        if m:
            extracted_metrics[label] = float(m.group(1))

    # Present scalar metrics horizontally using Streamlit metric components
    if extracted_metrics:
        st.write("### Summary Metrics")
        cols = st.columns(len(extracted_metrics))
        for (label, value), col in zip(extracted_metrics.items(), cols):
            col.metric(label, f"{value:.3f}")
    else:
        st.info("No scalar summary metrics (ROC-AUC/Accuracy/Precision/Recall) found in report.")

    # Find feature importance section header to start parsing that block
    feat_header_idx = next((i for i, ln in enumerate(lines) if "Feature Importances" in ln), None)
    feature_df = None
    if feat_header_idx is not None:
        importance_lines = []  # Stores raw feature importance lines before structuring
        for k in range(feat_header_idx + 1, len(lines)):
            ln = lines[k].strip()
            if ln == "" or ln.startswith("dtype:"):
                break
            parts = ln.split()  # Split line into tokens; last token expected numeric importance
            if len(parts) >= 2 and parts[-1].isdigit():
                feature_name = " ".join(parts[:-1])
                importance_val = int(parts[-1])
                importance_lines.append((feature_name, importance_val))
        if importance_lines:
            feature_df = pd.DataFrame(importance_lines, columns=["Feature", "Importance"])

    # Display feature importances in both tabular and chart form if available
    if feature_df is not None and not feature_df.empty:
        feature_df = feature_df.sort_values("Importance", ascending=False)
        st.write("### Feature Importances")
        st.dataframe(feature_df, use_container_width=True)
        chart = (
            alt.Chart(feature_df)
            .mark_bar()
            .encode(
                x=alt.X("Feature:N", sort=feature_df["Feature"].tolist(), title="Feature"),
                y=alt.Y("Importance:Q", title="Importance Score"),
                tooltip=["Feature", "Importance"],
            )
            .properties(height=500)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No feature importances section found or it was empty.")

    # Provide a download of the displayed text file
    st.download_button(
        label="Download classification report text file",
        data=raw_report,
        file_name=latest_file,
        mime="text/plain",
    )