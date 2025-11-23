"""
Cross-platform log collection.
"""
from __future__ import annotations

import os
import platform
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import List

from hcai_ops.data.schemas import HCaiEvent
from .config import AgentConfig

try:
    import win32evtlog  # type: ignore
    import win32evtlogutil  # type: ignore
except Exception:  # pragma: no cover - non-Windows
    win32evtlog = None
    win32evtlogutil = None


def _tail_file(path: Path, n: int = 200) -> List[str]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
            return lines[-n:]
    except Exception:
        return []


def collect_logs(config: AgentConfig) -> List[HCaiEvent]:
    system = os.getenv("HCAI_AGENT_OS") or platform.system().lower()
    events: List[HCaiEvent] = []
    ts = datetime.now(UTC)

    if system.startswith("win"):
        if not win32evtlog:
            return events
        for log_name in config.log_paths.get("windows", ["Application", "System"]):
            try:
                handle = win32evtlog.OpenEventLog(None, log_name)
                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                total = win32evtlog.GetNumberOfEventLogRecords(handle)
                fetched = 0
                while fetched < 200:
                    records = win32evtlog.ReadEventLog(handle, flags, 0)
                    if not records:
                        break
                    for rec in records:
                        fetched += 1
                        if fetched > 200:
                            break
                        msg = win32evtlogutil.SafeFormatMessage(rec, log_name)
                        events.append(
                            HCaiEvent(
                                timestamp=ts,
                                source_id=config.agent_id,
                                event_type="log",
                                log_level=str(rec.EventType),
                                log_message=msg,
                                extras={"log_name": log_name},
                            )
                        )
            except Exception:
                continue
    else:
        for path_str in config.log_paths.get("linux", ["/var/log/syslog", "/var/log/messages"]):
            for line in _tail_file(Path(path_str)):
                events.append(
                    HCaiEvent(
                        timestamp=ts,
                        source_id=config.agent_id,
                        event_type="log",
                        log_level=None,
                        log_message=line.strip(),
                        extras={"path": path_str},
                    )
                )
    return events
