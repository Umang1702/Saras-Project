"""
Central authority on whether a tool call is allowed to run right now.

Nothing else in the codebase should decide "is this allowed" ad hoc — every
execution path goes through PermissionManager.check().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from security.confirmation import ConfirmationRequest, ConfirmationService
from security.policies import PermissionLevel
from utils.exceptions import PermissionDeniedError
from utils.logger import get_logger

logger = get_logger("security.permissions")


@dataclass
class PermissionDecision:
    allowed: bool
    needs_confirmation: bool
    confirmation: Optional[ConfirmationRequest] = None


class PermissionManager:
    def __init__(self, confirmation_service: ConfirmationService, high_risk_enabled: bool = False):
        self._confirmation_service = confirmation_service
        self._high_risk_enabled = high_risk_enabled

    def check(self, tool_name: str, level: PermissionLevel, summary: str, detail: str) -> PermissionDecision:
        if level.is_blocked_by_default and not self._high_risk_enabled:
            logger.warning("Blocked HIGH_RISK tool '%s' (not enabled in config).", tool_name)
            raise PermissionDeniedError(
                f"'{tool_name}' is a high-risk operation and is disabled by default."
            )

        if level.requires_confirmation:
            req = self._confirmation_service.request(summary=summary, detail=detail)
            logger.info("Confirmation required for '%s' (id=%s).", tool_name, req.id)
            return PermissionDecision(allowed=False, needs_confirmation=True, confirmation=req)

        return PermissionDecision(allowed=True, needs_confirmation=False)
