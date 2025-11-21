"""
Utilities to ingest raw data sources and convert them into HCaiEvent objects.
Provides parsers for common text formats and helpers to persist events to disk.
"""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Dict, Iterable, List, Optional
import ast

import pandas as pd

from .schemas import HCaiEvent


def dicts_to_events(payload: List[Dict[str, Any]]) -> List[HCaiEvent]:
    """
    Convert a list of dictionaries into a list of HCaiEvent objects.
    Unknown keys are preserved inside the extras field.
    """
    events: List[HCaiEvent] = []
    fields = set(HCaiEvent.__dataclass_fields__.keys())

    for item in payload:
        data = dict(item) if item is not None else {}
        event_kwargs: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}

        for key, value in data.items():
            if key == "timestamp" and value is not None:
                event_kwargs[key] = pd.to_datetime(value).to_pydatetime()
            elif key in fields:
                event_kwargs[key] = value
            else:
                extras[key] = value

        existing_extras = event_kwargs.get("extras")
        if isinstance(existing_extras, dict):
            extras = {**existing_extras, **extras}

        event_kwargs["extras"] = extras
        events.append(HCaiEvent(**event_kwargs))
    return events


def parse_prometheus_text(lines: Iterable[str], source_id: str) -> List[HCaiEvent]:
    """
    Parse Prometheus text exposition format into metric HCaiEvent objects.
    """
    events: List[HCaiEvent] = []
    now = datetime.now(UTC)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        metric_name, metric_value = parts[0], parts[1]

        try:
            value = float(metric_value)
        except ValueError:
            continue

        events.append(
            HCaiEvent(
                timestamp=now,
                source_id=source_id,
                event_type="metric",
                metric_name=metric_name,
                metric_value=value,
            )
        )
    return events


def parse_syslog_lines(lines: Iterable[str], default_source_id: Optional[str] = None) -> List[HCaiEvent]:
    """
    Parse standard syslog lines.
    Expected format:
        <Month> <Day> <Time> <Host> <Process> ... : <Message>
    """
    events: List[HCaiEvent] = []

    for line in lines:
        if not line:
            continue

        # Split header and message
        if ":" in line:
            header, message = line.rsplit(":", 1)
        else:
            header, message = line, ""
        log_message = message.strip()
        msg_upper = log_message.upper()

        # Log level detection
        if any(t in msg_upper for t in ["CRIT", "CRITICAL", "FATAL"]):
            log_level = "CRITICAL"
        elif any(t in msg_upper for t in ["ERR", "ERROR", "FAIL"]):
            log_level = "ERROR"
        elif any(t in msg_upper for t in ["WARN", "WARNING"]):
            log_level = "WARNING"
        elif "INFO" in msg_upper:
            log_level = "INFO"
        else:
            log_level = "DEBUG"

        # Extract hostname (always tokens[3] in standard syslog)
        tokens = header.split()
        if len(tokens) >= 4:
            source_id = tokens[3]
        else:
            source_id = default_source_id or "unknown"

        events.append(
            HCaiEvent(
                timestamp=datetime.now(UTC),
                source_id=source_id,
                event_type="log",
                log_message=log_message,
                log_level=log_level,
                extras={"raw_header": header.strip()},
            )
        )

    return events


def map_cloudflare_event(rec: Dict[str, Any], zone_id: str) -> HCaiEvent:
    status = rec.get("EdgeResponseStatus") or rec.get("status") or 200
    method = rec.get("ClientRequestMethod") or rec.get("method") or ""
    uri = rec.get("ClientRequestURI") or rec.get("path") or ""
    ip = rec.get("ClientIP") or rec.get("ip")
    ua = rec.get("ClientRequestUserAgent") or rec.get("user_agent")
    level = "INFO"
    if status and int(status) >= 500:
        level = "ERROR"
    elif status and int(status) >= 400:
        level = "WARNING"
    msg = f"{method} {uri} status={status}"
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=f"cloudflare:{zone_id}",
        event_type="log",
        log_level=level,
        log_message=msg,
        extras={
            "ip": ip,
            "country": rec.get("EdgeResponseCountry") or rec.get("country"),
            "uri": uri,
            "user_agent": ua,
            "raw": rec,
        },
    )


def map_docker_event(stats: Dict[str, Any], container_name: str) -> List[HCaiEvent]:
    ts = datetime.now(UTC)
    source_id = f"docker:{container_name}"
    cpu_percent = stats.get("cpu", stats.get("cpu_percent", 0.0))
    mem_usage = stats.get("mem") or stats.get("memory_usage") or stats.get("memory", 0.0)
    mem_limit = stats.get("mem_limit") or stats.get("memory_limit") or 0.0
    net_rx = stats.get("net_rx") or stats.get("net_rx_bytes") or 0
    net_tx = stats.get("net_tx") or stats.get("net_tx_bytes") or 0
    metrics = [
        ("docker_container_cpu_percent", float(cpu_percent)),
        ("docker_container_mem_usage_bytes", float(mem_usage)),
        ("docker_container_mem_limit_bytes", float(mem_limit)),
        ("docker_container_net_rx_bytes", float(net_rx)),
        ("docker_container_net_tx_bytes", float(net_tx)),
    ]
    events: List[HCaiEvent] = []
    for metric_name, metric_value in metrics:
        events.append(
            HCaiEvent(
                timestamp=ts,
                source_id=source_id,
                event_type="metric",
                metric_name=metric_name,
                metric_value=metric_value,
                extras={"raw": stats},
            )
        )
    return events


def map_k8s_event(rec: Dict[str, Any]) -> HCaiEvent:
    ts = datetime.now(UTC)
    ns = rec.get("namespace") or "default"
    kind = rec.get("kind") or "object"
    name = rec.get("name") or "unknown"
    level = "WARNING" if rec.get("type", "").lower() == "warning" else "INFO"
    msg = rec.get("message") or f"{kind} {name} {rec.get('action', '')}".strip()
    return HCaiEvent(
        timestamp=ts,
        source_id=f"k8s:{ns}:{kind}/{name}",
        event_type="log",
        log_level=level,
        log_message=msg,
        extras=rec,
    )


# Additional mapping to support monitoring event types
def map_system_event(payload: Dict[str, Any]) -> HCaiEvent:
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=payload.get("source_id", "system"),
        event_type="system",
        metric_name=payload.get("metric_name"),
        metric_value=payload.get("metric_value"),
        extras=payload,
        log_level=None,
        log_message=None,
    )


def map_network_event(payload: Dict[str, Any]) -> HCaiEvent:
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=payload.get("source_id", "network"),
        event_type="network",
        metric_name=payload.get("metric_name"),
        metric_value=payload.get("metric_value"),
        extras=payload,
    )


def map_process_event(payload: Dict[str, Any]) -> HCaiEvent:
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=payload.get("source_id", "process"),
        event_type="process",
        log_message=payload.get("log_message"),
        log_level=payload.get("log_level"),
        extras=payload,
    )


def map_service_event(payload: Dict[str, Any]) -> HCaiEvent:
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=payload.get("source_id", "service"),
        event_type="service",
        log_message=payload.get("log_message"),
        log_level=payload.get("log_level"),
        extras=payload,
    )


def map_log_event(payload: Dict[str, Any]) -> HCaiEvent:
    return HCaiEvent(
        timestamp=datetime.now(UTC),
        source_id=payload.get("source_id", "log"),
        event_type="log",
        log_message=payload.get("log_message"),
        log_level=payload.get("log_level", "ERROR"),
        extras=payload,
    )





def save_events_csv(path: str, events: List[HCaiEvent]) -> None:
    """
    Save a list of HCaiEvent objects to CSV on disk.
    """
    rows: List[Dict[str, Any]] = []

    for e in events:
        row = asdict(e)
        if isinstance(row.get("timestamp"), datetime):
            row["timestamp"] = row["timestamp"].isoformat()
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def load_events_csv(path: str) -> List[HCaiEvent]:
    """
    Load HCaiEvent objects from a CSV previously written by save_events_csv.
    """
    df = pd.read_csv(path)
    events: List[HCaiEvent] = []
    known_fields = set(HCaiEvent.__dataclass_fields__.keys())

    for row in df.to_dict(orient="records"):
        event_kwargs: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}

        for key, value in row.items():
            if key == "timestamp" and pd.notnull(value):
                event_kwargs[key] = pd.to_datetime(value).to_pydatetime()
            elif key in known_fields:
                # extras fields saved as str
                if key == "extras" and isinstance(value, str):
                    try:
                        value = ast.literal_eval(value)
                    except Exception:
                        pass
                event_kwargs[key] = value
            else:
                extras[key] = value

        existing_extras = event_kwargs.get("extras")
        if isinstance(existing_extras, dict):
            extras = {**existing_extras, **extras}

        event_kwargs["extras"] = extras
        events.append(HCaiEvent(**event_kwargs))

    return events
