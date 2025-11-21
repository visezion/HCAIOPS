from fastapi.testclient import TestClient

from hcai_ops.api.server import app, asset_registry
from hcai_ops.assets.asset_model import Asset


def test_monitoring_pipeline_full():
    client = TestClient(app)
    asset_registry._assets.clear()
    payload = {"id": "a1", "name": "srv", "type": "server", "status": "unknown", "ip": "127.0.0.1"}
    client.post("/api/assets", json=payload)
    resp = client.post("/api/assets/a1/probe")
    assert resp.status_code == 200
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
