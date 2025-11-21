from datetime import datetime, timedelta

from hcai_ops.automation.jobs import get_default_handlers
from hcai_ops.automation.runner import JobRunner
from hcai_ops.automation.scheduler import AutomationJob, Scheduler


def test_scheduler_due_jobs_respects_interval():
    scheduler = Scheduler()
    base = datetime(2025, 1, 1, 0, 0, 0)

    job1 = AutomationJob(
        id="j1",
        name="job1",
        job_type="dummy",
        interval_seconds=60,
        last_run_at=None,
    )
    job2 = AutomationJob(
        id="j2",
        name="job2",
        job_type="dummy",
        interval_seconds=120,
        last_run_at=base,
    )
    scheduler.add_job(job1)
    scheduler.add_job(job2)

    due1 = scheduler.due_jobs(base)
    assert {job.id for job in due1} == {"j1"}

    now2 = base + timedelta(seconds=180)
    due2 = scheduler.due_jobs(now2)
    assert {job.id for job in due2} == {"j1", "j2"}


def test_job_runner_runs_handlers_and_marks_last_run():
    scheduler = Scheduler()
    job = AutomationJob(
        id="p1",
        name="prometheus ingest",
        job_type="prometheus_text",
        interval_seconds=60,
        last_run_at=None,
        config={
            "prometheus_text": "# HELP cpu_usage CPU usage\ncpu_usage 0.5\n",
            "source_id": "web-1",
        },
    )
    scheduler.add_job(job)
    handlers = get_default_handlers()
    runner = JobRunner(scheduler, handlers)
    now = datetime(2025, 1, 1, 0, 0, 0)

    results = runner.run_due_jobs(now=now)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.error is None
    assert result.events
    event = result.events[0]
    assert event.event_type == "metric"
    assert event.metric_name == "cpu_usage"
    assert event.metric_value == 0.5
    assert event.source_id == "web-1"
    assert scheduler.get_job("p1").last_run_at == now


def test_job_runner_handles_unknown_job_type():
    scheduler = Scheduler()
    job = AutomationJob(
        id="u1",
        name="unknown job",
        job_type="unknown_type",
        interval_seconds=60,
    )
    scheduler.add_job(job)
    runner = JobRunner(scheduler, handlers={})
    now = datetime(2025, 1, 1, 0, 0, 0)

    results = runner.run_due_jobs(now=now)

    assert len(results) == 1
    result = results[0]
    assert result.success is False
    assert "Unknown job_type" in (result.error or "")
    assert result.events == []


def test_syslog_job_handler_basic():
    scheduler = Scheduler()
    job = AutomationJob(
        id="s1",
        name="syslog ingest",
        job_type="syslog",
        interval_seconds=60,
        last_run_at=None,
        config={
            "syslog_lines": ["Oct 11 22:14:15 myhost app[123]: Error connecting to db"],
        },
    )
    scheduler.add_job(job)
    handlers = get_default_handlers()
    runner = JobRunner(scheduler, handlers)
    now = datetime(2025, 1, 1, 0, 0, 0)

    results = runner.run_due_jobs(now=now)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.error is None
    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "log"
    assert "Error connecting to db" in event.log_message
    assert event.log_level == "ERROR"
    assert event.source_id == "myhost"
