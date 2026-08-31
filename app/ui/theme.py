"""
Shared UI constants and helpers — colours, fonts, and reusable style utilities.
"""
from __future__ import annotations

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK      = "#0d0d1a"
BG_CARD      = "#12122a"
BG_PANEL     = "#16163a"
BG_ROW_ALT  = "#1a1a35"
BG_HOVER     = "#20204a"

ACCENT       = "#7c6fff"      # purple
ACCENT2      = "#5e5bc0"
SUCCESS      = "#22c55e"
WARNING      = "#f59e0b"
DANGER       = "#ef4444"
INFO         = "#38bdf8"

FG_PRIMARY   = "#e8e8ff"
FG_SECONDARY = "#9090b0"
FG_MUTED     = "#5a5a7a"

BORDER       = "#2a2a50"

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_FAMILY  = "Segoe UI"
FONT_NORMAL  = (FONT_FAMILY, 10)
FONT_SMALL   = (FONT_FAMILY, 9)
FONT_BOLD    = (FONT_FAMILY, 10, "bold")
FONT_TITLE   = (FONT_FAMILY, 13, "bold")
FONT_H1      = (FONT_FAMILY, 18, "bold")
FONT_MONO    = ("Consolas", 9)


def bytes_human(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
