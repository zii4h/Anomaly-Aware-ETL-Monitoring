"""Launch with: streamlit run dashboard.py"""

import json
from contextlib import closing
from pathlib import Path

import pandas as pd
import streamlit as st

from etl_monitor.database import fetch_runs, open_db

st.set_page_config(page_title="ETL Monitor", page_icon="📊", layout="wide")
st.title("ETL Anomaly Monitor")
st.caption("Local starter dashboard · synthetic test data · rule checks + Isolation Forest")

path = Path(st.sidebar.text_input("SQLite database", "data/monitor.db"))
if not path.is_file():
    st.info("No monitoring data yet. In a terminal, run `etl-monitor demo` first.")
    st.stop()

with closing(open_db(path)) as connection:
    runs = fetch_runs(connection)

if not runs:
    st.info("No runs recorded. Run `etl-monitor demo` or process a CSV first.")
    st.stop()

frame = pd.DataFrame(runs).sort_values("run_id")
choices = sorted(frame["pipeline_name"].unique())
selected = st.sidebar.selectbox("Pipeline", choices)
frame = frame[frame["pipeline_name"] == selected].copy()
frame["detected_reasons"] = frame["reasons_json"].map(lambda raw: "; ".join(json.loads(raw)) or "None")

all_runs = len(frame)
anomalies = int((frame["status"] == "anomaly").sum())
total_loaded = int(frame["loaded_rows"].sum())
latest = frame.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Recorded runs", all_runs)
c2.metric("Flagged anomalies", anomalies)
c3.metric("Total rows loaded", f"{total_loaded:,}")
c4.metric("Latest status", latest["status"].upper())

st.subheader("Run trends")
st.line_chart(frame.set_index("run_id")[["input_rows", "loaded_rows"]])

c1, c2 = st.columns(2)
with c1:
    st.subheader("Quality metrics")
    metric = st.selectbox(
        "Metric", ["missing_rate", "duplicate_rate", "invalid_amount_rate", "invalid_date_rate", "mean_amount"]
    )
    st.line_chart(frame.set_index("run_id")[[metric]])
with c2:
    st.subheader("Model scores")
    st.caption("Negative values indicate an Isolation Forest outlier. Blank = model not used yet.")
    if frame["anomaly_score"].notna().any():
        st.line_chart(frame.set_index("run_id")[["anomaly_score"]])
    else:
        st.info("The model starts after 20 prior healthy runs.")

st.subheader("Runs and findings")
st.dataframe(
    frame.sort_values("run_id", ascending=False)[
        ["run_id", "started_at_utc", "status", "detector", "input_rows", "valid_rows",
         "loaded_rows", "anomaly_score", "detected_reasons"]
    ],
    use_container_width=True,
    hide_index=True,
)

st.caption("Research note: Anomaly flags are hypotheses for investigation, not proof of a data fault.")
