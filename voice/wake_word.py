"""
Wake-word detection for SARAS.

Listens for short phrases and checks whether the configured
wake word was recognized.
"""

from __future__ import annotations

import difflib

from voice.speech_to_text import SpeechToText
from utils.exceptions import (
    SpeechRecognitionFailedError,
    MicrophoneUnavailableError,
)
from utils.logger import get_logger


logger = get_logger("voice.wake_word")


import re

WAKE_WORD_VARIANTS = {
    "saras",
    "sarah",
    "sarus",
    "saris",
    "service",
    "sharas",
    "zaras",
    "soras",
    "sirius",
    "ceres",
    "saransh",
    "saroj",
    "saral",
    "sara",
    "saharsh",
    "sarath",
    "sharath",
    "sarishti",
    "sauras",
    "suras",
    "stars",
    "virus",
    "saurus",
    "sarras",
    "सारस",
    "सरस",
}

GREETINGS_AND_FILLERS = {
    "hey",
    "hello",
    "hi",
    "ok",
    "okay",
    "sun",
    "suno",
    "aey",
    "ae",
    "are",
    "arey",
    "bhai",
    "please",
    "zara",
    "ji",
}


class WakeWordDetector:
    def __init__(
        self,
        stt: SpeechToText,
        wake_word: str = "saras",
        similarity_threshold: float = 0.65,
    ):
        self._stt = stt
        self._wake_word = wake_word.lower().strip()
        self._threshold = similarity_threshold
        self._last_embedded_command: str | None = None

    @property
    def last_embedded_command(self) -> str | None:
        return self._last_embedded_command

    def listen_for_wake_word(self) -> bool:
        detected, command = self.detect_wake_word()
        self._last_embedded_command = command
        return detected

    def _is_wake_word_token(self, token: str) -> bool:
        t = token.lower().strip()
        if t == self._wake_word or t in WAKE_WORD_VARIANTS:
            return True
        similarity = difflib.SequenceMatcher(None, t, self._wake_word).ratio()
        return similarity >= self._threshold

    def detect_wake_word(self, phrase_time_limit: float = 3.5) -> tuple[bool, str | None]:
        """
        Listens for audio and returns (detected, embedded_command).
        If the user says 'Saras open Chrome', detected is True and embedded_command is 'open Chrome'.
        If the user only says 'Saras', detected is True and embedded_command is None.
        """
        try:
            heard = self._stt.listen_once(phrase_time_limit=phrase_time_limit)
        except MicrophoneUnavailableError:
            raise
        except SpeechRecognitionFailedError as exc:
            logger.debug("Wake-word listening cycle: %s", exc)
            return False, None

        heard_clean = heard.lower().strip()
        logger.info("Wake-word candidate input: %r", heard_clean)

        words = heard_clean.split()
        if not words:
            return False, None

        # Look for wake word match in the first 3 tokens
        match_idx = -1
        max_scan = min(len(words), 3)
        for idx in range(max_scan):
            if self._is_wake_word_token(words[idx]):
                # Verify that all prior words are allowable greeting/filler words
                prior_words = words[:idx]
                if all(w in GREETINGS_AND_FILLERS for w in prior_words):
                    match_idx = idx
                    break

        if match_idx != -1:
            remaining = words[match_idx + 1 :]
            # Strip leading fillers from embedded command (e.g. "Saras suno open chrome" -> "open chrome")
            while remaining and remaining[0] in GREETINGS_AND_FILLERS:
                remaining.pop(0)

            embedded_cmd = " ".join(remaining).strip() if remaining else None
            logger.info("Wake word matched! embedded_command=%r", embedded_cmd)
            return True, embedded_cmd

        # Whole-utterance fallback for single/double word transcriptions
        if len(words) <= 2:
            clean_sans_fillers = [w for w in words if w not in GREETINGS_AND_FILLERS]
            if clean_sans_fillers and any(self._is_wake_word_token(w) for w in clean_sans_fillers):
                logger.info("Wake word detected via filler-stripped match (%r)", heard_clean)
                return True, None
            if difflib.SequenceMatcher(None, heard_clean, self._wake_word).ratio() >= self._threshold:
                logger.info("Wake word fuzzy matched whole utterance (%r)", heard_clean)
                return True, None

        return False, None