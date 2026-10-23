"""
Main desktop window: sidebar navigation + a swappable content area, wired
directly to the SAME `Application` object app/bootstrap.py builds for the
CLI. No separate server, no duplicated logic — the UI is just another
front end calling `app.assistant.process_text(...)`.
"""
from __future__ import annotations

import threading

import customtkinter as ctk

from core.state import AssistantState
from ui import theme
from ui.views.chat_view import ChatView
from ui.views.dashboard_view import DashboardView
from ui.views.history_view import HistoryView
from ui.views.tools_view import ToolsView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SarasWindow(ctk.CTk):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.title("SARAS — Personal AI Agent")
        self.geometry("1080x680")
        self.minsize(880, 560)
        self.configure(fg_color=theme.BG_PRIMARY)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._voice_thread: threading.Thread | None = None
        self._build_sidebar()
        self._build_content_area()

        self.app.assistant.state.on_change(self._on_state_change)
        self._show("dashboard")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- Sidebar --------------------------------------------------------

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=theme.SIDEBAR_WIDTH, fg_color=theme.BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(28, 6))
        ctk.CTkLabel(header, text="SARAS", font=(theme.FONT_FAMILY, 24, "bold"),
                     text_color=theme.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(header, text="Personal AI Agent", font=theme.FONT_SMALL,
                     text_color=theme.TEXT_SECONDARY).pack(anchor="w")

        # status pill
        self.status_frame = ctk.CTkFrame(sidebar, fg_color=theme.BG_CARD, corner_radius=10)
        self.status_frame.pack(fill="x", padx=20, pady=(18, 22))
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color=theme.STATE_COLORS["IDLE"],
                                        font=(theme.FONT_FAMILY, 16))
        self.status_dot.pack(side="left", padx=(12, 4), pady=8)
        self.status_label = ctk.CTkLabel(self.status_frame, text="Idle", font=theme.FONT_SMALL,
                                          text_color=theme.TEXT_SECONDARY)
        self.status_label.pack(side="left", pady=8)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard"),
            ("chat", "💬  Chat"),
            ("tools", "🛠️  Tools"),
            ("history", "📜  History"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w", height=40, corner_radius=8,
                fg_color="transparent", hover_color=theme.BG_CARD_HOVER,
                text_color=theme.TEXT_SECONDARY, font=theme.FONT_BODY,
                command=lambda k=key: self._show(k),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self._nav_buttons[key] = btn

        # mic toggle at the bottom
        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self.mic_button = ctk.CTkButton(
            bottom, text="🎤  Start Voice Mode", height=42, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            font=theme.FONT_BODY, command=self._toggle_voice,
        )
        self.mic_button.pack(fill="x")
        self._voice_active = False

    def _build_content_area(self) -> None:
        self.content = ctk.CTkFrame(self, fg_color=theme.BG_PRIMARY, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views = {
            "dashboard": DashboardView(self.content, self.app),
            "chat": ChatView(self.content, self.app),
            "tools": ToolsView(self.content, self.app),
            "history": HistoryView(self.content, self.app),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def _show(self, key: str) -> None:
        for name, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=theme.ACCENT_SOFT if name == key else "transparent",
                text_color=theme.TEXT_PRIMARY if name == key else theme.TEXT_SECONDARY,
            )
        self.views[key].tkraise()
        if hasattr(self.views[key], "on_show"):
            self.views[key].on_show()

    # ---- Voice control -----------------------------------------------------

    def _toggle_voice(self) -> None:
        if self._voice_active:
            if self.app.voice_session:
                self.app.voice_session.stop()
            self._voice_active = False
            self.mic_button.configure(text="🎤  Start Voice Mode", fg_color=theme.ACCENT)
            if "chat" in self.views:
                self.views["chat"].append_system_message("⏹ Voice mode stopped.")
            return

        if self.app.voice_session is None:
            self.views["chat"].append_system_message(
                "Voice mode isn't available (no microphone/voice dependencies detected). Use the chat box instead."
            )
            self._show("chat")
            return

        self._voice_active = True
        self.mic_button.configure(text="⏹  Stop Voice Mode", fg_color=theme.DANGER)
        if "chat" in self.views:
            self.views["chat"].append_system_message("🎙️ Voice mode active. Say 'Saras' — I will chime and say 'Yes, I'm listening.'")
        self._voice_thread = threading.Thread(target=self.app.voice_session.run_forever, daemon=True)
        self._voice_thread.start()

    # ---- State sync (called from whichever thread changed state) -----------

    def _on_state_change(self, state: AssistantState) -> None:
        # StateManager callbacks may fire from the voice thread; tkinter is
        # not thread-safe, so marshal the UI update onto the main loop.
        self.after(0, self._apply_state, state)

    def _apply_state(self, state: AssistantState) -> None:
        color = theme.STATE_COLORS.get(state.value, theme.TEXT_MUTED)
        self.status_dot.configure(text_color=color)
        self.status_label.configure(text=state.value.replace("_", " ").title())
        if "dashboard" in self.views:
            self.views["dashboard"].update_state(state)

    def _on_close(self) -> None:
        if self.app.voice_session is not None:
            self.app.voice_session.stop()
        self.destroy()


def launch(app) -> None:
    window = SarasWindow(app)
    window.mainloop()
