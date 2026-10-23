"""
Controlled terminal execution.

This is the ONLY place in the codebase that calls subprocess with
user/LLM-influenced input, and it always goes through
security.command_validator.validate_command() first — never shell=True on
a raw string. See section 13/14 of the design brief this project follows.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from pydantic import Field

from app.config import get_settings
from security.command_validator import validate_command
from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult
from utils.exceptions import DangerousCommandError


class ExecuteCommandInput(ToolInput):
    program: str = Field(description="The executable to run, e.g. 'npm', 'python', 'git'.")
    args: list[str] = Field(default_factory=list, description="Argument list, e.g. ['install'].")
    working_dir: Optional[str] = Field(default=None, description="Directory to run in. Defaults to home.")


class ExecuteTerminalCommandTool(Tool):
    name = "execute_terminal_command"
    description = (
        "Run a single validated terminal command (e.g. 'npm install', 'python app.py', "
        "'git status'). Dangerous or destructive commands are rejected. Always requires confirmation."
    )
    permission_level = PermissionLevel.CONFIRM
    input_model = ExecuteCommandInput
    timeout_seconds = 60.0

    def confirmation_detail(self, params: ExecuteCommandInput) -> str:
        cmdline = " ".join([params.program, *params.args])
        return f"SARAS wants to run:\n  {cmdline}\nin {params.working_dir or '(home directory)'}."

    def run(self, params: ExecuteCommandInput) -> ToolResult:
        settings = get_settings()
        working_dir = params.working_dir or str(_home())

        try:
            validated = validate_command(
                program=params.program,
                args=params.args,
                working_dir=working_dir,
                allowed_roots=settings.terminal_allowed_roots_list(),
            )
        except DangerousCommandError as exc:
            return ToolResult(success=False, message="That command was blocked for safety reasons.", error=str(exc))

        try:
            proc = subprocess.run(
                [validated.program, *validated.args],
                cwd=validated.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, message="The command timed out.", error="timeout")
        except FileNotFoundError:
            return ToolResult(success=False, message=f"'{validated.program}' was not found.", error="not_found")

        success = proc.returncode == 0
        message = "Command completed successfully." if success else f"Command exited with code {proc.returncode}."
        return ToolResult(
            success=success,
            message=message,
            data={"stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "exit_code": proc.returncode},
        )

    def verify(self, params: ExecuteCommandInput, result: ToolResult) -> str | None:
        if result.data and result.data.get("exit_code") not in (0, None):
            return f"Command exited non-zero ({result.data['exit_code']})."
        return None


def _home():
    from pathlib import Path
    return Path.home()
