"""
Settings & Rule Configuration Panel:
  - Application Domain Categories
  - Protected System Paths & Exclusions
  - Safe Mode & Engine Defaults
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from app.config import cfg
from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_INPUT, BG_PANEL, BG_ROW_ALT, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO,
    PURPLE, PURPLE_SURFACE,
    SUCCESS, SUCCESS_LIGHT, SUCCESS_SURFACE,
    WARNING, WARNING_LIGHT,
)
from app.ui.widgets import (
    DangerButton, IconButton, PillBadge, PrimaryButton, SecondaryButton, SectionLabel, SuccessButton,
)


class SettingsPanel(tk.Frame):
    """Configuration & Rule Matrix Settings."""

    def __init__(self, parent, on_toast: Callable[[str, str], None], **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_toast = on_toast
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=20, padx=28)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Settings & Rule Configuration",
            font=FONT_H1,
            fg=FG_PRIMARY,
            bg=BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Manage application domain rules, protected system exclusions, and safe mode defaults",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 0))

        # ── Split Row: Category Rules & Protected Paths ───────────────────────
        split_frame = tk.Frame(self, bg=BG_DARK, padx=28)
        split_frame.pack(fill="both", expand=True, pady=(0, 20))
        split_frame.columnconfigure((0, 1), weight=1, uniform="settings")
        split_frame.rowconfigure(0, weight=1)

        # Left: Category Rules
        cat_card = tk.Frame(
            split_frame,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        cat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        SectionLabel(cat_card, text="🏷️ Application Category Rules", bg=BG_CARD).pack(
            fill="x", pady=(0, 12)
        )

        cat_tree_frame = tk.Frame(cat_card, bg=BG_CARD)
        cat_tree_frame.pack(fill="both", expand=True)

        self._cat_tree = ttk.Treeview(
            cat_tree_frame,
            columns=("priority", "category", "patterns"),
            show="headings",
            selectmode="browse",
        )
        self._cat_tree.heading("priority", text="Priority", anchor="center")
        self._cat_tree.heading("category", text="Domain Name", anchor="w")
        self._cat_tree.heading("patterns", text="Rule Match Patterns", anchor="w")

        self._cat_tree.column("priority", width=70, anchor="center")
        self._cat_tree.column("category", width=130)
        self._cat_tree.column("patterns", width=220)

        self._cat_tree.pack(side="left", fill="both", expand=True)
        cat_vsb = ttk.Scrollbar(cat_tree_frame, orient="vertical", command=self._cat_tree.yview)
        self._cat_tree.configure(yscrollcommand=cat_vsb.set)
        cat_vsb.pack(side="right", fill="y")

        self._populate_categories()

        # Right: Protected Paths & Engine Safety
        safe_card = tk.Frame(
            split_frame,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        safe_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        SectionLabel(safe_card, text="🔒 System Directory Exclusions", bg=BG_CARD).pack(
            fill="x", pady=(0, 12)
        )

        safe_tree_frame = tk.Frame(safe_card, bg=BG_CARD)
        safe_tree_frame.pack(fill="both", expand=True, pady=(0, 12))

        self._safe_tree = ttk.Treeview(
            safe_tree_frame,
            columns=("status", "path", "reason"),
            show="headings",
            selectmode="browse",
        )
        self._safe_tree.heading("status", text="Protection", anchor="center")
        self._safe_tree.heading("path", text="Excluded Directory Path", anchor="w")
        self._safe_tree.heading("reason", text="Reason", anchor="w")

        self._safe_tree.column("status", width=90, anchor="center")
        self._safe_tree.column("path", width=200)
        self._safe_tree.column("reason", width=140)

        self._safe_tree.pack(side="left", fill="both", expand=True)
        safe_vsb = ttk.Scrollbar(safe_tree_frame, orient="vertical", command=self._safe_tree.yview)
        self._safe_tree.configure(yscrollcommand=safe_vsb.set)
        safe_vsb.pack(side="right", fill="y")

        self._populate_protected_paths()

    def _populate_categories(self):
        default_cats = [
            ("1", "Development", "python, node, vscode, git, docker"),
            ("2", "Database", "postgres, mysql, sqlite, redis, mongo"),
            ("3", "Media", "vlc, ffmpeg, spotify, blender, gimp"),
            ("4", "Browsers", "chrome, firefox, edge, brave, opera"),
            ("5", "Productivity", "slack, discord, zoom, notion, obsidian"),
            ("6", "Utilities", "7zip, winrar, powershell, git-bash"),
            ("99", "General", "fallback unmatched binaries"),
        ]
        for item in default_cats:
            self._cat_tree.insert("", "end", values=item)

    def _populate_protected_paths(self):
        protected = [
            ("🔒 LOCKED", "C:\\Windows", "Core Operating System"),
            ("🔒 LOCKED", "C:\\Windows\\System32", "Critical OS Subsystems"),
            ("🔒 LOCKED", "C:\\ProgramData", "Shared System Application Data"),
            ("🔒 LOCKED", ".git / node_modules", "Source Control Repositories"),
        ]
        for item in protected:
            self._safe_tree.insert("", "end", values=item)
