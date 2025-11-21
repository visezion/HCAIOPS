from typing import Dict, Any

from fastapi import APIRouter

from hcai_ops.analytics import event_store
from hcai_ops.analytics.processors import CorrelationEngine
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine

router = APIRouter(prefix="/intelligence")

_risk_engine = RiskScoringEngine()
_incident_engine = IncidentEngine()
_recommendation_engine = RecommendationEngine()
_correlation_engine = CorrelationEngine()


def _compute_all() -> Dict[str, Any]:
    events = event_store.all()
    correlations = _correlation_engine.correlate(events)
    risk = _risk_engine.score(events, correlations=correlations)
    incidents = _incident_engine.generate(risk)
    recommendations = _recommendation_engine.generate(incidents)
    return {"risk": risk, "incidents": incidents, "recommendations": recommendations}


@router.get("/risk")
def get_risk():
    return _compute_all()["risk"]


@router.get("/incidents")
def get_incidents():
    return _compute_all()["incidents"]


@router.get("/recommendations")
def get_recommendations():
    return _compute_all()["recommendations"]


@router.get("/overview")
def get_overview():
    return _compute_all()
