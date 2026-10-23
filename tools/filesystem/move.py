"""Move or copy files/folders. Overwrites are treated as CONFIRM-level via the copy path."""
from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class MoveFileInput(ToolInput):
    source: str = Field(description="Path of the file or folder to move.")
    destination: str = Field(description="Destination folder path.")


class MoveFileTool(Tool):
    name = "move_file"
    description = "Move a file or folder into a destination folder."
    permission_level = PermissionLevel.LOW_RISK
    input_model = MoveFileInput

    def run(self, params: MoveFileInput) -> ToolResult:
        src = Path(params.source).expanduser()
        dest_dir = Path(params.destination).expanduser()
        if not src.exists():
            return ToolResult(success=False, message=f"Source '{src}' does not exist.", error="source_not_found")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / src.name
        try:
            shutil.move(str(src), str(dest_path))
        except Exception as exc:
            return ToolResult(success=False, message=f"Could not move '{src.name}'.", error=str(exc))
        return ToolResult(success=True, message=f"Moved {src.name} to {dest_dir}.", data={"new_path": str(dest_path)})

    def verify(self, params: MoveFileInput, result: ToolResult) -> str | None:
        if result.success and not Path(result.data["new_path"]).exists():
            return "The file does not exist at the destination after the move."
        return None


class CopyFileInput(ToolInput):
    source: str = Field(description="Path of the file or folder to copy.")
    destination: str = Field(description="Destination folder path.")


class CopyFileTool(Tool):
    name = "copy_file"
    description = "Copy a file or folder into a destination folder."
    permission_level = PermissionLevel.LOW_RISK
    input_model = CopyFileInput

    def run(self, params: CopyFileInput) -> ToolResult:
        src = Path(params.source).expanduser()
        dest_dir = Path(params.destination).expanduser()
        if not src.exists():
            return ToolResult(success=False, message=f"Source '{src}' does not exist.", error="source_not_found")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / src.name
        try:
            if src.is_dir():
                shutil.copytree(str(src), str(dest_path), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(dest_path))
        except Exception as exc:
            return ToolResult(success=False, message=f"Could not copy '{src.name}'.", error=str(exc))
        return ToolResult(success=True, message=f"Copied {src.name} to {dest_dir}.", data={"new_path": str(dest_path)})
