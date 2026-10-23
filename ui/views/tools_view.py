"""
Read-only catalogue of every registered tool and its permission level —
useful so the user can see exactly what SARAS is capable of and which
actions need confirmation, straight from the live ToolRegistry (never a
hardcoded list that could drift from reality).
"""
from __future__ import annotations

import customtkinter as ctk

from security.policies import PermissionLevel
from ui import theme

_BADGE_COLORS = {
    PermissionLevel.SAFE: (theme.SUCCESS, "SAFE"),
    PermissionLevel.LOW_RISK: (theme.INFO, "LOW RISK"),
    PermissionLevel.CONFIRM: (theme.WARNING, "CONFIRM"),
    PermissionLevel.HIGH_RISK: (theme.DANGER, "HIGH RISK"),
}


class ToolRow(ctk.CTkFrame):
    def __init__(self, master, name: str, description: str, level: PermissionLevel):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=10)
        color, label = _BADGE_COLORS[level]

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        ctk.CTkLabel(left, text=name, font=(theme.FONT_FAMILY, 14, "bold"),
                     text_color=theme.TEXT_PRIMARY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text=description, font=theme.FONT_SMALL,
                     text_color=theme.TEXT_SECONDARY, anchor="w", justify="left",
                     wraplength=560).pack(anchor="w", pady=(2, 0))

        badge = ctk.CTkLabel(self, text=label, font=(theme.FONT_FAMILY, 10, "bold"),
                              text_color="#0F1115", fg_color=color, corner_radius=8,
                              padx=10, pady=4)
        badge.pack(side="right", padx=16)


class ToolsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        ctk.CTkLabel(self, text="Tools", font=theme.FONT_TITLE, text_color=theme.TEXT_PRIMARY).pack(
            anchor="w", pady=(0, 4))
        ctk.CTkLabel(self, text="Everything SARAS is currently able to do.", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_SECONDARY).pack(anchor="w", pady=(0, 16))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)
        self._populated = False

    def on_show(self) -> None:
        if self._populated:
            return
        for tool in self.app.registry.list_tools():
            ToolRow(self.scroll, tool.name, tool.description, tool.permission_level).pack(
                fill="x", pady=4)
        self._populated = True
