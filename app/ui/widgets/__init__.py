"""
Reusable widget primitives:
  - StatCard    : stat summary tile
  - Toast       : temporary notification banner
  - SectionLabel: section heading with separator
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.theme import (
    ACCENT, BG_CARD, BG_DARK, BG_PANEL, BORDER,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER,
)


# ── StatCard ──────────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    """
    A colourful summary tile showing a label, large value, and subtitle.
    colour: accent hex string for the left border and value text.
    """

    def __init__(self, parent, label: str, value: str = "—",
                 subtitle: str = "", colour: str = ACCENT, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._colour = colour

        # Coloured left border
        tk.Frame(self, bg=colour, width=4).pack(side="left", fill="y")

        inner = tk.Frame(self, bg=BG_CARD, padx=14, pady=12)
        inner.pack(side="left", fill="both", expand=True)

        self._lbl_label = tk.Label(inner, text=label.upper(),
                                   font=FONT_SMALL, fg=FG_MUTED, bg=BG_CARD)
        self._lbl_label.pack(anchor="w")

        self._lbl_value = tk.Label(inner, text=value, font=(FONT_H1[0], 22, "bold"),
                                   fg=colour, bg=BG_CARD)
        self._lbl_value.pack(anchor="w")

        if subtitle:
            tk.Label(inner, text=subtitle, font=FONT_SMALL, fg=FG_MUTED, bg=BG_CARD
                     ).pack(anchor="w")

        # Rounded effect via relief
        self.config(relief="flat", bd=0,
                    highlightthickness=1, highlightbackground=BORDER)

    def update_value(self, value: str, subtitle: str = ""):
        self._lbl_value.config(text=value)


# ── Toast ─────────────────────────────────────────────────────────────────────

class Toast(tk.Toplevel):
    """
    Temporary floating notification that auto-dismisses after `ms` milliseconds.
    level: 'info' | 'success' | 'warning' | 'error'
    """

    _COLOURS = {
        "info":    (ACCENT,   "ℹ"),
        "success": (SUCCESS,  "✓"),
        "warning": (WARNING,  "⚠"),
        "error":   (DANGER,   "✕"),
    }

    def __init__(self, root: tk.Misc, message: str,
                 level: str = "info", ms: int = 3500):
        super().__init__(root)
        colour, icon = self._COLOURS.get(level, self._COLOURS["info"])

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg=BG_PANEL)

        frame = tk.Frame(self, bg=colour, padx=2, pady=2)
        frame.pack(fill="both", expand=True)
        inner = tk.Frame(frame, bg=BG_PANEL, padx=16, pady=10)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=f"{icon}  {message}",
                 font=FONT_NORMAL, fg=FG_PRIMARY, bg=BG_PANEL,
                 wraplength=340, justify="left").pack()

        # Position bottom-right corner of screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 60}")

        self.after(ms, self.destroy)


# ── SectionLabel ─────────────────────────────────────────────────────────────

class SectionLabel(tk.Frame):
    def __init__(self, parent, text: str, **kw):
        bg = kw.pop("bg", BG_DARK)
        super().__init__(parent, bg=bg, **kw)

        tk.Label(self, text=text, font=FONT_BOLD,
                 fg=ACCENT, bg=bg).pack(side="left", padx=(0, 12))
        tk.Frame(self, bg=BORDER, height=1).pack(side="left", fill="x", expand=True)


# ── IconButton ────────────────────────────────────────────────────────────────

class IconButton(tk.Button):
    """Flat icon button with hover highlight."""

    def __init__(self, parent, text: str, command=None,
                 fg=FG_PRIMARY, bg=BG_PANEL, active_bg=ACCENT,
                 padx=12, pady=6, **kw):
        super().__init__(
            parent, text=text, command=command,
            font=FONT_NORMAL, fg=fg, bg=bg,
            activeforeground=FG_PRIMARY, activebackground=active_bg,
            relief="flat", bd=0, cursor="hand2",
            padx=padx, pady=pady, **kw,
        )
        self._bg = bg
        self._active_bg = active_bg
        self.bind("<Enter>", lambda _: self.config(bg=active_bg))
        self.bind("<Leave>", lambda _: self.config(bg=bg))


class PrimaryButton(tk.Button):
    """Filled accent-coloured action button."""

    def __init__(self, parent, text: str, command=None, **kw):
        super().__init__(
            parent, text=text, command=command,
            font=FONT_BOLD, fg="#ffffff", bg=ACCENT,
            activeforeground="#ffffff", activebackground=ACCENT,
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=8, **kw,
        )
        self.bind("<Enter>", lambda _: self.config(bg="#9580ff"))
        self.bind("<Leave>", lambda _: self.config(bg=ACCENT))


class DangerButton(tk.Button):
    """Red destructive-action button."""

    def __init__(self, parent, text: str, command=None, **kw):
        super().__init__(
            parent, text=text, command=command,
            font=FONT_BOLD, fg="#ffffff", bg=DANGER,
            activeforeground="#ffffff", activebackground=DANGER,
            relief="flat", bd=0, cursor="hand2",
            padx=16, pady=8, **kw,
        )
        self.bind("<Enter>", lambda _: self.config(bg="#c0392b"))
        self.bind("<Leave>", lambda _: self.config(bg=DANGER))
