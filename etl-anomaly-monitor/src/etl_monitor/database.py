"""SQLite persistence for orders and pipeline monitoring history."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB = Path("data/monitor.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    order_date TEXT NOT NULL,
    source_run_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    input_file TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    input_rows INTEGER NOT NULL,
    valid_rows INTEGER NOT NULL,
    loaded_rows INTEGER NOT NULL,
    missing_rate REAL NOT NULL,
    duplicate_rate REAL NOT NULL,
    invalid_amount_rate REAL NOT NULL,
    invalid_date_rate REAL NOT NULL,
    mean_amount REAL NOT NULL,
    status TEXT NOT NULL,
    detector TEXT NOT NULL,
    anomaly_score REAL,
    reasons_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_pipeline_time
ON pipeline_runs (pipeline_name, run_id);
"""


def open_db(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def fetch_runs(
    conn: sqlite3.Connection, *, pipeline_name: str | None = None, limit: int | None = None
) -> list[dict]:
    sql = "SELECT * FROM pipeline_runs"
    params: list[object] = []
    if pipeline_name is not None:
        sql += " WHERE pipeline_name = ?"
        params.append(pipeline_name)
    sql += " ORDER BY run_id DESC"
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be a positive integer")
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(row) for row in conn.execute(sql, params).fetchall()]
