"""Two-layer detection: transparent quality rules + optional Isolation Forest."""

from __future__ import annotations

from statistics import median

import numpy as np
from sklearn.ensemble import IsolationForest

MIN_HEALTHY_RUNS = 20
FEATURES = (
    "input_rows",
    "missing_rate",
    "duplicate_rate",
    "invalid_amount_rate",
    "invalid_date_rate",
    "mean_amount",
)


def detect_anomaly(metrics: dict, previous_runs: list[dict]) -> dict:
    """Evaluate ONLY previous healthy runs to avoid training on the current run.

    The detector is a demonstration baseline, not a validated production model.
    """
    reasons: list[str] = []
    healthy = [run for run in previous_runs if run["status"] == "normal"]

    if metrics["input_rows"] == 0:
        reasons.append("Input file contains zero data rows")
    for field, threshold, label in [
        ("missing_rate", 0.05, "Missing required fields"),
        ("duplicate_rate", 0.05, "Duplicate order IDs"),
        ("invalid_amount_rate", 0.05, "Invalid amounts"),
        ("invalid_date_rate", 0.05, "Invalid order dates"),
    ]:
        if metrics[field] > threshold:
            reasons.append(f"{label}: {metrics[field]:.1%} (threshold {threshold:.0%})")

    # Compare against prior healthy runs, not one arbitrary fixed record count.
    if len(healthy) >= 5:
        expected_volume = median(run["input_rows"] for run in healthy)
        if expected_volume > 0 and metrics["input_rows"] < expected_volume * 0.6:
            reasons.append(
                f"Volume dropped to {metrics['input_rows']} rows "
                f"(healthy median {expected_volume:.0f})"
            )

    detector = "quality_rules (model warming up)"
    anomaly_score: float | None = None
    
    if len(healthy) >= MIN_HEALTHY_RUNS:
        training = np.array([[run[field] for field in FEATURES] for run in healthy], dtype=float)
        current = np.array([[metrics[field] for field in FEATURES]], dtype=float)
        model = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=42,
        )
        model.fit(training)
        anomaly_score = float(model.decision_function(current)[0])
        detector = "quality_rules + isolation_forest"
        if model.predict(current)[0] == -1:
            reasons.append("Isolation Forest identified an unusual metric pattern")

    return {
        "status": "anomaly" if reasons else "normal",
        "reasons": reasons,
        "detector": detector,
        "anomaly_score": anomaly_score,
    }
