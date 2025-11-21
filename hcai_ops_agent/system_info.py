"""
System information collection utilities.
"""
from __future__ import annotations

import platform
import socket
import time
import uuid
from typing import Dict, Any

try:
    import psutil
except Exception:  # pragma: no cover - env without psutil
    psutil = None


def _safe_psutil_call(fn, default):
    try:
        return fn()
    except Exception:
        return default


def collect_system_info() -> Dict[str, Any]:
    now = time.time()
    info: Dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "agent_uuid": str(uuid.getnode()),
    }
    if psutil:
        info.update(
            {
                "cpu_percent": _safe_psutil_call(lambda: psutil.cpu_percent(interval=0.1), 0.0),
                "ram_percent": _safe_psutil_call(lambda: psutil.virtual_memory().percent, 0.0),
                "disk_percent": _safe_psutil_call(lambda: psutil.disk_usage("/").percent, 0.0),
                "net_sent": _safe_psutil_call(lambda: psutil.net_io_counters().bytes_sent, 0),
                "net_recv": _safe_psutil_call(lambda: psutil.net_io_counters().bytes_recv, 0),
                "uptime": now - _safe_psutil_call(lambda: psutil.boot_time(), now),
                "process_count": _safe_psutil_call(lambda: len(psutil.pids()), 0),
            }
        )
    else:
        info.update(
            {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "disk_percent": 0.0,
                "net_sent": 0,
                "net_recv": 0,
                "uptime": 0,
                "process_count": 0,
            }
        )
    return info
