"""Natural-language-friendly file search: by name fragment, extension, recency, size."""
from __future__ import annotations

import datetime
import fnmatch
from pathlib import Path
from typing import Optional

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult

_DEFAULT_ROOTS = ["Desktop", "Downloads", "Documents", "Pictures"]


class SearchFilesInput(ToolInput):
    name_contains: Optional[str] = Field(default=None, description="Substring/pattern the filename should contain, e.g. 'resume'.")
    extension: Optional[str] = Field(default=None, description="File extension filter, e.g. 'pdf'.")
    modified_within_days: Optional[int] = Field(default=None, description="Only files modified within this many days.")
    min_size_mb: Optional[float] = Field(default=None, description="Only files at least this large, in MB.")
    search_root: Optional[str] = Field(default=None, description="Specific folder to search. Defaults to common user folders.")
    max_results: int = Field(default=20, le=200)


class SearchFilesTool(Tool):
    name = "search_files"
    description = "Search for files by name, extension, recency, or size across common user folders."
    permission_level = PermissionLevel.SAFE
    input_model = SearchFilesInput

    def run(self, params: SearchFilesInput) -> ToolResult:
        roots = [Path(params.search_root)] if params.search_root else [
            Path.home() / r for r in _DEFAULT_ROOTS
        ]

        pattern = f"*{params.name_contains}*" if params.name_contains else "*"
        if params.extension:
            ext = params.extension.lstrip(".")
            pattern = f"{pattern}.{ext}" if params.name_contains else f"*.{ext}"

        cutoff = None
        if params.modified_within_days is not None:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=params.modified_within_days)

        matches: list[dict] = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if not fnmatch.fnmatch(path.name.lower(), pattern.lower()):
                    continue
                stat = path.stat()
                if cutoff and datetime.datetime.fromtimestamp(stat.st_mtime) < cutoff:
                    continue
                if params.min_size_mb and stat.st_size < params.min_size_mb * 1024 * 1024:
                    continue
                matches.append({
                    "path": str(path),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
                if len(matches) >= params.max_results:
                    break
            if len(matches) >= params.max_results:
                break

        matches.sort(key=lambda m: m["modified"], reverse=True)
        message = f"Found {len(matches)} matching file(s)." if matches else "No matching files found."
        return ToolResult(success=True, message=message, data={"files": matches})
