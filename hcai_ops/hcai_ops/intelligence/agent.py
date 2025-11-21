from __future__ import annotations

from typing import Dict

from hcai_ops.agent_deploy.version import get_current_agent_version, compare_versions, get_current_agent_version
from hcai_ops.agent_deploy.update_manager import get_latest_bundle_info, needs_update
from hcai_ops.analytics import event_store
from hcai_ops.data.schemas import HCaiEvent
from datetime import UTC, datetime


def agent_check_in(agent_version: str) -> Dict[str, object]:
    latest_info = get_latest_bundle_info()
    latest_version = latest_info.get("version", get_current_agent_version())
    update_required = needs_update(agent_version, latest_version)
    download_url = None
    if update_required and latest_info.get("path"):
        download_url = f"/agent/download/{latest_version}"
    return {
        "update_required": update_required,
        "download_url": download_url,
        "latest_version": latest_version,
    }


def record_update_status(current_version: str, result: str, error_message: str | None = None):
    evt = HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id="agent",
        event_type="update_status",
        log_message=error_message,
        log_level=result,
        extras={"current_version": current_version},
    )
    event_store.add_events([evt])
