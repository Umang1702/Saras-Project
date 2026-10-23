"""
News headlines via NewsAPI, replacing the old inline `elif "news" in c.lower()`
block. API key comes only from config (never hardcoded), and every failure
mode (missing key, bad status, rate limit, malformed JSON, empty results,
timeout) is handled explicitly instead of silently doing nothing.
"""
from __future__ import annotations

from typing import Optional

import requests
from pydantic import Field

from app.config import get_settings
from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class GetNewsInput(ToolInput):
    category: Optional[str] = Field(default=None, description="News category, e.g. 'technology', 'business'.")
    country: Optional[str] = Field(default=None, description="Two-letter country code, defaults to configured country.")
    max_headlines: int = Field(default=5, le=20)


class GetNewsTool(Tool):
    name = "get_news"
    description = "Fetch the latest top news headlines, optionally filtered by category or country."
    permission_level = PermissionLevel.SAFE
    input_model = GetNewsInput
    timeout_seconds = 10.0

    def run(self, params: GetNewsInput) -> ToolResult:
        settings = get_settings()
        if not settings.news_api_key:
            return ToolResult(success=False, message="News isn't configured — no NEWS_API_KEY is set.",
                               error="missing_api_key")

        query = {
            "country": params.country or settings.news_country,
            "apiKey": settings.news_api_key,
            "pageSize": params.max_headlines,
        }
        if params.category:
            query["category"] = params.category

        try:
            resp = requests.get("https://newsapi.org/v2/top-headlines", params=query, timeout=self.timeout_seconds)
        except requests.Timeout:
            return ToolResult(success=False, message="The news request timed out.", error="timeout")
        except requests.RequestException as exc:
            return ToolResult(success=False, message="Could not reach the news service.", error=str(exc))

        if resp.status_code == 429:
            return ToolResult(success=False, message="News service rate limit reached.", error="rate_limited")
        if resp.status_code != 200:
            return ToolResult(success=False, message=f"News service returned an error ({resp.status_code}).",
                               error=f"http_{resp.status_code}")

        try:
            data = resp.json()
        except ValueError:
            return ToolResult(success=False, message="The news service returned malformed data.", error="bad_json")

        articles = data.get("articles", [])
        if not articles:
            return ToolResult(success=True, message="No headlines available right now.", data={"headlines": []})

        headlines = [a.get("title", "").strip() for a in articles if a.get("title")]
        message = f"Top headline: {headlines[0]}" if headlines else "No headlines available."
        return ToolResult(success=True, message=message, data={"headlines": headlines})
