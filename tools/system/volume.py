"""
System volume control.

Windows volume control (pycaw) is Windows-only and requires COM, which isn't
available in every environment SARAS might be developed/tested on. This tool
degrades gracefully: it attempts pycaw on Windows and reports a clear,
honest failure everywhere else instead of pretending to succeed.
"""
from __future__ import annotations

import platform

from pydantic import Field

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class SetVolumeInput(ToolInput):
    percent: int = Field(ge=0, le=100, description="Target system volume, 0-100.")


class SetVolumeTool(Tool):
    name = "set_volume"
    description = "Set the system volume to a specific percentage (0-100)."
    permission_level = PermissionLevel.LOW_RISK
    input_model = SetVolumeInput

    def run(self, params: SetVolumeInput) -> ToolResult:
        if platform.system() != "Windows":
            return ToolResult(
                success=False,
                message="Volume control is only implemented for Windows right now.",
                error="unsupported_platform",
            )
        try:
            import comtypes
            try:
                comtypes.CoInitialize()
            except Exception:
                pass

            from pycaw.pycaw import AudioUtilities

            speakers = AudioUtilities.GetSpeakers()
            if hasattr(speakers, "EndpointVolume"):
                volume = speakers.EndpointVolume
            elif hasattr(speakers, "_dev"):
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume
                interface = speakers._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
            else:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume
                interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

            volume.SetMasterVolumeLevelScalar(params.percent / 100.0, None)
            return ToolResult(success=True, message=f"Volume set to {params.percent}%.",
                               data={"percent": params.percent})
        except ImportError:
            return ToolResult(
                success=False,
                message="Volume control requires the 'pycaw' and 'comtypes' packages on Windows.",
                error="missing_dependency",
            )
        except Exception as exc:  # pragma: no cover - hardware/OS dependent
            return ToolResult(success=False, message="Could not change the system volume.", error=str(exc))
