"""
Thin re-export: short-term/turn-scoped context is implemented in
core/context.py (ContextManager) since it's tightly coupled to the
orchestrator's control flow. This module exists so `memory/` reads
completely for the "short-term / long-term / preferences" design without
duplicating that logic in two places.
"""
from core.context import ContextManager, Turn  # noqa: F401
