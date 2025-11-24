from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from hcai_ops.analytics import event_store
from hcai_ops.data.schemas import HCaiEvent
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


def _log_action(incident_id: str, action: Dict[str, Any]) -> None:
    """Persist a control action to the event store for visibility."""
    evt = HCaiEvent(
        timestamp=datetime.now(timezone.utc),
        source_id=incident_id or "controller",
        event_type="control_action",
        log_message=action.get("action") or "control_action",
        log_level="INFO",
        extras={"reason": action.get("reason"), "incident_id": incident_id},
    )
    event_store.add_events([evt])


@router.post("/execute")
def execute_control(payload: Dict[str, Any] = None, loop: ControlLoop = Depends(get_control_loop)) -> Dict[str, Any]:
    payload = payload or {}
    dry_run = payload.get("dry_run", True)
    job_id = payload.get("job_id")
    plan = loop.build_plan()
    actions = plan.get("actions", {}) or {}

    if dry_run:
        return {"mode": "dry_run", "plan": plan, "job_id": job_id}

    executed: Dict[str, Any] = {}
    if job_id:
        # job_id is formatted as "{incident_id}-{index}" in the UI
        if "-" in job_id:
            incident_id, _, idx_str = job_id.partition("-")
            idx = int(idx_str) if idx_str.isdigit() else None
            act_list = actions.get(incident_id, [])
            if idx is not None and 0 <= idx < len(act_list):
                action = act_list[idx]
                executed[incident_id] = [action]
                _log_action(incident_id, action)
        else:
            for inc_id, act_list in actions.items():
                if act_list:
                    executed[inc_id] = [act_list[0]]
                    _log_action(inc_id, act_list[0])
    else:
        executed = actions
        for inc_id, act_list in actions.items():
            for action in act_list:
                _log_action(inc_id, action)

    return {"mode": "executed", "job_id": job_id, "executed_actions": executed}
