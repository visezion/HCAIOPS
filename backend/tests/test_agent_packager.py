import os
from pathlib import Path

from hcai_ops.agent_deploy.packager import generate_agent_bundle


def test_generate_agent_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_SIGN_KEY", "testkey")
    bundle_path = tmp_path / "bundle.zip"
    meta = generate_agent_bundle(bundle_path)
    assert Path(meta["path"]).exists()
    assert "checksum" in meta
    sig_path = Path(str(meta["path"]) + ".sig")
    assert sig_path.exists()
