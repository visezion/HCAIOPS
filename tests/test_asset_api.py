from fastapi.testclient import TestClient

from hcai_ops.api.server import app, asset_registry
from hcai_ops.assets.asset_model import Asset


def test_asset_api_endpoints():
    client = TestClient(app)
    asset_registry._assets.clear()  # reset
    payload = {"id": "a1", "name": "srv", "type": "server", "status": "unknown", "ip": "1.1.1.1"}
    resp = client.post("/api/assets", json=payload)
    assert resp.status_code == 200
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    assert any(item["id"] == "a1" for item in resp.json())
    resp = client.get("/api/assets/a1")
    assert resp.status_code == 200
    resp = client.post("/api/assets/a1/probe")
    assert resp.status_code == 200
    resp = client.delete("/api/assets/a1")
    assert resp.status_code == 200
