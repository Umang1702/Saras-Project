# SARAS — Personal AI Desktop Agent

SARAS is a modular, tool-based, voice-driven AI agent for Windows. This is
an architectural rewrite of a 4-file wake-word demo into a system built
around a **tool registry, a permission/confirmation layer, a bounded task
planner, and a verification step** — instead of an `if/elif` chain calling
OpenAI directly.

## What changed from the original project

| Before | Now |
|---|---|
| Hardcoded API keys in `main.py` / `client.py` | `.env` + `app/config.py`, nothing hardcoded |
| `if "open google" in c.lower(): ...` chain | `tools/` registry + LLM function-calling `planner.py` |
| LLM output executed with no guardrails | Every tool call passes through `security/permissions.py` |
| No confirmation before destructive actions | `delete_files` / `execute_terminal_command` require explicit "yes" |
| `client.chat.completions.create` old-style, unused `client.py` file | `intelligence/providers/openai_provider.py`, modern SDK, provider-agnostic interface |
| No verification that actions actually worked | `Tool.verify()` — e.g. checks the process is actually running after launch |
| One giant `except Exception` around the whole loop | Structured exceptions per layer (`utils/exceptions.py`) |
| `musicLibrary.py` hardcoded dict, `KeyError` on unknown song | `tools/media/playback.py`, graceful "not found" + suggestion |
| No persistence | SQLite (`memory/database.py`) for preferences, tool-execution audit log, routines |
| No scheduling | `scheduler/` — APScheduler with a persistent SQLite job store |

## Architecture

```
User (voice/text)
   -> voice/voice_session.py            (wake word -> STT -> callback -> TTS)
   -> core/assistant.py                 (entry point; resumes pending confirmations)
   -> core/orchestrator.py              (intent -> answer OR plan -> execute)
        -> intelligence/intent.py       (QUESTION / ACTION / MULTI_STEP)
        -> core/planner.py              (LLM function-calling -> bounded step list)
        -> core/executor.py             (validate -> permission check -> run -> verify)
             -> security/permissions.py (SAFE / LOW_RISK / CONFIRM / HIGH_RISK)
             -> security/confirmation.py
             -> tools/*                 (the only code that touches the OS)
   -> memory/, scheduler/               (persistence, reminders, routines)
```

The LLM never executes anything directly. It can only request a tool call
by name + structured arguments; the executor decides whether that's
allowed to run, and how.

## Project layout

```
SARAS/
├── app/            entry point + config + DI wiring (bootstrap.py)
├── core/           orchestrator, planner, executor, context, state
├── voice/          STT, TTS, wake word, audio manager, voice session
├── intelligence/   LLM provider abstraction, intent classification, prompts
├── tools/          every OS capability, one Tool subclass each
│   ├── filesystem/ applications/ browser/ system/ terminal/ media/ news/
├── memory/         SQLite-backed preferences + short-term context + audit log
├── scheduler/       persistent reminders/routines (APScheduler)
├── security/        permission levels, command validator, confirmation flow
├── utils/            logging, exception hierarchy
└── tests/            pytest suite (no real files are ever touched/deleted)
```

## Installation

Requires **Python 3.10+** on Windows (voice/system tools target Windows;
core logic is OS-agnostic and will run on Linux/macOS in text mode).

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set at least `OPENAI_API_KEY`. `NEWS_API_KEY` is optional
(only `get_news` needs it).

On Windows, `PyAudio` sometimes needs a prebuilt wheel — if `pip install`
fails on it, install via `pipwin install pyaudio` or grab a wheel from
Christoph Gohlke's archive.

## Running

```bash
python -m app.main            # voice mode (say "Saras", wait for "Yes?", then speak)
python -m app.main --text     # text mode — good for development/testing
```

If no microphone is available, voice mode automatically falls back to text
mode with a warning instead of crashing.

## Example commands

```
Saras, tell me my battery percentage.
Saras, open Chrome.
Saras, search Google for the latest Python version.
Saras, find all PDFs in Downloads.
Saras, create a folder called Projects.
Saras, run git status.                 -> asks for confirmation first
Saras, delete these files.             -> asks for confirmation first
Saras, play believer.
Saras, give me today's top headlines.
What is a hash map?                    -> answered directly, no tool call
```

## Security model

Every tool declares a `PermissionLevel`:

- **SAFE** — read-only (battery, storage, list processes, search files, screenshot). Runs immediately.
- **LOW_RISK** — reversible side effects (open app/browser, create folder, move/copy file, set volume). Runs immediately.
- **CONFIRM** — `delete_files`, `execute_terminal_command`. SARAS explains what will happen and waits for an explicit "yes" before running.
- **HIGH_RISK** — reserved for future destructive/admin operations (registry edits, disk operations). Disabled by default (`high_risk_enabled=False` in `bootstrap.py`); there is no built-in tool at this level yet.

`security/command_validator.py` is the terminal's second, independent
safety layer: a binary allow-list, a deny-list of dangerous
binaries/patterns (chaining, redirection into a drive root, command
substitution, `curl`/`wget`, PowerShell/`iex`), and a requirement that the
working directory sit inside a configured allowed root. Commands never run
via `shell=True` on a raw string — always an explicit argument list.

**Prompt injection defense** (`intelligence/prompts.py`): the system
prompt tells the model explicitly that only the user's direct message and
these system rules can authorize a tool call — never text found inside a
tool result or fetched web page. When browser/document-reading tools are
added later, wrap their output with `prompts.wrap_untrusted(...)` before
it re-enters the conversation.

## Verification

Several tools implement `Tool.verify()` and are checked after a successful
run: `open_application` / `close_application` check the process actually
started/stopped, `create_folder` checks the folder exists, `move_file`
checks the file exists at the destination, `delete_files` checks the paths
are actually gone, `execute_terminal_command` checks the exit code.
Verification issues are appended to the response rather than silently
ignored, e.g. *"VS Code opened, but no matching process was found running."*

## Testing

```bash
pytest
```

16 tests cover the tool registry, permission/confirmation logic, the
terminal command validator (the highest-stakes component), and the
planner against a fake LLM provider — no network calls, no real files
touched or deleted.

## Adding a new tool

1. Create `tools/<category>/<name>.py`, subclass `Tool`, define
   `name`, `description`, `permission_level`, an `input_model`
   (Pydantic), and `run()`.
2. Register it in `app/bootstrap.py::build_registry()`.

Nothing in `core/` needs to change — the planner discovers tools via
`registry.llm_schemas()`. This is how `tools/gmail/`, `tools/spotify/`,
`tools/calendar/`, etc. can be added later without touching the
orchestrator.

## Known gaps / future extension points

This is Phases 1–8 of the design brief's development order (architecture,
voice, LLM abstraction, tool registry, core Windows tools, security,
planner/orchestrator, verification), plus a working memory/scheduler
layer. Not yet implemented, and intentionally scoped out to avoid
shipping half-working code:

- **System tray / desktop UI** (`ui/` from the original brief) — the
  `core/state.py` state machine and `EventBus` are ready for a tray icon
  to subscribe to; no UI framework is wired up yet.
- **Window management** (focus/minimize/maximize specific windows) —
  deliberately deferred rather than shipped as fragile coordinate-based
  automation; `pywin32`/`pygetwindow` would be the next step.
- **Computer vision / screen understanding** — not started; `tools/system/screenshot.py`
  is the natural attachment point for an OCR/vision tool later.
- **Routines as a DSL** — `memory/database.py` has a `routines` table and
  `scheduler/jobs.py` has a `make_routine_job` hook, but there's no
  natural-language routine *builder* yet (e.g. "start my work routine"
  parsing into a saved step list) — currently routines must be created by
  calling `Database.save_routine()` directly.
- **Volume/window APIs are Windows-only** and degrade with an explicit
  error message on other platforms, by design.
