"""
SQLite data-access layer. Kept intentionally thin (no ORM) since SQLite is
explicitly the "don't over-engineer" choice for a personal desktop agent —
but the repository methods here are the only place raw SQL appears, so
swapping to PostgreSQL later means changing this one file.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

from utils.logger import get_logger

logger = get_logger("memory.database")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    success INTEGER NOT NULL,
    message TEXT NOT NULL,
    verification_issue TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routines (
    name TEXT PRIMARY KEY,
    steps_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- preferences ------------------------------------------------------------

    def set_preference(self, key: str, value: Any) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO preferences(key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value), datetime.now().isoformat()),
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def all_preferences(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        return {k: json.loads(v) for k, v in rows}

    # --- conversation log (long-term, separate from in-memory short-term context) ---

    def log_conversation_turn(self, role: str, content: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations(role, content, created_at) VALUES (?, ?, ?)",
                (role, content, datetime.now().isoformat()),
            )

    # --- tool execution audit log --------------------------------------------------------

    def record_tool_execution(
        self, tool_name: str, arguments: dict, success: bool, message: str, verification_issue: Optional[str]
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO tool_executions(tool_name, arguments_json, success, message, verification_issue, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tool_name, json.dumps(arguments), int(success), message, verification_issue, datetime.now().isoformat()),
            )

    # --- routines -------------------------------------------------------------------------

    def save_routine(self, name: str, steps: list[dict]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO routines(name, steps_json, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET steps_json=excluded.steps_json",
                (name, json.dumps(steps), datetime.now().isoformat()),
            )

    def get_routine(self, name: str) -> Optional[list[dict]]:
        with self._connect() as conn:
            row = conn.execute("SELECT steps_json FROM routines WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_routines(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM routines").fetchall()
        return [r[0] for r in rows]
