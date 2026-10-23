"""
Tests for the terminal command validator — the most safety-critical piece
of the project. These NEVER execute anything; they only check that
validate_command raises/returns correctly. No real files are touched.
"""
import tempfile

import pytest

from security.command_validator import validate_command
from utils.exceptions import DangerousCommandError


def test_blocked_binary_rejected(tmp_path):
    with pytest.raises(DangerousCommandError):
        validate_command("format", ["C:"], str(tmp_path), [str(tmp_path)])


def test_dangerous_pattern_rejected(tmp_path):
    with pytest.raises(DangerousCommandError):
        validate_command("git", ["status", "&&", "del", "everything"], str(tmp_path), [str(tmp_path)])


def test_binary_not_on_allowlist_rejected(tmp_path):
    with pytest.raises(DangerousCommandError):
        validate_command("some_random_unknown_tool", [], str(tmp_path), [str(tmp_path)])


def test_working_dir_outside_allowed_roots_rejected(tmp_path):
    other = tempfile.mkdtemp()
    with pytest.raises(DangerousCommandError):
        validate_command("git", ["status"], other, [str(tmp_path)])


def test_valid_command_passes(tmp_path):
    result = validate_command("git", ["status"], str(tmp_path), [str(tmp_path)])
    assert result.program == "git"
    assert result.args == ["status"]
