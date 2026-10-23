"""
Text-to-speech abstraction.

The original project kept both pyttsx3 (offline, synchronous) AND
gTTS+pygame (online, needs a temp mp3 file) side by side, with an unused
`speak_old` function left dangling. This is redundant: pick one path by
config, and only fall back to the other on failure. pyttsx3 is the default
because it's offline and doesn't leave temp files on disk.
"""
from __future__ import annotations

import os
import tempfile

from utils.exceptions import TextToSpeechError
from utils.logger import get_logger

logger = get_logger("voice.tts")


class TextToSpeech:
    def __init__(self, engine: str = "pyttsx3", rate: int = 180):
        self._engine_name = engine
        self._rate = rate
        self._pyttsx3_engine = None

    def speak(self, text: str) -> None:
        if not text:
            return
        try:
            if self._engine_name == "pyttsx3":
                self._speak_pyttsx3(text)
            else:
                self._speak_gtts(text)
        except Exception as exc:
            logger.warning("Primary TTS engine '%s' failed (%s); falling back.", self._engine_name, exc)
            try:
                if self._engine_name == "pyttsx3":
                    self._speak_gtts(text)
                else:
                    self._speak_pyttsx3(text)
            except Exception as fallback_exc:
                raise TextToSpeechError(str(fallback_exc)) from fallback_exc

    def _speak_pyttsx3(self, text: str) -> None:
        import pyttsx3
        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", self._rate)
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()

    def _speak_gtts(self, text: str) -> None:
        from gtts import gTTS
        import pygame

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "speech.mp3")
            gTTS(text).save(path)

            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
