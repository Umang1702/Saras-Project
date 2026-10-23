"""
Short-term conversational/task context: what SARAS just did, what app is
currently in focus, and recent turns — so "search Deloitte" after
"open Chrome" resolves against the current browser context, and "open the
first result" resolves against the previous tool's result.

Long-lived preferences live in memory/long_term.py instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Turn:
    role: str          # "user" | "assistant"
    content: str


@dataclass
class ContextManager:
    max_turns: int = 12
    history: list[Turn] = field(default_factory=list)
    current_application: Optional[str] = None
    last_tool_name: Optional[str] = None
    last_tool_result: Optional[Any] = None

    def add_turn(self, role: str, content: str) -> None:
        self.history.append(Turn(role=role, content=content))
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns:]

    def record_tool_result(self, tool_name: str, result: Any) -> None:
        self.last_tool_name = tool_name
        self.last_tool_result = result
        if tool_name == "open_browser":
            self.current_application = "browser"
        elif tool_name == "open_application":
            data = getattr(result, "data", None) or {}
            self.current_application = data.get("executable")

    def as_llm_history(self) -> list[dict[str, str]]:
        return [{"role": t.role, "content": t.content} for t in self.history]
