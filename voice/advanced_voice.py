"""
Advanced Voice Session for SARAS.

Provides:
1. Instant acoustic hardware chimes (wake chime, listening prompt, completion).
2. Guaranteed verbal acknowledgment ("Yes, I'm listening!" or "Yes, on it!").
3. Prominent console and UI visual banners.
4. Seamless support for both two-turn ("Saras" -> "Yes?" -> command) and
   single-shot ("Saras open Chrome") voice interactions.
5. Resilient error recovery and noise tolerance.
"""
from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

from core.state import AssistantState, StateManager
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from voice.wake_word import WakeWordDetector
from utils.exceptions import (
    MicrophoneUnavailableError,
    SpeechRecognitionFailedError,
    TextToSpeechError,
)
from utils.logger import get_logger

logger = get_logger("voice.advanced_session")


def play_chime(kind: str = "wake") -> None:
    """Plays quick acoustic hardware chimes on Windows without audio blocking."""
    if sys.platform != "win32":
        return

    def _beep():
        try:
            import winsound
            if kind == "wake":
                winsound.Beep(880, 70)
                winsound.Beep(1320, 100)
            elif kind == "listen":
                winsound.Beep(1320, 50)
            elif kind == "done":
                winsound.Beep(1000, 60)
                winsound.Beep(1400, 80)
            elif kind == "error":
                winsound.Beep(440, 100)
                winsound.Beep(330, 120)
        except Exception:
            pass

    threading.Thread(target=_beep, daemon=True).start()


def safe_print(text: str = "") -> None:
    """Print text safely across any Windows console code page without UnicodeEncodeError."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            print(text.encode(sys.stdout.encoding or "ascii", errors="replace").decode(sys.stdout.encoding or "ascii"))
        except Exception:
            pass


class AdvancedVoiceSession:
    """
    Production-grade Voice Assistant controller for SARAS.
    Ensures immediate user feedback, high sensitivity, and robust execution.
    """

    def __init__(
        self,
        wake_word_detector: WakeWordDetector,
        stt: SpeechToText,
        tts: TextToSpeech,
        on_command: Callable[[str], str],
        state: StateManager,
        acknowledgment_phrase: str = "Yes, I'm listening.",
    ):
        self._wake = wake_word_detector
        self._stt = stt
        self._tts = tts
        self._on_command = on_command
        self._state = state
        self._ack_phrase = acknowledgment_phrase
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def run_forever(self) -> None:
        """Runs the continuous listening loop."""
        self._running = True
        logger.info("Starting Advanced Voice Session...")
        safe_print("\n" + "=" * 56)
        safe_print("[*] SARAS ADVANCED VOICE MODE ACTIVE")
        safe_print("    Wake Word: 'Saras' (or 'Hey Saras', 'Saras suno')")
        safe_print("    Say 'Saras' -> Wait for 'Yes' -> Speak your command")
        safe_print("=" * 56 + "\n")

        play_chime("wake")
        self._speak_safe("SARAS is ready. How can I help you?")

        while self._running:
            try:
                self._cycle_once()
            except Exception as exc:
                logger.exception("Unexpected error in voice cycle: %s", exc)
                self._state.set(AssistantState.IDLE)

    def stop(self) -> None:
        """Stops the voice session cleanly."""
        self._running = False
        logger.info("Advanced Voice Session stopped.")

    def _cycle_once(self) -> None:
        """Executes a single wake-word -> command -> execution turn."""
        self._state.set(AssistantState.LISTENING)

        # 1. Listen for wake word
        try:
            detected, embedded_command = self._wake.detect_wake_word(phrase_time_limit=3.5)
            if not detected:
                return
        except MicrophoneUnavailableError as exc:
            logger.error("Microphone unavailable: %s", exc)
            self._state.set(AssistantState.IDLE)
            return

        # 2. Wake word detected! Play instant chime
        play_chime("wake")
        safe_print("\n+--------------------------------------------------+")
        safe_print("| [!] SARAS: Wake word detected!                   |")
        safe_print("+--------------------------------------------------+")

        command = embedded_command

        # 3. Two-turn flow: user said only the wake word
        if not command:
            logger.info("Wake word detected without command. Giving verbal acknowledgment...")
            self._speak_safe(self._ack_phrase)
            self._state.set(AssistantState.LISTENING)
            play_chime("listen")
            safe_print("[*] Listening for command... (speak now)\n")

            try:
                command = self._stt.listen_once(phrase_time_limit=12.0, timeout=8.0)
                safe_print(f"you> {command}")
            except SpeechRecognitionFailedError:
                play_chime("error")
                self._speak_safe("Sorry, I didn't catch that. Please say Saras again.")
                self._state.set(AssistantState.IDLE)
                return
            except MicrophoneUnavailableError as exc:
                logger.error("Microphone unavailable during command capture: %s", exc)
                self._state.set(AssistantState.IDLE)
                return
        else:
            # Single-shot flow: user said "Saras open Chrome..."
            safe_print(f"you> {command}")
            # Immediate verbal confirmation so user knows it was heard
            self._speak_safe("Yes!")

        # 4. Process and execute command
        self._state.set(AssistantState.PROCESSING)
        safe_print("[*] SARAS processing command...")

        try:
            response_text = self._on_command(command)
        except Exception as exc:
            logger.exception("Unhandled error processing voice command %r", command)
            response_text = "I encountered an error processing that request."

        # 5. Play completion chime and speak response
        play_chime("done")
        self._speak_safe(response_text)
        self._state.set(AssistantState.IDLE)

    def _speak_safe(self, text: str) -> None:
        """Speaks response safely while updating assistant state."""
        if not text or not text.strip():
            return
        self._state.set(AssistantState.SPEAKING)
        try:
            safe_print(f"saras> {text}")
            self._tts.speak(text)
        except TextToSpeechError as exc:
            logger.error("TTS failed: %s", exc)
        finally:
            self._state.set(AssistantState.IDLE)
