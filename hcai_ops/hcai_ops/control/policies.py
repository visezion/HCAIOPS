from typing import Any, Dict, List


class PolicyEngine:
    """
    Converts incidents + recommendations into concrete actions.
    """

    def decide_actions(
        self,
        incidents: List[Dict[str, Any]],
        recommendations: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Decide action lists per incident based on severity and status.
        """
        actions: Dict[str, List[Dict[str, Any]]] = {}
        for incident in incidents:
            inc_id = incident.get("incident_id")
            severity = incident.get("severity", "low")
            status = incident.get("status", "open")
            rec = recommendations.get(inc_id, {}) if inc_id else {}
            reason_text = rec.get("probable_cause") or rec.get("recommended_action") or ""

            if status == "closed":
                actions[inc_id] = []
                continue

            planned: List[Dict[str, Any]] = []
            if severity == "high":
                planned.append({"action": "restart_service", "reason": reason_text or "high severity incident with critical degradation"})
                planned.append({"action": "scale_up", "reason": reason_text or "high CPU and high error rate"})
            elif severity == "medium":
                planned.append({"action": "open_ticket", "reason": reason_text or "medium severity incident"})
            else:
                planned.append({"action": "monitor", "reason": reason_text or "low severity incident"})

            actions[inc_id] = planned
        return actions
