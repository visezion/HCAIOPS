from pathlib import Path

from fastapi.testclient import TestClient

from hcai_ops.api.server import app
from hcai_ops.agent_deploy.packager import generate_agent_bundle
from hcai_ops.agent_deploy.packager import BUNDLES_DIR


def test_download_server_endpoints(tmp_path, monkeypatch):
    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    generate_agent_bundle(BUNDLES_DIR / "agent-1.0.0.zip")
    client = TestClient(app)
    resp = client.get("/agent/latest")
    assert resp.status_code == 200
    latest = resp.json()
    resp = client.get(f"/agent/download/{latest['version']}")
    assert resp.status_code == 200
