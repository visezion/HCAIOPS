"""
Async load generators for stress testing.
"""
from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import List, Dict, Any

from hcai_ops.data.ingest import (
    parse_syslog_lines,
    parse_prometheus_text,
    map_cloudflare_event,
    map_docker_event,
    map_k8s_event,
)
from hcai_ops.data.schemas import HCaiEvent


class SyslogGenerator:
    def __init__(self, rate_per_second: int, total_events: int):
        self.rate = max(1, rate_per_second)
        self.total = total_events

    async def run(self) -> List[HCaiEvent]:
        events: List[HCaiEvent] = []
        for i in range(self.total):
            line = f"Oct 11 22:14:{15 + (i % 45):02d} host{i%3} app[{i%100}]: Test log {i}"
            evts = parse_syslog_lines([line])
            events.extend(evts)
            await asyncio.sleep(1 / self.rate)
        return events


class PrometheusGenerator:
    def __init__(self, rate_per_second: int, total_events: int):
        self.rate = max(1, rate_per_second)
        self.total = total_events

    async def run(self) -> List[HCaiEvent]:
        events: List[HCaiEvent] = []
        for i in range(self.total):
            text = [f"node_cpu_seconds_total {0.1 * (i % 10)}", f"node_memory_usage {1000 + i}"]
            evts = parse_prometheus_text(text, source_id="loadgen")
            events.extend(evts)
            await asyncio.sleep(1 / self.rate)
        return events


class CloudflareGenerator:
    def __init__(self, rate_per_second: int, total_events: int):
        self.rate = max(1, rate_per_second)
        self.total = total_events

    async def run(self) -> List[HCaiEvent]:
        events: List[HCaiEvent] = []
        for i in range(self.total):
            rec = {
                "EdgeResponseStatus": 200 if i % 5 else 500,
                "ClientRequestMethod": "GET",
                "ClientRequestURI": f"/path/{i}",
                "ClientIP": "1.1.1.1",
                "ClientRequestUserAgent": "loadgen",
            }
            events.append(map_cloudflare_event(rec, zone_id="loadzone"))
            await asyncio.sleep(1 / self.rate)
        return events


class DockerStatsGenerator:
    def __init__(self, rate_per_second: int, total_events: int):
        self.rate = max(1, rate_per_second)
        self.total = total_events

    async def run(self) -> List[HCaiEvent]:
        events: List[HCaiEvent] = []
        for i in range(self.total):
            stats = {
                "container_id": f"abc{i}",
                "cpu": 0.25,
                "mem": 128 + i,
                "mem_limit": 256,
                "net_rx": 10 * i,
                "net_tx": 5 * i,
            }
            events.extend(map_docker_event(stats, container_name=f"cont{i%3}"))
            await asyncio.sleep(1 / self.rate)
        return events


class K8sEventGenerator:
    def __init__(self, rate_per_second: int, total_events: int):
        self.rate = max(1, rate_per_second)
        self.total = total_events

    async def run(self) -> List[HCaiEvent]:
        events: List[HCaiEvent] = []
        for i in range(self.total):
            rec = {"kind": "Pod", "name": f"pod{i}", "action": "Started", "type": "Normal", "namespace": "default"}
            events.append(map_k8s_event(rec))
            await asyncio.sleep(1 / self.rate)
        return events


GENERATOR_MAP = {
    "syslog": SyslogGenerator,
    "prometheus": PrometheusGenerator,
    "cloudflare": CloudflareGenerator,
    "docker": DockerStatsGenerator,
    "k8s": K8sEventGenerator,
}


def _is_hcaievent_list(events: List[Any]) -> bool:
    return all(isinstance(e, HCaiEvent) for e in events)


async def run_profile_async(profile: Dict[str, Any]) -> Dict[str, Any]:
    evt_type = profile.get("type")
    total = int(profile.get("events", 0))
    rate = int(profile.get("rate", 1))
    Gen = GENERATOR_MAP.get(evt_type)
    if not Gen:
        return {"events": 0, "duration": 0, "eps": 0}
    gen = Gen(rate, total)
    start = asyncio.get_event_loop().time()
    events = await gen.run()
    duration = asyncio.get_event_loop().time() - start
    eps = len(events) / duration if duration > 0 else len(events)
    try:
        from hcai_ops.analytics import event_store
        event_store.add_events(events)
    except Exception:
        pass
    return {"events": len(events), "duration": duration, "eps": eps, "valid": _is_hcaievent_list(events)}
