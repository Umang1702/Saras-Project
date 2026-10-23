"""
Long-term preference storage: durable facts like "preferred browser =
Chrome" that should survive restarts, backed by the preferences table in
memory/database.py. Never stores secrets — see the module docstring
warning replicated here intentionally.
"""
from __future__ import annotations

from typing import Any, Optional

from memory.database import Database

_FORBIDDEN_KEY_FRAGMENTS = ("password", "token", "secret", "api_key", "apikey")


class PreferencesStore:
    def __init__(self, db: Database):
        self._db = db

    def set(self, key: str, value: Any) -> None:
        if any(frag in key.lower() for frag in _FORBIDDEN_KEY_FRAGMENTS):
            raise ValueError(f"Refusing to store '{key}' as a preference — looks like a secret.")
        self._db.set_preference(key, value)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._db.get_preference(key, default)

    def all(self) -> dict:
        return self._db.all_preferences()
