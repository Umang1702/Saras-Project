"""
Formats the final concise user-facing reply from structured execution
results, keeping internal step-by-step detail out of what's spoken/shown.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StepOutcome:
    tool_name: str
    success: bool
    message: str


def summarize(outcomes: list[StepOutcome]) -> str:
    if not outcomes:
        return "Okay."
    if len(outcomes) == 1:
        return outcomes[0].message

    failures = [o for o in outcomes if not o.success]
    if not failures:
        messages = [o.message.rstrip(".") for o in outcomes if o.message]
        return ". ".join(messages) + "."

    ok_parts = ", ".join(o.tool_name for o in outcomes if o.success)
    fail = failures[0]
    prefix = f"{ok_parts} done, but " if ok_parts else ""
    return f"{prefix}{fail.tool_name} failed: {fail.message}"
