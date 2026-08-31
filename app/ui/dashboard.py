"""
Dashboard panel — the home screen showing summary stat cards and
a quick-start section.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.ui.theme import (
    ACCENT, BG_CARD, BG_DARK, BG_PANEL, BORDER,
    FG_PRIMARY, FG_SECONDARY, FG_MUTED,
    FONT_BOLD, FONT_H1, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER, INFO,
    bytes_human,
)
from app.ui.widgets import StatCard, SectionLabel, PrimaryButton, IconButton


class DashboardPanel(tk.Frame):
    """
    Main dashboard view.
    Shows:
      - 4 stat cards (apps, duplicates, groups, recoverable space)
      - Recent scan summary
      - Quick-action buttons
    """

    def __init__(self, parent, on_start_scan: Callable, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_start_scan = on_start_scan
        self._build()

    def _build(self):
        # ── Header ──────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=20, padx=24)
        header.pack(fill="x")

        tk.Label(header, text="🔍  Application Duplicate Detector",
                 font=FONT_H1, fg=ACCENT, bg=BG_DARK).pack(anchor="w")
        tk.Label(header, text="Identify and safely remove duplicate application installs",
                 font=FONT_NORMAL, fg=FG_SECONDARY, bg=BG_DARK).pack(anchor="w")

        # ── Stat cards ───────────────────────────────────────────────────
        cards_frame = tk.Frame(self, bg=BG_DARK, padx=24)
        cards_frame.pack(fill="x", pady=(0, 16))
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="c")

        self._card_apps = StatCard(cards_frame, "Apps Scanned", "—",
                                   colour=INFO)
        self._card_apps.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=6)

        self._card_groups = StatCard(cards_frame, "Duplicate Groups", "—",
                                     colour=WARNING)
        self._card_groups.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        self._card_copies = StatCard(cards_frame, "Duplicate Copies", "—",
                                     colour=DANGER)
        self._card_copies.grid(row=0, column=2, sticky="ew", padx=8, pady=6)

        self._card_space = StatCard(cards_frame, "Recoverable Space", "—",
                                    colour=SUCCESS)
        self._card_space.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=6)

        # ── Quick actions ────────────────────────────────────────────────
        actions = tk.Frame(self, bg=BG_DARK, padx=24, pady=4)
        actions.pack(fill="x")

        SectionLabel(actions, "Quick Actions", bg=BG_DARK).pack(fill="x", pady=(0, 12))

        btn_row = tk.Frame(actions, bg=BG_DARK)
        btn_row.pack(anchor="w")

        PrimaryButton(btn_row, "⚡  Full System Scan",
                      command=lambda: self._on_start_scan("full")
                      ).pack(side="left", padx=(0, 10))

        IconButton(btn_row, "📁  Scan a Folder",
                   command=lambda: self._on_start_scan("directory"),
                   bg=BG_PANEL, active_bg=ACCENT
                   ).pack(side="left")

        # ── Recent activity ──────────────────────────────────────────────
        recent_frame = tk.Frame(self, bg=BG_DARK, padx=24, pady=16)
        recent_frame.pack(fill="both", expand=True)

        SectionLabel(recent_frame, "Recent Scans", bg=BG_DARK).pack(fill="x", pady=(0, 10))

        # Table
        cols = ("Scan ID", "Type", "Root", "Status", "Apps", "Groups", "Started")
        self._tree = ttk.Treeview(
            recent_frame, columns=cols, show="headings",
            height=8, selectmode="browse",
        )
        for col in cols:
            self._tree.heading(col, text=col)
        self._tree.column("Scan ID", width=60, anchor="center")
        self._tree.column("Type",    width=80, anchor="center")
        self._tree.column("Root",    width=220)
        self._tree.column("Status",  width=90, anchor="center")
        self._tree.column("Apps",    width=60, anchor="center")
        self._tree.column("Groups",  width=70, anchor="center")
        self._tree.column("Started", width=160)

        vsb = ttk.Scrollbar(recent_frame, orient="vertical", command=self._tree.yview)
        self._tree.config(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        # Style tags
        self._tree.tag_configure("done",      foreground=SUCCESS)
        self._tree.tag_configure("error",     foreground=DANGER)
        self._tree.tag_configure("cancelled", foreground=WARNING)
        self._tree.tag_configure("running",   foreground=INFO)

    # ------------------------------------------------------------------
    # Public update API (called by the main app after DB refresh)
    # ------------------------------------------------------------------

    def refresh_stats(self, stats: dict):
        self._card_apps.update_value(str(stats.get("total_apps", "—")))
        self._card_groups.update_value(str(stats.get("duplicate_groups", "—")))
        self._card_copies.update_value(str(stats.get("duplicate_copies", "—")))
        rb = stats.get("recoverable_bytes", 0)
        self._card_space.update_value(bytes_human(rb) if rb else "—")

    def refresh_scans(self, scans: list):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for s in scans[:20]:
            root_disp = (s.root_path[:40] + "…") if len(s.root_path) > 40 else (s.root_path or "Full System")
            self._tree.insert(
                "", "end",
                values=(s.id, s.scan_type.title(), root_disp,
                        s.status.upper(), s.apps_found, s.duplicates_found,
                        (s.started_at or "")[:19]),
                tags=(s.status,),
            )
