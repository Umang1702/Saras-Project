"""Close a running application by process name."""
from __future__ import annotations

import time

import psutil
from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class CloseApplicationInput(ToolInput):
    application_name: str = Field(description="Name of the process/application to close, e.g. 'chrome', 'code'.")


class CloseApplicationTool(Tool):
    name = "close_application"
    description = "Close a running application by name."
    permission_level = PermissionLevel.LOW_RISK
    input_model = CloseApplicationInput

    def run(self, params: CloseApplicationInput) -> ToolResult:
        target = params.application_name.strip().lower()
        matched = [p for p in psutil.process_iter(["name"]) if target in (p.info["name"] or "").lower()]
        if not matched:
            return ToolResult(success=False, message=f"No running process matches '{params.application_name}'.",
                               error="process_not_found")
        for proc in matched:
            try:
                proc.terminate()
            except psutil.Error:
                pass
        self._closed_pids = [p.pid for p in matched]
        return ToolResult(success=True, message=f"Closing {params.application_name}.",
                           data={"pids": self._closed_pids, "name_fragment": target})

    def verify(self, params: CloseApplicationInput, result: ToolResult) -> str | None:
        if not result.success:
            return None
        time.sleep(1.0)
        target = (result.data or {}).get("name_fragment", "")
        still_running = any(target in (p.name() or "").lower() for p in psutil.process_iter(["name"]))
        if still_running:
            return f"{params.application_name} does not appear to have fully closed."
        return None
