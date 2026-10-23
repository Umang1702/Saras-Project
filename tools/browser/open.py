"""Open the default (or a named) browser at a URL, or a well-known site by name."""
from __future__ import annotations

import webbrowser
from typing import Optional

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult

_KNOWN_SITES = {
    "google": "https://google.com",
    "youtube": "https://youtube.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
}


class OpenBrowserInput(ToolInput):
    url: Optional[str] = Field(default=None, description="Full URL to open, e.g. https://github.com")
    site_name: Optional[str] = Field(
        default=None, description="A well-known site name instead of a URL, e.g. 'youtube', 'google'."
    )


class OpenBrowserTool(Tool):
    name = "open_browser"
    description = "Open a URL, or a well-known website by name, in the default web browser."
    permission_level = PermissionLevel.LOW_RISK
    input_model = OpenBrowserInput

    def run(self, params: OpenBrowserInput) -> ToolResult:
        target = params.url
        if not target and params.site_name:
            target = _KNOWN_SITES.get(params.site_name.strip().lower())
        if not target:
            return ToolResult(success=False, message="I don't know which site or URL to open.",
                               error="no_url_resolved")
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        opened = webbrowser.open(target)
        if not opened:
            return ToolResult(success=False, message="Could not open the browser.", error="webbrowser_open_failed")
        return ToolResult(success=True, message=f"Opened {target}", data={"url": target})
