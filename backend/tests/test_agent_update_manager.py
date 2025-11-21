import os
from pathlib import Path

from hcai_ops.agent_deploy.update_manager import needs_update, verify_bundle, download_bundle, extract_and_install


def test_needs_update():
    assert needs_update("1.0.0", "1.0.1") is True
    assert needs_update("1.0.1", "1.0.0") is False


def test_verify_and_extract(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_SIGN_KEY", "testkey")
    bundle = tmp_path / "b.zip"
    bundle.write_text("data")
    sig = tmp_path / "b.zip.sig"
    import hashlib, hmac

    sig.write_text(hmac.new(b"testkey", bundle.read_bytes(), hashlib.sha256).hexdigest())
    assert verify_bundle(bundle)
    install = tmp_path / "install"
    extract_and_install(bundle, install)
    assert (install / bundle.name).exists()


def test_download_bundle_file(tmp_path):
    src = tmp_path / "src.zip"
    src.write_text("data")
    dst = download_bundle(f"file://{src}")
    assert dst.exists()
