"""
Human-in-the-loop confirmation for CONFIRM/HIGH_RISK actions.

Flow:
    Executor wants to run a risky tool
        -> ConfirmationService.request(...) builds a human-readable prompt
           and stores a pending ConfirmationRequest
        -> caller speaks/prints the prompt and waits for the user's reply
        -> ConfirmationService.resolve(id, "yes"/"no") finalizes it
        -> Executor proceeds or aborts based on the resolution

This is intentionally synchronous/simple (no autonomous loop that guesses
consent) — SARAS never proceeds with a CONFIRM-level action without an
explicit affirmative reply.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

_AFFIRMATIVE = {"yes", "y", "yeah", "yep", "confirm", "go ahead", "do it", "sure"}
_NEGATIVE = {"no", "n", "nope", "cancel", "stop", "don't", "do not"}


@dataclass
class ConfirmationRequest:
    id: str
    summary: str          # short human-readable description, e.g. "Delete 37 files"
    detail: str            # longer explanation of consequences
    resolved: bool = False
    approved: Optional[bool] = None


class ConfirmationService:
    def __init__(self) -> None:
        self._pending: dict[str, ConfirmationRequest] = {}

    def request(self, summary: str, detail: str) -> ConfirmationRequest:
        req = ConfirmationRequest(id=str(uuid.uuid4()), summary=summary, detail=detail)
        self._pending[req.id] = req
        return req

    def prompt_text(self, req: ConfirmationRequest) -> str:
        return f"{req.detail}\n\nDo you want me to continue? (yes/no)"

    def resolve_from_speech(self, confirmation_id: str, spoken_reply: str) -> bool:
        """Parses a free-form spoken/typed reply ('yes' / 'no' / 'cancel' / ...)
        into an approve/deny decision and stores the resolution."""
        normalized = spoken_reply.strip().lower()
        approved = any(word in normalized for word in _AFFIRMATIVE) and not any(
            word in normalized for word in _NEGATIVE
        )
        return self.resolve(confirmation_id, approved)

    def resolve(self, confirmation_id: str, approved: bool) -> bool:
        req = self._pending.get(confirmation_id)
        if req is None:
            return False
        req.resolved = True
        req.approved = approved
        return True

    def get(self, confirmation_id: str) -> Optional[ConfirmationRequest]:
        return self._pending.get(confirmation_id)
