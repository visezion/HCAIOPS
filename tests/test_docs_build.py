import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from hcai_ops.api.server import app


def test_mkdocs_file_exists():
    assert Path("mkdocs.yml").exists()


def test_mkdocs_build_if_available(monkeypatch):
    """Build docs if mkdocs is installed; otherwise skip gracefully."""
    try:
        import mkdocs  # noqa: F401
    except ImportError:
        return
    cmd = [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", "site_test"]
    res = subprocess.run(cmd, capture_output=True)
    assert res.returncode == 0


def test_custom_swagger_routes():
    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200
    resp = client.get("/redoc")
    assert resp.status_code == 200
