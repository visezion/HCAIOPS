"""
Kubernetes events integration.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Callable, List

from hcai_ops.data.schemas import HCaiEvent


def _enabled() -> bool:
    return os.getenv("HCAI_K8S_ENABLED", "false").lower() == "true"


def _load_k8s_config():
    from importlib import import_module

    config = import_module("kubernetes.config")
    in_cluster = os.getenv("HCAI_K8S_IN_CLUSTER", "false").lower() == "true"
    if in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config()


def fetch_recent_k8s_events(limit: int = 100) -> List[HCaiEvent]:
    if not _enabled():
        return []
    try:
        from importlib import import_module

        _load_k8s_config()
        client = import_module("kubernetes.client")
        api = client.CoreV1Api()
        resp = api.list_event_for_all_namespaces(limit=limit)
    except Exception:
        return []

    events: List[HCaiEvent] = []
    now = datetime.now(UTC)
    for item in getattr(resp, "items", []):
        typ = getattr(item, "type", "") or ""
        level = "INFO"
        if typ.lower() == "warning":
            level = "WARNING"
        involved = getattr(item, "involved_object", None)
        ns = getattr(getattr(item, "metadata", None), "namespace", None)
        kind = getattr(involved, "kind", None) if involved else None
        name = getattr(involved, "name", None) if involved else None
        src = f"k8s:{ns or 'default'}:{kind or 'object'}/{name or 'unknown'}"
        msg = getattr(item, "message", "") or ""
        evt = HCaiEvent(
            timestamp=now,
            source_id=src,
            event_type="log",
            log_level=level,
            log_message=msg,
            extras={
                "reason": getattr(item, "reason", None),
                "namespace": ns,
                "first_timestamp": getattr(item, "first_timestamp", None),
                "last_timestamp": getattr(item, "last_timestamp", None),
                "count": getattr(item, "count", None),
                "type": typ,
            },
        )
        events.append(evt)
    return events


def watch_k8s_events_forever(handler: Callable[[HCaiEvent], None]) -> None:
    if not _enabled():
        return
    import importlib
    import time

    _load_k8s_config()
    client = importlib.import_module("kubernetes.client")
    watch = importlib.import_module("kubernetes.watch").Watch()

    while True:
        try:
            for event in watch.stream(client.CoreV1Api().list_event_for_all_namespaces):
                obj = event.get("object")
                if obj is None:
                    continue
                hc_events = fetch_recent_k8s_events(limit=1)
                for evt in hc_events:
                    handler(evt)
        except Exception:
            time.sleep(5)
