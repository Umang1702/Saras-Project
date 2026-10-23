"""
Executes a single tool call end-to-end:
  validate input -> permission check (-> confirmation if needed)
  -> run with timeout -> verify -> log.

This is the ONLY place tools are actually invoked from. The planner never
calls a tool directly, and the LLM never gets raw execution access — see
section 5 of the design brief ("LLM must NOT directly control the computer").
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError as PydanticValidationError

from memory.database import Database
from security.confirmation import ConfirmationRequest
from security.permissions import PermissionManager
from tools.base import Tool, ToolResult
from tools.registry import ToolRegistry
from utils.exceptions import ToolExecutionError, ToolNotFoundError, ToolTimeoutError, ToolValidationError
from utils.logger import get_logger

logger = get_logger("core.executor")


@dataclass
class ExecutionOutcome:
    tool_name: str
    result: ToolResult
    verification_issue: Optional[str] = None
    needs_confirmation: bool = False
    confirmation: Optional[ConfirmationRequest] = None


class Executor:
    def __init__(self, registry: ToolRegistry, permissions: PermissionManager, db: Optional[Database] = None):
        self._registry = registry
        self._permissions = permissions
        self._db = db
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def execute(self, tool_name: str, arguments: dict, force: bool = False) -> ExecutionOutcome:
        tool = self._registry.get(tool_name)

        try:
            params = tool.input_model(**arguments)
        except PydanticValidationError as exc:
            raise ToolValidationError(f"Invalid arguments for '{tool_name}': {exc}") from exc

        if not force:
            decision = self._permissions.check(
                tool_name=tool_name,
                level=tool.permission_level,
                summary=tool.name,
                detail=tool.confirmation_detail(params),
            )
            if decision.needs_confirmation:
                return ExecutionOutcome(
                    tool_name=tool_name,
                    result=ToolResult(success=False, message="Waiting for your confirmation."),
                    needs_confirmation=True,
                    confirmation=decision.confirmation,
                )

        future = self._pool.submit(tool.run, params)
        try:
            result = future.result(timeout=tool.timeout_seconds)
        except concurrent.futures.TimeoutError:
            logger.error("Tool '%s' timed out after %.1fs.", tool_name, tool.timeout_seconds)
            raise ToolTimeoutError(f"'{tool_name}' timed out.")
        except Exception as exc:
            logger.exception("Tool '%s' raised unexpectedly.", tool_name)
            raise ToolExecutionError(str(exc)) from exc

        verification_issue = None
        if result.success:
            try:
                verification_issue = tool.verify(params, result)
            except Exception as exc:  # verification must never crash the run
                logger.warning("Verification for '%s' raised: %s", tool_name, exc)

        self._log_execution(tool_name, params.model_dump(), result, verification_issue)
        return ExecutionOutcome(tool_name=tool_name, result=result, verification_issue=verification_issue)

    def execute_confirmed(self, tool_name: str, arguments: dict) -> ExecutionOutcome:
        """Called after a CONFIRM-level action has been explicitly approved."""
        return self.execute(tool_name, arguments, force=True)

    def _log_execution(self, tool_name: str, arguments: dict, result: ToolResult, verification_issue: Optional[str]) -> None:
        logger.info(
            "tool=%s success=%s verification_issue=%s", tool_name, result.success, verification_issue
        )
        if self._db:
            self._db.record_tool_execution(tool_name, arguments, result.success, result.message, verification_issue)
