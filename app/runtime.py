from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.content import resolve_job_message
from app.config import load_config
from app.sender import WeChatSender


def run(
    config_path: Path,
    once_job_name: str | None = None,
    preview_job_name: str | None = None,
) -> None:
    config = load_config(config_path)
    _setup_logging(config_path.parent)

    if preview_job_name is not None:
        job = _find_job_by_name(config.jobs, preview_job_name)
        message = resolve_job_message(job)
        print(message)
        return

    if once_job_name is not None:
        job = _find_job_by_name(config.jobs, once_job_name)

        logger = logging.getLogger(__name__)
        sender = WeChatSender()
        logger.info("manual_run name=%s to=%s", job.name, job.to)
        sender.send(job.to, resolve_job_message(job))
        logger.info("manual_run_success name=%s to=%s", job.name, job.to)
        return

    sender = WeChatSender()
    from app.scheduler import create_scheduler

    scheduler = create_scheduler(config, sender.send)
    jobs = scheduler.get_jobs()
    if not jobs:
        raise RuntimeError("No enabled jobs found in config.")

    logger = logging.getLogger(__name__)
    logger.info("scheduler_started jobs=%s", len(jobs))
    for job in jobs:
        logger.info("registered_job id=%s next_run=%s", job.id, job.next_run_time)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler_stopping")
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")


def _find_job_by_name(jobs: list, job_name: str):
    job = next((item for item in jobs if item.name == job_name), None)
    if job is None:
        raise ValueError(f"Job not found: {job_name}")
    return job


def _setup_logging(project_root: Path) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
