from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from hcai_ops.analytics import event_store
from hcai_ops.analytics.processors import CorrelationEngine
from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine
from hcai_ops.api.server import app


def _reset_store():
    event_store._events = []  # type: ignore[attr-defined]


def test_risk_scoring_basic():
    engine = RiskScoringEngine()
    events = [
        HCaiEvent(timestamp=datetime(2025, 1, 1, 0, 0, 0), source_id="web-1", event_type="log", log_level="ERROR", log_message="err"),
        HCaiEvent(timestamp=datetime(2025, 1, 1, 0, 1, 0), source_id="web-1", event_type="metric", metric_name="cpu_usage", metric_value=0.95),
    ]
    risk = engine.score(events, correlations=[{"source_id": "web-1"}])
    assert "web-1" in risk
    entry = risk["web-1"]
    assert entry["errors"] == 1
    assert entry["metric_anomalies"] == 1
    assert entry["correlations"] == 1
    assert entry["risk"] == min(10 + 15 + 25, 100)


def test_incident_generation():
    engine = IncidentEngine()
    risks = {
        "web-1": {"risk": 75},
        "api-1": {"risk": 35},
        "worker-1": {"risk": 5},
    }
    incidents = engine.generate(risks)
    lookup = {i["source_id"]: i for i in incidents}
    assert lookup["web-1"]["severity"] == "high"
    assert lookup["web-1"]["status"] == "open"
    assert lookup["api-1"]["severity"] == "medium"
    assert lookup["worker-1"]["status"] == "closed"


def test_recommendation_engine():
    incidents = [
        {"incident_id": "inc-0001", "source_id": "web-1", "severity": "high"},
        {"incident_id": "inc-0002", "source_id": "api-1", "severity": "medium"},
        {"incident_id": "inc-0003", "source_id": "worker-1", "severity": "low"},
    ]
    engine = RecommendationEngine()
    recs = engine.generate(incidents)
    assert len(recs) == 3
    high = next(r for r in recs if r["source_id"] == "web-1")
    assert "Critical system degradation" in high["probable_cause"]
    low = next(r for r in recs if r["source_id"] == "worker-1")
    assert "Monitor" in low["recommended_action"]


def test_intelligence_api():
    _reset_store()
    base = datetime(2025, 1, 1, 0, 0, 0)
    events = [
        HCaiEvent(timestamp=base, source_id="app01", event_type="metric", metric_name="cpu_usage", metric_value=0.95),
        HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="app01", event_type="log", log_level="ERROR", log_message="Error connecting"),
    ]
    event_store.add_events(events)
    client = TestClient(app)

    resp = client.get("/intelligence/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "risk" in data and "incidents" in data and "recommendations" in data
    assert data["risk"]["app01"]["risk"] >= 25
    assert data["incidents"][0]["source_id"] == "app01"
