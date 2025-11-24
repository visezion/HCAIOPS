from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from hcai_ops.data.schemas import HCaiEvent


class MetricAggregator:
    """Aggregate metric events by name and source."""

    def aggregate(self, events: List[HCaiEvent]) -> Dict[str, Dict[str, float]]:
        summary: Dict[str, Dict[str, float]] = {}
        for event in events:
            if event.metric_name is None or event.metric_value is None:
                continue
            key = f"{event.metric_name}:{event.source_id}"
            bucket = summary.setdefault(key, {"count": 0, "min": event.metric_value, "max": event.metric_value, "avg": 0.0})
            bucket["count"] += 1
            bucket["min"] = min(bucket["min"], event.metric_value)
            bucket["max"] = max(bucket["max"], event.metric_value)
            # Running average
            bucket["avg"] = ((bucket["avg"] * (bucket["count"] - 1)) + event.metric_value) / bucket["count"]
        return summary


class LogAnomalyDetector:
    """Detect anomalies based on error log volume per source."""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold

    def detect(self, events: List[HCaiEvent]) -> List[Dict[str, object]]:
        error_counts: Dict[str, int] = {}
        for event in events:
            if event.event_type != "log":
                continue
            level = (event.log_level or "").upper()
            if level == "ERROR" or level == "CRITICAL":
                error_counts[event.source_id] = error_counts.get(event.source_id, 0) + 1

        results: List[Dict[str, object]] = []
        for source_id, count in error_counts.items():
            results.append(
                {
                    "source_id": source_id,
                    "error_count": count,
                    "threshold": self.threshold,
                    "anomaly": count >= self.threshold,
                }
            )
        return results


class CorrelationEngine:
    """Correlate high metrics with recent error logs."""

    def __init__(self, metric_threshold: float = 0.9, window_minutes: int = 5) -> None:
        self.metric_threshold = metric_threshold
        self.window = timedelta(minutes=window_minutes)

    def correlate(self, events: List[HCaiEvent]) -> List[Dict[str, object]]:
        findings: List[Dict[str, object]] = []
        logs_by_source: Dict[str, List[HCaiEvent]] = {}
        for event in events:
            if event.event_type == "log":
                logs_by_source.setdefault(event.source_id, []).append(event)

        for event in events:
            if event.metric_value is None or event.metric_name is None:
                continue
            if event.metric_value <= self.metric_threshold:
                continue
            source_logs = logs_by_source.get(event.source_id, [])
            for log_event in source_logs:
                if log_event.log_level and log_event.log_level.upper() == "ERROR":
                    if abs((event.timestamp - log_event.timestamp)) <= self.window:
                        findings.append(
                            {
                                "source_id": event.source_id,
                                "metric": event.metric_name,
                                "metric_value": event.metric_value,
                                "log_message": log_event.log_message,
                            }
                        )
                        break
        return findings


class MetricThresholdDetector:
    """
    Flag metric samples that cross configured percentage thresholds.
    Designed for agent metrics like cpu_percent/ram_percent/disk_percent.
    """

    DEFAULT_THRESHOLDS = {
        "cpu": 85.0,
        "cpu_percent": 85.0,
        "system.cpu_percent": 85.0,
        "ram_percent": 90.0,
        "memory_percent": 90.0,
        "disk_percent": 90.0,
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None, lookback_minutes: int = 10) -> None:
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.lookback = timedelta(minutes=lookback_minutes)

    @staticmethod
    def _normalize_percent(value: object) -> Optional[float]:
        try:
            num = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        # Accept either 0-1 or 0-100 values; normalize to 0-100.
        if 0 <= num <= 1.5:
            return num * 100.0
        return num

    def detect(self, events: List[HCaiEvent]) -> List[Dict[str, object]]:
        now = datetime.now(timezone.utc)
        cutoff = now - self.lookback

        latest: Dict[str, tuple[datetime, HCaiEvent]] = {}
        for event in events:
            if event.event_type != "metric" or event.metric_name is None or event.metric_value is None:
                continue
            ts = event.timestamp
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            if ts < cutoff:
                continue
            key = f"{event.metric_name}:{event.source_id}"
            if key not in latest or ts > latest[key][0]:
                latest[key] = (ts, event)

        findings: List[Dict[str, object]] = []
        for key, (ts, evt) in latest.items():
            metric_name, source_id = key.split(":", 1)
            threshold = self.thresholds.get(metric_name)
            if threshold is None:
                continue
            normalized_value = self._normalize_percent(evt.metric_value)
            if normalized_value is None:
                continue

            is_anomaly = normalized_value >= threshold
            message = (
                f"High {metric_name}: {normalized_value:.1f}% >= {threshold}%"
                if is_anomaly
                else f"{metric_name} at {normalized_value:.1f}% (threshold {threshold}%)"
            )

            findings.append(
                {
                    "id": f"{metric_name}:{source_id}",
                    "source_id": source_id,
                    "metric": metric_name,
                    "current_value": round(normalized_value, 2),
                    "threshold": threshold,
                    "anomaly": is_anomaly,
                    "message": message,
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else None,
                    "type": "metric_threshold",
                }
            )
        return findings
