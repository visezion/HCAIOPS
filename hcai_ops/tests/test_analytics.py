from datetime import UTC, datetime, timedelta

from hcai_ops.analytics.store import EventStore
from hcai_ops.analytics.processors import MetricAggregator, LogAnomalyDetector, CorrelationEngine
from hcai_ops.data.schemas import HCaiEvent


def test_event_store_filters():
    store = EventStore()
    base = datetime(2025, 1, 1, 0, 0, 0)
    events = [
        HCaiEvent(timestamp=base, source_id="s1", event_type="metric", metric_name="cpu", metric_value=0.5),
        HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="s1", event_type="log", log_message="error", log_level="ERROR"),
    ]
    store.add_events(events)

    metrics = store.filter(event_type="metric")
    assert len(metrics) == 1
    assert metrics[0].metric_name == "cpu"

    since_events = store.since(base + timedelta(seconds=30))
    assert len(since_events) == 1
    assert since_events[0].event_type == "log"


def test_metric_aggregator_summary():
    aggregator = MetricAggregator()
    events = [
        HCaiEvent(timestamp=datetime.now(UTC), source_id="web-1", event_type="metric", metric_name="cpu_usage", metric_value=0.4),
        HCaiEvent(timestamp=datetime.now(UTC), source_id="web-1", event_type="metric", metric_name="cpu_usage", metric_value=0.6),
        HCaiEvent(timestamp=datetime.now(UTC), source_id="web-1", event_type="metric", metric_name="cpu_usage", metric_value=1.0),
    ]
    summary = aggregator.aggregate(events)
    key = "cpu_usage:web-1"
    assert key in summary
    assert summary[key]["count"] == 3
    assert summary[key]["min"] == 0.4
    assert summary[key]["max"] == 1.0
    assert summary[key]["avg"] == (0.4 + 0.6 + 1.0) / 3


def test_log_anomaly_detector():
    detector = LogAnomalyDetector(threshold=3)
    events = [
        HCaiEvent(timestamp=datetime.now(UTC), source_id="api-gateway", event_type="log", log_message="err1", log_level="ERROR"),
        HCaiEvent(timestamp=datetime.now(UTC), source_id="api-gateway", event_type="log", log_message="err2", log_level="ERROR"),
        HCaiEvent(timestamp=datetime.now(UTC), source_id="api-gateway", event_type="log", log_message="err3", log_level="ERROR"),
        HCaiEvent(timestamp=datetime.now(UTC), source_id="api-gateway", event_type="log", log_message="err4", log_level="ERROR"),
    ]
    anomalies = detector.detect(events)
    assert len(anomalies) == 1
    entry = anomalies[0]
    assert entry["source_id"] == "api-gateway"
    assert entry["error_count"] == 4
    assert entry["anomaly"] is True


def test_correlation_engine():
    engine = CorrelationEngine(metric_threshold=0.9, window_minutes=5)
    base = datetime(2025, 1, 1, 0, 0, 0)
    events = [
        HCaiEvent(timestamp=base, source_id="app01", event_type="metric", metric_name="cpu_usage", metric_value=0.95),
        HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="app01", event_type="log", log_message="Error connecting", log_level="ERROR"),
    ]
    correlations = engine.correlate(events)
    assert len(correlations) == 1
    corr = correlations[0]
    assert corr["source_id"] == "app01"
    assert corr["metric"] == "cpu_usage"
    assert corr["metric_value"] == 0.95
    assert "Error connecting" in corr["log_message"]
