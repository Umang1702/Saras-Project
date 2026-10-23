"""Open a file with its default associated application."""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class OpenFileInput(ToolInput):
    path: str = Field(description="Path of the file to open.")


class OpenFileTool(Tool):
    name = "open_file"
    description = "Open a file with its default associated application."
    permission_level = PermissionLevel.LOW_RISK
    input_model = OpenFileInput

    def run(self, params: OpenFileInput) -> ToolResult:
        target = Path(params.path).expanduser()
        if not target.exists():
            return ToolResult(success=False, message=f"File '{target}' does not exist.", error="not_found")
        try:
            if platform.system() == "Windows":
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            return ToolResult(success=False, message=f"Could not open '{target.name}'.", error=str(exc))
        return ToolResult(success=True, message=f"Opening {target.name}.", data={"path": str(target)})
