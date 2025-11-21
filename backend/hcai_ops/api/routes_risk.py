from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter

from ..data.schemas import HCaiEvent
from ..models.risk_model import RiskModel

router = APIRouter(prefix="/risk", tags=["risk"])

MODEL_DIR = Path("models_store")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

risk_model: Optional[RiskModel] = None


def _dicts_to_events(payload: List[Dict[str, Any]]) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    for item in payload:
        data = dict(item)
        if "timestamp" in data:
            data["timestamp"] = pd.to_datetime(data["timestamp"])
        events.append(HCaiEvent(**data))
    return events


@router.post("/predict")
async def predict_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    if risk_model is None:
        return {"error": "risk model not loaded"}
    try:
        probability = risk_model.predict_from_features(features)
        return {"risk": probability}
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}


@router.post("/train")
async def train_risk(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    global risk_model
    if risk_model is None:
        risk_model = RiskModel()
    try:
        event_objs = _dicts_to_events(events)
        metrics = risk_model.fit_from_events(event_objs)
        risk_model.save(MODEL_DIR / "risk_model.pkl")
        return metrics
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}
