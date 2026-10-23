"""
Tests for the enhanced LocalOrchestrator and multi-task capabilities.
Ensures SARAS can execute local commands, multi-task chains,
conversational queries, and media commands without any external LLM.
"""
from __future__ import annotations

import pytest

from core.context import ContextManager
from core.executor import ExecutionOutcome, Executor
from core.local_orchestrator import LocalOrchestrator
from security.confirmation import ConfirmationService
from security.permissions import PermissionManager
from tools.base import Tool, ToolInput, ToolResult
from tools.registry import ToolRegistry
from voice.wake_word import WakeWordDetector


from security.policies import PermissionLevel


class MockSTT:
    def __init__(self, utterance: str = "saras"):
        self.utterance = utterance

    def listen_once(self, phrase_time_limit=None) -> str:
        return self.utterance


class MockTool(Tool):
    name = "mock_tool"
    description = "Mock tool for testing."
    permission_level = PermissionLevel.SAFE
    input_model = ToolInput

    def run(self, params: ToolInput) -> ToolResult:
        return ToolResult(success=True, message="mock success")


@pytest.fixture
def local_setup():
    registry = ToolRegistry()
    registry.register(MockTool())
    confirmations = ConfirmationService()
    permissions = PermissionManager(confirmations)
    executor = Executor(registry, permissions)
    context = ContextManager()
    orchestrator = LocalOrchestrator(executor, context, confirmations)
    return orchestrator, context


def test_conversational_time(local_setup):
    orchestrator, _ = local_setup
    result = orchestrator.handle("what time is it?")
    assert "current time is" in result.text.lower()


def test_conversational_date(local_setup):
    orchestrator, _ = local_setup
    result = orchestrator.handle("aaj ki date kya hai")
    assert "today is" in result.text.lower()


def test_conversational_identity(local_setup):
    orchestrator, _ = local_setup
    result = orchestrator.handle("tum kaun ho")
    assert "i am saras" in result.text.lower()


def test_conversational_help(local_setup):
    orchestrator, _ = local_setup
    result = orchestrator.handle("help")
    assert "applications" in result.text.lower() or "what i can do" in result.text.lower()


def test_parse_single_tools(local_setup):
    orchestrator, _ = local_setup

    # App
    steps = orchestrator._parse_command("open chrome")
    assert len(steps) == 1
    assert steps[0][0] == "open_application"
    assert steps[0][1]["application_name"] == "chrome"

    # Hindi App
    steps = orchestrator._parse_command("notepad kholo")
    assert len(steps) == 1
    assert steps[0][0] == "open_application"
    assert steps[0][1]["application_name"] == "notepad"

    # Battery
    steps = orchestrator._parse_command("battery kitni hai")
    assert len(steps) == 1
    assert steps[0][0] == "get_battery_status"

    # System Info
    steps = orchestrator._parse_command("tell me system info")
    assert len(steps) == 1
    assert steps[0][0] == "get_system_information"

    # Storage
    steps = orchestrator._parse_command("storage space kitni hai")
    assert len(steps) == 1
    assert steps[0][0] == "get_storage_status"

    # Screenshot
    steps = orchestrator._parse_command("take screenshot")
    assert len(steps) == 1
    assert steps[0][0] == "take_screenshot"

    # Volume
    steps = orchestrator._parse_command("volume 75 karo")
    assert len(steps) == 1
    assert steps[0][0] == "set_volume"
    assert steps[0][1]["percent"] == 75

    # Music
    steps = orchestrator._parse_command("play believer")
    assert len(steps) == 1
    assert steps[0][0] == "play_music"
    assert steps[0][1]["song"] == "believer"

    # Web search
    steps = orchestrator._parse_command("search python tutorial on google")
    assert len(steps) == 1
    assert steps[0][0] == "search_web"
    assert "python tutorial" in steps[0][1]["query"]

    # Web browser website
    steps = orchestrator._parse_command("open youtube")
    assert len(steps) == 1
    assert steps[0][0] == "open_browser"

    # Create folder
    steps = orchestrator._parse_command("create folder called Projects")
    assert len(steps) == 1
    assert steps[0][0] == "create_folder"
    assert steps[0][1]["path"].lower() == "projects"


def test_multi_command_parsing(local_setup):
    orchestrator, _ = local_setup

    # English: and
    steps = orchestrator._parse_command("open chrome and tell me battery")
    assert len(steps) == 2
    assert steps[0][0] == "open_application"
    assert steps[1][0] == "get_battery_status"

    # Hindi: aur
    steps = orchestrator._parse_command("battery batao aur volume 80 karo aur chrome kholo")
    assert len(steps) == 3
    assert steps[0][0] == "get_battery_status"
    assert steps[1][0] == "set_volume"
    assert steps[1][1]["percent"] == 80
    assert steps[2][0] == "open_application"

    # Hindi: aur fir
    steps = orchestrator._parse_command("screenshot lo aur fir play believer")
    assert len(steps) == 2
    assert steps[0][0] == "take_screenshot"
    assert steps[1][0] == "play_music"
    assert steps[1][1]["song"] == "believer"


def test_wake_word_detection_variants():
    # Exact
    stt = MockSTT("saras")
    detector = WakeWordDetector(stt)
    detected, cmd = detector.detect_wake_word()
    assert detected is True
    assert cmd is None

    # Greeting prefix
    stt = MockSTT("hey saras")
    detector = WakeWordDetector(stt)
    detected, cmd = detector.detect_wake_word()
    assert detected is True
    assert cmd is None

    # Embedded single-shot command
    stt = MockSTT("saras open chrome")
    detector = WakeWordDetector(stt)
    detected, cmd = detector.detect_wake_word()
    assert detected is True
    assert cmd == "open chrome"

    # Variant
    stt = MockSTT("hey sarah tell me battery")
    detector = WakeWordDetector(stt)
    detected, cmd = detector.detect_wake_word()
    assert detected is True
    assert cmd == "tell me battery"

    # Unrelated speech
    stt = MockSTT("random other sentence")
    detector = WakeWordDetector(stt)
    detected, cmd = detector.detect_wake_word()
    assert detected is False
    assert cmd is None
