"""
Docker metrics collection.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import List

from hcai_ops.data.schemas import HCaiEvent


def _enabled() -> bool:
    return os.getenv("HCAI_DOCKER_ENABLED", "false").lower() == "true"


def collect_docker_metrics() -> List[HCaiEvent]:
    if not _enabled():
        return []
    try:
        import docker  # type: ignore
    except Exception:
        return []

    try:
        client = docker.from_env()
        containers = client.containers.list()
    except Exception:
        return []

    events: List[HCaiEvent] = []
    ts = datetime.now(UTC)
    for c in containers:
        try:
            stats = c.stats(stream=False)
        except Exception:
            continue
        name = getattr(c, "name", None) or c.id[:12]
        source_id = f"docker:{name}"
        cpu_percent = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0.0)
        mem_usage = stats.get("memory_stats", {}).get("usage", 0.0)
        mem_limit = stats.get("memory_stats", {}).get("limit", 0.0)
        net = stats.get("networks", {}) or {}
        net_rx = net.get("eth0", {}).get("rx_bytes", 0) if isinstance(net, dict) else 0
        net_tx = net.get("eth0", {}).get("tx_bytes", 0) if isinstance(net, dict) else 0

        metrics = [
            ("docker_container_cpu_percent", float(cpu_percent)),
            ("docker_container_mem_usage_bytes", float(mem_usage)),
            ("docker_container_mem_limit_bytes", float(mem_limit)),
            ("docker_container_net_rx_bytes", float(net_rx)),
            ("docker_container_net_tx_bytes", float(net_tx)),
        ]
        for metric_name, metric_value in metrics:
            events.append(
                HCaiEvent(
                    timestamp=ts,
                    source_id=source_id,
                    event_type="metric",
                    metric_name=metric_name,
                    metric_value=metric_value,
                    extras={"container_id": getattr(c, "id", None), "raw": stats},
                )
            )
    return events
