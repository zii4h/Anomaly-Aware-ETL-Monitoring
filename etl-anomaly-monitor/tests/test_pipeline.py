from contextlib import closing

import pandas as pd
import pytest

from etl_monitor.database import fetch_runs, open_db
from etl_monitor.pipeline import analyze_orders, process_csv


def test_preprocessing_excludes_invalid_and_duplicate_rows():
    data = pd.DataFrame([
        {"order_id": "1", "customer_id": "C1", "amount": "10", "order_date": "2026-01-01"},
        {"order_id": "1", "customer_id": "C1", "amount": "10", "order_date": "2026-01-01"},
        {"order_id": "2", "customer_id": "", "amount": "20", "order_date": "2026-01-02"},
        {"order_id": "3", "customer_id": "C3", "amount": "-5", "order_date": "2026-01-03"},
        {"order_id": "4", "customer_id": "C4", "amount": "20", "order_date": "2026-01-04"},
    ])
    metrics, clean = analyze_orders(data)
    assert metrics["input_rows"] == 5
    assert metrics["valid_rows"] == 2
    assert metrics["duplicate_rate"] == 0.2
    assert metrics["missing_rate"] == 0.2
    assert metrics["invalid_amount_rate"] == 0.2
    assert [row[0] for row in clean] == ["1", "4"]


def test_repeated_csv_load_is_idempotent_but_runs_are_logged(tmp_path):
    csv_path = tmp_path / "batch.csv"
    db_path = tmp_path / "monitor.db"
    pd.DataFrame([
        {"order_id": "1", "customer_id": "C1", "amount": 12, "order_date": "2026-01-01"},
        {"order_id": "2", "customer_id": "C2", "amount": 19, "order_date": "2026-01-01"},
    ]).to_csv(csv_path, index=False)

    first = process_csv(csv_path, db_path=db_path)
    second = process_csv(csv_path, db_path=db_path)
    assert first["loaded_rows"] == 2
    assert second["loaded_rows"] == 0
    assert second["valid_rows"] == 2
    with closing(open_db(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert len(fetch_runs(conn)) == 2


def test_empty_file_is_an_anomaly(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("order_id,customer_id,amount,order_date\n", encoding="utf-8")
    result = process_csv(csv_path, db_path=tmp_path / "monitor.db")
    assert result["status"] == "anomaly"
    assert result["input_rows"] == 0


def test_missing_column_reports_clear_error(tmp_path):
    csv_path = tmp_path / "wrong.csv"
    csv_path.write_text("order_id,amount\n1,50\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing CSV columns: customer_id, order_date"):
        process_csv(csv_path, db_path=tmp_path / "monitor.db")
