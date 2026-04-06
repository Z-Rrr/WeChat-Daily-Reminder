from __future__ import annotations

from datetime import datetime

import pytest

from app.content import render_template, _extract_json_path, fetch_http_json_message
from app.config import HttpJsonSourceConfig, MessageJob


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------

def _fixed_dt() -> datetime:
    return datetime(2024, 3, 18, 8, 30, 0)  # Monday


def test_render_date():
    assert render_template("今天是 ${date}", _fixed_dt()) == "今天是 2024-03-18"


def test_render_time():
    assert render_template("时间 ${time}", _fixed_dt()) == "时间 08:30"


def test_render_datetime():
    assert render_template("${datetime}", _fixed_dt()) == "2024-03-18 08:30:00"


def test_render_weekday_monday():
    assert render_template("${weekday}", _fixed_dt()) == "星期一"


def test_render_weekday_sunday():
    dt = datetime(2024, 3, 17, 12, 0, 0)  # Sunday
    assert render_template("${weekday}", dt) == "星期日"


def test_render_multiple_placeholders():
    result = render_template("${date} ${weekday} ${time}", _fixed_dt())
    assert result == "2024-03-18 星期一 08:30"


def test_render_no_placeholders():
    assert render_template("早上好", _fixed_dt()) == "早上好"


def test_render_strips_whitespace():
    assert render_template("  hello  ", _fixed_dt()) == "hello"


def test_render_unknown_placeholder_untouched():
    assert render_template("${unknown}", _fixed_dt()) == "${unknown}"


# ---------------------------------------------------------------------------
# _extract_json_path
# ---------------------------------------------------------------------------

def test_extract_top_level_key():
    assert _extract_json_path({"msg": "hello"}, "msg") == "hello"


def test_extract_nested_key():
    payload = {"data": {"message": "world"}}
    assert _extract_json_path(payload, "data.message") == "world"


def test_extract_list_index():
    payload = {"items": ["a", "b", "c"]}
    assert _extract_json_path(payload, "items.1") == "b"


def test_extract_missing_key_returns_none():
    assert _extract_json_path({"a": 1}, "b") is None


def test_extract_missing_nested_key_returns_none():
    assert _extract_json_path({"data": {}}, "data.message") is None


def test_extract_out_of_range_index_returns_none():
    assert _extract_json_path({"items": [1, 2]}, "items.5") is None


def test_extract_non_dict_non_list_returns_none():
    assert _extract_json_path({"val": "string"}, "val.sub") is None


def test_extract_deep_path():
    payload = {"a": {"b": {"c": 42}}}
    assert _extract_json_path(payload, "a.b.c") == 42


# ---------------------------------------------------------------------------
# fetch_http_json_message — fallback behaviour (no real network calls)
# ---------------------------------------------------------------------------

def _make_source(**kwargs) -> HttpJsonSourceConfig:
    defaults = dict(url="https://example.com", method="GET", timeout_seconds=5)
    defaults.update(kwargs)
    return HttpJsonSourceConfig(**defaults)


def test_fetch_uses_fallback_on_url_error():
    source = _make_source(
        url="http://127.0.0.1:1",  # unreachable
        fallback="备用文案",
        timeout_seconds=1,
    )
    result = fetch_http_json_message(source, _fixed_dt())
    assert result == "备用文案"


def test_fetch_raises_without_fallback_on_url_error():
    source = _make_source(url="http://127.0.0.1:1", timeout_seconds=1)
    with pytest.raises(RuntimeError, match="Failed to fetch"):
        fetch_http_json_message(source, _fixed_dt())


# ---------------------------------------------------------------------------
# resolve_job_message
# ---------------------------------------------------------------------------

from app.content import resolve_job_message


def test_resolve_static_message():
    job = MessageJob(
        name="test",
        time="08:00",
        to="好友",
        static_message="早上好 ${date}",
    )
    result = resolve_job_message(job, _fixed_dt())
    assert result == "早上好 2024-03-18"


def test_resolve_missing_source_raises():
    job = MessageJob(name="bad", time="08:00", to="好友")
    with pytest.raises(ValueError, match="does not define a message source"):
        resolve_job_message(job, _fixed_dt())
