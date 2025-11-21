from datetime import UTC, datetime

from hcai_ops.agent.engine import AgentEngine
from hcai_ops.data.store import EventStore
from hcai_ops.data.schemas import HCaiEvent


def test_agent_plan_basic():
    store = EventStore()
    store.add_event(
        HCaiEvent(
            timestamp=datetime.now(UTC),
            source_id="s1",
            event_type="metric",
            metric_name="cpu_usage",
            metric_value=0.9,
        )
    )
    agent = AgentEngine(store)
    out = agent.build_plan()
    assert "plan" in out


def test_agent_simulation():
    agent = AgentEngine(EventStore())
    sim = agent.simulate_plan({"risk_score": 0.2, "actions": ["reduce_load"]})
    assert sim["impact"] == "low"


def test_agent_execute_safe():
    agent = AgentEngine(EventStore())
    res = agent.execute_plan({"risk_score": 0.3, "actions": ["scale_up"]})
    assert res["executed"] is True


def test_agent_execute_blocked():
    agent = AgentEngine(EventStore())
    res = agent.execute_plan({"risk_score": 0.95, "actions": ["reboot_cluster"]})
    assert res["executed"] is False
