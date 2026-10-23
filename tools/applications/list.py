"""List currently running user-facing applications."""
from __future__ import annotations

import psutil

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class NoInput(ToolInput):
    pass


class ListRunningApplicationsTool(Tool):
    name = "list_running_applications"
    description = "List the names of currently running applications/processes."
    permission_level = PermissionLevel.SAFE
    input_model = NoInput

    def run(self, params: NoInput) -> ToolResult:
        names = sorted({p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]})
        preview = ", ".join(names[:15])
        message = f"{len(names)} processes running. Examples: {preview}."
        return ToolResult(success=True, message=message, data={"processes": names})
