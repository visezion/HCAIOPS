from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter

from ..data.schemas import HCaiEvent
from ..models.alert_model import AlertImportanceModel

router = APIRouter(prefix="/alerts", tags=["alerts"])

MODEL_DIR = Path("models_store")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

alert_model: Optional[AlertImportanceModel] = None


def _dicts_to_events(payload: List[Dict[str, Any]]) -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    for item in payload:
        data = dict(item)
        if "timestamp" in data:
            data["timestamp"] = pd.to_datetime(data["timestamp"])
        events.append(HCaiEvent(**data))
    return events


@router.post("/predict")
async def predict_alert(features: Dict[str, Any]) -> Dict[str, Any]:
    if alert_model is None:
        return {"error": "alert model not loaded"}
    try:
        probability = alert_model.predict_importance(features)
        return {"importance": probability}
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}


@router.post("/train")
async def train_alerts(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    global alert_model
    if alert_model is None:
        alert_model = AlertImportanceModel()
    try:
        event_objs = _dicts_to_events(events)
        metrics = alert_model.fit_from_events(event_objs)
        alert_model.save(MODEL_DIR / "alert_model.pkl")
        return metrics
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"error": str(exc)}
