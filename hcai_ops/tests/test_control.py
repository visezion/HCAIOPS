from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from hcai_ops.analytics import event_store
from hcai_ops.analytics.store import EventStore
from hcai_ops.control.loops import ControlLoop
from hcai_ops.control.policies import PolicyEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.api.server import app


def _reset_global_store():
    event_store._events = []  # type: ignore[attr-defined]


def test_policy_engine_basic():
    incidents = [
        {"incident_id": "inc-1", "source_id": "web-1", "severity": "high", "status": "open"},
        {"incident_id": "inc-2", "source_id": "web-2", "severity": "medium", "status": "open"},
        {"incident_id": "inc-3", "source_id": "web-3", "severity": "low", "status": "open"},
        {"incident_id": "inc-4", "source_id": "web-4", "severity": "high", "status": "closed"},
    ]
    recommendations = {
        "inc-1": {"probable_cause": "critical degradation"},
        "inc-2": {"probable_cause": "elevated errors"},
        "inc-3": {"probable_cause": "minor anomaly"},
        "inc-4": {"probable_cause": "resolved"},
    }
    engine = PolicyEngine()
    actions = engine.decide_actions(incidents, recommendations)

    assert {"restart_service", "scale_up"} == {a["action"] for a in actions["inc-1"]}
    assert actions["inc-2"][0]["action"] == "open_ticket"
    assert actions["inc-3"][0]["action"] == "monitor"
    assert actions["inc-4"] == []


def test_control_loop_plan():
    store = EventStore()
    base = datetime(2025, 1, 1, 0, 0, 0)
    store.add_events(
        [
            HCaiEvent(timestamp=base, source_id="app01", event_type="metric", metric_name="cpu_usage", metric_value=0.95),
            HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="app01", event_type="log", log_level="ERROR", log_message="error"),
        ]
    )

    loop = ControlLoop(
        event_store=store,
        risk_engine=RiskScoringEngine(),
        incident_engine=IncidentEngine(),
        recommendation_engine=RecommendationEngine(),
        policy_engine=PolicyEngine(),
    )

    plan = loop.build_plan()
    assert plan["risk"]
    assert plan["incidents"]
    inc = plan["incidents"][0]
    assert inc["source_id"] == "app01"
    assert plan["recommendations"]
    assert plan["actions"][inc["incident_id"]]


def test_control_api_plan_endpoint():
    _reset_global_store()
    base = datetime(2025, 1, 1, 0, 0, 0)
    event_store.add_events(
        [
            HCaiEvent(timestamp=base, source_id="svc1", event_type="metric", metric_name="cpu_usage", metric_value=0.92),
            HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="svc1", event_type="log", log_level="ERROR", log_message="err"),
        ]
    )
    client = TestClient(app)
    resp = client.get("/control/plan")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["risk", "incidents", "recommendations", "actions"]:
        assert key in data


def test_control_api_execute_endpoint():
    _reset_global_store()
    base = datetime(2025, 1, 1, 0, 0, 0)
    event_store.add_events(
        [
            HCaiEvent(timestamp=base, source_id="svc1", event_type="metric", metric_name="cpu_usage", metric_value=0.95),
            HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="svc1", event_type="log", log_level="ERROR", log_message="err"),
        ]
    )
    client = TestClient(app)

    resp = client.post("/control/execute", json={"dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "dry_run"
    assert isinstance(data["plan"], dict)

    resp2 = client.post("/control/execute", json={"dry_run": False})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["mode"] == "simulated"
    assert isinstance(data2["executed_actions"], dict)
