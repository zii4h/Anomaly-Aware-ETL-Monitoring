"""CSV -> validated orders -> SQLite, while recording data quality metrics."""

from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .database import DEFAULT_DB, fetch_runs, open_db
from .detection import detect_anomaly

REQUIRED_COLUMNS = ("order_id", "customer_id", "amount", "order_date")


def analyze_orders(frame: pd.DataFrame) -> tuple[dict, list[tuple[str, str, float, str]]]:
    """Return run metrics and valid rows; do not modify the caller's DataFrame."""
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing CSV columns: {', '.join(missing_columns)}")

    df = frame.loc[:, REQUIRED_COLUMNS].copy().reset_index(drop=True)
    count = len(df)
    for col in ("order_id", "customer_id", "order_date"):
        df[col] = df[col].astype("string").str.strip()

    blank_ids = df["order_id"].isna() | df["order_id"].eq("")
    blank_customers = df["customer_id"].isna() | df["customer_id"].eq("")
    blank_dates = df["order_date"].isna() | df["order_date"].eq("")
    missing_required = blank_ids | blank_customers | blank_dates

    duplicates = df["order_id"].duplicated(keep="first") & ~blank_ids
    amounts = pd.to_numeric(df["amount"], errors="coerce")
    invalid_amounts = amounts.isna() | (amounts <= 0)
    dates = pd.to_datetime(df["order_date"], errors="coerce", format="%Y-%m-%d")
    invalid_dates = dates.isna()

    valid_mask = ~(missing_required | duplicates | invalid_amounts | invalid_dates)
    valid_rows: list[tuple[str, str, float, str]] = [
        (str(df.at[i, "order_id"]), str(df.at[i, "customer_id"]), float(amounts.loc[i]), str(dates.loc[i].date()))
        for i in df.index[valid_mask]
    ]
    denominator = max(count, 1)
    valid_amounts = amounts[~invalid_amounts]
    metrics = {
        "input_rows": count,
        "valid_rows": len(valid_rows),
        "missing_rate": float(missing_required.sum() / denominator),
        "duplicate_rate": float(duplicates.sum() / denominator),
        "invalid_amount_rate": float(invalid_amounts.sum() / denominator),
        "invalid_date_rate": float(invalid_dates.sum() / denominator),
        "mean_amount": float(valid_amounts.mean()) if not valid_amounts.empty else 0.0,
    }
    return metrics, valid_rows


def process_csv(
    csv_path: str | Path,
    *,
    db_path: str | Path = DEFAULT_DB,
    pipeline_name: str = "orders_etl",
) -> dict:
    """Process one CSV and save all run metrics and valid new records.

    Schema errors fail before storing a run. Future versions can track failures too.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")
    frame = pd.read_csv(path, dtype="string")
    metrics, valid_rows = analyze_orders(frame)

    with closing(open_db(db_path)) as conn:
        previous_runs = fetch_runs(conn, pipeline_name=pipeline_name)
        result = detect_anomaly(metrics, previous_runs)
        # Inserts and run history are in one transaction.
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO pipeline_runs (
                    pipeline_name, input_file, started_at_utc, input_rows,
                    valid_rows, loaded_rows, missing_rate, duplicate_rate,
                    invalid_amount_rate, invalid_date_rate, mean_amount,
                    status, detector, anomaly_score, reasons_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pipeline_name,
                    str(path),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    metrics["input_rows"],
                    metrics["valid_rows"],
                    0,
                    metrics["missing_rate"],
                    metrics["duplicate_rate"],
                    metrics["invalid_amount_rate"],
                    metrics["invalid_date_rate"],
                    metrics["mean_amount"],
                    result["status"],
                    result["detector"],
                    result["anomaly_score"],
                    json.dumps(result["reasons"]),
                ),
            )
            run_id = int(cursor.lastrowid)
            start_count = conn.total_changes
            conn.executemany(
                """
                INSERT OR IGNORE INTO orders
                (order_id, customer_id, amount, order_date, source_run_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(oid, cid, amt, date, run_id) for oid, cid, amt, date in valid_rows],
            )
            loaded_rows = conn.total_changes - start_count
            conn.execute(
                "UPDATE pipeline_runs SET loaded_rows = ? WHERE run_id = ?",
                (loaded_rows, run_id),
            )

    return {"run_id": run_id, "input_file": str(path), **metrics, "loaded_rows": loaded_rows, **result}
