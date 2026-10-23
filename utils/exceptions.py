"""
Structured exception hierarchy for SARAS.

Every failure mode in the system should raise one of these instead of a bare
Exception, so the orchestrator and voice layer can decide how to react
(retry, ask for confirmation, apologize to the user, log and continue, etc.)
without parsing error strings.
"""
from __future__ import annotations


class SarasError(Exception):
    """Base class for all SARAS-raised errors."""


# ---- Configuration -------------------------------------------------------

class ConfigurationError(SarasError):
    """Raised when required configuration/secrets are missing or invalid."""


# ---- Tools -----------------------------------------------------------------

class ToolError(SarasError):
    """Base class for tool-related errors."""


class ToolNotFoundError(ToolError):
    """Raised when the planner/executor references a tool that isn't registered."""


class ToolValidationError(ToolError):
    """Raised when tool input fails schema validation."""


class ToolExecutionError(ToolError):
    """Raised when a tool runs but fails during execution."""


class ToolTimeoutError(ToolError):
    """Raised when a tool exceeds its allotted execution time."""


class ToolVerificationError(ToolError):
    """Raised when a tool reports success but post-execution verification fails."""


# ---- Security ----------------------------------------------------------------

class SecurityError(SarasError):
    """Base class for security/permission errors."""


class PermissionDeniedError(SecurityError):
    """Raised when an action is disallowed outright by policy."""


class ConfirmationRequiredError(SecurityError):
    """Raised when an action requires explicit user confirmation before running."""

    def __init__(self, message: str, confirmation_id: str):
        super().__init__(message)
        self.confirmation_id = confirmation_id


class DangerousCommandError(SecurityError):
    """Raised by the command validator when a terminal command is blocked outright."""


class UntrustedContentError(SecurityError):
    """Raised when content sourced from an untrusted origin (web page, file,
    tool output) attempts to be treated as a direct user instruction."""


# ---- Voice --------------------------------------------------------------------

class VoiceError(SarasError):
    """Base class for voice subsystem errors."""


class MicrophoneUnavailableError(VoiceError):
    pass


class SpeechRecognitionFailedError(VoiceError):
    pass


class TextToSpeechError(VoiceError):
    pass


# ---- Intelligence ---------------------------------------------------------------

class LLMProviderError(SarasError):
    """Base class for LLM provider errors (network, auth, rate limit, parsing)."""


class LLMRateLimitError(LLMProviderError):
    pass


class LLMMalformedOutputError(LLMProviderError):
    pass


# ---- Planning ---------------------------------------------------------------------

class PlannerError(SarasError):
    pass


class PlanExecutionAbortedError(PlannerError):
    """Raised when a multi-step plan is cancelled or a step fails without a retry path."""


# ---- Scheduler ------------------------------------------------------------------------

class SchedulerError(SarasError):
    pass


class JobNotFoundError(SchedulerError):
    pass
