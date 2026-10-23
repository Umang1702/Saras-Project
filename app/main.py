"""
Entry point. Deliberately thin — this is the "bootstrap only" main.py
described by the SARAS architecture.

Usage:
    python -m app.main
        Voice mode with OpenAI enabled.

    python -m app.main --text
        Text mode with OpenAI enabled.

    python -m app.main --local
        Voice mode with OpenAI disabled.

    python -m app.main --local --text
        Text mode with OpenAI disabled.
"""

from __future__ import annotations

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.bootstrap import build_application
from utils.logger import get_logger


logger = get_logger("app.main")


def run_text_loop(app) -> None:
    """Run SARAS using keyboard/text input."""

    print("SARAS (text mode). Type 'exit' to quit.")

    while True:
        try:
            text = input("you> ").strip()

        except (EOFError, KeyboardInterrupt):
            print()
            break

        if text.lower() in {"exit", "quit"}:
            break

        if not text:
            continue

        try:
            response = app.assistant.process_text(text)
            print(f"saras> {response}")

        except Exception as exc:
            logger.exception("Command processing failed.")
            print(f"saras> I couldn't process that command: {exc}")


def run_voice_loop(app) -> None:
    """Run SARAS using microphone and wake-word detection."""

    if app.voice_session is None:
        print(
            "Voice subsystem is unavailable "
            "(missing microphone/dependencies). "
            "Falling back to text mode."
        )
        run_text_loop(app)
        return

    print("\n" + "=" * 60)
    print("🤖  SARAS PERSONAL AI AGENT — ADVANCED VOICE ENGINE")
    print("=" * 60)
    print("  1. Say 'Saras' (or 'Hey Saras', 'Saras suno')")
    print("  2. SARAS will chime & reply: 'Yes, I'm listening.'")
    print("  3. Speak your command (e.g. 'open Chrome', 'battery batao')")
    print("  Or speak in one breath: 'Saras calculator kholo'")
    print("=" * 60 + "\n")

    try:
        app.voice_session.run_forever()

    except KeyboardInterrupt:
        print("\nStopping SARAS...")
        app.voice_session.stop()

    except Exception:
        logger.exception("Voice session stopped unexpectedly.")
        print("SARAS voice session stopped unexpectedly.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SARAS personal AI desktop agent"
    )

    parser.add_argument(
        "--text",
        action="store_true",
        help="Run in text-only mode instead of voice.",
    )

    parser.add_argument(
        "--ui",
        "--gui",
        action="store_true",
        dest="ui",
        help="Run SARAS in modern desktop GUI window.",
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help=(
            "Run in local desktop mode without OpenAI. "
            "Uses deterministic local command routing."
        ),
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # BUILD APPLICATION
    # ---------------------------------------------------------

    try:
        app = build_application(
            local_mode=args.local
        )

    except Exception as exc:
        logger.exception("Failed to start SARAS.")
        print(f"SARAS failed to start: {exc}")
        return 1

    # ---------------------------------------------------------
    # RUN SARAS
    # ---------------------------------------------------------

    try:
        if args.ui:
            from ui.app_window import launch
            launch(app)
        elif args.text:
            run_text_loop(app)
        else:
            run_voice_loop(app)

    finally:
        if app.voice_session:
            try:
                app.voice_session.stop()
            except Exception:
                logger.exception(
                    "Failed to stop voice session cleanly."
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())