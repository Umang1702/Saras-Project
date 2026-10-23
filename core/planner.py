"""
Task planner: turns a user message (+ tool schemas) into an ordered list of
tool calls, using the LLM's function-calling output as the primary signal.

Deliberately NOT an autonomous "agent loop" that keeps calling tools until
it decides it's done — that is exactly the unrestricted-loop pattern the
design brief prohibits. Each planning pass produces a bounded plan
(<= max_steps), the executor runs it step by step, and if the user wants
more after seeing results, that's a new turn.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from intelligence.llm import LLMService
from intelligence.providers.base import ToolCallRequest
from tools.registry import ToolRegistry
from utils.exceptions import PlannerError
from utils.logger import get_logger

logger = get_logger("core.planner")

MAX_STEPS = 6


@dataclass
class PlanStep:
    tool_name: str
    arguments: dict


@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)
    direct_answer: str | None = None  # set when the LLM chose to just answer, no tools


class TaskPlanner:
    def __init__(self, llm: LLMService, registry: ToolRegistry):
        self._llm = llm
        self._registry = registry

    def plan(self, user_text: str, history: list[dict[str, str]]) -> Plan:
        response = self._llm.ask(user_text, history, tools=self._registry.llm_schemas())

        if not response.tool_calls:
            return Plan(direct_answer=response.text or "")

        steps: list[PlanStep] = []
        for call in response.tool_calls[:MAX_STEPS]:
            if not self._registry.has(call.tool_name):
                logger.warning("Planner referenced unknown tool '%s'; skipping.", call.tool_name)
                continue
            steps.append(PlanStep(tool_name=call.tool_name, arguments=call.arguments))

        if not steps:
            raise PlannerError("The model requested tools, but none were valid/registered.")

        return Plan(steps=steps)
