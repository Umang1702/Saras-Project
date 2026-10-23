"""
Validates terminal commands before they are ever handed to subprocess.

This is the single most important security boundary in SARAS: it is the
only thing standing between "run npm install" and "format C:". It must be
conservative by default — when in doubt, block.

Design:
  - Deny-list of dangerous patterns (destructive, system-altering, privilege
    escalation, obfuscation attempts).
  - Working directory must be inside one of the configured allowed roots.
  - No shell metacharacters that allow chaining into a second, unvalidated
    command (&&, ;, |, backticks, $(...)) — each call runs exactly one
    program with an explicit argument list, never `shell=True` on a raw
    string typed by an LLM.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from utils.exceptions import DangerousCommandError

# Commands/binaries that are never allowed, regardless of arguments.
_BLOCKED_BINARIES = {
    "format", "diskpart", "cipher", "vssadmin", "bcdedit", "bootrec",
    "reg", "regedit", "net", "netsh", "sc", "takeown", "icacls",
    "shutdown", "restart-computer", "stop-computer", "remove-item",
    "rd", "rmdir", "del", "erase", "fsutil", "attrib", "wmic",
    "powershell", "pwsh",  # scripting hosts are blocked outright; run real
                            # binaries directly instead of shelling into a
                            # script interpreter that could hide anything.
}

# Regex patterns applied to the full command line for dangerous *intent*,
# even via an otherwise-allowed binary.
_DANGEROUS_PATTERNS = [
    re.compile(r"-\s*rf\b"),                 # rm -rf style flags
    re.compile(r"/s\b.*/q\b", re.IGNORECASE),  # del /s /q
    re.compile(r">\s*[A-Za-z]:\\"),           # redirect into a drive root
    re.compile(r"\$\("),                       # command substitution
    re.compile(r"`"),                            # backtick substitution
    re.compile(r"&&|\|\||;|\|"),                  # command chaining/piping
    re.compile(r"curl|wget", re.IGNORECASE),        # arbitrary remote fetch+exec risk
    re.compile(r"iex\b", re.IGNORECASE),              # PowerShell Invoke-Expression
]

# Binaries considered safe to run for everyday dev workflows.
_ALLOWED_BINARIES = {
    "python", "python3", "pip", "pip3", "node", "npm", "npx", "yarn", "pnpm",
    "git", "dir", "ls", "cd", "echo", "cat", "type", "code", "dotnet",
    "cargo", "go", "make", "pytest",
}


@dataclass
class ValidatedCommand:
    program: str
    args: list[str]
    working_dir: str


def validate_command(
    program: str,
    args: Sequence[str],
    working_dir: str,
    allowed_roots: Sequence[str],
) -> ValidatedCommand:
    """Raises DangerousCommandError if the command is not allowed.
    Returns a normalized ValidatedCommand otherwise."""

    prog_name = Path(program).stem.lower()

    if prog_name in _BLOCKED_BINARIES:
        raise DangerousCommandError(f"'{program}' is a blocked command and cannot be executed by SARAS.")

    full_line = " ".join([program, *args])
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(full_line):
            raise DangerousCommandError(
                f"Command rejected: matched a disallowed pattern ({pattern.pattern})."
            )

    if prog_name not in _ALLOWED_BINARIES:
        raise DangerousCommandError(
            f"'{program}' is not on the terminal tool's allow-list. "
            "Add it explicitly if this is a trusted, everyday tool."
        )

    resolved_dir = str(Path(working_dir).expanduser().resolve())
    if not any(_is_within(resolved_dir, root) for root in allowed_roots):
        raise DangerousCommandError(
            f"Working directory '{resolved_dir}' is outside the allowed roots."
        )

    return ValidatedCommand(program=program, args=list(args), working_dir=resolved_dir)


def _is_within(path: str, root: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).expanduser().resolve())
        return True
    except ValueError:
        return False
