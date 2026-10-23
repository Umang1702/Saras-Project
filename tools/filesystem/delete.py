"""
Delete files/folders — the canonical CONFIRM-level operation.

Deletion NEVER runs without going through PermissionManager first (see
core/executor.py). This tool also refuses to touch anything outside the
user's own home directory tree, as a second independent guard.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class DeleteFilesInput(ToolInput):
    paths: list[str] = Field(description="Absolute paths of files/folders to delete.")


class DeleteFilesTool(Tool):
    name = "delete_files"
    description = "Permanently delete one or more files or folders. Always requires confirmation."
    permission_level = PermissionLevel.CONFIRM
    input_model = DeleteFilesInput

    def confirmation_detail(self, params: DeleteFilesInput) -> str:
        count = len(params.paths)
        preview = "\n".join(f"  - {p}" for p in params.paths[:10])
        more = f"\n  ...and {count - 10} more" if count > 10 else ""
        return (
            f"I found {count} item(s) to delete:\n{preview}{more}\n\n"
            "Deleting them may not be reversible."
        )

    def run(self, params: DeleteFilesInput) -> ToolResult:
        home = Path.home().resolve()
        deleted, failed = [], []
        for raw in params.paths:
            target = Path(raw).expanduser().resolve()
            try:
                target.relative_to(home)
            except ValueError:
                failed.append((raw, "outside home directory, refused"))
                continue
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                else:
                    failed.append((raw, "does not exist"))
                    continue
                deleted.append(raw)
            except Exception as exc:
                failed.append((raw, str(exc)))

        success = len(failed) == 0
        message = f"Deleted {len(deleted)} item(s)."
        if failed:
            message += f" {len(failed)} failed."
        return ToolResult(success=success, message=message, data={"deleted": deleted, "failed": failed})

    def verify(self, params: DeleteFilesInput, result: ToolResult) -> str | None:
        for raw in (result.data or {}).get("deleted", []):
            if Path(raw).expanduser().exists():
                return f"'{raw}' still exists after the delete operation."
        return None
