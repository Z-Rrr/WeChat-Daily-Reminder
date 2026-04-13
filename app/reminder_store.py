from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Reminder:
    id: int
    send_date: str
    send_time: str
    recipient: str
    content: str
    enabled: bool
    sent_at: str | None
    created_at: str


class ReminderStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    send_date TEXT NOT NULL,
                    send_time TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sent_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_schedule
                ON reminders (send_date, send_time, enabled, sent_at)
                """
            )

    def list_reminders(self) -> list[Reminder]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, send_date, send_time, recipient, content, enabled, sent_at, created_at
                FROM reminders
                ORDER BY send_date ASC, send_time ASC, id ASC
                """
            ).fetchall()

        return [
            Reminder(
                id=row["id"],
                send_date=row["send_date"],
                send_time=row["send_time"],
                recipient=row["recipient"],
                content=row["content"],
                enabled=bool(row["enabled"]),
                sent_at=row["sent_at"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_reminder(self, send_date: str, send_time: str, recipient: str, content: str) -> int:
        created_at = datetime.utcnow().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO reminders (send_date, send_time, recipient, content, enabled, sent_at, created_at)
                VALUES (?, ?, ?, ?, 1, NULL, ?)
                """,
                (send_date, send_time, recipient, content, created_at),
            )
            return int(cur.lastrowid)

    def delete_reminder(self, reminder_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    def set_enabled(self, reminder_id: int, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE reminders SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, reminder_id),
            )

    def mark_sent(self, reminder_id: int) -> None:
        sent_at = datetime.utcnow().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE reminders SET sent_at = ? WHERE id = ?",
                (sent_at, reminder_id),
            )

    def reset_sent(self, reminder_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE reminders SET sent_at = NULL WHERE id = ?", (reminder_id,))

    def due_reminders(self, send_date: str, send_time: str) -> list[Reminder]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, send_date, send_time, recipient, content, enabled, sent_at, created_at
                FROM reminders
                WHERE send_date = ?
                  AND send_time = ?
                  AND enabled = 1
                  AND sent_at IS NULL
                ORDER BY id ASC
                """,
                (send_date, send_time),
            ).fetchall()

        return [
            Reminder(
                id=row["id"],
                send_date=row["send_date"],
                send_time=row["send_time"],
                recipient=row["recipient"],
                content=row["content"],
                enabled=bool(row["enabled"]),
                sent_at=row["sent_at"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
