"""
Reusable UI Primitives & Widgets for IADCS Desktop Application:
  - StatCard        : Rich metric card with luminous indicator
  - PrimaryButton   : Electric indigo call-to-action button
  - SuccessButton   : Emerald safe operation button
  - DangerButton    : Rose coral removal button
  - SecondaryButton : Sleek dark glass outline button
  - IconButton      : Compact utility button
  - SectionLabel    : Section heading with accent bar
  - PillBadge       : Rounded status badge
  - Toast           : Animated floating notification banner
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_PANEL, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT, DANGER_SURFACE,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO, INFO_SURFACE,
    SUCCESS, SUCCESS_LIGHT, SUCCESS_SURFACE,
    WARNING, WARNING_LIGHT, WARNING_SURFACE,
)


# ── StatCard ─────────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    """
    A modern metric card showing an uppercase label, large bold value,
    status subtitle, and a luminous accent border.
    """

    def __init__(self, parent, label: str, value: str = "0",
                 subtitle: str = "", colour: str = ACCENT, icon: str = "📊", **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._colour = colour

        # Luminous left color accent strip
        tk.Frame(self, bg=colour, width=5).pack(side="left", fill="y")

        inner = tk.Frame(self, bg=BG_CARD, padx=16, pady=14)
        inner.pack(side="left", fill="both", expand=True)

        top_row = tk.Frame(inner, bg=BG_CARD)
        top_row.pack(fill="x", anchor="w")

        tk.Label(top_row, text=icon, font=FONT_NORMAL, bg=BG_CARD, fg=colour).pack(side="left", padx=(0, 6))
        self._lbl_label = tk.Label(
            top_row,
            text=label.upper(),
            font=(FONT_SMALL[0], 9, "bold"),
            fg=FG_SECONDARY,
            bg=BG_CARD,
        )
        self._lbl_label.pack(side="left")

        self._lbl_value = tk.Label(
            inner,
            text=value,
            font=(FONT_H1[0], 20, "bold"),
            fg=colour if colour != FG_PRIMARY else FG_PRIMARY,
            bg=BG_CARD,
        )
        self._lbl_value.pack(anchor="w", pady=(4, 2))

        self._lbl_sub = tk.Label(
            inner,
            text=subtitle,
            font=FONT_SMALL,
            fg=FG_MUTED,
            bg=BG_CARD,
        )
        self._lbl_sub.pack(anchor="w")

        # Border styling
        self.config(relief="flat", bd=0, highlightthickness=1, highlightbackground=BORDER)

    def update_value(self, value: str, subtitle: str = ""):
        self._lbl_value.config(text=value)
        if subtitle:
            self._lbl_sub.config(text=subtitle)


# ── SectionLabel ─────────────────────────────────────────────────────────────

class SectionLabel(tk.Frame):
    """Clean section header with luminous accent bar and optional subtitle."""

    def __init__(self, parent, text: str, subtitle: str = "", bg: str = BG_DARK, **kw):
        super().__init__(parent, bg=bg, **kw)
        row = tk.Frame(self, bg=bg)
        row.pack(fill="x", anchor="w")

        # Small vertical accent bar
        tk.Frame(row, bg=ACCENT, width=4, height=18).pack(side="left", padx=(0, 8))
        tk.Label(row, text=text, font=FONT_TITLE, fg=FG_PRIMARY, bg=bg).pack(side="left")

        if subtitle:
            tk.Label(self, text=subtitle, font=FONT_SMALL, fg=FG_SECONDARY, bg=bg).pack(
                anchor="w", padx=(12, 0), pady=(2, 0)
            )


# ── Button Primitives ────────────────────────────────────────────────────────

class PrimaryButton(tk.Button):
    """Electric Indigo gradient call-to-action button."""

    def __init__(self, parent, text: str, command: Optional[Callable] = None, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONT_BOLD,
            fg="#ffffff",
            bg=ACCENT,
            activeforeground="#ffffff",
            activebackground=ACCENT_HOVER,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            **kw,
        )
        self.bind("<Enter>", lambda e: self.config(bg=ACCENT_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=ACCENT))


class SuccessButton(tk.Button):
    """Emerald safe-operation button (e.g. Safe Quarantine / Restore)."""

    def __init__(self, parent, text: str, command: Optional[Callable] = None, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONT_BOLD,
            fg="#ffffff",
            bg=SUCCESS,
            activeforeground="#ffffff",
            activebackground="#059669",
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            **kw,
        )
        self.bind("<Enter>", lambda e: self.config(bg="#059669"))
        self.bind("<Leave>", lambda e: self.config(bg=SUCCESS))


class DangerButton(tk.Button):
    """Rose coral removal button."""

    def __init__(self, parent, text: str, command: Optional[Callable] = None, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONT_BOLD,
            fg="#ffffff",
            bg=DANGER,
            activeforeground="#ffffff",
            activebackground="#e11d48",
            relief="flat",
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
            **kw,
        )
        self.bind("<Enter>", lambda e: self.config(bg="#e11d48"))
        self.bind("<Leave>", lambda e: self.config(bg=DANGER))


class SecondaryButton(tk.Button):
    """Sleek dark glass outline button."""

    def __init__(self, parent, text: str, command: Optional[Callable] = None, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONT_BOLD,
            fg=FG_PRIMARY,
            bg=BG_CARD,
            activeforeground="#ffffff",
            activebackground=BG_CARD_HOVER,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
            padx=14,
            pady=7,
            cursor="hand2",
            **kw,
        )
        self.bind("<Enter>", lambda e: self.config(bg=BG_CARD_HOVER, fg="#ffffff"))
        self.bind("<Leave>", lambda e: self.config(bg=BG_CARD, fg=FG_PRIMARY))


class IconButton(tk.Button):
    """Compact utility button."""

    def __init__(self, parent, text: str, command: Optional[Callable] = None,
                 bg: str = BG_CARD, fg: str = FG_PRIMARY, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONT_NORMAL,
            fg=fg,
            bg=bg,
            activeforeground="#ffffff",
            activebackground=BG_CARD_HOVER,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=10,
            pady=5,
            cursor="hand2",
            **kw,
        )


# ── PillBadge ────────────────────────────────────────────────────────────────

class PillBadge(tk.Label):
    """Rounded pill badge for statuses like ORIGINAL, DUPLICATE, QUARANTINED."""

    def __init__(self, parent, text: str, level: str = "info", **kw):
        colors = {
            "success": (SUCCESS_LIGHT, SUCCESS_SURFACE),
            "warning": (WARNING_LIGHT, WARNING_SURFACE),
            "danger":  (DANGER_LIGHT, DANGER_SURFACE),
            "info":    (INFO, INFO_SURFACE),
            "accent":  (ACCENT_LIGHT, ACCENT_SURFACE),
        }
        fg_col, bg_col = colors.get(level, colors["info"])
        super().__init__(
            parent,
            text=f"  {text}  ",
            font=(FONT_SMALL[0], 8, "bold"),
            fg=fg_col,
            bg=bg_col,
            relief="flat",
            bd=0,
            **kw,
        )


# ── Toast Notifications ──────────────────────────────────────────────────────

class Toast(tk.Toplevel):
    """
    Modern floating notification banner with smooth icon and auto-fade.
    level: 'info' | 'success' | 'warning' | 'error'
    """

    _CONFIGS = {
        "info":    (ACCENT,   "#1e1b4b", "ℹ️"),
        "success": (SUCCESS,  "#064e3b", "✓"),
        "warning": (WARNING,  "#78350f", "⚠️"),
        "error":   (DANGER,   "#881337", "✕"),
    }

    def __init__(self, root: tk.Misc, message: str, level: str = "info", ms: int = 3600):
        super().__init__(root)
        border_col, bg_col, icon = self._CONFIGS.get(level, self._CONFIGS["info"])

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=bg_col)

        frame = tk.Frame(
            self,
            bg=bg_col,
            padx=18,
            pady=12,
            highlightthickness=1,
            highlightbackground=border_col,
        )
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=icon, font=FONT_BOLD, fg=border_col, bg=bg_col).pack(
            side="left", padx=(0, 10)
        )
        tk.Label(frame, text=message, font=FONT_BOLD, fg=FG_PRIMARY, bg=bg_col).pack(
            side="left"
        )

        self.update_idletasks()
        rx = root.winfo_rootx() + root.winfo_width() - self.winfo_width() - 24
        ry = root.winfo_rooty() + root.winfo_height() - self.winfo_height() - 24
        self.geometry(f"+{max(0, rx)}+{max(0, ry)}")

        self.after(ms, self._dismiss)

    def _dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass
