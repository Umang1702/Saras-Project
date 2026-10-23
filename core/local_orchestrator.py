"""
Local command orchestrator.

Handles common desktop/personal commands without using an LLM.
It intentionally reuses the normal Executor so that validation,
permissions, confirmation, execution, verification and logging remain
identical to the AI-driven path.
"""

from __future__ import annotations

from datetime import datetime
import re
from dataclasses import dataclass

from core.context import ContextManager
from core.executor import Executor
from intelligence.response import StepOutcome, summarize
from security.confirmation import ConfirmationService
from utils.exceptions import SarasError
from utils.logger import get_logger


logger = get_logger("core.local_orchestrator")


@dataclass
class LocalOrchestratorResult:
    text: str
    pending_confirmation_id: str | None = None
    pending_tool_name: str | None = None
    pending_arguments: dict | None = None
    remaining_steps: list | None = None


class LocalOrchestrator:
    """
    Deterministic local command router.

    No OpenAI, no LLM and no planner are used here.
    """

    def __init__(
        self,
        executor: Executor,
        context: ContextManager,
        confirmations: ConfirmationService,
    ):
        self._executor = executor
        self._context = context
        self._confirmations = confirmations

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def handle(self, user_text: str) -> LocalOrchestratorResult:
        self._context.add_turn("user", user_text)

        # 1. Offline conversational queries (time, date, identity, help)
        conversational_reply = self._handle_conversational(user_text)
        if conversational_reply is not None:
            self._context.add_turn("assistant", conversational_reply)
            return LocalOrchestratorResult(text=conversational_reply)

        try:
            steps = self._parse_command(user_text)

            if not steps:
                text = (
                    "I couldn't understand that command. "
                    "Try saying 'open Chrome', 'battery batao', 'play Believer', "
                    "'search Python on Google', 'volume 80', or ask 'what time is it?'."
                )
                self._context.add_turn("assistant", text)
                return LocalOrchestratorResult(text=text)

            outcomes: list[StepOutcome] = []

            for index, (tool_name, arguments) in enumerate(steps):
                logger.info(
                    "Local command mapped: %s -> %s %s",
                    user_text,
                    tool_name,
                    arguments,
                )

                outcome = self._executor.execute(tool_name, arguments)

                if outcome.needs_confirmation and outcome.confirmation:
                    prompt = (
                        f"{outcome.confirmation.detail}\n\n"
                        "Do you want me to continue? (yes/no)"
                    )

                    self._context.add_turn("assistant", prompt)

                    return LocalOrchestratorResult(
                        text=prompt,
                        pending_confirmation_id=outcome.confirmation.id,
                        pending_tool_name=tool_name,
                        pending_arguments=arguments,
                        remaining_steps=steps[index + 1 :],
                    )

                self._context.record_tool_result(
                    tool_name,
                    outcome.result,
                )

                message = outcome.result.message

                if outcome.verification_issue:
                    message += f" (Note: {outcome.verification_issue})"

                outcomes.append(
                    StepOutcome(
                        tool_name=tool_name,
                        success=outcome.result.success,
                        message=message,
                    )
                )

            text = summarize(outcomes)
            self._context.add_turn("assistant", text)

            return LocalOrchestratorResult(text=text)

        except SarasError as exc:
            logger.warning("Local command failed: %s", exc)

            text = f"I couldn't do that: {exc}"
            self._context.add_turn("assistant", text)

            return LocalOrchestratorResult(text=text)

        except Exception as exc:
            logger.exception("Unexpected local command failure")

            text = f"I couldn't complete that command: {exc}"
            self._context.add_turn("assistant", text)

            return LocalOrchestratorResult(text=text)

    # ---------------------------------------------------------
    # CONFIRMATION RESUME
    # ---------------------------------------------------------

    def resume_confirmed_step(
        self,
        tool_name: str,
        arguments: dict,
        remaining_steps: list,
    ) -> LocalOrchestratorResult:

        outcomes: list[StepOutcome] = []

        outcome = self._executor.execute_confirmed(
            tool_name,
            arguments,
        )

        self._context.record_tool_result(
            tool_name,
            outcome.result,
        )

        message = outcome.result.message

        if outcome.verification_issue:
            message += f" (Note: {outcome.verification_issue})"

        outcomes.append(
            StepOutcome(
                tool_name=tool_name,
                success=outcome.result.success,
                message=message,
            )
        )

        for index, step in enumerate(remaining_steps or []):
            next_tool, next_arguments = step

            next_outcome = self._executor.execute(
                next_tool,
                next_arguments,
            )

            if (
                next_outcome.needs_confirmation
                and next_outcome.confirmation
            ):
                prompt = (
                    f"{next_outcome.confirmation.detail}\n\n"
                    "Do you want me to continue? (yes/no)"
                )

                return LocalOrchestratorResult(
                    text=prompt,
                    pending_confirmation_id=next_outcome.confirmation.id,
                    pending_tool_name=next_tool,
                    pending_arguments=next_arguments,
                    remaining_steps=remaining_steps[index + 1 :],
                )

            self._context.record_tool_result(
                next_tool,
                next_outcome.result,
            )

            msg = next_outcome.result.message

            if next_outcome.verification_issue:
                msg += f" (Note: {next_outcome.verification_issue})"

            outcomes.append(
                StepOutcome(
                    tool_name=next_tool,
                    success=next_outcome.result.success,
                    message=msg,
                )
            )

        text = summarize(outcomes)
        self._context.add_turn("assistant", text)

        return LocalOrchestratorResult(text=text)

    # ---------------------------------------------------------
    # LOCAL COMMAND PARSER
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # OFFLINE CONVERSATIONAL / INTENT HANDLER
    # ---------------------------------------------------------

    def _handle_conversational(self, text: str) -> str | None:
        norm = self._normalize(text)
        norm = re.sub(r"^\s*(?:hey|hello|hi|suno|ok|okay)?\s*saras[\s,:-]*", "", norm).strip()

        if not norm:
            return "Hello! I am SARAS. How can I help you today?"

        # Time query
        if any(p in norm for p in ["what time", "what is the time", "current time", "time kya", "kitne baje", "batao time", "time bata", "samay kya"]):
            now_str = datetime.now().strftime("%I:%M %p")
            return f"The current time is {now_str}."

        # Date query
        if any(p in norm for p in ["what date", "what is the date", "today's date", "todays date", "date kya", "aaj ki date", "aaj kaun sa din", "what day is today", "tarikh kya"]):
            date_str = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {date_str}."

        # Identity & Name
        if any(p in norm for p in ["who are you", "what is your name", "tum kaun ho", "tera naam", "naam kya", "who made you", "kaun ho tum"]):
            return "I am SARAS, your personal AI desktop agent for Windows."

        # Greetings
        if norm in {"hello", "hi", "hey", "namaste", "suno", "kaise ho", "how are you", "kaisa chal raha hai"}:
            return "Hello! I'm SARAS, active and ready for your commands. What would you like to do?"

        # Help & Capabilities
        if any(p in norm for p in ["what can you do", "help", "kya kar sakte ho", "commands", "features", "madad", "capabilities"]):
            return (
                "Here is what I can do for you locally without any external API key:\n"
                "• Applications: 'Open Chrome', 'Launch Notepad', 'Calculator kholo', 'Band karo Edge'\n"
                "• Web Search: 'Search Python tutorials on Google', 'Google par search karo machine learning'\n"
                "• Websites: 'Open YouTube', 'Go to GitHub', 'Open ChatGPT'\n"
                "• Music: 'Play Believer', 'Arijit Singh ke gane chalao'\n"
                "• System Info: 'Battery status', 'RAM usage', 'Storage space', 'List running apps'\n"
                "• Audio & Screen: 'Take screenshot', 'Set volume to 80', 'Volume 50 karo'\n"
                "• Files & Folders: 'Create folder Projects', 'Search files in Downloads'\n"
                "• Multi-Tasking: 'Open Chrome and tell me battery and play Believer'"
            )

        return None

    # ---------------------------------------------------------
    # LOCAL COMMAND PARSER
    # ---------------------------------------------------------

    def _parse_command(self, text: str) -> list[tuple[str, dict]]:
        normalized = self._normalize(text)
        normalized = re.sub(r"^\s*saras[\s,:-]*", "", normalized)

        raw_parts = self._split_multi_command(normalized)
        if not raw_parts:
            return []

        # Merge parts that cannot stand alone as independent commands
        merged_parts: list[str] = []
        for part in raw_parts:
            if not merged_parts:
                merged_parts.append(part)
            else:
                if self._parse_single(part) is not None:
                    merged_parts.append(part)
                else:
                    merged_parts[-1] = merged_parts[-1] + " and " + part

        steps: list[tuple[str, dict]] = []
        for part in merged_parts:
            parsed = self._parse_single(part)
            if parsed:
                steps.append(parsed)

        return steps

    def _parse_single(self, command: str) -> tuple[str, dict] | None:
        cmd = command.strip()
        if not cmd:
            return None

        # -----------------------------------------------------
        # MUSIC & MEDIA
        # -----------------------------------------------------
        music_match = re.search(r"^(?:play|chalao|bajao)\s+(?:song|music|gana)?\s*(.+?)(?:\s+(?:song|music|gana|chalao|bajao|karo))?$", cmd)
        if not music_match:
            music_match = re.search(r"^(.+?)\s+(?:song|gana)\s+(?:play|chalao|bajao|karo)$", cmd)
        if music_match:
            song = music_match.group(1).strip()
            if song and song not in {"music", "song", "gana", "kuch"}:
                return ("play_music", {"song": song})

        search_music_match = re.search(r"^(?:search\s+music|search\s+song|gana\s+dhoondo)\s+(.+)$", cmd)
        if search_music_match:
            return ("search_music", {"query": search_music_match.group(1).strip()})

        # -----------------------------------------------------
        # WEB SEARCH
        # -----------------------------------------------------
        search_match = re.search(r"^(?:search\s+google\s+for|search\s+on\s+google\s+for|search\s+for)\s+(.+)$", cmd)
        if not search_match:
            search_match = re.search(r"^(?:search|google|dhoondo|khojo)\s+(.+?)(?:\s+(?:on|in|par)\s+google)?$", cmd)
        if not search_match:
            search_match = re.search(r"^(.+?)\s+(?:google\s+par\s+search\s+karo|par\s+search\s+karo|search\s+karo)$", cmd)
        if search_match:
            q = search_match.group(1).strip()
            if q and not any(q.startswith(w) for w in ["music", "song", "file", "folder", "running"]):
                return ("search_web", {"query": q})

        # -----------------------------------------------------
        # WEBSITES & BROWSING
        # -----------------------------------------------------
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
            "wikipedia": "https://www.wikipedia.org",
        }
        site_match = re.search(r"^(?:open|go\s+to|visit|kholo)\s+(?:website\s+|site\s+)?(.+)$", cmd)
        if site_match:
            target = site_match.group(1).strip().lower()
            if target in known_sites:
                return ("open_browser", {"url": known_sites[target], "site_name": target})
            if target.startswith(("http://", "https://", "www.")) or target.endswith((".com", ".org", ".net", ".io", ".in", ".co")):
                url = target if target.startswith(("http://", "https://")) else f"https://{target}"
                return ("open_browser", {"url": url})

        # -----------------------------------------------------
        # RUNNING APPLICATIONS
        # -----------------------------------------------------
        if any(p in cmd for p in ["list running", "running applications", "running apps", "running processes", "konsi apps chal rahi", "kya chal raha hai"]):
            return ("list_running_applications", {"limit": 10})

        # -----------------------------------------------------
        # APPLICATIONS (Launch & Close)
        # -----------------------------------------------------
        app = self._extract_app_name(
            cmd,
            [
                r"^(?:open|launch|start|run)\s+(?:app\s+|application\s+)?(.+)$",
                r"^(.+?)\s+(?:open|start|launch)\s*(?:karo|kar do)?$",
                r"^(.+?)\s+(?:khol[o]?|chalao|chala do|shuru karo)$",
            ],
        )
        if app:
            cleaned = self._clean_app_name(app)
            if cleaned.lower() in known_sites:
                return ("open_browser", {"url": known_sites[cleaned.lower()], "site_name": cleaned.lower()})
            return (
                "open_application",
                {
                    "application_name": cleaned,
                    "arguments": [],
                },
            )

        app = self._extract_app_name(
            cmd,
            [
                r"^(?:close|quit|exit|stop|kill)\s+(?:app\s+|application\s+)?(.+)$",
                r"^(.+?)\s+(?:close|band karo|band kar do|rok do)$",
            ],
        )
        if app:
            return (
                "close_application",
                {
                    "application_name": self._clean_app_name(app),
                },
            )

        # -----------------------------------------------------
        # BATTERY
        # -----------------------------------------------------
        if any(p in cmd for p in [
            "battery",
            "battery status",
            "battery percentage",
            "battery kitni",
            "battery bata",
            "charge kitna",
            "charge bata",
        ]):
            return ("get_battery_status", {})

        # -----------------------------------------------------
        # SYSTEM INFORMATION
        # -----------------------------------------------------
        if any(p in cmd for p in [
            "system information",
            "system info",
            "system status",
            "cpu usage",
            "ram usage",
            "memory usage",
            "computer information",
            "system bata",
            "specs",
        ]):
            return ("get_system_information", {})

        # -----------------------------------------------------
        # STORAGE
        # -----------------------------------------------------
        if any(p in cmd for p in [
            "storage",
            "disk space",
            "free space",
            "hard disk",
            "disk status",
            "storage bata",
            "space kitni",
        ]):
            return ("get_storage_status", {})

        # -----------------------------------------------------
        # SCREENSHOT
        # -----------------------------------------------------
        if any(p in cmd for p in [
            "screenshot",
            "screen shot",
            "screen capture",
            "screen photo",
            "screenshot lo",
            "screenshot le",
            "screen capture karo",
            "capture screen",
        ]):
            return ("take_screenshot", {})

        # -----------------------------------------------------
        # VOLUME
        # -----------------------------------------------------
        volume_match = re.search(r"(?:volume|sound|awaaz)\s*(?:to|at|ko)?\s*(\d{1,3})", cmd)
        if not volume_match:
            volume_match = re.search(r"(\d{1,3})\s*(?:percent|%)\s*(?:volume|sound|awaaz)", cmd)
        if volume_match:
            percent = max(0, min(100, int(volume_match.group(1))))
            return ("set_volume", {"percent": percent})

        # -----------------------------------------------------
        # FILESYSTEM
        # -----------------------------------------------------
        folder_match = re.search(r"^(?:create|make|naya)\s+(?:a\s+)?(?:folder|directory)\s+(?:called|named|ka\s+naam)?\s*(.+?)(?:\s*(?:banao|karo))?$", cmd)
        if folder_match:
            folder_name = folder_match.group(1).strip().strip("'\"")
            if folder_name and folder_name not in {"folder", "directory"}:
                return ("create_folder", {"path": folder_name})

        open_file_match = re.search(r"^(?:open|kholo)\s+(?:file|document)\s+(.+)$", cmd)
        if open_file_match:
            return ("open_file", {"path": open_file_match.group(1).strip().strip("'\"")})

        delete_file_match = re.search(r"^(?:delete|remove|hatao)\s+(?:file|files|the\s+file)\s+(.+)$", cmd)
        if delete_file_match:
            path = delete_file_match.group(1).strip().strip("'\"")
            return ("delete_files", {"paths": [path]})

        search_file_match = re.search(r"^(?:find|search|dhoondo)\s+(?:all\s+)?(?:files|documents|pdfs?|images?)\s+(?:in\s+(.+?)\s+for\s+(.+)|for\s+(.+?)\s+in\s+(.+)|named\s+(.+)|in\s+(.+))$", cmd)
        if search_file_match:
            g = [x for x in search_file_match.groups() if x]
            query = g[-1].strip() if g else "*"
            path = g[0].strip() if len(g) > 1 else "."
            return ("search_files", {"query": query, "search_path": path})

        # -----------------------------------------------------
        # TERMINAL
        # -----------------------------------------------------
        term_match = re.search(r"^(?:run|execute|chalao)\s+(?:terminal\s+command\s+|command\s+|terminal\s+me\s+)?(git status|dir|ipconfig|ping\s+\S+|python\s+--version|echo\s+.+)$", cmd)
        if term_match:
            return ("execute_terminal_command", {"command": term_match.group(1).strip()})

        return None

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()

        replacements = {
            "google chrome": "chrome",
            "chrome browser": "chrome",
            "visual studio code": "vs code",
            "visual studio": "vs code",
            "vs-code": "vs code",
            "calculator app": "calculator",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _clean_app_name(name: str) -> str:
        name = name.strip()

        removable = [
            " please",
            " please karo",
            " karo",
            " kar do",
            " ko",
            " app",
            " application",
        ]

        changed = True
        while changed:
            changed = False
            for suffix in removable:
                if name.endswith(suffix):
                    name = name[: -len(suffix)].strip()
                    changed = True

        return name

    @staticmethod
    def _extract_app_name(
        command: str,
        patterns: list[str],
    ) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                value = match.group(1).strip()
                if value:
                    return value
        return None

    @staticmethod
    def _split_multi_command(command: str) -> list[str]:
        pattern = (
            r"\s+(?:and\s+then|after\s+that|aur\s+fir|aur\s+phir|ke\s+baad)\s+"
            r"|\s+(?:and|aur|then|fir|phir|tatha)\s+"
            r"|\s*;\s*"
            r"|\s*,\s*"
        )
        parts = re.split(pattern, command)
        return [part.strip() for part in parts if part.strip()]