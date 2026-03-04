"""Async SQLite store for persistent task history, steps, and user preferences.

Uses aiosqlite for non-blocking I/O.  Tables are auto-created on first call
to ``initialize()``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# SQL DDL
# ---------------------------------------------------------------------------

_CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    task_text       TEXT NOT NULL,
    context         TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    result_json     TEXT,
    created_at      TEXT NOT NULL,
    completed_at    TEXT,
    duration_seconds REAL
);
"""

_CREATE_STEPS = """
CREATE TABLE IF NOT EXISTS steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT NOT NULL REFERENCES tasks(id),
    step_number INTEGER NOT NULL,
    action      TEXT,
    element     TEXT,
    reasoning   TEXT,
    thinking    TEXT,
    success     INTEGER,
    error       TEXT,
    created_at  TEXT NOT NULL
);
"""

_CREATE_PREFERENCES = """
CREATE TABLE IF NOT EXISTS preferences (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_steps_task_id ON steps(task_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);",
]


class SQLiteStore:
    """Async wrapper around aiosqlite for the browser-agent database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    # -- lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Open the DB connection and create tables if missing."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA foreign_keys=ON;")
        await self._db.execute(_CREATE_TASKS)
        await self._db.execute(_CREATE_STEPS)
        await self._db.execute(_CREATE_PREFERENCES)
        for idx_sql in _CREATE_INDEXES:
            await self._db.execute(idx_sql)
        await self._db.commit()
        logger.info("sqlite_store_initialized", db_path=self._db_path)

    async def close(self) -> None:
        """Close the DB connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "SQLiteStore not initialized — call initialize() first"
        return self._db

    # -- tasks -------------------------------------------------------------

    async def save_task(
        self,
        task_id: str,
        task_text: str,
        status: str,
        context: str | None = None,
        result_json: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        """Insert or replace a task record."""
        now = datetime.now(timezone.utc).isoformat()
        completed_at = now if status in ("completed", "failed") else None
        await self.db.execute(
            """
            INSERT INTO tasks (id, task_text, context, status, result_json, created_at, completed_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                result_json = excluded.result_json,
                completed_at = excluded.completed_at,
                duration_seconds = excluded.duration_seconds
            """,
            (task_id, task_text, context, status, result_json, now, completed_at, duration_seconds),
        )
        await self.db.commit()

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Return a single task row as a dict, or None."""
        cursor = await self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_tasks(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Return tasks ordered by creation time (newest first)."""
        cursor = await self.db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def task_count(self) -> int:
        """Return total number of tasks."""
        cursor = await self.db.execute("SELECT COUNT(*) FROM tasks")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # -- steps -------------------------------------------------------------

    async def save_step(
        self,
        task_id: str,
        step_number: int,
        action: str | None = None,
        element: str | None = None,
        reasoning: str | None = None,
        thinking: str | None = None,
        success: bool | None = None,
        error: str | None = None,
    ) -> None:
        """Insert a step record for a task."""
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO steps (task_id, step_number, action, element, reasoning, thinking, success, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, step_number, action, element, reasoning, thinking,
             int(success) if success is not None else None, error, now),
        )
        await self.db.commit()

    async def get_steps(self, task_id: str) -> list[dict[str, Any]]:
        """Return all steps for a task, ordered by step_number."""
        cursor = await self.db.execute(
            "SELECT * FROM steps WHERE task_id = ? ORDER BY step_number",
            (task_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]

    # -- preferences -------------------------------------------------------

    async def set_preference(self, key: str, value: str) -> None:
        """Set or update a user preference."""
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO preferences (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        await self.db.commit()

    async def get_preference(self, key: str) -> str | None:
        """Return the value of a preference, or None."""
        cursor = await self.db.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def get_all_preferences(self) -> dict[str, str]:
        """Return all preferences as a dict."""
        cursor = await self.db.execute("SELECT key, value FROM preferences")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}

    # -- helpers -----------------------------------------------------------

    async def get_recent_task_summaries(self, limit: int = 10) -> list[dict[str, str]]:
        """Return lightweight summaries of recent completed tasks (for memory injection)."""
        cursor = await self.db.execute(
            """
            SELECT id, task_text, status, result_json, duration_seconds
            FROM tasks
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        summaries = []
        for r in rows:
            result_data = json.loads(r["result_json"]) if r["result_json"] else {}
            summaries.append({
                "task_id": r["id"],
                "task": r["task_text"],
                "result": result_data.get("final_result", "")[:500] if result_data else "",
                "duration": r["duration_seconds"],
            })
        return summaries
