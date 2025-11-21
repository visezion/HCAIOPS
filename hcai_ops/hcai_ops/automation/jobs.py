from datetime import datetime
from typing import Dict, List

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.data.ingest import parse_prometheus_text, parse_syslog_lines
from hcai_ops.automation.scheduler import AutomationJob
from hcai_ops.integrations.cloudflare import pull_cloudflare_events
from hcai_ops.integrations.prometheus_scraper import scrape_all_prometheus_targets
from hcai_ops.integrations.docker_metrics import collect_docker_metrics
from hcai_ops.integrations.kubernetes_events import fetch_recent_k8s_events


def prometheus_text_job_handler(job: AutomationJob, now: datetime) -> List[HCaiEvent]:
    raw_text = job.config.get("prometheus_text", "")
    source_id = job.config.get("source_id", "unknown")
    lines = raw_text.splitlines()
    return parse_prometheus_text(lines, source_id=source_id)


def syslog_job_handler(job: AutomationJob, now: datetime) -> List[HCaiEvent]:
    lines = job.config.get("syslog_lines", [])
    default_source_id = job.config.get("default_source_id")
    return parse_syslog_lines(lines, default_source_id=default_source_id)


def cloudflare_pull_job() -> List[HCaiEvent]:
    try:
        return pull_cloudflare_events()
    except Exception:
        return []


def prometheus_scrape_job() -> List[HCaiEvent]:
    return scrape_all_prometheus_targets()


def docker_metrics_job() -> List[HCaiEvent]:
    return collect_docker_metrics()


def k8s_events_job() -> List[HCaiEvent]:
    return fetch_recent_k8s_events()


def get_default_handlers() -> Dict[str, "JobHandler"]:
    from hcai_ops.automation.runner import JobHandler

    return {
        "prometheus_text": prometheus_text_job_handler,
        "syslog": syslog_job_handler,
        "cloudflare_pull": lambda job, now: cloudflare_pull_job(),
        "prometheus_scrape": lambda job, now: prometheus_scrape_job(),
        "docker_metrics": lambda job, now: docker_metrics_job(),
        "k8s_events": lambda job, now: k8s_events_job(),
    }
