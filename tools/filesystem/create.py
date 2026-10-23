"""Create folders (and empty files) safely within the user's own file tree."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class CreateFolderInput(ToolInput):
    path: str = Field(description="Absolute or ~-relative path of the folder to create.")


class CreateFolderTool(Tool):
    name = "create_folder"
    description = "Create a new folder at the given path (parents created as needed)."
    permission_level = PermissionLevel.LOW_RISK
    input_model = CreateFolderInput

    def run(self, params: CreateFolderInput) -> ToolResult:
        target = Path(params.path).expanduser()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return ToolResult(success=False, message=f"Could not create folder '{target}'.", error=str(exc))
        return ToolResult(success=True, message=f"Created folder {target}.", data={"path": str(target)})

    def verify(self, params: CreateFolderInput, result: ToolResult) -> str | None:
        if result.success and not Path(result.data["path"]).is_dir():
            return "The folder does not actually exist after creation."
        return None
