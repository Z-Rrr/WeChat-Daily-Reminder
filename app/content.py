from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, request

from app.config import HttpJsonSourceConfig, MessageJob


WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def resolve_job_message(job: MessageJob, now: datetime | None = None) -> str:
    current_time = now or datetime.now()

    if job.http_json_source is not None:
        return fetch_http_json_message(job.http_json_source, current_time)

    if job.static_message is None:
        raise ValueError(f"Job '{job.name}' does not define a message source.")

    return render_template(job.static_message, current_time)


def fetch_http_json_message(
    source: HttpJsonSourceConfig,
    now: datetime | None = None,
) -> str:
    current_time = now or datetime.now()
    req = request.Request(source.url, method=source.method, headers=source.headers)

    try:
        with request.urlopen(req, timeout=source.timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
    except error.URLError as exc:
        if source.fallback is not None:
            return render_template(source.fallback, current_time)
        raise RuntimeError(f"Failed to fetch message source: {exc}") from exc

    if not body:
        if source.fallback is not None:
            return render_template(source.fallback, current_time)
        raise ValueError("HTTP message source returned an empty response.")

    if source.json_path:
        try:
            payload = json.loads(body)
            value = _extract_json_path(payload, source.json_path)
        except Exception as exc:
            if source.fallback is not None:
                return render_template(source.fallback, current_time)
            raise RuntimeError(
                f"Failed to parse message source JSON path '{source.json_path}': {exc}"
            ) from exc

        if value is None:
            if source.fallback is not None:
                return render_template(source.fallback, current_time)
            raise ValueError(
                f"JSON path '{source.json_path}' did not resolve to a message value."
            )

        return render_template(str(value), current_time)

    return render_template(body, current_time)


def render_template(template: str, now: datetime | None = None) -> str:
    current_time = now or datetime.now()
    replacements = {
        "${date}": current_time.strftime("%Y-%m-%d"),
        "${datetime}": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "${time}": current_time.strftime("%H:%M"),
        "${weekday}": WEEKDAY_NAMES[current_time.weekday()],
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result.strip()


def _extract_json_path(payload: Any, json_path: str) -> Any:
    current: Any = payload
    for part in json_path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
            continue

        if isinstance(current, list):
            if not part.isdigit():
                return None
            index = int(part)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue

        return None

    return current