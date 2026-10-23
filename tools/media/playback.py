"""
Music playback tool.

Preserves the original musicLibrary.py behaviour (open a YouTube link) but
as a proper tool with a searchable library instead of a bare dict import
scattered through if/elif logic, and with graceful handling of unknown
songs instead of a raw KeyError crashing the whole assistant.
"""
from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Optional

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult

_DEFAULT_LIBRARY = {
    "perfect": "https://www.youtube.com/watch?v=kPhpHvnnn0Q",
    "blue": "https://www.youtube.com/watch?v=GFGPSx6cPN0",
    "baby": "https://www.youtube.com/watch?v=kffacxfA7G4",
    "believer": "https://www.youtube.com/watch?v=W0DM5lcj6mw",
    "weapon": "https://www.youtube.com/watch?v=5VubhvUQaD8",
    "hanuman": "https://www.youtube.com/watch?v=AETFvQonfV8",
}


def _library_path() -> Path:
    from app.config import get_settings
    return Path(get_settings().data_dir) / "music_library.json"


def _load_library() -> dict:
    path = _library_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return dict(_DEFAULT_LIBRARY)


def _save_library(library: dict) -> None:
    path = _library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(library, indent=2))


class PlayMusicInput(ToolInput):
    song: str = Field(description="Name of the song to play, matched against the music library.")


class PlayMusicTool(Tool):
    name = "play_music"
    description = "Play a song by name from the SARAS music library (opens it in the browser)."
    permission_level = PermissionLevel.LOW_RISK
    input_model = PlayMusicInput

    def run(self, params: PlayMusicInput) -> ToolResult:
        library = _load_library()
        key = params.song.strip().lower()
        link = library.get(key)
        if not link:
            # Check for partial match in library
            close = [name for name in library if key in name or name in key]
            if close:
                link = library[close[0]]
                webbrowser.open(link)
                return ToolResult(
                    success=True,
                    message=f"Playing '{close[0]}' from library.",
                    data={"url": link, "source": "library"},
                )

            # Fallback to direct YouTube search so ANY requested song works
            import urllib.parse
            query_encoded = urllib.parse.quote_plus(params.song)
            youtube_url = f"https://www.youtube.com/results?search_query={query_encoded}"
            webbrowser.open(youtube_url)
            return ToolResult(
                success=True,
                message=f"Playing '{params.song}' on YouTube.",
                data={"url": youtube_url, "source": "youtube_search"},
            )

        webbrowser.open(link)
        return ToolResult(success=True, message=f"Playing {params.song}.", data={"url": link, "source": "library"})


class SearchMusicInput(ToolInput):
    query: str = Field(description="Partial song name to search the library for.")


class SearchMusicTool(Tool):
    name = "search_music"
    description = "Search the music library for songs matching a partial name."
    permission_level = PermissionLevel.SAFE
    input_model = SearchMusicInput

    def run(self, params: SearchMusicInput) -> ToolResult:
        library = _load_library()
        matches = [name for name in library if params.query.lower() in name]
        message = f"Found {len(matches)} match(es): {', '.join(matches)}." if matches else "No matches found."
        return ToolResult(success=True, message=message, data={"matches": matches})
