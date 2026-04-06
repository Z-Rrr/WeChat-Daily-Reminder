from __future__ import annotations

import json
import pytest
from pathlib import Path

from app.config import load_config, AppConfig, MessageJob, HttpJsonSourceConfig


def _write_config(tmp_path: Path, data: dict) -> Path:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(data), encoding="utf-8")
    return cfg


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_load_static_message(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {"name": "test-job", "time": "08:00", "to": "好友A", "message": "早上好"}
        ]
    })
    app = load_config(cfg)
    assert isinstance(app, AppConfig)
    assert len(app.jobs) == 1
    job = app.jobs[0]
    assert isinstance(job, MessageJob)
    assert job.name == "test-job"
    assert job.time == "08:00"
    assert job.to == "好友A"
    assert job.static_message == "早上好"
    assert job.http_json_source is None
    assert job.enabled is True


def test_load_http_json_source(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {
                "name": "weather",
                "time": "09:00",
                "to": "文件传输助手",
                "message_source": {
                    "type": "http_json",
                    "url": "https://example.com/api",
                    "method": "GET",
                    "timeout_seconds": 5,
                    "json_path": "data.text",
                    "fallback": "接口不可用",
                },
            }
        ]
    })
    app = load_config(cfg)
    job = app.jobs[0]
    assert job.http_json_source is not None
    src = job.http_json_source
    assert isinstance(src, HttpJsonSourceConfig)
    assert src.url == "https://example.com/api"
    assert src.method == "GET"
    assert src.timeout_seconds == 5
    assert src.json_path == "data.text"
    assert src.fallback == "接口不可用"


def test_load_legacy_message_dict_source(tmp_path):
    """The old 'message': {…} dict form is still accepted."""
    cfg = _write_config(tmp_path, {
        "jobs": [
            {
                "name": "legacy",
                "time": "10:00",
                "to": "好友",
                "message": {
                    "type": "http_json",
                    "url": "https://example.com",
                },
            }
        ]
    })
    app = load_config(cfg)
    assert app.jobs[0].http_json_source is not None


def test_disabled_job(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {"name": "off", "time": "07:00", "to": "好友", "message": "hi", "enabled": False}
        ]
    })
    app = load_config(cfg)
    assert app.jobs[0].enabled is False


def test_default_timezone(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "08:00", "to": "好友", "message": "hi"}]
    })
    app = load_config(cfg)
    assert app.timezone == "Asia/Shanghai"


def test_custom_timezone(tmp_path):
    cfg = _write_config(tmp_path, {
        "timezone": "America/New_York",
        "jobs": [{"name": "j", "time": "08:00", "to": "好友", "message": "hi"}]
    })
    app = load_config(cfg)
    assert app.timezone == "America/New_York"


def test_http_method_uppercased(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {
                "name": "m",
                "time": "08:00",
                "to": "好友",
                "message_source": {"type": "http_json", "url": "https://x.com", "method": "get"},
            }
        ]
    })
    app = load_config(cfg)
    assert app.jobs[0].http_json_source.method == "GET"


def test_multiple_jobs(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {"name": "a", "time": "08:00", "to": "A", "message": "hi"},
            {"name": "b", "time": "12:00", "to": "B", "message": "hello"},
        ]
    })
    app = load_config(cfg)
    assert len(app.jobs) == 2
    assert app.jobs[0].name == "a"
    assert app.jobs[1].name == "b"


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------

def test_missing_config_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.json")


def test_missing_jobs_key(tmp_path):
    cfg = _write_config(tmp_path, {"timezone": "Asia/Shanghai"})
    with pytest.raises(ValueError, match="'jobs'"):
        load_config(cfg)


def test_empty_jobs_list(tmp_path):
    cfg = _write_config(tmp_path, {"jobs": []})
    with pytest.raises(ValueError, match="no jobs"):
        load_config(cfg)


def test_invalid_time_format(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "8:00", "to": "好友", "message": "hi"}]
    })
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(cfg)


def test_invalid_time_hour(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "25:00", "to": "好友", "message": "hi"}]
    })
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(cfg)


def test_missing_name(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"time": "08:00", "to": "好友", "message": "hi"}]
    })
    with pytest.raises(ValueError, match="name"):
        load_config(cfg)


def test_missing_to(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "08:00", "message": "hi"}]
    })
    with pytest.raises(ValueError, match="to"):
        load_config(cfg)


def test_missing_message_source(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "08:00", "to": "好友"}]
    })
    with pytest.raises(ValueError, match="message"):
        load_config(cfg)


def test_invalid_enabled_type(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [{"name": "j", "time": "08:00", "to": "好友", "message": "hi", "enabled": "yes"}]
    })
    with pytest.raises(ValueError, match="enabled"):
        load_config(cfg)


def test_invalid_timeout_zero(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {
                "name": "j",
                "time": "08:00",
                "to": "好友",
                "message_source": {
                    "type": "http_json",
                    "url": "https://x.com",
                    "timeout_seconds": 0,
                },
            }
        ]
    })
    with pytest.raises(ValueError, match="timeout_seconds"):
        load_config(cfg)


def test_unknown_source_type(tmp_path):
    cfg = _write_config(tmp_path, {
        "jobs": [
            {
                "name": "j",
                "time": "08:00",
                "to": "好友",
                "message_source": {"type": "graphql", "url": "https://x.com"},
            }
        ]
    })
    with pytest.raises(ValueError, match="http_json"):
        load_config(cfg)


def test_invalid_timezone(tmp_path):
    cfg = _write_config(tmp_path, {
        "timezone": "",
        "jobs": [{"name": "j", "time": "08:00", "to": "好友", "message": "hi"}]
    })
    with pytest.raises(ValueError, match="timezone"):
        load_config(cfg)
