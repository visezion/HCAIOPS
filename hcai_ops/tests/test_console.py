from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from hcai_ops.api.server import app
from hcai_ops.analytics import event_store
from hcai_ops.data.schemas import HCaiEvent


def _reset_store():
    event_store._events = []  # type: ignore[attr-defined]


def test_console_routes():
    _reset_store()
    base = datetime(2025, 1, 1, 0, 0, 0)
    event_store.add_events(
        [
            HCaiEvent(timestamp=base, source_id="svc1", event_type="metric", metric_name="cpu_usage", metric_value=0.9),
            HCaiEvent(timestamp=base + timedelta(minutes=1), source_id="svc1", event_type="log", log_level="ERROR", log_message="err"),
        ]
    )
    client = TestClient(app)

    resp = client.get("/console/")
    assert resp.status_code == 200
    assert "HCAI Console" in resp.text

    plan_resp = client.get("/console/plan")
    assert plan_resp.status_code == 200
    data = plan_resp.json()
    assert isinstance(data, dict)
    for key in ["risk", "incidents", "recommendations", "actions"]:
        assert key in data
