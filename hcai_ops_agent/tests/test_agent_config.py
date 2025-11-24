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


def test_env_overrides(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setenv("HCAI_AGENT_CONFIG_PATH", str(cfg_path))
    base_cfg = load_config()
    assert base_cfg.api_url.startswith("http")

    monkeypatch.setenv("HCAI_AGENT_API_URL", "https://hcaiops.vicezion.com")
    monkeypatch.setenv("HCAI_AGENT_TOKEN", "token-123")
    monkeypatch.setenv("HCAI_AGENT_ID", "agent-xyz")

    cfg = load_config()
    assert cfg.api_url == "https://hcaiops.vicezion.com"
    assert cfg.token == "token-123"
    assert cfg.agent_id == "agent-xyz"
