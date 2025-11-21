from typing import Any, Dict, List


class RecommendationEngine:
    """Produce recommendations for each incident."""

    def generate(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        for incident in incidents:
            severity = incident.get("severity", "low")
            if severity == "high":
                cause = "Critical system degradation detected"
                action = "Restart services, investigate logs, scale resources"
                impact = "System instability and service disruption"
            elif severity == "medium":
                cause = "Elevated errors or high load"
                action = "Check logs, verify resource usage"
                impact = "Performance degradation"
            else:
                cause = "Minor anomalies detected"
                action = "Monitor system"
                impact = "Minimal impact expected"

            recommendations.append(
                {
                    "incident_id": incident.get("incident_id"),
                    "source_id": incident.get("source_id"),
                    "severity": severity,
                    "probable_cause": cause,
                    "recommended_action": action,
                    "impact_if_ignored": impact,
                }
            )
        return recommendations
