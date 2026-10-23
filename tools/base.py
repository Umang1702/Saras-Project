"""
Base abstraction every capability in SARAS must implement.

This is the contract that replaces:

    if "open google" in c.lower():
        webbrowser.open("https://google.com")

with a discoverable, validated, permission-checked, verifiable unit the
planner/executor can reason about generically instead of the assistant
core needing to know about every possible command string.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Type

from pydantic import BaseModel

from security.policies import PermissionLevel


@dataclass
class ToolResult:
    success: bool
    message: str                 # concise, user-facing summary
    data: Any = None              # structured data for the planner/LLM to use
    error: Optional[str] = None    # machine-readable error detail (never shown raw to user)


class ToolInput(BaseModel):
    """Base class for tool input schemas. Concrete tools subclass this with
    their own Pydantic fields, giving the LLM a structured function-calling
    schema instead of parsing raw strings itself."""


class Tool(ABC):
    name: str
    description: str
    permission_level: PermissionLevel
    input_model: Type[ToolInput] = ToolInput
    timeout_seconds: float = 15.0

    @abstractmethod
    def run(self, params: ToolInput) -> ToolResult:
        """Execute the tool. Must not raise for expected failure modes —
        return ToolResult(success=False, ...) instead. Only raise for
        genuinely unexpected/programmer errors."""
        raise NotImplementedError

    def verify(self, params: ToolInput, result: ToolResult) -> Optional[str]:
        """Optional post-execution verification. Return None if verification
        passed or isn't applicable to this tool, or a human-readable failure
        reason if the claimed result doesn't actually hold (e.g. the app
        isn't actually running, the file wasn't actually created)."""
        return None

    def confirmation_detail(self, params: ToolInput) -> str:
        """Human-readable explanation shown when this tool requires
        confirmation. Override for tools with PermissionLevel.CONFIRM+."""
        return f"SARAS wants to run '{self.name}'."

    def schema(self) -> dict:
        """JSON schema describing this tool for LLM function-calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_model.model_json_schema(),
        }
