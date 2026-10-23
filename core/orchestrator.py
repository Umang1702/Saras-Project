"""
Top-level coordinator: intent -> (direct answer | plan -> execute steps) ->
concise response text. This replaces `processCommand()`'s if/elif chain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.context import ContextManager
from core.executor import Executor
from core.planner import TaskPlanner
from intelligence.intent import IntentClassifier, IntentType
from intelligence.llm import LLMService
from intelligence.response import StepOutcome, summarize
from utils.exceptions import SarasError
from utils.logger import get_logger

logger = get_logger("core.orchestrator")


@dataclass
class OrchestratorResult:
    text: str
    pending_confirmation_id: str | None = None
    pending_tool_name: str | None = None
    pending_arguments: dict | None = None
    remaining_steps: list | None = None  # remaining PlanStep objects, for multi-step plans


class Orchestrator:
    def __init__(
        self,
        llm: LLMService,
        planner: TaskPlanner,
        executor: Executor,
        context: ContextManager,
        intent_classifier: IntentClassifier,
        local_fallback: Any | None = None,
    ):
        self._llm = llm
        self._planner = planner
        self._executor = executor
        self._context = context
        self._intent = intent_classifier
        self._local_fallback = local_fallback

    def handle(self, user_text: str) -> OrchestratorResult:
        self._context.add_turn("user", user_text)

        try:
            intent = self._intent.classify(user_text)
            logger.debug("Intent for %r classified as %s", user_text, intent)

            if intent is IntentType.QUESTION:
                response = self._llm.ask(user_text, self._context.as_llm_history())
                text = response.text or "I'm not sure how to answer that."
                self._context.add_turn("assistant", text)
                return OrchestratorResult(text=text)

            plan = self._planner.plan(user_text, self._context.as_llm_history())

            if plan.direct_answer is not None:
                text = plan.direct_answer or "Okay."
                self._context.add_turn("assistant", text)
                return OrchestratorResult(text=text)

            outcomes: list[StepOutcome] = []
            for i, step in enumerate(plan.steps):
                outcome = self._executor.execute(step.tool_name, step.arguments)

                if outcome.needs_confirmation and outcome.confirmation:
                    prompt = f"{outcome.confirmation.detail}\n\nDo you want me to continue? (yes/no)"
                    self._context.add_turn("assistant", prompt)
                    return OrchestratorResult(
                        text=prompt,
                        pending_confirmation_id=outcome.confirmation.id,
                        pending_tool_name=step.tool_name,
                        pending_arguments=step.arguments,
                        remaining_steps=plan.steps[i + 1:],
                    )

                self._context.record_tool_result(step.tool_name, outcome.result)
                message = outcome.result.message
                if outcome.verification_issue:
                    message += f" (Note: {outcome.verification_issue})"
                outcomes.append(StepOutcome(tool_name=step.tool_name, success=outcome.result.success, message=message))

            text = summarize(outcomes)
            self._context.add_turn("assistant", text)
            return OrchestratorResult(text=text)

        except Exception as exc:
            if self._local_fallback is not None:
                logger.warning(
                    "AI orchestrator failed (%s). Seamlessly falling back to local orchestrator.",
                    exc,
                )
                return self._local_fallback.handle(user_text)

            logger.warning("Handled SarasError: %s", exc)
            text = f"I couldn't do that: {exc}"
            self._context.add_turn("assistant", text)
            return OrchestratorResult(text=text)

    def resume_confirmed_step(self, tool_name: str, arguments: dict, remaining_steps: list) -> OrchestratorResult:
        """Runs a previously-confirmed step, then continues any remaining
        steps of the same plan (re-checking permissions for each — a later
        step could itself require its own confirmation)."""
        outcomes: list[StepOutcome] = []
        outcome = self._executor.execute_confirmed(tool_name, arguments)
        self._context.record_tool_result(tool_name, outcome.result)
        message = outcome.result.message
        if outcome.verification_issue:
            message += f" (Note: {outcome.verification_issue})"
        outcomes.append(StepOutcome(tool_name=tool_name, success=outcome.result.success, message=message))

        for i, step in enumerate(remaining_steps or []):
            next_outcome = self._executor.execute(step.tool_name, step.arguments)
            if next_outcome.needs_confirmation and next_outcome.confirmation:
                prompt = f"{next_outcome.confirmation.detail}\n\nDo you want me to continue? (yes/no)"
                self._context.add_turn("assistant", prompt)
                return OrchestratorResult(
                    text=prompt,
                    pending_confirmation_id=next_outcome.confirmation.id,
                    pending_tool_name=step.tool_name,
                    pending_arguments=step.arguments,
                    remaining_steps=remaining_steps[i + 1:],
                )
            self._context.record_tool_result(step.tool_name, next_outcome.result)
            msg = next_outcome.result.message
            if next_outcome.verification_issue:
                msg += f" (Note: {next_outcome.verification_issue})"
            outcomes.append(StepOutcome(tool_name=step.tool_name, success=next_outcome.result.success, message=msg))

        text = summarize(outcomes)
        self._context.add_turn("assistant", text)
        return OrchestratorResult(text=text)
