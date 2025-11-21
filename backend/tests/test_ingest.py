from datetime import datetime

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.data.ingest import (
    dicts_to_events,
    parse_prometheus_text,
    parse_syslog_lines,
    save_events_csv,
    load_events_csv,
)


def test_dicts_to_events_basic():
    payload = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "source_id": "s1",
            "event_type": "metric",
            "metric_name": "cpu",
            "metric_value": 0.5,
            "unknown_field": "x",
        }
    ]
    events = dicts_to_events(payload)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, HCaiEvent)
    assert event.metric_name == "cpu"
    assert event.extras.get("unknown_field") == "x"


def test_parse_prometheus_text_basic():
    lines = [
        "# HELP cpu_usage CPU usage",
        "cpu_usage 0.42",
    ]
    events = parse_prometheus_text(lines, source_id="web-1")
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "metric"
    assert event.metric_name == "cpu_usage"
    assert event.metric_value == 0.42
    assert event.source_id == "web-1"


def test_parse_syslog_lines_basic():
    line = "Oct 11 22:14:15 myhost app[123]: Error connecting to db"
    events = parse_syslog_lines([line])
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "log"
    assert "Error connecting to db" in event.log_message
    assert event.log_level == "ERROR"
    assert event.source_id == "myhost"


def test_save_and_load_events_csv_roundtrip(tmp_path):
    path = tmp_path / "test_events_roundtrip.csv"
    events = [
        HCaiEvent(
            timestamp=datetime(2025, 1, 1, 0, 0, 0),
            source_id="s1",
            event_type="metric",
            metric_name="cpu",
            metric_value=0.9,
            extras={"note": "sample"},
        )
    ]

    save_events_csv(str(path), events)
    loaded = load_events_csv(str(path))

    assert len(loaded) == len(events)
    assert loaded[0].source_id == "s1"
    assert loaded[0].event_type == "metric"
    assert loaded[0].metric_name == "cpu"
    assert loaded[0].metric_value == 0.9
