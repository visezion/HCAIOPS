from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from hcai_ops.agent_deploy.update_manager import get_latest_bundle_info

router = APIRouter()
BUNDLES_DIR = Path(__file__).resolve().parent / "bundles"


@router.get("/agent/latest")
def latest_agent():
    info = get_latest_bundle_info()
    if not info:
        raise HTTPException(status_code=404, detail="No bundle available")
    return info


@router.get("/agent/download/{version}")
def download_agent(version: str):
    path = BUNDLES_DIR / f"agent-{version}.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Bundle not found")
    return FileResponse(path)
