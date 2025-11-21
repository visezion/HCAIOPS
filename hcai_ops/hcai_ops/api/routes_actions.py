from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter

from ..data.schemas import HCaiEvent
from ..models.action_model import ActionRecommender

router = APIRouter(prefix="/actions", tags=["actions"])

MODEL_DIR = Path("models_store")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

action_model: Optional[ActionRecommender] = None


def _dicts_to_events(payload: List[Dict[str, Any]]) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    for item in payload:
        data = dict(item)
        if "timestamp" in data:
            data["timestamp"] = pd.to_datetime(data["timestamp"])
        events.append(HCaiEvent(**data))
    return events


@router.post("/recommend")
async def recommend_action(features: Dict[str, Any]) -> Dict[str, Any]:
    if action_model is None:
        return {"error": "action model not loaded"}
    try:
        action = action_model.recommend_action(features)
        if action is None:
            return {"error": "no recommendation available"}
        return {"action": action}
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}


@router.post("/train")
async def train_actions(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    global action_model
    if action_model is None:
        action_model = ActionRecommender()
    try:
        event_objs = _dicts_to_events(events)
        action_model.fit_from_events(event_objs)
        rows = len(action_model.action_history) if action_model.action_history is not None else 0
        action_model.save(MODEL_DIR / "action_model.pkl")
        return {"status": "trained", "rows": rows}
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}
