from typing import Any, Dict

from hcai_ops.analytics.processors import CorrelationEngine


class ControlLoop:
    """
    Orchestrates risk scoring, incident generation, recommendations and actions.
    Operates only in memory and returns a plan, no real side effects.
    """

    def __init__(self, event_store, risk_engine, incident_engine, recommendation_engine, policy_engine):
        self.event_store = event_store
        self.risk_engine = risk_engine
        self.incident_engine = incident_engine
        self.recommendation_engine = recommendation_engine
        self.policy_engine = policy_engine
        self.correlation_engine = CorrelationEngine()

    def build_plan(self) -> Dict[str, Any]:
        """
        Build a full control plan.
        """
        events = self.event_store.all()
        correlations = self.correlation_engine.correlate(events)
        risk = self.risk_engine.score(events, correlations=correlations)
        incidents = self.incident_engine.generate(risk)
        rec_list = self.recommendation_engine.generate(incidents)
        rec_map = {rec["incident_id"]: rec for rec in rec_list if rec.get("incident_id")}
        actions = self.policy_engine.decide_actions(incidents, rec_map)

        return {
            "risk": risk,
            "incidents": incidents,
            "recommendations": rec_map,
            "actions": actions,
        }
