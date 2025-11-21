from hcai_ops_agent.config import AgentConfig
from hcai_ops_agent.metrics import build_metric_events


def test_build_metric_events():
    cfg = AgentConfig._default()
    events = build_metric_events(cfg)
    assert events
    assert all(evt.event_type == "metric" for evt in events)
    assert all(evt.source_id == cfg.agent_id for evt in events)
