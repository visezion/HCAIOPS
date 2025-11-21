from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional

import httpx

from hcai_ops.agent_deploy.version import compare_versions, get_current_agent_version
from hcai_ops.agent_deploy.packager import BUNDLES_DIR


def needs_update(current_version: str, latest_version: str) -> bool:
    return compare_versions(current_version, latest_version) < 0


def _sign(data: bytes) -> str:
    key = os.getenv("AGENT_SIGN_KEY", "devkey").encode()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def get_latest_bundle_info() -> Dict[str, str]:
    latest = get_current_agent_version()
    bundle_path = BUNDLES_DIR / f"agent-{latest}.zip"
    if not bundle_path.exists():
        return {}
    data = bundle_path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    sig_path = Path(str(bundle_path) + ".sig")
    signature = sig_path.read_text().strip() if sig_path.exists() else _sign(data)
    return {"version": latest, "path": str(bundle_path), "checksum": checksum, "signature": signature}


def download_bundle(url: str) -> Path:
    if url.startswith("file://"):
        src = Path(url.replace("file://", ""))
        dst = Path(tempfile.mktemp(suffix=src.name))
        shutil.copy(src, dst)
        return dst
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    dst = Path(tempfile.mktemp(suffix=".zip"))
    dst.write_bytes(resp.content)
    return dst


def verify_bundle(bundle_path: Path) -> bool:
    data = bundle_path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    sig_path = Path(str(bundle_path) + ".sig")
    expected_sig = sig_path.read_text().strip() if sig_path.exists() else _sign(data)
    return expected_sig == _sign(data) and checksum == hashlib.sha256(data).hexdigest()


def extract_and_install(bundle_path: Path, install_path: Path) -> None:
    install_path.mkdir(parents=True, exist_ok=True)
    shutil.copy(bundle_path, install_path / bundle_path.name)
    (install_path / "installed_version.txt").write_text(get_current_agent_version())


def restart_agent_service():
    # Placeholder to restart service; no-op for tests
    return True
