import json
from pathlib import Path

from hcai_ops_agent.config import AgentConfig, load_config


def test_config_generate(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setenv("HCAI_AGENT_CONFIG_PATH", str(cfg_path))
    cfg = load_config()
    assert cfg.agent_id
    assert cfg.api_url.startswith("http")
    # saved
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text())
    assert data["agent_id"] == cfg.agent_id

