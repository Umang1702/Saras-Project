"""Read-only system information tools: general info, battery, storage."""
from __future__ import annotations

import platform
import shutil

import psutil

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult


class NoInput(ToolInput):
    pass


class SystemInfoTool(Tool):
    name = "get_system_information"
    description = "Get basic system information: OS, CPU usage, memory usage."
    permission_level = PermissionLevel.SAFE
    input_model = NoInput

    def run(self, params: NoInput) -> ToolResult:
        info = {
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": psutil.cpu_percent(interval=0.3),
            "memory_percent": psutil.virtual_memory().percent,
        }
        message = (
            f"You're on {info['os']}. CPU is at {info['cpu_percent']}% "
            f"and memory at {info['memory_percent']}%."
        )
        return ToolResult(success=True, message=message, data=info)


class BatteryStatusTool(Tool):
    name = "get_battery_status"
    description = "Get the laptop's current battery percentage and charging status."
    permission_level = PermissionLevel.SAFE
    input_model = NoInput

    def run(self, params: NoInput) -> ToolResult:
        battery = psutil.sensors_battery()
        if battery is None:
            return ToolResult(success=False, message="No battery detected on this machine.", error="no_battery")
        state = "charging" if battery.power_plugged else "on battery"
        message = f"Battery is at {round(battery.percent)}% and {state}."
        return ToolResult(success=True, message=message, data={"percent": battery.percent, "plugged": battery.power_plugged})


class StorageStatusTool(Tool):
    name = "get_storage_status"
    description = "Get free/used disk space on the main system drive."
    permission_level = PermissionLevel.SAFE
    input_model = NoInput

    def run(self, params: NoInput) -> ToolResult:
        total, used, free = shutil.disk_usage("/")
        gb = 1024 ** 3
        message = f"You have {free // gb} GB free out of {total // gb} GB."
        return ToolResult(success=True, message=message, data={
            "total_gb": total // gb, "used_gb": used // gb, "free_gb": free // gb,
        })
