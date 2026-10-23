"""
Tests for AdvancedVoiceSession and WakeWordDetector.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from core.state import AssistantState, StateManager
from utils.exceptions import MicrophoneUnavailableError, SpeechRecognitionFailedError
from voice.advanced_voice import AdvancedVoiceSession
from voice.wake_word import WakeWordDetector


class MockSTT:
    def __init__(self, utterances: list[str] | str):
        if isinstance(utterances, str):
            self.utterances = [utterances]
        else:
            self.utterances = list(utterances)
        self.call_count = 0

    def listen_once(self, phrase_time_limit=None, timeout=None) -> str:
        self.call_count += 1
        if not self.utterances:
            raise SpeechRecognitionFailedError("No more mock utterances")
        val = self.utterances.pop(0)
        if isinstance(val, Exception):
            raise val
        return val


class MockTTS:
    def __init__(self):
        self.spoken = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


def test_wake_word_two_turn_utterances():
    """Verify various forms of saying just the wake word."""
    test_cases = [
        "saras",
        "Hey saras",
        "hello Saras",
        "ok saras",
        "suno saras",
        "Saras suno",
        "saras bhai",
        "sarah",
        "sharas",
        "zaras",
        "service",
        "सारस",
        "सरस",
    ]
    for utterance in test_cases:
        stt = MockSTT(utterance)
        detector = WakeWordDetector(stt=stt, wake_word="saras")
        detected, cmd = detector.detect_wake_word()
        assert detected is True, f"Failed to detect wake word in {utterance!r}"
        assert cmd is None or cmd == "", f"Expected no embedded command in {utterance!r}, got {cmd!r}"


def test_wake_word_single_shot_extraction():
    """Verify wake word + embedded command extraction."""
    test_cases = [
        ("saras open chrome", "open chrome"),
        ("hey saras open chrome", "open chrome"),
        ("saras suno battery batao", "battery batao"),
        ("ok saras search python on google", "search python on google"),
        ("suno saras bhai volume 50 karo", "volume 50 karo"),
    ]
    for utterance, expected_cmd in test_cases:
        stt = MockSTT(utterance)
        detector = WakeWordDetector(stt=stt, wake_word="saras")
        detected, cmd = detector.detect_wake_word()
        assert detected is True, f"Failed to detect wake word in {utterance!r}"
        assert cmd == expected_cmd, f"Expected command {expected_cmd!r}, got {cmd!r}"


def test_wake_word_non_matches():
    """Verify unrelated phrases do not trigger wake word."""
    non_matches = [
        "open the browser",
        "hello there my friend",
        "what is the weather today",
        "play some music please",
    ]
    for utterance in non_matches:
        stt = MockSTT(utterance)
        detector = WakeWordDetector(stt=stt, wake_word="saras")
        detected, cmd = detector.detect_wake_word()
        assert detected is False, f"False positive for {utterance!r}"
        assert cmd is None


def test_advanced_voice_session_two_turn_flow():
    """User says 'Saras' -> Assistant responds 'Yes, I'm listening.' -> User says command -> Executed."""
    stt = MockSTT(["saras", "tell me the time"])
    tts = MockTTS()
    state = StateManager()
    on_cmd = MagicMock(return_value="The time is 2:30 PM.")

    detector = WakeWordDetector(stt=stt, wake_word="saras")
    session = AdvancedVoiceSession(
        wake_word_detector=detector,
        stt=stt,
        tts=tts,
        on_command=on_cmd,
        state=state,
        acknowledgment_phrase="Yes, I'm listening.",
    )

    with patch("voice.advanced_voice.play_chime"):
        session._cycle_once()

    # Verify verbal acknowledgment "Yes, I'm listening." was spoken
    assert "Yes, I'm listening." in tts.spoken
    # Verify command was executed
    on_cmd.assert_called_once_with("tell me the time")
    # Verify final answer was spoken
    assert "The time is 2:30 PM." in tts.spoken
    assert state.state == AssistantState.IDLE


def test_advanced_voice_session_single_shot_flow():
    """User says 'Saras open chrome' -> Assistant acknowledges 'Yes!' -> Executed."""
    stt = MockSTT(["saras open chrome"])
    tts = MockTTS()
    state = StateManager()
    on_cmd = MagicMock(return_value="Opening Google Chrome.")

    detector = WakeWordDetector(stt=stt, wake_word="saras")
    session = AdvancedVoiceSession(
        wake_word_detector=detector,
        stt=stt,
        tts=tts,
        on_command=on_cmd,
        state=state,
    )

    with patch("voice.advanced_voice.play_chime"):
        session._cycle_once()

    # Single-shot acknowledgment
    assert "Yes!" in tts.spoken
    on_cmd.assert_called_once_with("open chrome")
    assert "Opening Google Chrome." in tts.spoken
    assert state.state == AssistantState.IDLE


def test_advanced_voice_session_speech_recognition_error_recovery():
    """User says 'Saras' -> STT fails to recognize command -> Assistant speaks 'Sorry' -> Returns to IDLE."""
    stt = MockSTT(["saras", SpeechRecognitionFailedError("noise")])
    tts = MockTTS()
    state = StateManager()
    on_cmd = MagicMock()

    detector = WakeWordDetector(stt=stt, wake_word="saras")
    session = AdvancedVoiceSession(
        wake_word_detector=detector,
        stt=stt,
        tts=tts,
        on_command=on_cmd,
        state=state,
    )

    with patch("voice.advanced_voice.play_chime"):
        session._cycle_once()

    assert "Yes, I'm listening." in tts.spoken
    assert any("Sorry" in phrase for phrase in tts.spoken)
    on_cmd.assert_not_called()
    assert state.state == AssistantState.IDLE
