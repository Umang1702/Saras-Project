"""
Provider-agnostic LLM interface. core/ and intelligence/llm.py only ever
talk to this interface, never to a specific SDK, so adding
AnthropicProvider / GeminiProvider / LocalModelProvider later is a matter
of implementing this class — nothing else changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCallRequest:
    tool_name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: Optional[str] = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
    ) -> LLMResponse:
        """messages: list of {"role": "user"|"assistant", "content": str}.
        tools: optional list of tool schemas (see tools/base.py Tool.schema())
        for the provider to choose from via function calling."""
        raise NotImplementedError
