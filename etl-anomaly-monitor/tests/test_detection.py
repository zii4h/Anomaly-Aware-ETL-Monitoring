from etl_monitor.detection import MIN_HEALTHY_RUNS, detect_anomaly


def healthy_metrics(input_rows=200, mean_amount=115.0):
    return {
        "input_rows": input_rows,
        "missing_rate": 0.0,
        "duplicate_rate": 0.0,
        "invalid_amount_rate": 0.0,
        "invalid_date_rate": 0.0,
        "mean_amount": mean_amount,
    }


def test_rule_flags_missing_fields_without_training():
    metrics = {**healthy_metrics(), "missing_rate": 0.3}
    finding = detect_anomaly(metrics, [])
    assert finding["status"] == "anomaly"
    assert "Missing required fields" in finding["reasons"][0]
    assert finding["anomaly_score"] is None


def test_volume_rule_uses_only_healthy_history():
    history = [{**healthy_metrics(200), "status": "normal"} for _ in range(5)]
    history.append({**healthy_metrics(10), "status": "anomaly"})
    finding = detect_anomaly(healthy_metrics(35), history)
    assert any("Volume dropped" in reason for reason in finding["reasons"])


def test_model_uses_earlier_healthy_runs():
    history = [
        {**healthy_metrics(190 + (i % 20), 110 + (i % 10)), "status": "normal"}
        for i in range(MIN_HEALTHY_RUNS)
    ]
    finding = detect_anomaly(healthy_metrics(201, 114), history)
    assert finding["detector"] == "quality_rules + isolation_forest"
    assert isinstance(finding["anomaly_score"], float)


def test_model_only_amount_shift_detected_after_baseline():
    from etl_monitor.demo import make_orders
    from etl_monitor.pipeline import analyze_orders

    history = []
    for i in range(25):
        metrics, _ = analyze_orders(make_orders(f"n{i}", seed=1729 + i))
        history.append({**metrics, "status": "normal"})
    shifted, _ = analyze_orders(make_orders("shift", kind="amount_shift", seed=1800))
    finding = detect_anomaly(shifted, history)
    assert finding["status"] == "anomaly"
    assert "Isolation Forest identified an unusual metric pattern" in finding["reasons"]
