"""Thin service wrapper the rest of the app depends on instead of a raw provider."""
from __future__ import annotations

from typing import Optional

from intelligence.prompts import SYSTEM_PROMPT
from intelligence.providers.base import LLMProvider, LLMResponse


class LLMService:
    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def ask(self, user_text: str, history: list[dict[str, str]], tools: Optional[list[dict]] = None) -> LLMResponse:
        messages = [*history, {"role": "user", "content": user_text}]
        return self._provider.complete(SYSTEM_PROMPT, messages, tools=tools)

    def raw_complete(self, system_prompt: str, user_text: str) -> Optional[str]:
        response = self._provider.complete(system_prompt, [{"role": "user", "content": user_text}])
        return response.text
