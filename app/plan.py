from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


DATE_HEADING_RE = re.compile(r"^#{1,6}\s*(\d{4}-\d{2}-\d{2})\s*$")
ENTRY_RE = re.compile(r"^\s*[-*+]\s*(\d{2}:\d{2})\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*$")
CONTINUATION_RE = re.compile(r"^\s{2,}(.*\S.*)\s*$")


def load_markdown_plan_jobs(
    plan_path: Path,
    timezone_name: str,
    target_date_offset_days: int = 1,
):
    from app.config import MessageJob

    if not plan_path.exists():
        raise FileNotFoundError(f"Daily plan file not found: {plan_path}")

    target_date = _target_date(timezone_name, target_date_offset_days)
    text = plan_path.read_text(encoding="utf-8")
    jobs = parse_markdown_plan(text, target_date)

    if not jobs:
        raise ValueError(
            f"No markdown plan entries found for {target_date.isoformat()} in {plan_path}."
        )

    return [
        MessageJob(
            name=job.name,
            time=job.time,
            to=job.to,
            enabled=job.enabled,
            static_message=job.static_message,
            http_json_source=job.http_json_source,
        )
        for job in jobs
    ]


def parse_markdown_plan(markdown: str, target_date: date):
    from app.config import MessageJob

    lines = markdown.splitlines()
    jobs: list[MessageJob] = []

    active_section: date | None = None
    current_time: str | None = None
    current_to: str | None = None
    current_message_lines: list[str] = []
    section_has_heading = False

    def flush_entry() -> None:
        nonlocal current_time, current_to, current_message_lines
        if current_time is None or current_to is None:
            return

        message = "\n".join(current_message_lines).strip()
        if not message:
            raise ValueError(
                f"Markdown plan entry at {current_time} for {current_to} is missing message text."
            )

        jobs.append(
            MessageJob(
                name=_build_job_name(target_date, current_time, current_to, len(jobs) + 1),
                time=current_time,
                to=current_to,
                static_message=message,
            )
        )
        current_time = None
        current_to = None
        current_message_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()

        if not line.strip():
            if current_time is not None:
                current_message_lines.append("")
            continue

        heading_match = DATE_HEADING_RE.match(line.strip())
        if heading_match:
            flush_entry()
            active_section = datetime.strptime(heading_match.group(1), "%Y-%m-%d").date()
            section_has_heading = True
            continue

        entry_match = ENTRY_RE.match(line)
        if entry_match:
            if section_has_heading and active_section != target_date:
                flush_entry()
                continue

            flush_entry()
            current_time = entry_match.group(1)
            current_to = entry_match.group(2).strip()
            current_message_lines = [entry_match.group(3).strip()]
            continue

        continuation_match = CONTINUATION_RE.match(line)
        if continuation_match and current_time is not None:
            current_message_lines.append(continuation_match.group(1))
            continue

        flush_entry()

    flush_entry()

    return jobs


def _target_date(timezone_name: str, target_date_offset_days: int) -> date:
    if target_date_offset_days < 0:
        raise ValueError("target_date_offset_days must be zero or positive.")

    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception as exc:  # pragma: no cover - depends on local tz database
        raise ValueError(f"Invalid timezone for daily plan: {timezone_name}") from exc

    return (now + timedelta(days=target_date_offset_days)).date()


def _build_job_name(target_date: date, time_value: str, recipient: str, index: int) -> str:
    recipient_slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", recipient).strip("-")
    if not recipient_slug:
        recipient_slug = "recipient"
    return f"plan-{target_date.isoformat()}-{time_value.replace(':', '')}-{recipient_slug}-{index}"