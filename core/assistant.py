"""
Top-level Assistant object: the thing app/main.py actually runs. Wires the
voice session (or a plain text loop) to the Orchestrator, and correctly
resumes a pending CONFIRM-level action from the user's next reply
("yes"/"no") using the exact tool/arguments/remaining-plan the orchestrator
paused on — no re-guessing.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from core.orchestrator import Orchestrator
from core.state import AssistantState, StateManager
from security.confirmation import ConfirmationService
from utils.logger import get_logger

logger = get_logger("core.assistant")


class Assistant:
    def __init__(
        self,
        orchestrator: Any,
        confirmation_service: ConfirmationService,
        state: Optional[StateManager] = None,
        fallback_orchestrator: Optional[Any] = None,
    ):
        self._orchestrator = orchestrator
        self._fallback_orchestrator = fallback_orchestrator
        self._confirmations = confirmation_service
        self._state = state or StateManager()
        self._pending_confirmation_id: Optional[str] = None
        self._pending_tool_name: Optional[str] = None
        self._pending_arguments: Optional[dict] = None
        self._pending_remaining_steps: Optional[list] = None
        self._interaction_listeners: list[Callable[[str, str], None]] = []

    @property
    def state(self) -> StateManager:
        return self._state

    def on_interaction(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback for all user-assistant interactions (voice or text)."""
        self._interaction_listeners.append(callback)

    def _notify_interaction(self, user_text: str, response_text: str) -> None:
        for cb in self._interaction_listeners:
            try:
                cb(user_text, response_text)
            except Exception as exc:
                logger.debug("Interaction listener callback failed: %s", exc)

    def process_text(self, text: str) -> str:
        self._state.set(AssistantState.PROCESSING)
        try:
            if self._pending_confirmation_id:
                return self._resolve_pending(text)

            try:
                result = self._orchestrator.handle(text)
            except Exception as primary_exc:
                if self._fallback_orchestrator is not None and self._fallback_orchestrator is not self._orchestrator:
                    logger.warning(
                        "Primary orchestrator failed (%s). Falling back to LocalOrchestrator.",
                        primary_exc,
                    )
                    result = self._fallback_orchestrator.handle(text)
                else:
                    raise

            self._store_pending(result)
            self._notify_interaction(text, result.text)
            return result.text
        finally:
            if self._state.state == AssistantState.PROCESSING:
                self._state.set(
                    AssistantState.AWAITING_CONFIRMATION if self._pending_confirmation_id else AssistantState.IDLE
                )

    def _store_pending(self, result) -> None:
        self._pending_confirmation_id = result.pending_confirmation_id
        self._pending_tool_name = result.pending_tool_name
        self._pending_arguments = result.pending_arguments
        self._pending_remaining_steps = result.remaining_steps

    def _resolve_pending(self, reply: str) -> str:
        confirmation_id = self._pending_confirmation_id
        tool_name = self._pending_tool_name
        arguments = self._pending_arguments or {}
        remaining = self._pending_remaining_steps or []

        self._pending_confirmation_id = None
        self._pending_tool_name = None
        self._pending_arguments = None
        self._pending_remaining_steps = None
        self._state.set(AssistantState.IDLE)

        approved = self._confirmations.resolve_from_speech(confirmation_id, reply)
        if not approved:
            return "Okay, I won't do that."

        try:
            result = self._orchestrator.resume_confirmed_step(tool_name, arguments, remaining)
        except Exception as primary_exc:
            if self._fallback_orchestrator is not None and self._fallback_orchestrator is not self._orchestrator:
                result = self._fallback_orchestrator.resume_confirmed_step(tool_name, arguments, remaining)
            else:
                raise

        self._store_pending(result)
        return result.text
