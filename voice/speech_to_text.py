"""
Speech-to-text abstraction.

Uses SpeechRecognition with Google's Web Speech backend.
"""

from __future__ import annotations

from typing import Optional

import speech_recognition as sr

from voice.audio_manager import AudioManager
from utils.exceptions import (
    SpeechRecognitionFailedError,
)
from utils.logger import get_logger

logger = get_logger("voice.stt")


class SpeechToText:
    def __init__(
        self,
        audio_manager: AudioManager,
        listen_timeout: int = 10,
        language: str = "en-IN",
    ):
        self._audio = audio_manager
        self._listen_timeout = listen_timeout
        self._language = language or "en-IN"

    def listen_once(
        self,
        phrase_time_limit: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        effective_timeout = timeout if timeout is not None else self._listen_timeout
        logger.debug(
            "Listening... timeout=%ss phrase_limit=%s language=%s",
            effective_timeout,
            phrase_time_limit,
            self._language,
        )

        try:
            with self._audio.microphone() as source:
                audio = self._audio.recognizer.listen(
                    source,
                    timeout=effective_timeout,
                    phrase_time_limit=phrase_time_limit,
                )

        except sr.WaitTimeoutError as exc:
            logger.debug("Listening timed out: no speech detected.")
            raise SpeechRecognitionFailedError("No speech detected before timeout.") from exc

        except OSError as exc:
            raise SpeechRecognitionFailedError(f"Audio input error: {exc}") from exc

        # Fast recognition: prioritize en-IN, then hi-IN / en-US
        languages_to_try = [self._language]
        if self._language == "en-IN":
            languages_to_try.append("hi-IN")
        elif self._language not in {"en-US", "en-IN"}:
            languages_to_try.append("en-US")

        last_error = None
        for lang in languages_to_try:
            try:
                text = self._audio.recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    text = text.strip()
                    logger.info("Speech recognized (%s): %r", lang, text)
                    return text
            except sr.UnknownValueError:
                continue
            except sr.RequestError as exc:
                last_error = exc
                logger.warning("Google STT service unreachable for %s: %s", lang, exc)
                break
            except Exception as exc:
                last_error = exc
                break

        # If Google failed due to request error, try local whisper/sphinx if available
        try:
            if hasattr(self._audio.recognizer, "recognize_whisper"):
                text = self._audio.recognizer.recognize_whisper(audio)
                if text and text.strip():
                    text = text.strip()
                    logger.info("Speech recognized (local whisper): %r", text)
                    return text
        except Exception:
            pass

        if last_error is not None:
            raise SpeechRecognitionFailedError(
                f"Speech recognition service unavailable: {last_error}"
            )

        raise SpeechRecognitionFailedError("Speech was captured but could not be understood.")