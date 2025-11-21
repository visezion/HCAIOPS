"""
Stress testing utilities for HCAI OPS.
"""
from __future__ import annotations

import asyncio
import random
import tracemalloc
from typing import Dict, Any, List

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.testing.loadgen import (
    run_profile_async,
    SyslogGenerator,
    PrometheusGenerator,
    CloudflareGenerator,
    DockerStatsGenerator,
    K8sEventGenerator,
)


def run_stress_test(profile: Dict[str, Any]) -> Dict[str, Any]:
    tracemalloc.start()
    summary = asyncio.run(run_profile_async(profile))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    summary["memory_bytes"] = peak
    return summary


def run_full_ingest_test() -> Dict[str, Any]:
    profiles = [
        {"type": "syslog", "events": 20, "rate": 50},
        {"type": "prometheus", "events": 20, "rate": 50},
        {"type": "cloudflare", "events": 10, "rate": 20},
        {"type": "docker", "events": 10, "rate": 20},
        {"type": "k8s", "events": 10, "rate": 20},
    ]
    totals = 0
    all_events: List[HCaiEvent] = []
    for prof in profiles:
        gen_map = {
            "syslog": SyslogGenerator,
            "prometheus": PrometheusGenerator,
            "cloudflare": CloudflareGenerator,
            "docker": DockerStatsGenerator,
            "k8s": K8sEventGenerator,
        }
        Gen = gen_map[prof["type"]]
        gen = Gen(prof["rate"], prof["events"])
        events = asyncio.run(gen.run())
        totals += len(events)
        all_events.extend(events)
        try:
            from hcai_ops.analytics import event_store
            event_store.add_events(events)
        except Exception:
            pass
    ok = all(isinstance(e, HCaiEvent) for e in all_events)
    return {"total_events": totals, "valid": ok}
