"""
Callables the scheduler invokes. Kept separate from scheduler.py so job
logic (what happens when a reminder fires) is easy to find and test
independently of APScheduler wiring.
"""
from __future__ import annotations

from typing import Callable

from utils.logger import get_logger

logger = get_logger("scheduler.jobs")


def make_reminder_job(message: str, speak: Callable[[str], None]) -> Callable[[], None]:
    def _job() -> None:
        logger.info("Reminder fired: %s", message)
        speak(f"Reminder: {message}")
    return _job


def make_routine_job(routine_name: str, run_routine: Callable[[str], None]) -> Callable[[], None]:
    def _job() -> None:
        logger.info("Routine '%s' triggered by schedule.", routine_name)
        run_routine(routine_name)
    return _job
