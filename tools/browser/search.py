"""Perform a web search via the default browser (Google search URL)."""
from __future__ import annotations

import urllib.parse
import webbrowser

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class WebSearchInput(ToolInput):
    query: str = Field(description="Search query text.")


class WebSearchTool(Tool):
    name = "search_web"
    description = "Search the web for a query and open the results in the browser."
    permission_level = PermissionLevel.LOW_RISK
    input_model = WebSearchInput

    def run(self, params: WebSearchInput) -> ToolResult:
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(params.query)
        opened = webbrowser.open(url)
        if not opened:
            return ToolResult(success=False, message="Could not open a browser to search.", error="webbrowser_open_failed")
        return ToolResult(success=True, message=f"Searching for '{params.query}'.", data={"url": url})
