from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


@dataclass
class AutomationJob:
    """
    Represents a recurring automation task.
    """

    id: str
    name: str
    job_type: str
    interval_seconds: int
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run_at: Optional[datetime] = None


class Scheduler:
    """
    In memory scheduler that tracks jobs and decides which ones are due.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, AutomationJob] = {}

    def add_job(self, job: AutomationJob) -> None:
        """Add or overwrite a job by id."""
        self._jobs[job.id] = job

    def get_job(self, job_id: str) -> Optional[AutomationJob]:
        """Return a job by id if present."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[AutomationJob]:
        """Return all registered jobs."""
        return list(self._jobs.values())

    def due_jobs(self, now: Optional[datetime] = None) -> List[AutomationJob]:
        """Return jobs that are due to run at the provided time."""
        current_time = now or datetime.now(UTC)
        due: List[AutomationJob] = []
        for job in self._jobs.values():
            if not job.enabled:
                continue
            if job.last_run_at is None:
                due.append(job)
                continue
            elapsed = (current_time - job.last_run_at).total_seconds()
            if elapsed >= job.interval_seconds:
                due.append(job)
        return due

    def mark_run(self, job_id: str, ran_at: Optional[datetime] = None) -> None:
        """Mark a job as having run at the provided time."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        job.last_run_at = ran_at or datetime.now(UTC)
