from datetime import UTC, datetime, timedelta

import pytest

from hcai_ops.analytics.processors import MetricThresholdDetector
from hcai_ops.data.schemas import HCaiEvent


def _metric(ts: datetime, name: str, value: float) -> HCaiEvent:
    return HCaiEvent(timestamp=ts, source_id="agent-1", event_type="metric", metric_name=name, metric_value=value)


def test_metric_threshold_detector_flags_high_cpu_percent():
    now = datetime.now(UTC)
    events = [
        _metric(now - timedelta(minutes=1), "cpu_percent", 96.2),
        _metric(now - timedelta(minutes=1), "ram_percent", 40),
    ]
    detector = MetricThresholdDetector()
    findings = detector.detect(events)

    cpu = next((f for f in findings if f["metric"] == "cpu_percent"), None)
    assert cpu is not None
    assert cpu["anomaly"] is True
    assert cpu["current_value"] >= 96


def test_metric_threshold_detector_normalizes_unit_range():
    now = datetime.now(UTC)
    events = [
        _metric(now - timedelta(minutes=2), "system.cpu_percent", 0.92),
    ]
    detector = MetricThresholdDetector()
    findings = detector.detect(events)

    assert len(findings) == 1
    entry = findings[0]
    assert entry["anomaly"] is True
    assert entry["current_value"] == pytest.approx(92.0, rel=0.01)


def test_metric_threshold_detector_respects_lookback_window():
    now = datetime.now(UTC)
    events = [
        _metric(now - timedelta(minutes=30), "cpu_percent", 99.0),
    ]
    detector = MetricThresholdDetector(lookback_minutes=5)
    findings = detector.detect(events)

    assert findings == []
