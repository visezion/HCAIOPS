from typing import Any, Dict

from fastapi import APIRouter, Depends

from hcai_ops.analytics import event_store
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine
from hcai_ops.control.policies import PolicyEngine
from hcai_ops.control.loops import ControlLoop

router = APIRouter(prefix="/control", tags=["control"])


def get_control_loop() -> ControlLoop:
    return ControlLoop(
        event_store=event_store,
        risk_engine=RiskScoringEngine(),
        incident_engine=IncidentEngine(),
        recommendation_engine=RecommendationEngine(),
        policy_engine=PolicyEngine(),
    )


@router.get("/plan")
def get_plan(loop: ControlLoop = Depends(get_control_loop)) -> Dict[str, Any]:
    return loop.build_plan()


@router.post("/execute")
def execute_control(payload: Dict[str, Any] = None, loop: ControlLoop = Depends(get_control_loop)) -> Dict[str, Any]:
    payload = payload or {}
    dry_run = payload.get("dry_run", True)
    plan = loop.build_plan()
    if dry_run:
        return {"mode": "dry_run", "plan": plan}
    return {"mode": "simulated", "executed_actions": plan.get("actions", {})}
