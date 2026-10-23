"""
Centralized microphone/audio access for SARAS.

Uses the configured PyAudio/SpeechRecognition input device.
Microphone selection is controlled through SARAS_MICROPHONE_DEVICE.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

from utils.exceptions import MicrophoneUnavailableError
from utils.logger import get_logger

logger = get_logger("voice.audio_manager")


class AudioManager:
    def __init__(self, device_index: Optional[int] = None):
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise MicrophoneUnavailableError(
                "The 'speech_recognition' package is not installed."
            ) from exc

        self._sr = sr
        self._recognizer = sr.Recognizer()

        # Responsive speech recognition configuration
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.8
        self._recognizer.phrase_threshold = 0.3
        self._recognizer.non_speaking_duration = 0.5

        # Explicit argument has priority.
        if device_index is None:
            raw_device = os.getenv("SARAS_MICROPHONE_DEVICE", "").strip()
            if raw_device:
                try:
                    device_index = int(raw_device)
                except ValueError:
                    logger.warning("SARAS_MICROPHONE_DEVICE must be an integer; ignoring invalid value.")
                    device_index = None

        self._device_index = device_index
        self._device_name = "Windows default microphone"
        self._calibrated = False

        self._validate_and_setup_device()

    def _validate_and_setup_device(self) -> None:
        if self._device_index is not None:
            try:
                devices = self._sr.Microphone.list_microphone_names()
                if 0 <= self._device_index < len(devices):
                    self._device_name = devices[self._device_index]
                    logger.info("SARAS microphone selected: index=%s name=%s", self._device_index, self._device_name)
                else:
                    logger.warning(
                        "Microphone device index %s is outside range (0-%s). Falling back to Windows default.",
                        self._device_index,
                        len(devices) - 1,
                    )
                    self._device_index = None
                    self._device_name = "Windows default microphone"
            except Exception as exc:
                logger.warning("Could not inspect microphone devices (%s). Falling back to default.", exc)
                self._device_index = None
                self._device_name = "Windows default microphone"
        else:
            self._device_name = "Windows default microphone"
            logger.info("SARAS microphone configured: Windows default input")

    @property
    def recognizer(self):
        return self._recognizer

    @property
    def device_index(self) -> Optional[int]:
        return self._device_index

    @property
    def device_name(self) -> str:
        return self._device_name

    def calibrate_ambient_noise(self, duration: float = 1.0) -> None:
        """Calibrate the recognizer for ambient noise level."""
        if self._calibrated:
            return
        try:
            with self.microphone() as source:
                logger.info("Calibrating microphone for ambient noise (%ss)...", duration)
                self._recognizer.adjust_for_ambient_noise(source, duration=duration)
                self._calibrated = True
                logger.info("Ambient noise calibrated. Energy threshold: %.1f", self._recognizer.energy_threshold)
        except Exception as exc:
            logger.warning("Ambient noise calibration skipped: %s", exc)

    @contextmanager
    def microphone(self):
        """
        Open the microphone with automatic fallback if the configured device fails.
        """
        mic = None
        source = None
        try:
            mic = (
                self._sr.Microphone(device_index=self._device_index)
                if self._device_index is not None
                else self._sr.Microphone()
            )
            source = mic.__enter__()
            if source.stream is None:
                raise OSError(f"Input stream could not be started for {self._device_name}")
        except Exception as primary_exc:
            if self._device_index is not None:
                logger.warning(
                    "Configured microphone index %s failed (%s). Falling back to system default microphone.",
                    self._device_index,
                    primary_exc,
                )
                if mic and source:
                    try:
                        mic.__exit__(None, None, None)
                    except Exception:
                        pass
                try:
                    self._device_index = None
                    self._device_name = "Windows default microphone"
                    mic = self._sr.Microphone()
                    source = mic.__enter__()
                    if source.stream is None:
                        raise MicrophoneUnavailableError("Default microphone input stream could not be started.")
                    logger.info("Fallback default microphone opened successfully.")
                except Exception as fallback_exc:
                    if mic:
                        try:
                            mic.__exit__(None, None, None)
                        except Exception:
                            pass
                    raise MicrophoneUnavailableError(
                        f"Could not open microphone '{self._device_name}': {fallback_exc}"
                    ) from fallback_exc
            else:
                if mic:
                    try:
                        mic.__exit__(None, None, None)
                    except Exception:
                        pass
                raise MicrophoneUnavailableError(
                    f"Could not open microphone '{self._device_name}': {primary_exc}"
                ) from primary_exc

        try:
            yield source
        finally:
            try:
                mic.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Microphone cleanup warning: %s", exc)
