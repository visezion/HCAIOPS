"""
Utilities for loading real-world datasets (syslog, Windows logs, Prometheus dumps, CSV metrics)
into HCaiEvent objects with robust validation and replay support.
"""

from __future__ import annotations

import csv
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from .ingest import dicts_to_events, parse_prometheus_text, parse_syslog_lines
from .schemas import HCaiEvent

logger = logging.getLogger(__name__)


def _normalize_timestamp(value: Optional[str | datetime]) -> datetime:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return datetime.now(UTC)
    return ts.to_pydatetime()


def _append_warning(event: HCaiEvent, message: str) -> None:
    warnings = event.extras.get("warnings") or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    warnings.append(message)
    event.extras["warnings"] = warnings


def load_syslog_file(path: str) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    warnings: List[str] = []
    file_path = Path(path)
    default_source = file_path.stem or "syslog"

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = (line.rstrip("\n") for line in fh)
            parsed = parse_syslog_lines(lines, default_source_id=default_source)
            events.extend(parsed)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load syslog file %s", path)
        evt = HCaiEvent(
            timestamp=datetime.now(UTC),
            source_id=default_source,
            event_type="log",
            log_level="ERROR",
            log_message="Failed to load syslog file",
            extras={"warnings": [str(exc)]},
        )
        events.append(evt)

    for evt in events:
        if not evt.source_id or evt.source_id == "unknown":
            evt.source_id = default_source
        if warnings:
            evt.extras["warnings"] = warnings
    return events


def load_prometheus_file(path: str, source_id: str) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    warnings: List[str] = []
    file_path = Path(path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            raw_lines = list(fh.readlines())

        clean_lines: List[str] = []
        for line in raw_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                warnings.append(f"Skipped malformed prometheus line: {stripped}")
                continue
            try:
                float(parts[1])
            except Exception:
                warnings.append(f"Non-numeric metric value: {stripped}")
                continue
            clean_lines.append(stripped)

        events = parse_prometheus_text(clean_lines, source_id=source_id)
        for evt in events:
            if warnings:
                evt.extras["warnings"] = warnings
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load prometheus file %s", path)
        evt = HCaiEvent(
            timestamp=datetime.now(UTC),
            source_id=source_id,
            event_type="metric",
            metric_name="load_error",
            metric_value=None,
            extras={"warnings": [str(exc)]},
        )
        events = [evt]

    return events


def load_csv_metrics(path: str, source_id: str) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    file_path = Path(path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.DictReader(fh)
            required = {"timestamp", "metric_name", "metric_value"}
            if not required.issubset(reader.fieldnames or set()):
                raise ValueError("CSV missing required columns")

            for row in reader:
                warnings: List[str] = []
                try:
                    ts = _normalize_timestamp(row.get("timestamp"))
                except Exception:
                    ts = datetime.now(UTC)
                    warnings.append("Invalid timestamp")

                name = (row.get("metric_name") or "").strip()
                try:
                    value = float(row.get("metric_value")) if row.get("metric_value") not in (None, "") else None
                except Exception:
                    value = None
                    warnings.append("Invalid metric_value")

                evt = HCaiEvent(
                    timestamp=ts,
                    source_id=source_id,
                    event_type="metric",
                    metric_name=name or None,
                    metric_value=value,
                    extras={"warnings": warnings} if warnings else {},
                )
                events.append(evt)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load csv metrics file %s", path)
        evt = HCaiEvent(
            timestamp=datetime.now(UTC),
            source_id=source_id,
            event_type="metric",
            metric_name="load_error",
            metric_value=None,
            extras={"warnings": [str(exc)]},
        )
        events = [evt]

    return events


def detect_log_type(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".log"):
        return "syslog"
    if lower.endswith(".txt") or "prometheus" in lower:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for _ in range(5):
                    line = fh.readline()
                    if not line:
                        break
                    if "cpu_usage" in line or "memory_usage" in line:
                        return "prometheus"
        except Exception:
            return "unknown"
        return "syslog"
    if lower.endswith(".csv"):
        return "csv_metrics"
    return "unknown"


def load_any_dataset(path: str) -> List[HCaiEvent]:
    path_obj = Path(path)
    if not path_obj.exists():
        logger.error("File not found: %s", path)
        return []

    detected = detect_log_type(str(path_obj))
    try:
        if detected == "syslog":
            return load_syslog_file(str(path_obj))
        if detected == "prometheus":
            source = path_obj.stem or "prometheus"
            return load_prometheus_file(str(path_obj), source_id=source)
        if detected == "csv_metrics":
            source = path_obj.stem or "metrics"
            return load_csv_metrics(str(path_obj), source_id=source)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load dataset %s", path)
        evt = HCaiEvent(
            timestamp=datetime.now(UTC),
            source_id="unknown",
            event_type="log",
            log_level="ERROR",
            log_message="Failed to load dataset",
            extras={"warnings": [str(exc)]},
        )
        return [evt]

    return []


def replay_events(events: List[HCaiEvent], speed: float = 1.0) -> Iterable[HCaiEvent]:
    """
    Yield events respecting original timing scaled by speed.
    If speed == 0, replay instantly.
    """
    if speed < 0:
        speed = 0

    sorted_events = sorted(events, key=lambda e: e.timestamp or datetime.now(UTC))
    if not sorted_events:
        return

    prev_time = sorted_events[0].timestamp or datetime.now(UTC)
    for event in sorted_events:
        current = event.timestamp or datetime.now(UTC)
        if speed == 0:
            yield event
            continue

        delay = (current - prev_time).total_seconds()
        if delay > 0:
            time.sleep(delay / speed)
        yield event
        prev_time = current
