"""
Audit log view — every tool execution SARAS has performed, straight from
the SQLite `tool_executions` table (memory/database.py), so nothing shown
here is UI-side state that could drift from what actually happened.
"""
from __future__ import annotations

import customtkinter as ctk

from ui import theme


class HistoryRow(ctk.CTkFrame):
    def __init__(self, master, entry: dict):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=10)
        icon = "✅" if entry["success"] else "⚠️"
        icon_color = theme.SUCCESS if entry["success"] else theme.WARNING

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(row, text=icon, font=(theme.FONT_FAMILY, 14), text_color=icon_color).pack(side="left")
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True, padx=(10, 0))

        ctk.CTkLabel(text_col, text=f"{entry['tool_name']}", font=(theme.FONT_FAMILY, 13, "bold"),
                     text_color=theme.TEXT_PRIMARY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_col, text=entry["message"], font=theme.FONT_SMALL,
                     text_color=theme.TEXT_SECONDARY, anchor="w", wraplength=560, justify="left").pack(anchor="w")
        if entry.get("verification_issue"):
            ctk.CTkLabel(text_col, text=f"⚠ {entry['verification_issue']}", font=theme.FONT_SMALL,
                         text_color=theme.WARNING, anchor="w").pack(anchor="w")

        ctk.CTkLabel(row, text=entry["created_at"][:19].replace("T", " "), font=theme.FONT_SMALL,
                     text_color=theme.TEXT_MUTED).pack(side="right")


class HistoryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="History", font=theme.FONT_TITLE, text_color=theme.TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(header, text="↻  Refresh", width=110, height=32, corner_radius=8,
                     fg_color=theme.BG_CARD, hover_color=theme.BG_CARD_HOVER,
                     text_color=theme.TEXT_PRIMARY, command=self.refresh).pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        try:
            rows = self.app.db.recent_tool_executions(limit=50)
        except Exception:
            rows = []
        if not rows:
            ctk.CTkLabel(self.scroll, text="No actions recorded yet.", font=theme.FONT_BODY,
                         text_color=theme.TEXT_MUTED).pack(anchor="w", pady=10)
            return
        for entry in rows:
            HistoryRow(self.scroll, entry).pack(fill="x", pady=4)
