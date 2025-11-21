from typing import Any, Dict, List, Optional

from hcai_ops.data.schemas import HCaiEvent


class RiskScoringEngine:
    """Compute risk scores per source using simple heuristic rules."""

    def score(
        self,
        events: List[HCaiEvent],
        correlations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, float]]:
        scores: Dict[str, Dict[str, float]] = {}
        correlations = correlations or []
        correlation_counts: Dict[str, int] = {}
        for corr in correlations:
            source = corr.get("source_id")
            if source is None:
                continue
            correlation_counts[source] = correlation_counts.get(source, 0) + 1

        for event in events:
            source = event.source_id
            entry = scores.setdefault(
                source,
                {"errors": 0, "metric_anomalies": 0, "correlations": correlation_counts.get(source, 0), "risk": 0.0},
            )
            if event.event_type == "log":
                level = (event.log_level or "").upper()
                if level == "ERROR":
                    entry["errors"] += 1
                    entry["risk"] += 10
                elif level == "CRITICAL":
                    entry["errors"] += 1
                    entry["risk"] += 20
            if event.metric_value is not None and event.metric_value > 0.9:
                entry["metric_anomalies"] += 1
                entry["risk"] += 15

        for source_id, count in correlation_counts.items():
            entry = scores.setdefault(
                source_id,
                {"errors": 0, "metric_anomalies": 0, "correlations": 0, "risk": 0.0},
            )
            entry["correlations"] = count
            entry["risk"] += 25 * count

        for entry in scores.values():
            entry["risk"] = min(float(entry["risk"]), 100.0)
        return scores
