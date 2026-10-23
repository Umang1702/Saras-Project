"""
Thin re-export so `tools/terminal/` reads naturally alongside `execute.py`
without duplicating logic. The real implementation lives in
security/command_validator.py since permission/security code belongs in the
security layer, not the tools layer — tools only *consume* the validator.
"""
from security.command_validator import ValidatedCommand, validate_command  # noqa: F401
