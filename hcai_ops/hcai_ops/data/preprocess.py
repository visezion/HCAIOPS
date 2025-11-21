from dataclasses import asdict
from typing import Dict, List

import numpy as np
import pandas as pd

from .schemas import HCaiEvent


def _events_to_df(events: List[HCaiEvent]) -> pd.DataFrame:
    df = pd.DataFrame([asdict(e) for e in events])
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def create_time_windows(events: List[HCaiEvent], window_size_minutes: int) -> List[Dict]:
    if not events:
        return []

    df = _events_to_df(events)
    df["window_start"] = df["timestamp"].dt.floor(f"{window_size_minutes}min")
    window_delta = pd.Timedelta(minutes=window_size_minutes)
    error_levels = {"ERROR", "CRITICAL"}

    rows: List[Dict] = []
    for (source_id, window_start), group in df.groupby(["source_id", "window_start"]):
        cpu_vals = group.loc[group["metric_name"] == "cpu", "metric_value"].dropna()
        error_rate_vals = group.loc[group["metric_name"] == "error_rate", "metric_value"].dropna()
        log_levels = (
            group.loc[group["event_type"] == "log", "log_level"]
            .fillna("")
            .astype(str)
            .str.upper()
        )

        rows.append(
            {
                "source_id": source_id,
                "window_start": window_start,
                "window_end": window_start + window_delta,
                "cpu_avg": float(cpu_vals.mean()) if not cpu_vals.empty else 0.0,
                "cpu_std": float(cpu_vals.std(ddof=0)) if not cpu_vals.empty else 0.0,
                "error_rate": float(error_rate_vals.mean()) if not error_rate_vals.empty else 0.0,
                "log_error_count": int(log_levels.isin(error_levels).sum()),
            }
        )

    return rows


def build_risk_training_table(events: List[HCaiEvent]) -> pd.DataFrame:
    time_rows = create_time_windows(events, window_size_minutes=5)
    if not time_rows:
        return pd.DataFrame(
            columns=[
                "source_id",
                "window_start",
                "cpu_avg_5m",
                "cpu_std_5m",
                "error_rate_5m",
                "log_error_count_5m",
                "incident_in_next_10m",
            ]
        )

    windows_df = pd.DataFrame(time_rows)
    # Compute label using incidents that occur after the window start.
    events_df = _events_to_df(events)
    incidents_df = events_df[events_df["event_type"] == "incident"][["source_id", "timestamp"]]

    def incident_in_next_10m(row: pd.Series) -> int:
        start = row["window_start"]
        end = start + pd.Timedelta(minutes=10)
        match = incidents_df[
            (incidents_df["source_id"] == row["source_id"])
            & (incidents_df["timestamp"] > start)
            & (incidents_df["timestamp"] <= end)
        ]
        return int(not match.empty)

    result = pd.DataFrame(
        {
            "source_id": windows_df["source_id"],
            "window_start": windows_df["window_start"],
            "cpu_avg_5m": windows_df["cpu_avg"],
            "cpu_std_5m": windows_df["cpu_std"],
            "error_rate_5m": windows_df["error_rate"],
            "log_error_count_5m": windows_df["log_error_count"],
        }
    )
    result["incident_in_next_10m"] = result.apply(incident_in_next_10m, axis=1)
    return result


def build_alert_training_table(events: List[HCaiEvent]) -> pd.DataFrame:
    events_df = _events_to_df(events)
    alert_mask = events_df["event_type"] == "alert"
    if alert_mask.sum() == 0:
        return pd.DataFrame(
            columns=[
                "alert_id",
                "source_id",
                "timestamp",
                "severity",
                "cpu_at_alert",
                "error_rate_at_alert",
                "log_count_last_5m",
                "label",
            ]
        )

    alerts_df = events_df[alert_mask].copy()
    metrics_df = events_df[events_df["metric_name"].notna()].copy()
    logs_df = events_df[events_df["event_type"] == "log"].copy()
    action_df = events_df[
        events_df["op_action_type"].notna() | events_df["applied_action"].notna()
    ].copy()

    def latest_metric_before(source_id: str, ts: pd.Timestamp, metric_name: str) -> float:
        subset = metrics_df[
            (metrics_df["source_id"] == source_id)
            & (metrics_df["metric_name"] == metric_name)
            & (metrics_df["timestamp"] <= ts)
        ].sort_values("timestamp")
        return float(subset["metric_value"].iloc[-1]) if not subset.empty else np.nan

    rows: List[Dict] = []
    for alert in alerts_df.itertuples(index=False):
        ts = alert.timestamp
        source_id = alert.source_id
        severity = np.nan
        if hasattr(alert, "extras") and isinstance(alert.extras, dict):
            severity = alert.extras.get("severity", alert.extras.get("severity_score", np.nan))
        if hasattr(alert, "metric_value") and not pd.isna(alert.metric_value):
            severity = alert.metric_value if pd.isna(severity) else severity

        cpu_at_alert = latest_metric_before(source_id, ts, "cpu")
        error_rate_at_alert = latest_metric_before(source_id, ts, "error_rate")
        time_window_start = ts - pd.Timedelta(minutes=5)
        log_count = logs_df[
            (logs_df["source_id"] == source_id)
            & (logs_df["timestamp"] > time_window_start)
            & (logs_df["timestamp"] <= ts)
        ].shape[0]

        related_action = action_df[
            (action_df["alert_id"] == getattr(alert, "alert_id", None))
            | (
                (action_df["source_id"] == source_id)
                & (action_df["timestamp"] >= ts)
                & (action_df["timestamp"] <= ts + pd.Timedelta(minutes=10))
            )
        ]
        label = 1 if not related_action.empty else 0

        rows.append(
            {
                "alert_id": getattr(alert, "alert_id", None),
                "source_id": source_id,
                "timestamp": ts,
                "severity": severity,
                "cpu_at_alert": cpu_at_alert,
                "error_rate_at_alert": error_rate_at_alert,
                "log_count_last_5m": log_count,
                "label": label,
            }
        )

    return pd.DataFrame(rows)


def build_action_training_table(events: List[HCaiEvent]) -> pd.DataFrame:
    events_df = _events_to_df(events)
    if events_df.empty:
        return pd.DataFrame(
            columns=["incident_type", "cpu_before", "error_rate_before", "applied_action", "outcome_label"]
        )

    metrics_df = events_df[events_df["metric_name"].notna()].copy()
    incidents_df = events_df[events_df["event_type"] == "incident"].copy()
    actions_df = events_df[
        events_df["applied_action"].notna() | events_df["op_action_type"].notna()
    ].copy()

    def latest_metric_before(source_id: str, ts: pd.Timestamp, metric_name: str) -> float:
        subset = metrics_df[
            (metrics_df["source_id"] == source_id)
            & (metrics_df["metric_name"] == metric_name)
            & (metrics_df["timestamp"] <= ts)
        ].sort_values("timestamp")
        return float(subset["metric_value"].iloc[-1]) if not subset.empty else np.nan

    rows: List[Dict] = []
    for action in actions_df.itertuples(index=False):
        ts = action.timestamp
        source_id = action.source_id
        recent_incident = incidents_df[
            (incidents_df["source_id"] == source_id) & (incidents_df["timestamp"] <= ts)
        ].sort_values("timestamp")
        if recent_incident.empty:
            continue

        incident = recent_incident.iloc[-1]
        rows.append(
            {
                "incident_type": incident.get("incident_label", None)
                if isinstance(incident, pd.Series)
                else getattr(incident, "incident_label", None),
                "cpu_before": latest_metric_before(source_id, ts, "cpu"),
                "error_rate_before": latest_metric_before(source_id, ts, "error_rate"),
                "applied_action": getattr(action, "applied_action", None)
                or getattr(action, "recommended_action", None)
                or getattr(action, "op_action_type", None),
                "outcome_label": getattr(action, "outcome_label", None),
            }
        )

    return pd.DataFrame(rows)
