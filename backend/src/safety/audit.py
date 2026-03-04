"""Audit logger — records every agent action to SQLite for accountability.

Each action taken by the agent is logged with metadata including whether it
was flagged as destructive, whether the user confirmed it, and the model used.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from src.utils.logging import get_logger

logger = get_logger(__name__)

_CREATE_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    action_type     TEXT,
    target_element  TEXT,
    url             TEXT,
    was_destructive INTEGER NOT NULL DEFAULT 0,
    user_confirmed  INTEGER,
    was_blocked     INTEGER NOT NULL DEFAULT 0,
    model_used      TEXT,
    reasoning       TEXT
);
"""

_CREATE_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_log(task_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);",
]


class AuditLogger:
    """Logs every agent action to an SQLite audit_log table."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open DB and create audit_log table if needed."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute(_CREATE_AUDIT_LOG)
        for sql in _CREATE_AUDIT_INDEXES:
            await self._db.execute(sql)
        await self._db.commit()
        logger.info("audit_logger_initialized", db_path=self._db_path)

    async def close(self) -> None:
        """Close the DB connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "AuditLogger not initialized"
        return self._db

    async def log_action(
        self,
        task_id: str,
        action_type: str | None = None,
        target_element: str | None = None,
        url: str | None = None,
        was_destructive: bool = False,
        user_confirmed: bool | None = None,
        was_blocked: bool = False,
        model_used: str | None = None,
        reasoning: str | None = None,
    ) -> str:
        """Record an action in the audit log.  Returns the generated audit ID."""
        audit_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            """
            INSERT INTO audit_log
                (id, task_id, timestamp, action_type, target_element, url,
                 was_destructive, user_confirmed, was_blocked, model_used, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                task_id,
                now,
                action_type,
                target_element[:500] if target_element else None,
                url,
                int(was_destructive),
                int(user_confirmed) if user_confirmed is not None else None,
                int(was_blocked),
                model_used,
                reasoning[:1000] if reasoning else None,
            ),
        )
        await self.db.commit()
        return audit_id

    async def get_audit_trail(self, task_id: str) -> list[dict[str, Any]]:
        """Return all audit entries for a task, ordered by timestamp."""
        cursor = await self.db.execute(
            "SELECT * FROM audit_log WHERE task_id = ? ORDER BY timestamp",
            (task_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_audit_trail_by_date(
        self,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Return audit entries within a date range (ISO 8601 strings)."""
        cursor = await self.db.execute(
            """
            SELECT * FROM audit_log
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
            """,
            (start, end),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def count(self, task_id: str | None = None) -> int:
        """Return total audit entries, optionally filtered by task."""
        if task_id:
            cursor = await self.db.execute(
                "SELECT COUNT(*) FROM audit_log WHERE task_id = ?",
                (task_id,),
            )
        else:
            cursor = await self.db.execute("SELECT COUNT(*) FROM audit_log")
        row = await cursor.fetchone()
        return row[0] if row else 0
