import sys

from hcai_ops.integrations.kubernetes_events import fetch_recent_k8s_events


class FakeMetadata:
    def __init__(self):
        self.namespace = "default"


class FakeInvolved:
    def __init__(self):
        self.kind = "Pod"
        self.name = "pod1"


class FakeEvent:
    def __init__(self):
        self.type = "Warning"
        self.message = "Pod failed"
        self.reason = "Failed"
        self.metadata = FakeMetadata()
        self.involved_object = FakeInvolved()
        self.first_timestamp = None
        self.last_timestamp = None
        self.count = 1


class FakeResp:
    def __init__(self):
        self.items = [FakeEvent()]


class FakeClient:
    class CoreV1Api:
        def list_event_for_all_namespaces(self, limit=100):
            return FakeResp()


def test_fetch_recent_k8s_events(monkeypatch):
    monkeypatch.setenv("HCAI_K8S_ENABLED", "true")
    monkeypatch.setenv("HCAI_K8S_IN_CLUSTER", "false")

    class FakeConfig:
        def load_kube_config(self):
            return None

        def load_incluster_config(self):
            return None

    sys.modules["kubernetes.config"] = FakeConfig()
    sys.modules["kubernetes.client"] = FakeClient()

    events = fetch_recent_k8s_events()
    assert events
    evt = events[0]
    assert evt.log_level == "WARNING"
    assert evt.source_id.startswith("k8s:")
