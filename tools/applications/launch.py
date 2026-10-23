"""
Launch an application by name.

Supports:
- Applications available on PATH
- Common Windows installation locations
- Common application aliases
- Direct executable paths
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


# ---------------------------------------------------------
# APPLICATION ALIASES
# ---------------------------------------------------------

_APP_ALIASES: dict[str, list[str]] = {
    "chrome": ["chrome.exe", "chrome", "google-chrome"],
    "google chrome": ["chrome.exe", "chrome", "google-chrome"],
    "edge": ["msedge.exe", "msedge"],
    "microsoft edge": ["msedge.exe", "msedge"],
    "vs code": ["code.exe", "code"],
    "vscode": ["code.exe", "code"],
    "visual studio code": ["code.exe", "code"],
    "firefox": ["firefox.exe", "firefox"],
    "notepad": ["notepad.exe", "notepad"],
    "calculator": ["calc.exe", "calc"],
    "calc": ["calc.exe", "calc"],
    "paint": ["mspaint.exe", "mspaint"],
    "terminal": ["wt.exe", "wt", "cmd.exe", "cmd"],
    "cmd": ["cmd.exe", "cmd"],
    "powershell": ["powershell.exe", "powershell"],
    "explorer": ["explorer.exe", "explorer"],
    "task manager": ["taskmgr.exe", "taskmgr"],
    "taskmgr": ["taskmgr.exe", "taskmgr"],
    "word": ["winword.exe", "winword"],
    "excel": ["excel.exe", "excel"],
    "powerpoint": ["powerpnt.exe", "powerpnt"],
    "spotify": ["spotify.exe", "spotify"],
}


class LaunchApplicationInput(ToolInput):
    application_name: str = Field(
        description=(
            "Name of the application to launch, "
            "for example 'Chrome' or 'VS Code'."
        )
    )

    arguments: list[str] = Field(
        default_factory=list,
        description=(
            "Optional command-line arguments, "
            "such as a file or folder path."
        ),
    )


class LaunchApplicationTool(Tool):

    name = "open_application"

    description = (
        "Launch a desktop application by name, optionally "
        "with command-line arguments."
    )

    permission_level = PermissionLevel.LOW_RISK

    input_model = LaunchApplicationInput

    # -----------------------------------------------------
    # WINDOWS INSTALLATION LOCATIONS
    # -----------------------------------------------------

    def _windows_candidates(
        self,
        application_name: str,
    ) -> list[Path]:

        if os.name != "nt":
            return []

        name = application_name.strip().lower()

        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            "",
        )

        program_files = os.environ.get(
            "PROGRAMFILES",
            "",
        )

        program_files_x86 = os.environ.get(
            "PROGRAMFILES(X86)",
            "",
        )

        candidates: list[Path] = []

        # -------------------------------------------------
        # GOOGLE CHROME
        # -------------------------------------------------

        if name in {"chrome", "google chrome"}:

            if local_app_data:
                candidates.extend(
                    [
                        Path(local_app_data)
                        / "Google"
                        / "Chrome"
                        / "Application"
                        / "chrome.exe",

                        Path(local_app_data)
                        / "Google"
                        / "Chrome SxS"
                        / "Application"
                        / "chrome.exe",
                    ]
                )

            if program_files:
                candidates.append(
                    Path(program_files)
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                )

            if program_files_x86:
                candidates.append(
                    Path(program_files_x86)
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                )

        # -------------------------------------------------
        # VISUAL STUDIO CODE
        # -------------------------------------------------

        elif name in {
            "vs code",
            "vscode",
            "visual studio code",
        }:

            if local_app_data:
                candidates.append(
                    Path(local_app_data)
                    / "Programs"
                    / "Microsoft VS Code"
                    / "Code.exe"
                )

            if program_files:
                candidates.append(
                    Path(program_files)
                    / "Microsoft VS Code"
                    / "Code.exe"
                )

            if program_files_x86:
                candidates.append(
                    Path(program_files_x86)
                    / "Microsoft VS Code"
                    / "Code.exe"
                )

        # -------------------------------------------------
        # FIREFOX
        # -------------------------------------------------

        elif name == "firefox":

            if program_files:
                candidates.append(
                    Path(program_files)
                    / "Mozilla Firefox"
                    / "firefox.exe"
                )

            if program_files_x86:
                candidates.append(
                    Path(program_files_x86)
                    / "Mozilla Firefox"
                    / "firefox.exe"
                )

        # -------------------------------------------------
        # SPOTIFY
        # -------------------------------------------------

        elif name == "spotify":

            if local_app_data:
                candidates.append(
                    Path(local_app_data)
                    / "Spotify"
                    / "Spotify.exe"
                )

        return candidates

    # -----------------------------------------------------
    # RESOLVE EXECUTABLE
    # -----------------------------------------------------

    def _resolve_executable(
        self,
        application_name: str,
    ) -> str | None:

        key = application_name.strip().lower()

        candidates = _APP_ALIASES.get(
            key,
            [application_name],
        )

        # First: search PATH
        for candidate in candidates:
            resolved = shutil.which(candidate)

            if resolved:
                return resolved

        # Second: search standard Windows locations
        for path in self._windows_candidates(
            application_name
        ):
            if path.exists() and path.is_file():
                return str(path)

        # Third: allow a direct executable path
        direct_path = Path(application_name)

        if direct_path.exists() and direct_path.is_file():
            return str(direct_path)

        return None

    # -----------------------------------------------------
    # EXECUTE
    # -----------------------------------------------------

    def run(
        self,
        params: LaunchApplicationInput,
    ) -> ToolResult:

        application_name = (
            params.application_name.strip()
        )

        if not application_name:
            return ToolResult(
                success=False,
                message="No application name was provided.",
                error="empty_application_name",
            )

        resolved = self._resolve_executable(
            application_name
        )

        if resolved is None:
            # Check if application_name is actually a known website or web domain
            known_sites = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "github": "https://www.github.com",
                "twitter": "https://www.twitter.com",
                "x": "https://www.x.com",
                "reddit": "https://www.reddit.com",
                "instagram": "https://www.instagram.com",
                "facebook": "https://www.facebook.com",
                "gmail": "https://mail.google.com",
                "chatgpt": "https://chatgpt.com",
                "netflix": "https://www.netflix.com",
                "linkedin": "https://www.linkedin.com",
                "whatsapp": "https://web.whatsapp.com",
            }
            app_lower = application_name.lower().strip()
            target_url = known_sites.get(app_lower)
            if not target_url and (app_lower.endswith((".com", ".org", ".net", ".io", ".in", ".co")) or "www." in app_lower):
                target_url = app_lower if app_lower.startswith(("http://", "https://")) else f"https://{app_lower}"

            if target_url:
                import webbrowser
                webbrowser.open(target_url)
                return ToolResult(
                    success=True,
                    message=f"Opened {application_name} in your browser.",
                    data={"url": target_url, "type": "web_url"},
                )

            return ToolResult(
                success=False,
                message=(
                    f"I couldn't find '{application_name}' "
                    "in PATH or common Windows installation "
                    "locations."
                ),
                error="app_not_found",
            )

        try:

            subprocess.Popen(
                [
                    resolved,
                    *params.arguments,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

        except Exception as exc:

            return ToolResult(
                success=False,
                message=(
                    f"Failed to launch "
                    f"{application_name}."
                ),
                error=str(exc),
            )

        return ToolResult(
            success=True,
            message=f"Opening {application_name}.",
            data={
                "executable": resolved,
            },
        )

    # -----------------------------------------------------
    # VERIFY
    # -----------------------------------------------------

    def verify(
        self,
        params: LaunchApplicationInput,
        result: ToolResult,
    ) -> str | None:

        if not result.success:
            return None

        import psutil

        executable = (
            result.data or {}
        ).get(
            "executable",
            "",
        )

        if not executable:
            return "Application executable could not be verified."

        executable_name = (
            Path(executable)
            .name
            .lower()
        )

        # Give Windows a moment to start the process.
        time.sleep(1.0)

        for process in psutil.process_iter(
            ["name"]
        ):
            try:

                process_name = (
                    process.info["name"]
                    or ""
                ).lower()

                if (
                    process_name == executable_name
                    or executable_name in process_name
                ):
                    return None

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        return (
            f"{params.application_name} was launched, "
            "but its process could not be verified."
        )