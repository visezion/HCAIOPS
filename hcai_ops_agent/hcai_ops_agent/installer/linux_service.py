"""
Linux systemd service definition helper.
"""
from pathlib import Path

SERVICE_TEMPLATE = """[Unit]
Description=HCAI Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/hcai_agent/main.py
Restart=always

[Install]
WantedBy=multi-user.target
"""


def write_systemd_service(path: Path | None = None) -> Path:
    """
    Write systemd unit file content to the given path (default /etc/systemd/system/hcai_agent.service).
    """
    target = path or Path("/etc/systemd/system/hcai_agent.service")
    target.write_text(SERVICE_TEMPLATE)
    return target
