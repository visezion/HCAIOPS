from typing import Any, Dict, List


class IncidentEngine:
    """Derive incidents from risk scores and track their lifecycle."""

    def __init__(self) -> None:
        self._counter = 1
        self._incidents: Dict[str, Dict[str, Any]] = {}

    def _next_id(self) -> str:
        inc_id = f"inc-{self._counter:04d}"
        self._counter += 1
        return inc_id

    def generate(self, risks: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Create or update incidents based on risk scores.
        One incident per source_id. Close incident if risk < 10.
        """
        for source_id, data in risks.items():
            risk_value = data.get("risk", 0)
            if risk_value >= 60:
                severity = "high"
                summary = "High system error rate and CPU saturation"
            elif risk_value >= 30:
                severity = "medium"
                summary = "Elevated errors or resource usage detected"
            else:
                severity = "low"
                summary = "Low level anomalies detected"

            incident = self._incidents.get(source_id)
            if incident is None:
                incident = {
                    "incident_id": self._next_id(),
                    "source_id": source_id,
                    "severity": severity,
                    "risk": risk_value,
                    "summary": summary,
                    "status": "open",
                }
                self._incidents[source_id] = incident
            else:
                incident.update(
                    {
                        "severity": severity,
                        "risk": risk_value,
                        "summary": summary,
                    }
                )
                if incident.get("status") == "closed" and risk_value >= 10:
                    incident["status"] = "open"

            if risk_value < 10:
                incident["status"] = "closed"

        # Remove sources not present? requirement not explicit, keep existing.
        return list(self._incidents.values())
