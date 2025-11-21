import sys

from hcai_ops.integrations.docker_metrics import collect_docker_metrics


class FakeContainer:
    id = "abc123"
    name = "web"

    def stats(self, stream=False):
        return {
            "cpu_stats": {"cpu_usage": {"total_usage": 1.0}},
            "memory_stats": {"usage": 1024, "limit": 2048},
            "networks": {"eth0": {"rx_bytes": 10, "tx_bytes": 20}},
        }


class FakeDocker:
    def __init__(self):
        self.containers = self

    def list(self):
        return [FakeContainer()]


def test_collect_docker_metrics(monkeypatch):
    monkeypatch.setenv("HCAI_DOCKER_ENABLED", "true")
    sys.modules["docker"] = type("M", (), {"from_env": lambda: FakeDocker()})
    events = collect_docker_metrics()
    assert events
    names = {e.metric_name for e in events}
    assert "docker_container_cpu_percent" in names
