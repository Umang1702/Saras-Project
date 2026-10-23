"""
Centralized configuration.

All secrets and environment-dependent values live here and ONLY here,
loaded from environment variables / a `.env` file. No module outside this
file should ever contain a literal API key, model name, or file path.

The previous SARAS hardcoded:
    newsapi = "Your News Api"
    client = OpenAI(api_key="Your OpenAI api")
directly inside main.py and client.py. Both are gone.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- AI provider -------------------------------------------------
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    llm_provider: str = Field(default="openai", alias="SARAS_LLM_PROVIDER")

    # --- External services ---------------------------------------------
    news_api_key: Optional[str] = Field(default=None, alias="NEWS_API_KEY")
    news_country: str = Field(default="in", alias="SARAS_NEWS_COUNTRY")

    # Voice settings
    wake_word: str = Field(default="saras", alias="SARAS_WAKE_WORD")
    tts_engine: str = Field(default="pyttsx3", alias="SARAS_TTS_ENGINE")  # pyttsx3 | gtts
    voice_rate: int = Field(default=180, alias="SARAS_VOICE_RATE")
    listen_timeout_seconds: int = Field(default=10, alias="SARAS_LISTEN_TIMEOUT")
    stt_language: str = Field(default="en-IN", alias="SARAS_STT_LANGUAGE")
    microphone_device: Optional[int] = Field(default=None, alias="SARAS_MICROPHONE_DEVICE")

    @field_validator("microphone_device", mode="before")
    @classmethod
    def parse_microphone_device(cls, v):
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return int(v)

    # Mode / fallback
    local_mode: bool = Field(default=False, alias="SARAS_LOCAL_MODE")
    auto_local_fallback: bool = Field(default=True, alias="SARAS_AUTO_LOCAL_FALLBACK")

    # --- User preferences (defaults; overridable at runtime via memory) ----
    default_browser: Optional[str] = Field(default=None, alias="SARAS_DEFAULT_BROWSER")
    default_editor: Optional[str] = Field(default="code", alias="SARAS_DEFAULT_EDITOR")
    default_workspace: Optional[str] = Field(default=None, alias="SARAS_DEFAULT_WORKSPACE")

    # --- Security ------------------------------------------------------------
    terminal_allowed_roots: str = Field(
        default="", alias="SARAS_TERMINAL_ALLOWED_ROOTS"
    )  # ';'-separated absolute paths; empty = user's home dir only
    require_confirmation_for_delete: bool = Field(default=True, alias="SARAS_CONFIRM_DELETE")

    # --- Storage / logging --------------------------------------------------------
    data_dir: str = Field(default=str(Path.home() / ".saras"), alias="SARAS_DATA_DIR")
    log_level: str = Field(default="INFO", alias="SARAS_LOG_LEVEL")

    @property
    def db_path(self) -> str:
        return str(Path(self.data_dir) / "saras.db")

    @property
    def log_dir(self) -> str:
        return str(Path(self.data_dir) / "logs")

    def terminal_allowed_roots_list(self) -> list[str]:
        if not self.terminal_allowed_roots.strip():
            return [str(Path.home())]
        return [p.strip() for p in self.terminal_allowed_roots.split(";") if p.strip()]

    def ensure_dirs(self) -> None:
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Singleton accessor so the whole app shares one config instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
