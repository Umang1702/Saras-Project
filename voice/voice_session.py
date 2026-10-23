"""
Orchestrates the listening/processing/speaking state machine for a single
voice interaction cycle: wait for wake word -> listen for command -> hand
off to a callback (the Assistant) -> speak the response.

Errors at any stage (microphone unavailable, recognition failure) are
caught and reported instead of crashing the whole loop, unlike the original
main.py's single bare `except Exception as e: print(...)` around everything.
"""
from __future__ import annotations

from typing import Callable

from core.state import AssistantState, StateManager
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from voice.wake_word import WakeWordDetector
from utils.exceptions import MicrophoneUnavailableError, SpeechRecognitionFailedError, TextToSpeechError
from utils.logger import get_logger

logger = get_logger("voice.session")


from voice.advanced_voice import AdvancedVoiceSession, play_chime

# The Advanced Voice Engine is the primary, production-grade VoiceSession
class VoiceSession(AdvancedVoiceSession):
    """
    Primary voice session for SARAS.
    Inherits all advanced capabilities from AdvancedVoiceSession:
    - Zero-latency acoustic chimes
    - Guaranteed "Yes, I'm listening!" verbal feedback
    - Resilient wake-word detection & single-shot handling
    """
    pass

__all__ = ["VoiceSession", "AdvancedVoiceSession", "play_chime"]
