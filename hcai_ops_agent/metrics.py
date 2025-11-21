"""
Metric aggregation for the agent.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import List

from hcai_ops.data.schemas import HCaiEvent
from .config import AgentConfig
from .system_info import collect_system_info


def build_metric_events(config: AgentConfig) -> List[HCaiEvent]:
    sysinfo = collect_system_info()
    timestamp = datetime.now(UTC)
    metrics = []
    for key in ["cpu_percent", "ram_percent", "disk_percent", "net_sent", "net_recv", "uptime", "process_count"]:
        value = sysinfo.get(key)
        metrics.append(
            HCaiEvent(
                timestamp=timestamp,
                source_id=config.agent_id,
                event_type="metric",
                metric_name=key,
                metric_value=float(value) if value is not None else None,
                extras={"system_info": sysinfo},
            )
        )
    return metrics
