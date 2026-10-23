"""
Dependency wiring.

This is the ONLY file that constructs concrete instances of every layer
and connects them.

SARAS supports two execution modes:

1. AI mode:
   Voice/Text -> IntentClassifier -> Planner -> Executor -> Tools
   Uses OpenAI for reasoning and planning.

2. Local mode:
   Voice/Text -> LocalOrchestrator -> Executor -> Tools
   Does NOT initialize or call OpenAI.

The Executor, PermissionManager, ToolRegistry and actual tools are shared
between both modes so security and execution behavior remain consistent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings

from core.assistant import Assistant
from core.context import ContextManager
from core.executor import Executor
from core.local_orchestrator import LocalOrchestrator
from core.orchestrator import Orchestrator
from core.planner import TaskPlanner
from core.state import StateManager

from intelligence.intent import IntentClassifier
from intelligence.llm import LLMService
from intelligence.providers.openai_provider import OpenAIProvider

from memory.database import Database
from memory.long_term import PreferencesStore

from security.command_validator import validate_command  # noqa: F401
from security.confirmation import ConfirmationService
from security.permissions import PermissionManager

from tools.applications.close import CloseApplicationTool
from tools.applications.launch import LaunchApplicationTool
from tools.applications.list import ListRunningApplicationsTool

from tools.browser.open import OpenBrowserTool
from tools.browser.search import WebSearchTool

from tools.filesystem.create import CreateFolderTool
from tools.filesystem.delete import DeleteFilesTool
from tools.filesystem.move import CopyFileTool, MoveFileTool
from tools.filesystem.open import OpenFileTool
from tools.filesystem.search import SearchFilesTool

from tools.media.playback import PlayMusicTool, SearchMusicTool
from tools.news.news import GetNewsTool

from tools.registry import ToolRegistry

from tools.system.information import (
    BatteryStatusTool,
    StorageStatusTool,
    SystemInfoTool,
)
from tools.system.screenshot import ScreenshotTool
from tools.system.volume import SetVolumeTool

from tools.terminal.execute import ExecuteTerminalCommandTool

from utils.logger import configure_logging, get_logger

from voice.audio_manager import AudioManager
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from voice.advanced_voice import AdvancedVoiceSession
from voice.voice_session import VoiceSession
from voice.wake_word import WakeWordDetector


@dataclass
class Application:
    settings: Settings
    db: Database
    preferences: PreferencesStore
    registry: ToolRegistry
    assistant: Assistant
    voice_session: VoiceSession | None


def build_registry() -> ToolRegistry:
    """
    Create and register every SARAS tool.

    The registry is shared by both AI mode and Local mode.
    """

    registry = ToolRegistry()

    tools = [
        # Browser
        OpenBrowserTool(),
        WebSearchTool(),

        # System
        SystemInfoTool(),
        BatteryStatusTool(),
        StorageStatusTool(),
        SetVolumeTool(),
        ScreenshotTool(),

        # Applications
        LaunchApplicationTool(),
        CloseApplicationTool(),
        ListRunningApplicationsTool(),

        # Filesystem
        SearchFilesTool(),
        CreateFolderTool(),
        MoveFileTool(),
        CopyFileTool(),
        DeleteFilesTool(),
        OpenFileTool(),

        # Terminal
        ExecuteTerminalCommandTool(),

        # Media
        PlayMusicTool(),
        SearchMusicTool(),

        # News
        GetNewsTool(),
    ]

    for tool in tools:
        registry.register(tool)

    return registry


def build_application(local_mode: bool = False) -> Application:
    """
    Build the complete SARAS application.

    local_mode=True:
        OpenAI is NOT initialized.
        LocalOrchestrator is used.

    local_mode=False:
        OpenAI is initialized.
        Normal AI Orchestrator is used.
    """

    settings = get_settings()

    configure_logging(
        settings.log_dir,
        settings.log_level,
    )

    logger = get_logger("bootstrap")

    logger.info("Booting SARAS...")

    if local_mode:
        logger.info("SARAS starting in LOCAL mode. OpenAI is disabled.")
    else:
        logger.info("SARAS starting in AI mode.")

    # ---------------------------------------------------------
    # DATABASE / MEMORY
    # ---------------------------------------------------------

    db = Database(settings.db_path)

    preferences = PreferencesStore(db)

    # ---------------------------------------------------------
    # TOOL REGISTRY
    # ---------------------------------------------------------

    registry = build_registry()

    # ---------------------------------------------------------
    # SECURITY / EXECUTION
    # ---------------------------------------------------------

    confirmation_service = ConfirmationService()

    permissions = PermissionManager(
        confirmation_service,
        high_risk_enabled=False,
    )

    executor = Executor(
        registry,
        permissions,
        db=db,
    )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = ContextManager()

    # ---------------------------------------------------------
    # ORCHESTRATOR
    # ---------------------------------------------------------

    local_orchestrator = LocalOrchestrator(
        executor=executor,
        context=context,
        confirmations=confirmation_service,
    )

    has_valid_key = bool(
        settings.openai_api_key
        and not settings.openai_api_key.startswith("sk-proj-placeholder")
        and len(settings.openai_api_key.strip()) > 20
    )

    should_use_local = (
        local_mode
        or settings.local_mode
        or not has_valid_key
        or settings.llm_provider.lower() in {"local", "none"}
    )

    orchestrator = local_orchestrator
    fallback_orchestrator = local_orchestrator

    if not should_use_local:
        try:
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )

            llm = LLMService(provider)

            planner = TaskPlanner(
                llm,
                registry,
            )

            intent_classifier = IntentClassifier(
                llm,
            )

            orchestrator = Orchestrator(
                llm,
                planner,
                executor,
                context,
                intent_classifier,
                local_fallback=local_orchestrator,
            )

            logger.info("AI Orchestrator initialized with OpenAI.")

        except Exception as exc:
            logger.warning(
                "OpenAI initialization failed (%s). Defaulting to LocalOrchestrator.",
                exc,
            )
            orchestrator = local_orchestrator
    else:
        logger.info(
            "LocalOrchestrator active. Offline deterministic mode engaged."
        )

    # ---------------------------------------------------------
    # ASSISTANT
    # ---------------------------------------------------------

    state = StateManager()

    assistant = Assistant(
        orchestrator=orchestrator,
        confirmation_service=confirmation_service,
        state=state,
        fallback_orchestrator=fallback_orchestrator,
    )

    # ---------------------------------------------------------
    # VOICE SUBSYSTEM
    # ---------------------------------------------------------

    voice_session = None

    try:
        audio = AudioManager(
            device_index=settings.microphone_device
        )
        audio.calibrate_ambient_noise(duration=1.0)

        stt = SpeechToText(
            audio,
            listen_timeout=settings.listen_timeout_seconds,
            language=settings.stt_language,
        )

        tts = TextToSpeech(
            engine=settings.tts_engine,
            rate=settings.voice_rate,
        )

        wake = WakeWordDetector(
            stt,
            wake_word=settings.wake_word,
        )

        voice_session = AdvancedVoiceSession(
            wake,
            stt,
            tts,
            on_command=assistant.process_text,
            state=state,
            acknowledgment_phrase="Yes, I'm listening.",
        )

        logger.info("Voice subsystem initialized successfully.")

    except Exception as exc:
        logger.warning(
            "Voice subsystem unavailable (%s). "
            "Falling back to text mode only.",
            exc,
        )

    # ---------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------

    logger.info("SARAS boot complete.")

    return Application(
        settings=settings,
        db=db,
        preferences=preferences,
        registry=registry,
        assistant=assistant,
        voice_session=voice_session,
    )