from fastapi.testclient import TestClient

from hcai_ops.api.server import app
from hcai_ops.intelligence.agent import agent_check_in


def test_agent_update_flow(monkeypatch):
    client = TestClient(app)
    resp = client.get("/agent/ping", params={"version": "0.0.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "update_required" in data
