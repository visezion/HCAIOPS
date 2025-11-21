from typing import List

import pandas as pd

from .schemas import HCaiEvent


def load_metrics_csv(path: str) -> List[HCaiEvent]:
    """Load metric events from a CSV file into HCaiEvent objects."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    events: List[HCaiEvent] = []
    for row in df.itertuples(index=False):
        events.append(
            HCaiEvent(
                timestamp=row.timestamp,
                source_id=str(row.source_id),
                event_type="metric",
                metric_name=getattr(row, "metric_name", None),
                metric_value=float(row.metric_value) if pd.notnull(row.metric_value) else None,
            )
        )
    return events


def load_incidents_csv(path: str) -> List[HCaiEvent]:
    """Load incident events from a CSV file into HCaiEvent objects."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    events: List[HCaiEvent] = []
    for row in df.itertuples(index=False):
        events.append(
            HCaiEvent(
                timestamp=row.timestamp,
                source_id=str(row.source_id),
                event_type="incident",
                incident_label=getattr(row, "incident_label", None),
            )
        )
    return events


def load_logs_csv(path: str) -> List[HCaiEvent]:
    """Load log events from a CSV file into HCaiEvent objects."""
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    events: List[HCaiEvent] = []
    for row in df.itertuples(index=False):
        events.append(
            HCaiEvent(
                timestamp=row.timestamp,
                source_id=str(row.source_id),
                event_type="log",
                log_message=getattr(row, "log_message", None),
                log_level=getattr(row, "log_level", None),
            )
        )
    return events


def combine_events(
    metrics: List[HCaiEvent],
    logs: List[HCaiEvent],
    incidents: List[HCaiEvent],
) -> List[HCaiEvent]:
    """Merge multiple event lists and return them sorted by timestamp."""
    combined = [*(metrics or []), *(logs or []), *(incidents or [])]
    return sorted(combined, key=lambda e: e.timestamp)
