"""
Chat-style interface: type a command (or it fills in from voice mode) and
see SARAS's reply as chat bubbles, plus a confirm/cancel prompt when an
action needs it — mirroring exactly what would happen over voice, so text
and voice mode share one code path (app.assistant.process_text).
"""
from __future__ import annotations

import threading

import customtkinter as ctk

from core.state import AssistantState
from ui import theme


class MessageBubble(ctk.CTkFrame):
    def __init__(self, master, text: str, sender: str):
        is_user = sender == "user"
        super().__init__(master, fg_color="transparent")

        bubble_color = theme.ACCENT if is_user else theme.BG_CARD
        text_color = "#FFFFFF" if is_user else theme.TEXT_PRIMARY
        anchor = "e" if is_user else "w"

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(anchor=anchor, fill="x")

        bubble = ctk.CTkLabel(
            wrapper, text=text, font=theme.FONT_BODY, text_color=text_color,
            fg_color=bubble_color, corner_radius=14, justify="left",
            wraplength=460, padx=14, pady=10,
        )
        bubble.pack(anchor=anchor, padx=(80, 0) if is_user else (0, 80), pady=4)


class ChatView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._awaiting_confirmation = False

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Chat", font=theme.FONT_TITLE, text_color=theme.TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w", pady=(0, 16))

        self.messages_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.CORNER_RADIUS)
        self.messages_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 14))

        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            input_row, placeholder_text="Type a command, e.g. \"tell me my battery percentage\"",
            height=44, corner_radius=10, font=theme.FONT_BODY,
            fg_color=theme.BG_CARD, border_color=theme.BORDER,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self._send())

        self.send_button = ctk.CTkButton(
            input_row, text="Send", width=90, height=44, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, command=self._send,
        )
        self.send_button.grid(row=0, column=1)

        self.append_system_message("Hi, I'm SARAS. Type a command below, or use the mic button in the sidebar.")
        self._last_sent_text = None
        self.app.assistant.on_interaction(self._on_assistant_interaction)

    def _on_assistant_interaction(self, user_text: str, response_text: str) -> None:
        if self._last_sent_text == user_text:
            self._last_sent_text = None
            return
        self.after(0, self._render_external_interaction, user_text, response_text)

    def _render_external_interaction(self, user_text: str, response_text: str) -> None:
        self._append_user_message(user_text)
        self.append_system_message(response_text)

    def append_system_message(self, text: str) -> None:
        MessageBubble(self.messages_frame, text, sender="assistant").pack(fill="x", pady=2)
        self._scroll_to_bottom()

    def _append_user_message(self, text: str) -> None:
        MessageBubble(self.messages_frame, text, sender="user").pack(fill="x", pady=2)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        self.after(50, lambda: self.messages_frame._parent_canvas.yview_moveto(1.0))

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self._last_sent_text = text
        self.entry.delete(0, "end")
        self._append_user_message(text)
        self.send_button.configure(state="disabled")

        def worker():
            try:
                response = self.app.assistant.process_text(text)
            except Exception as exc:
                response = f"Something went wrong: {exc}"
            self.after(0, self._on_response, response)

        threading.Thread(target=worker, daemon=True).start()

    def _on_response(self, response: str) -> None:
        self.append_system_message(response)
        self.send_button.configure(state="normal")
        self._awaiting_confirmation = self.app.assistant.state.state == AssistantState.AWAITING_CONFIRMATION
        if self._awaiting_confirmation:
            self.entry.configure(placeholder_text="Reply yes or no...")
