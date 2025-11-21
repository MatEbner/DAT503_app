import os
import json
import pandas as pd
import streamlit as st

# Load prediction JSON into a normalized DataFrame.
# Ensures required columns exist and coerces types.

@st.cache_data(show_spinner=False)
def load_predictions(json_path: str) -> pd.DataFrame:
    
    if not os.path.exists(json_path):
        return pd.DataFrame(columns=["Ticker", "Date", "ProbUp", "Signal"])

    with open(json_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if isinstance(raw, dict):
        records = []
        for tk, entries in raw.items():
            if isinstance(entries, list):
                for e in entries:
                    if isinstance(e, dict):
                        records.append({"Ticker": tk, **e})
            elif isinstance(entries, dict):
                records.append({"Ticker": tk, **entries})
        raw = records

    df = pd.DataFrame(raw)
    for col in ["Ticker", "Date", "ProbUp", "Signal"]:
        if col not in df.columns:
            df[col] = pd.NA

    df["Date"] = pd.to_datetime(df["Date"], unit="ms", errors="coerce")
    df["ProbUp"] = pd.to_numeric(df["ProbUp"], errors="coerce")
    return df
