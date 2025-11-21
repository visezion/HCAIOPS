from datetime import UTC, datetime, timedelta
from pathlib import Path
import time

import pytest

from hcai_ops.data.real_dataset import (
    detect_log_type,
    load_any_dataset,
    load_csv_metrics,
    load_prometheus_file,
    load_syslog_file,
    replay_events,
)
from hcai_ops.data.schemas import HCaiEvent


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"


def test_load_syslog_file_basic():
    path = SAMPLE_DIR / "syslog_linux.log"
    events = load_syslog_file(str(path))
    assert len(events) == 3
    assert all(evt.event_type == "log" for evt in events)
    # source derived from line hostname
    assert all(evt.source_id == "host1" for evt in events)
    assert any(evt.log_level == "ERROR" for evt in events)
    assert all("raw_header" in evt.extras for evt in events)


def test_load_prometheus_file_basic():
    path = SAMPLE_DIR / "prometheus_dump.txt"
    events = load_prometheus_file(str(path), source_id="lab")
    assert len(events) == 3
    assert all(evt.event_type == "metric" for evt in events)
    assert {evt.metric_name for evt in events} >= {"cpu_usage", "memory_usage"}
    assert all(isinstance(evt.metric_value, float) for evt in events)


def test_load_csv_metrics_basic():
    path = SAMPLE_DIR / "metrics.csv"
    events = load_csv_metrics(str(path), source_id="lab")
    assert len(events) == 2
    assert all(evt.event_type == "metric" for evt in events)
    assert all(evt.metric_name == "cpu_usage" for evt in events)
    assert all(isinstance(evt.metric_value, float) for evt in events)
    assert all(evt.timestamp.year == 2025 for evt in events)


def test_detect_log_type():
    assert detect_log_type(str(SAMPLE_DIR / "syslog_linux.log")) == "syslog"
    assert detect_log_type(str(SAMPLE_DIR / "prometheus_dump.txt")) == "prometheus"
    assert detect_log_type(str(SAMPLE_DIR / "metrics.csv")) == "csv_metrics"
    assert detect_log_type(str(SAMPLE_DIR / "windows_logs.txt")) in {"syslog", "unknown"}


def test_load_any_dataset():
    events = load_any_dataset(str(SAMPLE_DIR / "prometheus_dump.txt"))
    assert events
    assert all(evt.event_type == "metric" for evt in events)


def test_replay_events_order():
    now = datetime.now(UTC)
    e1 = HCaiEvent(timestamp=now + timedelta(seconds=1), source_id="s1", event_type="log", log_message="a")
    e2 = HCaiEvent(timestamp=now, source_id="s2", event_type="log", log_message="b")
    replayed = list(replay_events([e1, e2], speed=0))
    assert replayed[0].log_message == "b"
    assert replayed[1].log_message == "a"


def test_replay_events_timing():
    now = datetime.now(UTC)
    e1 = HCaiEvent(timestamp=now, source_id="s1", event_type="log", log_message="a")
    e2 = HCaiEvent(timestamp=now + timedelta(seconds=0.2), source_id="s1", event_type="log", log_message="b")
    start = time.perf_counter()
    list(replay_events([e1, e2], speed=5.0))
    elapsed = time.perf_counter() - start
    # 0.2s / 5 = 0.04s; allow buffer
    assert elapsed < 0.2
