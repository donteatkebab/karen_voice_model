from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from bot.models import ApprovedGroup, StoredMessage


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self.init_schema()

    @contextmanager
    def cursor(self):
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cur.close()

    def init_schema(self) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS approved_groups (
                    group_id INTEGER PRIMARY KEY,
                    group_title TEXT NOT NULL,
                    approved_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_group_created
                ON messages(group_id, created_at)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_activity (
                    group_id INTEGER PRIMARY KEY,
                    last_voice_at TEXT NOT NULL
                )
                """
            )

    def approve_group(self, group_id: int, group_title: str, approved_at: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO approved_groups (group_id, group_title, approved_at)
                VALUES (?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    group_title = excluded.group_title,
                    approved_at = excluded.approved_at
                """,
                (group_id, group_title, approved_at),
            )

    def is_group_approved(self, group_id: int) -> bool:
        with self.cursor() as cur:
            row = cur.execute(
                "SELECT 1 FROM approved_groups WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            return row is not None

    def list_approved_groups(self) -> list[ApprovedGroup]:
        with self.cursor() as cur:
            rows = cur.execute(
                "SELECT group_id, group_title, approved_at FROM approved_groups ORDER BY approved_at ASC"
            ).fetchall()
            return [ApprovedGroup(**dict(row)) for row in rows]

    def add_message(
        self,
        *,
        group_id: int,
        telegram_message_id: int,
        user_id: int,
        username: str,
        text: str,
        created_at: str,
        history_limit: int,
    ) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (
                    group_id, telegram_message_id, user_id, username, text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, telegram_message_id, user_id, username, text, created_at),
            )
            cur.execute(
                """
                DELETE FROM messages
                WHERE group_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM messages
                      WHERE group_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
                """,
                (group_id, group_id, history_limit),
            )

    def count_messages(self, group_id: int) -> int:
        with self.cursor() as cur:
            row = cur.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            return int(row["count"]) if row else 0

    def count_messages_since(self, group_id: int, since_iso: str) -> int:
        with self.cursor() as cur:
            row = cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM messages
                WHERE group_id = ? AND created_at >= ?
                """,
                (group_id, since_iso),
            ).fetchone()
            return int(row["count"]) if row else 0

    def get_recent_messages(self, group_id: int, limit: int = 50) -> list[StoredMessage]:
        with self.cursor() as cur:
            rows = cur.execute(
                """
                SELECT id, group_id, telegram_message_id, user_id, username, text, created_at
                FROM messages
                WHERE group_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (group_id, limit),
            ).fetchall()
            messages = [StoredMessage(**dict(row)) for row in rows]
            return list(reversed(messages))

    def get_recent_message(self, group_id: int, limit: int = 50) -> StoredMessage | None:
        messages = self.get_recent_messages(group_id, limit=limit)
        if not messages:
            return None
        return messages[-1]

    def get_message_by_telegram_id(
        self, group_id: int, telegram_message_id: int
    ) -> StoredMessage | None:
        with self.cursor() as cur:
            row = cur.execute(
                """
                SELECT id, group_id, telegram_message_id, user_id, username, text, created_at
                FROM messages
                WHERE group_id = ? AND telegram_message_id = ?
                LIMIT 1
                """,
                (group_id, telegram_message_id),
            ).fetchone()
            return StoredMessage(**dict(row)) if row else None

    def get_last_voice_at(self, group_id: int) -> str | None:
        with self.cursor() as cur:
            row = cur.execute(
                "SELECT last_voice_at FROM bot_activity WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            return str(row["last_voice_at"]) if row else None

    def set_last_voice_at(self, group_id: int, last_voice_at: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bot_activity (group_id, last_voice_at)
                VALUES (?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    last_voice_at = excluded.last_voice_at
                """,
                (group_id, last_voice_at),
            )
