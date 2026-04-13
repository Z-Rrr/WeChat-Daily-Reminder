from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, render_template_string, request

from app.bot_sender import WebhookBotConfig, WebhookBotSender
from app.reminder_store import ReminderStore


PAGE_HTML = """
<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>WeChat Daily Reminder</title>
  <style>
    body { font-family: -apple-system, Segoe UI, sans-serif; margin: 24px; background: #f6f7fb; color: #1f2937; }
    .card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 6px 24px rgba(0,0,0,.08); margin-bottom: 16px; }
    input, textarea { width: 100%; padding: 10px; margin: 6px 0 10px; border: 1px solid #d1d5db; border-radius: 8px; box-sizing: border-box; }
    button { border: 0; border-radius: 8px; padding: 8px 12px; cursor: pointer; background: #0f766e; color: #fff; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; border-bottom: 1px solid #e5e7eb; padding: 10px 8px; vertical-align: top; }
    .muted { color: #6b7280; font-size: 12px; }
    .row-actions form { display: inline; margin-right: 6px; }
    .danger { background: #b91c1c; }
    .secondary { background: #374151; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h2>新增提醒</h2>
    <form method=\"post\" action=\"/tasks\">
      <label>日期 (YYYY-MM-DD)</label>
      <input name=\"send_date\" placeholder=\"2026-04-14\" required />

      <label>时间 (HH:MM)</label>
      <input name=\"send_time\" placeholder=\"08:30\" required />

      <label>发送对象</label>
      <input name=\"recipient\" placeholder=\"文件传输助手\" required />

      <label>消息内容</label>
      <textarea name=\"content\" rows=\"4\" required></textarea>

      <button type=\"submit\">保存提醒</button>
    </form>
    <p class=\"muted\">当前时区: {{ timezone }}</p>
  </div>

  <div class=\"card\">
    <h2>提醒列表</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>计划</th>
          <th>对象</th>
          <th>内容</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
      {% for item in reminders %}
        <tr>
          <td>{{ item.id }}</td>
          <td>{{ item.send_date }} {{ item.send_time }}</td>
          <td>{{ item.recipient }}</td>
          <td>{{ item.content }}</td>
          <td>
            {% if item.enabled %}启用{% else %}停用{% endif %}<br/>
            <span class=\"muted\">发送时间: {{ item.sent_at or '未发送' }}</span>
          </td>
          <td class=\"row-actions\">
            <form method=\"post\" action=\"/tasks/{{ item.id }}/toggle\">
              <button class=\"secondary\" type=\"submit\">{% if item.enabled %}禁用{% else %}启用{% endif %}</button>
            </form>
            <form method=\"post\" action=\"/tasks/{{ item.id }}/reset\">
              <button class=\"secondary\" type=\"submit\">重置已发送</button>
            </form>
            <form method=\"post\" action=\"/tasks/{{ item.id }}/send-now\">
              <button type=\"submit\">立即发送</button>
            </form>
            <form method=\"post\" action=\"/tasks/{{ item.id }}/delete\">
              <button class=\"danger\" type=\"submit\">删除</button>
            </form>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _validate_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def _validate_time(value: str) -> str:
    datetime.strptime(value, "%H:%M")
    return value


def create_app(
    db_path: Path,
    timezone_name: str,
    bot_webhook_url: str,
    bot_api_key: str | None,
    bot_timeout_seconds: int,
) -> Flask:
    app = Flask(__name__)
    logger = logging.getLogger("web")

    store = ReminderStore(db_path)
    sender = WebhookBotSender(
        WebhookBotConfig(
            webhook_url=bot_webhook_url,
            api_key=bot_api_key,
            timeout_seconds=bot_timeout_seconds,
        )
    )
    tz = ZoneInfo(timezone_name)

    scheduler = BackgroundScheduler(timezone=timezone_name)

    def run_due_jobs() -> None:
        now = datetime.now(tz)
        send_date = now.strftime("%Y-%m-%d")
        send_time = now.strftime("%H:%M")
        due = store.due_reminders(send_date=send_date, send_time=send_time)

        if not due:
            return

        logger.info("due_jobs date=%s time=%s count=%s", send_date, send_time, len(due))
        for item in due:
            try:
                sender.send(item.recipient, item.content)
                store.mark_sent(item.id)
                logger.info("job_sent id=%s recipient=%s", item.id, item.recipient)
            except Exception:
                logger.exception("job_send_failed id=%s recipient=%s", item.id, item.recipient)

    scheduler.add_job(run_due_jobs, trigger="cron", second="0")
    scheduler.start()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/", methods=["GET"])
    def index():
        reminders = store.list_reminders()
        return render_template_string(PAGE_HTML, reminders=reminders, timezone=timezone_name)

    @app.route("/tasks", methods=["POST"])
    def create_task():
        send_date = _validate_date(request.form.get("send_date", "").strip())
        send_time = _validate_time(request.form.get("send_time", "").strip())
        recipient = request.form.get("recipient", "").strip()
        content = request.form.get("content", "").strip()

        if not recipient or not content:
            return ("recipient/content required", 400)

        store.create_reminder(
            send_date=send_date,
            send_time=send_time,
            recipient=recipient,
            content=content,
        )
        return redirect("/")

    @app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
    def toggle_task(task_id: int):
        tasks = {item.id: item for item in store.list_reminders()}
        if task_id not in tasks:
            return ("not found", 404)
        store.set_enabled(task_id, not tasks[task_id].enabled)
        return redirect("/")

    @app.route("/tasks/<int:task_id>/reset", methods=["POST"])
    def reset_task(task_id: int):
        store.reset_sent(task_id)
        return redirect("/")

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task(task_id: int):
        store.delete_reminder(task_id)
        return redirect("/")

    @app.route("/tasks/<int:task_id>/send-now", methods=["POST"])
    def send_now(task_id: int):
        tasks = {item.id: item for item in store.list_reminders()}
        if task_id not in tasks:
            return ("not found", 404)

        item = tasks[task_id]
        sender.send(item.recipient, item.content)
        store.mark_sent(task_id)
        return redirect("/")

    @app.teardown_appcontext
    def _shutdown_scheduler(_exc: Exception | None) -> None:
        # Keep scheduler lifecycle bound to process; avoid duplicate shutdown calls.
        pass

    return app


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run web portal + DB + scheduler")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db-path", default="data/reminders.db")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--bot-webhook-url", required=True)
    parser.add_argument("--bot-api-key", default=None)
    parser.add_argument("--bot-timeout-seconds", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    _setup_logging()
    args = _parse_args()

    app = create_app(
        db_path=Path(args.db_path).resolve(),
        timezone_name=args.timezone,
        bot_webhook_url=args.bot_webhook_url,
        bot_api_key=args.bot_api_key,
        bot_timeout_seconds=args.bot_timeout_seconds,
    )

    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
