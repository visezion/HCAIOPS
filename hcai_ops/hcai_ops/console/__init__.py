import click

from hcai_ops.analytics import event_store


@click.group()
def cli():
    """HCAI OPS CLI."""


@cli.command("start-agent")
def cli_start_agent():
    from hcai_ops_agent.main import run
    run()


@cli.command("pull-cloudflare")
def pull_cloudflare():
    """One shot pull from Cloudflare and store events."""
    from hcai_ops.integrations.cloudflare import pull_cloudflare_events

    events = pull_cloudflare_events()
    event_store.add_events(events)


@cli.command("scrape-prometheus")
def scrape_prometheus():
    """One shot scrape of all configured Prometheus targets."""
    from hcai_ops.integrations.prometheus_scraper import scrape_all_prometheus_targets

    events = scrape_all_prometheus_targets()
    event_store.add_events(events)


@cli.command("docker-metrics")
def docker_metrics():
    """Collect Docker metrics once and store them."""
    from hcai_ops.integrations.docker_metrics import collect_docker_metrics

    events = collect_docker_metrics()
    event_store.add_events(events)


@cli.command("k8s-events")
def k8s_events():
    """Fetch recent Kubernetes events once and store them."""
    from hcai_ops.integrations.kubernetes_events import fetch_recent_k8s_events

    events = fetch_recent_k8s_events()
    event_store.add_events(events)


@cli.command("run-syslog-server")
def run_syslog_server():
    """Start the syslog receiver bound to configured ports."""
    from hcai_ops.integrations.syslog_server import run_syslog_server_forever

    run_syslog_server_forever()


@cli.command("stress")
def stress():
    """Run full ingest stress test and print performance summary."""
    from hcai_ops.testing.stress_test import run_full_ingest_test

    summary = run_full_ingest_test()
    click.echo(f"Total events: {summary.get('total_events')}")
    click.echo(f"Events valid: {summary.get('valid')}")
