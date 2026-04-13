from __future__ import annotations

from datetime import date

import pytest

from app.plan import parse_markdown_plan


def test_parse_markdown_plan_for_target_date():
    markdown = """## 2026-04-14

- 08:30 | 文件传输助手 | 早上好
  今天先处理最重要的事情。
- 12:20 | 文件传输助手 | 午安

## 2026-04-15

- 08:30 | 文件传输助手 | 明天的内容
"""

    jobs = parse_markdown_plan(markdown, date(2026, 4, 14))

    assert len(jobs) == 2
    assert jobs[0].time == "08:30"
    assert jobs[0].to == "文件传输助手"
    assert jobs[0].static_message == "早上好\n今天先处理最重要的事情。"
    assert jobs[1].static_message == "午安"


def test_parse_markdown_plan_without_heading():
    markdown = """- 08:30 | 文件传输助手 | 早上好
- 12:20 | 文件传输助手 | 午安
"""

    jobs = parse_markdown_plan(markdown, date(2026, 4, 14))

    assert len(jobs) == 2


def test_parse_markdown_plan_requires_message():
    markdown = """## 2026-04-14

- 08:30 | 文件传输助手 |
"""

    with pytest.raises(ValueError, match="missing message text"):
        parse_markdown_plan(markdown, date(2026, 4, 14))