"""
Fast, offline, zero-LLM-call router for common commands.

The original SARAS used `if "open google" in c.lower(): ...` for exactly
this reason: local, unambiguous commands shouldn't need a network round
trip to an LLM just to decide "call open_browser with url=google.com".

This module restores that speed/cost/offline benefit WITHOUT bringing back
the original's problems:
  - it produces the same structured (tool_name, arguments) shape the
    planner produces, so it still goes through core/executor.py's full
    permission/validation/verification pipeline — nothing here bypasses
    security.
  - it's additive: if nothing matches, the orchestrator falls back to the
    LLM-based planner (core/planner.py), so open-ended/ambiguous phrasing
    still works.
  - matchers are declared as data (pattern -> tool + arg extractor), not
    scattered through control flow, so adding a new fast-path command
    doesn't grow a giant if/elif chain.

This is intentionally a small, curated set covering the most common,
low-ambiguity commands. It does not attempt to cover multi-step requests,
file deletion, or terminal execution — those always go through the LLM
planner since they genuinely need reasoning (which files? which command?).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

_KNOWN_SITES = ("google", "youtube", "facebook", "linkedin", "github", "gmail")


@dataclass
class LocalMatch:
    tool_name: str
    arguments: dict


_Matcher = Callable[[str], Optional[LocalMatch]]


def _match_open_site(text: str) -> Optional[LocalMatch]:
    m = re.search(r"\bopen\s+([a-z]+)\b", text)
    if m and m.group(1) in _KNOWN_SITES:
        return LocalMatch("open_browser", {"site_name": m.group(1)})
    return None


def _match_open_application(text: str) -> Optional[LocalMatch]:
    m = re.match(r"^(?:open|launch|start)\s+(.+)$", text)
    if m and m.group(1) not in _KNOWN_SITES:
        return LocalMatch("open_application", {"application_name": m.group(1).strip()})
    return None


def _match_close_application(text: str) -> Optional[LocalMatch]:
    m = re.match(r"^close\s+(.+)$", text)
    if m:
        return LocalMatch("close_application", {"application_name": m.group(1).strip()})
    return None


def _match_battery(text: str) -> Optional[LocalMatch]:
    if "battery" in text:
        return LocalMatch("get_battery_status", {})
    return None


def _match_storage(text: str) -> Optional[LocalMatch]:
    if "storage" in text or "disk space" in text or "free space" in text:
        return LocalMatch("get_storage_status", {})
    return None


def _match_system_info(text: str) -> Optional[LocalMatch]:
    if "system info" in text or "cpu usage" in text or "memory usage" in text:
        return LocalMatch("get_system_information", {})
    return None


def _match_screenshot(text: str) -> Optional[LocalMatch]:
    if "screenshot" in text:
        return LocalMatch("take_screenshot", {})
    return None


def _match_running_apps(text: str) -> Optional[LocalMatch]:
    if "running" in text and ("app" in text or "process" in text):
        return LocalMatch("list_running_applications", {})
    return None


def _match_play_music(text: str) -> Optional[LocalMatch]:
    m = re.match(r"^play\s+(.+)$", text)
    if m:
        return LocalMatch("play_music", {"song": m.group(1).strip()})
    return None


def _match_web_search(text: str) -> Optional[LocalMatch]:
    m = re.match(r"^search(?:\s+(?:google|the web|for))?\s+(?:for\s+)?(.+)$", text)
    if m:
        return LocalMatch("search_web", {"query": m.group(1).strip()})
    return None


def _match_news(text: str) -> Optional[LocalMatch]:
    if "news" in text or "headline" in text:
        category = None
        for cat in ("technology", "business", "sports", "health", "science", "entertainment"):
            if cat in text:
                category = cat
                break
        return LocalMatch("get_news", {"category": category} if category else {})
    return None


def _match_set_volume(text: str) -> Optional[LocalMatch]:
    m = re.search(r"volume\s+to\s+(\d{1,3})", text)
    if m:
        percent = min(100, int(m.group(1)))
        return LocalMatch("set_volume", {"percent": percent})
    return None


# Order matters: more specific patterns first.
_MATCHERS: list[_Matcher] = [
    _match_battery,
    _match_storage,
    _match_system_info,
    _match_screenshot,
    _match_running_apps,
    _match_open_site,
    _match_open_application,
    _match_close_application,
    _match_play_music,
    _match_web_search,
    _match_news,
    _match_set_volume,
]


class LocalCommandRouter:
    """Tries every matcher in order; returns the first hit, or None if the
    LLM planner should handle this instead."""

    def match(self, text: str) -> Optional[LocalMatch]:
        normalized = text.strip().lower()
        for matcher in _MATCHERS:
            result = matcher(normalized)
            if result is not None:
                return result
        return None
