from pathlib import Path

from hcai_ops_agent.config import AgentConfig
from hcai_ops_agent.logs import collect_logs


def test_collect_logs_linux(tmp_path, monkeypatch):
    sample = tmp_path / "syslog"
    sample.write_text("line1\nline2\n")
    cfg = AgentConfig._default()
    cfg.log_paths["linux"] = [str(sample)]
    monkeypatch.setenv("HCAI_AGENT_OS", "linux")
    events = collect_logs(cfg)
    assert events
    assert all(evt.event_type == "log" for evt in events)
