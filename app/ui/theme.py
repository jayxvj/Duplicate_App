"""
IADCS Sentinel — Obsidian Cyber-Glass Design System Theme
Shared UI constants: Color palette, typography, radii, and formatting utilities.
"""
from __future__ import annotations

# ── Obsidian Cyber-Glass Palette ─────────────────────────────────────────────
BG_DARK          = "#070b14"      # Deep space canvas
BG_SURFACE       = "#0d1527"      # Sidebar & app containers
BG_CARD          = "#111c35"      # Glassmorphism cards
BG_CARD_HOVER    = "#182544"      # Hover state for cards
BG_PANEL         = "#131f3b"      # Panel backgrounds
BG_ROW_ALT       = "#0f1930"      # Alternating row background
BG_INPUT         = "#090f1d"      # Form inputs background

# ── Brand & Accent Highlights ────────────────────────────────────────────────
ACCENT           = "#6366f1"      # Electric Indigo (Primary)
ACCENT_HOVER     = "#4f46e5"
ACCENT_LIGHT     = "#818cf8"
ACCENT_SURFACE   = "#1e1b4b"

SUCCESS          = "#10b981"      # Emerald Glow (Safe operations & Reclaim)
SUCCESS_LIGHT    = "#34d399"
SUCCESS_SURFACE  = "#064e3b"

WARNING          = "#f59e0b"      # Amber Gold (Duplicate warnings)
WARNING_LIGHT    = "#fbbf24"
WARNING_SURFACE  = "#78350f"

DANGER           = "#f43f5e"      # Rose Coral (Destructive actions)
DANGER_LIGHT     = "#fb7185"
DANGER_SURFACE   = "#881337"

INFO             = "#38bdf8"      # Cyber Sky Blue (Status & Information)
INFO_SURFACE     = "#0c4a6e"

PURPLE           = "#a855f7"      # Violet Purple (Categories)
PURPLE_SURFACE   = "#581c87"

# ── Typography & Text Colors ─────────────────────────────────────────────────
FG_PRIMARY       = "#f8fafc"      # Crisp bright white
FG_SECONDARY     = "#94a3b8"      # Cool silver / secondary text
FG_MUTED         = "#64748b"      # Muted labels / metadata
FG_DISABLED      = "#475569"

BORDER           = "#1e293b"      # Subtle card & container borders
BORDER_ACTIVE    = "#4338ca"      # Active / selected border
BORDER_LIGHT     = "#334155"

# ── Fonts ────────────────────────────────────────────────────────────────────
FONT_FAMILY      = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"

FONT_SMALL       = (FONT_FAMILY, 9)
FONT_NORMAL      = (FONT_FAMILY, 10)
FONT_BOLD        = (FONT_FAMILY, 10, "bold")
FONT_TITLE       = (FONT_FAMILY, 13, "bold")
FONT_H2          = (FONT_FAMILY, 15, "bold")
FONT_H1          = (FONT_FAMILY, 18, "bold")

FONT_MONO        = (FONT_MONO_FAMILY, 9)
FONT_MONO_BOLD   = (FONT_MONO_FAMILY, 9, "bold")


def bytes_human(b: int) -> str:
    """Format bytes into high-precision human readable string."""
    if not b or b <= 0:
        return "0.0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"
