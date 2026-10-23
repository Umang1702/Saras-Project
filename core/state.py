"""Assistant runtime state machine, used by the voice session and UI/tray."""
from __future__ import annotations

from enum import Enum


class AssistantState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"


class StateManager:
    def __init__(self) -> None:
        self._state = AssistantState.IDLE
        self._listeners: list = []

    @property
    def state(self) -> AssistantState:
        return self._state

    def set(self, state: AssistantState) -> None:
        self._state = state
        for listener in self._listeners:
            listener(state)

    def on_change(self, callback) -> None:
        self._listeners.append(callback)
