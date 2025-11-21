from pathlib import Path

from fastapi.testclient import TestClient

from hcai_ops.api.server import app
from hcai_ops.agent_deploy.packager import generate_agent_bundle
from hcai_ops.agent_deploy.packager import BUNDLES_DIR


def test_agent_end_to_end(monkeypatch):
    # prepare newer bundle
    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    generate_agent_bundle(BUNDLES_DIR / "agent-1.0.0.zip")
    client = TestClient(app)
    resp = client.get("/agent/ping", params={"version": "0.0.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_required"] is True or data["update_required"] is False
    resp = client.post(
        "/agent/update_status",
        json={"current_version": "0.0.1", "update_result": "success", "error_message": None},
    )
    assert resp.status_code == 200
