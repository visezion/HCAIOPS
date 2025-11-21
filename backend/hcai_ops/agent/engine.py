from hcai_ops.data.store import EventStore
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine
from hcai_ops.control.policies import PolicyEngine
from hcai_ops.control.loops import ControlLoop


class AgentEngine:
    """
    Autonomous safe agent responsible for:
    - analyzing events and incidents
    - computing system plan
    - validating actions with safety guardrails
    - simulating effects
    - executing actions
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.risk = RiskScoringEngine()
        self.inc = IncidentEngine()
        self.rec = RecommendationEngine()
        self.pol = PolicyEngine()

    def build_plan(self):
        loop = ControlLoop(self.event_store, self.risk, self.inc, self.rec, self.pol)
        plan = loop.build_plan()
        return {"plan": plan}

    def simulate_plan(self, plan: dict):
        sim = {
            "predicted_risk_after": plan.get("risk_score", 0),
            "impact": "low" if plan.get("risk_score", 0) < 0.4 else "medium",
            "actions": plan.get("actions", []),
        }
        return sim

    def validate_plan(self, plan: dict):
        risk = plan.get("risk_score", 0)
        if risk > 0.9:
            return {"allowed": False, "reason": "risk too high"}
        return {"allowed": True}

    def execute_plan(self, plan: dict):
        validation = self.validate_plan(plan)
        if not validation["allowed"]:
            return {"executed": False, "reason": validation["reason"]}

        return {"executed": True, "actions": plan.get("actions", [])}
