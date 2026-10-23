"""
Persistent job scheduling using APScheduler with a SQLite job store, so
reminders/routines survive an application restart — unlike an in-memory
`threading.Timer` approach, which was the simplest alternative but doesn't
meet the "survives application restart" requirement.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable, Optional

from utils.exceptions import JobNotFoundError, SchedulerError
from utils.logger import get_logger

logger = get_logger("scheduler")


class Scheduler:
    def __init__(self, db_path: str):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        except ImportError as exc:
            raise SchedulerError("The 'apscheduler' package is not installed.") from exc

        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}")}
        self._scheduler = BackgroundScheduler(jobstores=jobstores)
        self._started = False

    def start(self) -> None:
        if not self._started:
            self._scheduler.start()
            self._started = True
            logger.info("Scheduler started.")

    def shutdown(self) -> None:
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    def add_one_off(self, run_at: datetime, func: Callable, job_id: Optional[str] = None) -> str:
        job_id = job_id or str(uuid.uuid4())
        self._scheduler.add_job(func, trigger="date", run_date=run_at, id=job_id, replace_existing=True)
        logger.info("Scheduled one-off job %s for %s.", job_id, run_at)
        return job_id

    def add_cron(self, cron_kwargs: dict, func: Callable, job_id: Optional[str] = None) -> str:
        """cron_kwargs example: {'hour': 19, 'minute': 0} for daily 7 PM,
        or {'day_of_week': 'mon', 'hour': 9} for every Monday at 9 AM."""
        job_id = job_id or str(uuid.uuid4())
        self._scheduler.add_job(func, trigger="cron", id=job_id, replace_existing=True, **cron_kwargs)
        logger.info("Scheduled recurring job %s with %s.", job_id, cron_kwargs)
        return job_id

    def cancel(self, job_id: str) -> None:
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"No scheduled job with id '{job_id}'.")
        self._scheduler.remove_job(job_id)
        logger.info("Cancelled job %s.", job_id)

    def list_jobs(self) -> list[dict]:
        return [
            {"id": j.id, "next_run": str(j.next_run_time), "func": j.func.__name__}
            for j in self._scheduler.get_jobs()
        ]
