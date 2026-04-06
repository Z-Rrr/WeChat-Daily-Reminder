from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import AppConfig, MessageJob
from app.content import resolve_job_message


def create_scheduler(
    config: AppConfig,
    send_func: Callable[[str, str], None],
) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=config.timezone)

    for job in config.jobs:
        if not job.enabled:
            continue
        hour, minute = _parse_hhmm(job.time)
        scheduler.add_job(
            func=_run_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            args=[job, send_func],
            id=job.name,
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
        )

    return scheduler


def _run_job(job: MessageJob, send_func: Callable[[str, str], None]) -> None:
    logger = logging.getLogger(__name__)
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("job_start name=%s to=%s at=%s", job.name, job.to, started_at)

    try:
        content = resolve_job_message(job)
        send_func(job.to, content)
    except Exception:
        logger.exception("job_error name=%s to=%s", job.name, job.to)
        return

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("job_success name=%s to=%s at=%s", job.name, job.to, finished_at)


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)
