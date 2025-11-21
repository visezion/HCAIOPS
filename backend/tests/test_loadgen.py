import asyncio

from hcai_ops.testing.loadgen import (
    SyslogGenerator,
    PrometheusGenerator,
    CloudflareGenerator,
    DockerStatsGenerator,
    K8sEventGenerator,
)
from hcai_ops.data.schemas import HCaiEvent


def test_syslog_generator_small():
    events = asyncio.run(SyslogGenerator(rate_per_second=100, total_events=5).run())
    assert len(events) == 5
    assert all(isinstance(e, HCaiEvent) for e in events)
    assert all(e.event_type == "log" for e in events)


def test_prometheus_generator_small():
    events = asyncio.run(PrometheusGenerator(rate_per_second=100, total_events=3).run())
    assert len(events) >= 3
    assert all(e.event_type == "metric" for e in events)
    assert all(isinstance(e.metric_value, float) for e in events)


def test_cloudflare_generator_small():
    events = asyncio.run(CloudflareGenerator(rate_per_second=50, total_events=2).run())
    assert len(events) == 2
    assert all(e.event_type == "log" for e in events)
    assert all(e.source_id.startswith("cloudflare") for e in events)


def test_docker_generator_small():
    events = asyncio.run(DockerStatsGenerator(rate_per_second=50, total_events=2).run())
    assert events
    assert all(e.event_type == "metric" for e in events)
    assert all("docker_container" in (e.metric_name or "") for e in events)


def test_k8s_generator_small():
    events = asyncio.run(K8sEventGenerator(rate_per_second=50, total_events=2).run())
    assert len(events) == 2
    assert all(e.event_type == "log" for e in events)
