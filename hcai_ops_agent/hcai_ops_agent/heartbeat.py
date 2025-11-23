"""
Heartbeat generation.
"""
from __future__ import annotations

from datetime import UTC, datetime

from hcai_ops.data.schemas import HCaiEvent
from .config import AgentConfig
from .system_info import collect_system_info

AGENT_VERSION = "1.0.0"


def build_heartbeat(config: AgentConfig) -> HCaiEvent:
    sysinfo = collect_system_info()
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=config.agent_id,
        event_type="heartbeat",
        log_level=None,
        log_message=None,
        metric_name=None,
        metric_value=None,
        extras={
            "status": "online",
            "version": AGENT_VERSION,
            "cpu_percent": sysinfo.get("cpu_percent", 0.0),
            "ram_percent": sysinfo.get("ram_percent", 0.0),
        },
    )
