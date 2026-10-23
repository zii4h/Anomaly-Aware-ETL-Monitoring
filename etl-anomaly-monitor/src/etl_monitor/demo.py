"""Reproducible synthetic order batches to explore normal and abnormal ETL runs."""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .database import DEFAULT_DB
from .pipeline import process_csv


def make_orders(run_tag: str, *, kind: str = "normal", seed: int = 0) -> pd.DataFrame:
    """Generate synthetic data. No customer or order is real."""
    rng = random.Random(seed)
    total = rng.randint(185, 215) if kind != "volume_drop" else 35
    start_date = date(2026, 1, 1)
    rows = []
    for i in range(total):
        amount = round(rng.uniform(50, 180), 2)
        if kind == "amount_shift":
            amount *= 14
        rows.append({
            "order_id": f"{run_tag}-{i:04d}",
            "customer_id": f"C{rng.randint(1, 80):03d}",
            "amount": round(amount, 2),
            "order_date": (start_date + timedelta(days=rng.randint(0, 60))).isoformat(),
        })
    if kind == "missing_customers":
        for row in rows[:60]:
            row["customer_id"] = ""
    elif kind == "duplicate_orders":
        for i in range(60):
            rows[i]["order_id"] = rows[60 + i]["order_id"]
    elif kind == "invalid_amounts":
        for row in rows[:60]:
            row["amount"] = -5.0
    elif kind not in {"normal", "volume_drop", "amount_shift"}:
        raise ValueError(f"Unknown demo scenario: {kind}")
    return pd.DataFrame(rows)


def run_demo(
    *,
    db_path: str | Path = DEFAULT_DB,
    output_dir: str | Path = "data/demo_inputs",
    normal_runs: int = 25,
) -> list[tuple[str, dict]]:
    """Seed normal history, then run five labeled anomaly examples."""
    if normal_runs < 0:
        raise ValueError("normal_runs cannot be negative")
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    batch_id = uuid4().hex[:8]
    results: list[tuple[str, dict]] = []
    scenarios = ["normal"] * normal_runs + [
        "volume_drop", "missing_customers", "duplicate_orders", "invalid_amounts", "amount_shift"
    ]
    for i, scenario in enumerate(scenarios):
        filename = folder / f"{batch_id}_{i:03d}_{scenario}.csv"
        make_orders(f"{batch_id}-{i:03d}", kind=scenario, seed=1729 + i).to_csv(filename, index=False)
        results.append((scenario, process_csv(filename, db_path=db_path)))
    return results
