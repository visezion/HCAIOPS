from __future__ import annotations

import hashlib
import hmac
import os
import zipfile
from pathlib import Path
from typing import Dict, List

from hcai_ops.agent_deploy.version import get_current_agent_version

BUNDLES_DIR = Path(__file__).resolve().parent / "bundles"


def collect_agent_files() -> List[Path]:
    base = Path(__file__).resolve().parents[2] / "hcai_ops_agent"
    if not base.exists():
        return []
    return [p for p in base.rglob("*.py")]


def _sign_bytes(data: bytes) -> str:
    key = os.getenv("AGENT_SIGN_KEY", "devkey").encode()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def generate_agent_bundle(output_path: Path | None = None) -> Dict[str, object]:
    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    version = get_current_agent_version()
    files = collect_agent_files()
    bundle_name = f"agent-{version}.zip"
    bundle_path = output_path or (BUNDLES_DIR / bundle_name)

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.relative_to(f.parents[2]))
    data = bundle_path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    signature = _sign_bytes(data)
    sig_path = Path(str(bundle_path) + ".sig")
    sig_path.write_text(signature)

    return {"version": version, "checksum": checksum, "files": [str(f) for f in files], "path": str(bundle_path), "signature": signature}
