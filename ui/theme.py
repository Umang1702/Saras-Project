"""
Central design tokens for the SARAS desktop UI. Keeping colors/fonts here
means every view looks consistent and the whole app's look can be
re-themed by editing one file.
"""
from __future__ import annotations

# --- Palette: dark, professional, single accent color -----------------------
BG_PRIMARY = "#0F1115"        # main window background
BG_SIDEBAR = "#15181E"        # sidebar background
BG_CARD = "#1B1F27"           # card / panel background
BG_CARD_HOVER = "#232833"
BORDER = "#2A2F3A"

ACCENT = "#5B8CFF"            # primary accent (buttons, active nav, links)
ACCENT_HOVER = "#4472E8"
ACCENT_SOFT = "#22283A"       # accent tint for subtle highlights

TEXT_PRIMARY = "#F2F3F5"
TEXT_SECONDARY = "#9AA1AC"
TEXT_MUTED = "#666D7A"

SUCCESS = "#3DD68C"
WARNING = "#F5B94D"
DANGER = "#F0654D"
INFO = "#5B8CFF"

STATE_COLORS = {
    "IDLE": TEXT_MUTED,
    "LISTENING": ACCENT,
    "PROCESSING": WARNING,
    "SPEAKING": SUCCESS,
    "AWAITING_CONFIRMATION": DANGER,
}

# --- Typography ---------------------------------------------------------------
FONT_FAMILY = "Segoe UI"       # ships with Windows; falls back gracefully elsewhere

FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 13, "normal")
FONT_HEADING = (FONT_FAMILY, 15, "bold")
FONT_BODY = (FONT_FAMILY, 13, "normal")
FONT_SMALL = (FONT_FAMILY, 11, "normal")
FONT_MONO = ("Consolas", 12, "normal")

# --- Layout ------------------------------------------------------------------
SIDEBAR_WIDTH = 220
CORNER_RADIUS = 12
PADDING = 16
