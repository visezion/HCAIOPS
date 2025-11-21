"""
Prometheus Node Exporter scraper.
"""
from __future__ import annotations

import os
from typing import List
from urllib.parse import urlparse

import httpx

from hcai_ops.data.ingest import parse_prometheus_text
from hcai_ops.data.schemas import HCaiEvent


def _targets_from_env() -> List[str]:
    env_val = os.getenv("HCAI_PROMETHEUS_TARGETS", "")
    if isinstance(env_val, str):
        return [t.strip() for t in env_val.split(",") if t.strip()]
    if isinstance(env_val, list):
        return env_val
    return []


def _enabled() -> bool:
    return os.getenv("HCAI_PROMETHEUS_ENABLED", "false").lower() == "true"


def scrape_prometheus_target(url: str, source_id: str | None = None) -> List[HCaiEvent]:
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        text = resp.text
    except Exception:
        return []
    lines = text.splitlines()
    sid = source_id
    if not sid:
        sid = urlparse(url).hostname or "prometheus"
    return parse_prometheus_text(lines, source_id=sid)


def scrape_all_prometheus_targets() -> List[HCaiEvent]:
    events: List[HCaiEvent] = []
    if not _enabled():
        return events
    for target in _targets_from_env():
        try:
            events.extend(scrape_prometheus_target(target))
        except Exception:
            continue
    return events
