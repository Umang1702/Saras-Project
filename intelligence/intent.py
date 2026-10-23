"""
Classifies user input as QUESTION / ACTION / MULTI_STEP before deciding
whether to just answer, run the planner for one tool call, or run the
planner for a multi-step plan. Cheap heuristics first; falls back to the
LLM only when the heuristic is unsure, to save latency/cost.
"""
from __future__ import annotations

from enum import Enum

from intelligence.llm import LLMService
from intelligence.prompts import QUESTION_VS_ACTION_HINT

_ACTION_VERBS = (
    "open", "close", "launch", "start", "stop", "play", "pause", "search",
    "find", "create", "make", "move", "copy", "delete", "remove", "run",
    "execute", "take a screenshot", "set volume", "remind me", "schedule",
)

_QUESTION_STARTERS = ("what", "who", "why", "how", "when", "is ", "are ", "can you tell", "explain")


class IntentType(str, Enum):
    QUESTION = "QUESTION"
    ACTION = "ACTION"
    MULTI_STEP = "MULTI_STEP"


class IntentClassifier:
    def __init__(self, llm: LLMService):
        self._llm = llm

    def classify(self, text: str) -> IntentType:
        lowered = text.lower().strip()

        if " and " in lowered or lowered.count(",") >= 1:
            if any(v in lowered for v in _ACTION_VERBS):
                return IntentType.MULTI_STEP

        if lowered.startswith(_QUESTION_STARTERS) and not any(v in lowered for v in _ACTION_VERBS):
            return IntentType.QUESTION

        if any(lowered.startswith(v) or f" {v} " in f" {lowered} " for v in _ACTION_VERBS):
            return IntentType.ACTION

        # Ambiguous — ask the LLM once, cheaply, with no tools attached.
        response = self._llm.raw_complete(QUESTION_VS_ACTION_HINT, text)
        normalized = (response or "").strip().upper()
        if normalized in IntentType.__members__:
            return IntentType[normalized]
        return IntentType.QUESTION
