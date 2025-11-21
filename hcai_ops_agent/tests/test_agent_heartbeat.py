from hcai_ops_agent.config import AgentConfig
from hcai_ops_agent.heartbeat import build_heartbeat


def test_build_heartbeat():
    cfg = AgentConfig._default()
    hb = build_heartbeat(cfg)
    assert hb.event_type == "heartbeat"
    assert hb.source_id == cfg.agent_id
    assert hb.extras["status"] == "online"
