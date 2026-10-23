"""
Dashboard: at-a-glance cards — assistant status, battery, storage, recent
actions. Reuses the SAME tools (get_battery_status, get_storage_status)
the assistant itself calls, via app.registry, rather than duplicating
system-info logic in the UI layer.
"""
from __future__ import annotations

import customtkinter as ctk

from ui import theme


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str, subtitle: str = ""):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=theme.CORNER_RADIUS)
        ctk.CTkLabel(self, text=title, font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY).pack(
            anchor="w", padx=18, pady=(16, 2))
        self.value_label = ctk.CTkLabel(self, text=value, font=(theme.FONT_FAMILY, 26, "bold"),
                                         text_color=theme.TEXT_PRIMARY)
        self.value_label.pack(anchor="w", padx=18)
        self.sub_label = ctk.CTkLabel(self, text=subtitle, font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED)
        self.sub_label.pack(anchor="w", padx=18, pady=(2, 16))

    def set_value(self, value: str, subtitle: str = "") -> None:
        self.value_label.configure(text=value)
        if subtitle:
            self.sub_label.configure(text=subtitle)


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        ctk.CTkLabel(self, text="Dashboard", font=theme.FONT_TITLE, text_color=theme.TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ctk.CTkLabel(self, text="Live status of your assistant and machine.", font=theme.FONT_SUBTITLE,
                     text_color=theme.TEXT_SECONDARY).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 20))

        for i in range(3):
            self.grid_columnconfigure(i, weight=1, uniform="cards")

        self.state_card = StatCard(self, "ASSISTANT STATE", "Idle", "Waiting for a command")
        self.state_card.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=6)

        self.battery_card = StatCard(self, "BATTERY", "—", "tap refresh to check")
        self.battery_card.grid(row=2, column=1, sticky="nsew", padx=10, pady=6)

        self.storage_card = StatCard(self, "STORAGE FREE", "—", "tap refresh to check")
        self.storage_card.grid(row=2, column=2, sticky="nsew", padx=(10, 0), pady=6)

        refresh_btn = ctk.CTkButton(self, text="↻  Refresh", width=120, height=32, corner_radius=8,
                                     fg_color=theme.BG_CARD, hover_color=theme.BG_CARD_HOVER,
                                     text_color=theme.TEXT_PRIMARY, command=self.refresh_stats)
        refresh_btn.grid(row=3, column=0, sticky="w", pady=(14, 0))

        # recent actions panel
        ctk.CTkLabel(self, text="Recent Actions", font=theme.FONT_HEADING, text_color=theme.TEXT_PRIMARY).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(28, 8))
        self.recent_frame = ctk.CTkFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.CORNER_RADIUS)
        self.recent_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(0, 4))
        self.grid_rowconfigure(5, weight=1)
        self.recent_list = ctk.CTkScrollableFrame(self.recent_frame, fg_color="transparent")
        self.recent_list.pack(fill="both", expand=True, padx=10, pady=10)

    def on_show(self) -> None:
        self.refresh_stats()
        self.refresh_recent()

    def update_state(self, state) -> None:
        label = state.value.replace("_", " ").title()
        subtitle_map = {
            "IDLE": "Waiting for a command",
            "LISTENING": "Listening for your voice",
            "PROCESSING": "Working on it...",
            "SPEAKING": "Responding",
            "AWAITING_CONFIRMATION": "Waiting for your yes/no",
        }
        self.state_card.set_value(label, subtitle_map.get(state.value, ""))

    def refresh_stats(self) -> None:
        try:
            battery_tool = self.app.registry.get("get_battery_status")
            result = battery_tool.run(battery_tool.input_model())
            if result.success:
                pct = round(result.data["percent"])
                plugged = "Charging" if result.data["plugged"] else "On battery"
                self.battery_card.set_value(f"{pct}%", plugged)
            else:
                self.battery_card.set_value("N/A", result.message)
        except Exception as exc:
            self.battery_card.set_value("Error", str(exc))

        try:
            storage_tool = self.app.registry.get("get_storage_status")
            result = storage_tool.run(storage_tool.input_model())
            if result.success:
                self.storage_card.set_value(f"{result.data['free_gb']} GB", f"of {result.data['total_gb']} GB total")
        except Exception as exc:
            self.storage_card.set_value("Error", str(exc))

    def refresh_recent(self) -> None:
        for child in self.recent_list.winfo_children():
            child.destroy()
        try:
            rows = self.app.db.recent_tool_executions(limit=8)
        except Exception:
            rows = []
        if not rows:
            ctk.CTkLabel(self.recent_list, text="No actions yet — try the Chat tab.",
                         font=theme.FONT_BODY, text_color=theme.TEXT_MUTED).pack(anchor="w", padx=6, pady=6)
            return
        for row in rows:
            icon = "✅" if row["success"] else "⚠️"
            line = f"{icon}  {row['tool_name']}  —  {row['message']}"
            ctk.CTkLabel(self.recent_list, text=line, font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY,
                         anchor="w", justify="left").pack(anchor="w", padx=6, pady=3, fill="x")
