from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.automation.scheduler import AutomationJob, Scheduler

JobHandler = Callable[[AutomationJob, datetime], List[HCaiEvent]]


@dataclass
class JobRunResult:
    job_id: str
    success: bool
    error: Optional[str] = None
    events: List[HCaiEvent] = None


class JobRunner:
    """
    Executes due jobs using registered job handlers and updates scheduler state.
    """

    def __init__(self, scheduler: Scheduler, handlers: Dict[str, JobHandler]) -> None:
        self.scheduler = scheduler
        self.handlers = handlers

    def run_due_jobs(self, now: Optional[datetime] = None) -> List[JobRunResult]:
        current_time = now or datetime.now(UTC)
        results: List[JobRunResult] = []

        for job in self.scheduler.due_jobs(current_time):
            handler = self.handlers.get(job.job_type)
            if handler is None:
                results.append(
                    JobRunResult(
                        job_id=job.id,
                        success=False,
                        error=f"Unknown job_type: {job.job_type}",
                        events=[],
                    )
                )
                continue

            try:
                events = handler(job, current_time) or []
                try:
                    from hcai_ops.analytics import event_store
                except Exception:
                    event_store = None
                if event_store is not None:
                    event_store.add_events(events)
                self.scheduler.mark_run(job.id, current_time)
                results.append(JobRunResult(job_id=job.id, success=True, error=None, events=events))
            except Exception as exc:  # pragma: no cover - defensive guard
                results.append(JobRunResult(job_id=job.id, success=False, error=str(exc), events=[]))

        return results
