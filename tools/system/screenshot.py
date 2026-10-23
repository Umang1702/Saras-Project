"""Take a screenshot and save it to disk."""
from __future__ import annotations

import datetime
from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class ScreenshotInput(ToolInput):
    save_dir: str = Field(default_factory=lambda: str(Path.home() / "Pictures" / "SARAS_Screenshots"))


class ScreenshotTool(Tool):
    name = "take_screenshot"
    description = "Take a screenshot of the current screen and save it as a PNG."
    permission_level = PermissionLevel.SAFE
    input_model = ScreenshotInput

    def run(self, params: ScreenshotInput) -> ToolResult:
        try:
            import mss
        except ImportError:
            return ToolResult(success=False, message="Screenshot support requires the 'mss' package.",
                               error="missing_dependency")

        out_dir = Path(params.save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = out_dir / f"screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"

        try:
            with mss.mss() as sct:
                sct.shot(output=str(filename))
        except Exception as exc:  # pragma: no cover - environment dependent
            return ToolResult(success=False, message="Could not capture the screen.", error=str(exc))

        return ToolResult(success=True, message=f"Screenshot saved to {filename}.", data={"path": str(filename)})

    def verify(self, params: ScreenshotInput, result: ToolResult) -> str | None:
        if result.success and result.data:
            if not Path(result.data["path"]).exists():
                return "The screenshot file does not actually exist on disk."
        return None
