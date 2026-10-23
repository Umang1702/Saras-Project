"""
Centralized structured logging for SARAS.

- Rotating file handler so logs don't grow unbounded.
- Console handler for interactive development.
- A `redact` helper so callers can scrub secrets before logging free-form data.
- Never call logger.info/debug/etc with raw API keys/tokens/passwords. Use
  `redact()` on any dict that might contain them.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

_SENSITIVE_KEYS = {
    "api_key", "apikey", "authorization", "password", "token",
    "secret", "openai_api_key", "news_api_key",
}

_configured = False


def redact(data: dict) -> dict:
    """Return a shallow copy of `data` with sensitive-looking keys masked."""
    out = {}
    for k, v in data.items():
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out


def configure_logging(log_dir: str, level: str = "INFO") -> None:
    global _configured
    if _configured:
        return

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = os.path.join(log_dir, "saras.log")

    root = logging.getLogger("saras")
    root.setLevel(level.upper())
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger under the `saras` root. Configures defaults
    lazily if `configure_logging` was never called (e.g. in unit tests)."""
    if not _configured:
        configure_logging(log_dir=os.path.join(os.path.expanduser("~"), ".saras", "logs"))
    return logging.getLogger(f"saras.{name}")
