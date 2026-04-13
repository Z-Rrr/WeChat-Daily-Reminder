from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.plan import load_markdown_plan_jobs


TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class HttpJsonSourceConfig:
    url: str
    method: str = "GET"
    timeout_seconds: int = 10
    headers: dict[str, str] = field(default_factory=dict)
    json_path: str | None = None
    fallback: str | None = None


@dataclass(frozen=True)
class MessageJob:
    name: str
    time: str
    to: str
    enabled: bool = True
    static_message: str | None = None
    http_json_source: HttpJsonSourceConfig | None = None


@dataclass(frozen=True)
class AppConfig:
    jobs: list[MessageJob]
    timezone: str = "Asia/Shanghai"


@dataclass(frozen=True)
class DailyPlanConfig:
    path: str
    target_date_offset_days: int = 1


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))

    timezone = raw.get("timezone", "Asia/Shanghai")
    if not isinstance(timezone, str) or not timezone.strip():
        raise ValueError("Config 'timezone' must be a non-empty string.")

    jobs: list[MessageJob] = []

    if "jobs" in raw:
        if not isinstance(raw["jobs"], list):
            raise ValueError("Config 'jobs' must be an array when present.")

        for idx, item in enumerate(raw["jobs"]):
            if not isinstance(item, dict):
                raise ValueError(f"jobs[{idx}] must be an object.")

            name = _required_str(item, "name", idx)
            time = _required_str(item, "time", idx)
            to = _required_str(item, "to", idx)
            enabled = item.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"jobs[{idx}].enabled must be boolean.")

            static_message: str | None = None
            http_json_source: HttpJsonSourceConfig | None = None

            if isinstance(item.get("message_source"), dict):
                http_json_source = _parse_http_json_source(item["message_source"], idx)
            elif isinstance(item.get("message"), dict):
                http_json_source = _parse_http_json_source(item["message"], idx)
            elif isinstance(item.get("message"), str):
                static_message = _required_str(item, "message", idx)
            else:
                raise ValueError(
                    f"jobs[{idx}] must define either a string 'message' or a 'message_source' object."
                )

            if TIME_RE.match(time) is None:
                raise ValueError(
                    f"jobs[{idx}].time must match HH:MM in 24-hour format, got '{time}'."
                )

            jobs.append(
                MessageJob(
                    name=name,
                    time=time,
                    to=to,
                    enabled=enabled,
                    static_message=static_message,
                    http_json_source=http_json_source,
                )
            )

    daily_plan = raw.get("daily_plan")
    if daily_plan is not None:
        plan_config = _parse_daily_plan_config(daily_plan)
        jobs.extend(
            load_markdown_plan_jobs(
                config_path.parent / plan_config.path,
                timezone.strip(),
                plan_config.target_date_offset_days,
            )
        )

    if not jobs:
        raise ValueError("Config has no jobs. Add at least one scheduled job or daily_plan.")

    return AppConfig(jobs=jobs, timezone=timezone.strip())


def _required_str(item: dict, key: str, idx: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"jobs[{idx}].{key} must be a non-empty string.")
    return value.strip()


def _parse_http_json_source(raw: Any, idx: int) -> HttpJsonSourceConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"jobs[{idx}].message_source must be an object.")

    source_type = raw.get("type", "http_json")
    if source_type != "http_json":
        raise ValueError(f"jobs[{idx}].message_source.type must be 'http_json'.")

    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"jobs[{idx}].message_source.url must be a non-empty string.")

    method = raw.get("method", "GET")
    if not isinstance(method, str) or not method.strip():
        raise ValueError(f"jobs[{idx}].message_source.method must be a non-empty string.")

    timeout_seconds = raw.get("timeout_seconds", 10)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ValueError(
            f"jobs[{idx}].message_source.timeout_seconds must be a positive integer."
        )

    headers = raw.get("headers", {})
    if not isinstance(headers, dict):
        raise ValueError(f"jobs[{idx}].message_source.headers must be an object.")

    normalized_headers: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(
                f"jobs[{idx}].message_source.headers must map strings to strings."
            )
        normalized_headers[key] = value

    json_path = raw.get("json_path")
    if json_path is not None and (not isinstance(json_path, str) or not json_path.strip()):
        raise ValueError(f"jobs[{idx}].message_source.json_path must be a non-empty string.")

    fallback = raw.get("fallback")
    if fallback is not None and (not isinstance(fallback, str) or not fallback.strip()):
        raise ValueError(f"jobs[{idx}].message_source.fallback must be a non-empty string.")

    return HttpJsonSourceConfig(
        url=url.strip(),
        method=method.strip().upper(),
        timeout_seconds=timeout_seconds,
        headers=normalized_headers,
        json_path=json_path.strip() if isinstance(json_path, str) else None,
        fallback=fallback.strip() if isinstance(fallback, str) else None,
    )


def _parse_daily_plan_config(raw: Any) -> DailyPlanConfig:
    if not isinstance(raw, dict):
        raise ValueError("Config 'daily_plan' must be an object.")

    path = raw.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Config 'daily_plan.path' must be a non-empty string.")

    target_date_offset_days = raw.get("target_date_offset_days", 1)
    if not isinstance(target_date_offset_days, int) or target_date_offset_days < 0:
        raise ValueError(
            "Config 'daily_plan.target_date_offset_days' must be a zero or positive integer."
        )

    return DailyPlanConfig(
        path=path.strip(),
        target_date_offset_days=target_date_offset_days,
    )
