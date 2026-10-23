"""
OpenAI provider using the modern `openai` Python SDK (>=1.0) client +
tools/function-calling interface — replacing the old:

    client = OpenAI(api_key="Your OpenAI api")
    completion = client.chat.completions.create(model="gpt-3.5-turbo", ...)

hardcoded pattern from the original client.py/main.py. The API key and
model now come exclusively from app.config.Settings.
"""
from __future__ import annotations

import json
from typing import Optional

from intelligence.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from utils.exceptions import ConfigurationError, LLMMalformedOutputError, LLMProviderError, LLMRateLimitError
from utils.logger import get_logger

logger = get_logger("intelligence.openai_provider")


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str], model: str):
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ConfigurationError("The 'openai' package is not installed.") from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
    ) -> LLMResponse:
        openai_tools = None
        if tools:
            openai_tools = [
                {"type": "function", "function": {
                    "name": t["name"], "description": t["description"], "parameters": t["parameters"],
                }}
                for t in tools
            ]

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system_prompt}, *messages],
                tools=openai_tools,
                temperature=0.3,
            )
        except Exception as exc:  # SDK raises typed errors; normalize to ours
            name = exc.__class__.__name__
            if "RateLimit" in name:
                raise LLMRateLimitError(str(exc)) from exc
            raise LLMProviderError(str(exc)) from exc

        choice = completion.choices[0].message
        tool_calls: list[ToolCallRequest] = []
        for call in (choice.tool_calls or []):
            try:
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise LLMMalformedOutputError(f"Bad tool-call arguments JSON: {exc}") from exc
            tool_calls.append(ToolCallRequest(tool_name=call.function.name, arguments=args))

        return LLMResponse(text=choice.content, tool_calls=tool_calls)
