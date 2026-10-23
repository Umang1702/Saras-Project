"""
Central registry every tool is registered into once, at bootstrap.

Adding a new capability (e.g. tools/gmail/) means writing a Tool subclass
and calling registry.register(...) in bootstrap.py — nothing in core/ or
intelligence/ needs to change.
"""
from __future__ import annotations

from typing import Iterable, Optional

from tools.base import Tool
from utils.exceptions import ToolNotFoundError
from utils.logger import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool
        logger.debug("Registered tool '%s' (permission=%s).", tool.name, tool.permission_level.name)

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"No tool named '{name}' is registered.")
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> Iterable[Tool]:
        return self._tools.values()

    def llm_schemas(self) -> list[dict]:
        """Function-calling schema list for every registered tool, handed to
        the LLM provider so it can choose among them by name."""
        return [t.schema() for t in self._tools.values()]
