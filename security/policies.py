"""
Permission levels for every tool in the system.

Every Tool declares exactly one of these. The PermissionManager (permissions.py)
uses this to decide whether a call proceeds silently, requires confirmation,
or is refused outright.
"""
from __future__ import annotations

from enum import IntEnum


class PermissionLevel(IntEnum):
    SAFE = 0              # read-only, no side effects: battery, storage info, list files
    LOW_RISK = 1           # reversible side effects: create folder, open app, set volume
    CONFIRM = 2             # needs explicit human confirmation: delete, overwrite, run arbitrary command
    HIGH_RISK = 3            # admin/destructive: registry edits, disk operations, security config changes

    @property
    def requires_confirmation(self) -> bool:
        return self >= PermissionLevel.CONFIRM

    @property
    def is_blocked_by_default(self) -> bool:
        # HIGH_RISK is never auto-approved even with "confirm" — it must be
        # explicitly enabled in config AND confirmed. There is no built-in
        # HIGH_RISK tool in this project; the level exists for future
        # integrations (e.g. registry editing) so they are opt-in, not silent.
        return self >= PermissionLevel.HIGH_RISK
