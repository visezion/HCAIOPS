from io import StringIO
from datetime import datetime, timedelta

import pandas as pd

from hcai_ops.data.loaders import load_incidents_csv, load_logs_csv, load_metrics_csv, combine_events
from hcai_ops.data.preprocess import build_risk_training_table, create_time_windows
from hcai_ops.data.schemas import HCaiEvent


def test_loaders_and_combine_events():
    metrics_csv = StringIO(
        "timestamp,source_id,metric_name,metric_value\n"
        "2025-01-01T00:00:00Z,s1,cpu,0.5\n"
        "2025-01-01T00:01:00Z,s1,cpu,0.7\n"
    )
    incidents_csv = StringIO(
        "timestamp,source_id,incident_label\n"
        "2025-01-01T00:02:00Z,s1,network\n"
    )
    logs_csv = StringIO(
        "timestamp,source_id,log_message,log_level\n"
        "2025-01-01T00:00:30Z,s1,error occurred,ERROR\n"
    )

    metrics = load_metrics_csv(metrics_csv)
    incidents = load_incidents_csv(incidents_csv)
    logs = load_logs_csv(logs_csv)

    assert all(isinstance(m, HCaiEvent) for m in metrics)
    assert all(isinstance(i, HCaiEvent) for i in incidents)
    assert all(isinstance(l, HCaiEvent) for l in logs)

    combined = combine_events(metrics, logs, incidents)
    timestamps = [e.timestamp for e in combined]
    assert timestamps == sorted(timestamps)


def test_preprocess_time_windows_and_risk_table():
    base = datetime(2025, 1, 1, 0, 0, 0)
    events = [
        HCaiEvent(timestamp=base, source_id="s1", event_type="metric", metric_name="cpu", metric_value=0.5),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1),
            source_id="s1",
            event_type="metric",
            metric_name="error_rate",
            metric_value=0.1,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=2),
            source_id="s1",
            event_type="log",
            log_message="oops",
            log_level="ERROR",
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=7),
            source_id="s1",
            event_type="incident",
            incident_label="network",
        ),
    ]

    windows = create_time_windows(events, window_size_minutes=5)
    assert windows, "Expected non-empty windows"
    window = windows[0]
    assert set(window.keys()) >= {"cpu_avg", "cpu_std", "error_rate", "log_error_count"}
    assert window["log_error_count"] == 1

    risk_df = build_risk_training_table(events)
    expected_cols = {
        "source_id",
        "window_start",
        "cpu_avg_5m",
        "cpu_std_5m",
        "error_rate_5m",
        "log_error_count_5m",
        "incident_in_next_10m",
    }
    assert expected_cols.issubset(set(risk_df.columns))
    assert risk_df["incident_in_next_10m"].max() == 1
