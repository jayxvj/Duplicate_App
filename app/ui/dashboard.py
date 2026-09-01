"""
Dashboard panel — the home screen showing rich stat cards,
1-click quick-start presets, and recent scan summaries.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_PANEL, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO,
    PURPLE,
    SUCCESS, SUCCESS_LIGHT,
    WARNING, WARNING_LIGHT,
    bytes_human,
)
from app.ui.widgets import (
    PrimaryButton, SecondaryButton, SuccessButton,
    StatCard, SectionLabel,
)


class DashboardPanel(tk.Frame):
    """
    Main dashboard view:
      - 4 Rich Stat Cards (Apps, Groups, Copies, Reclaimable Space)
      - Quick-Action Hero Box with 1-click presets
      - System Safeguards & Engine Status Box
      - Recent Scans Table
    """

    def __init__(self, parent, on_start_scan: Callable, on_navigate: Optional[Callable[[str], None]] = None, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_start_scan = on_start_scan
        self._on_navigate = on_navigate
        self._build()

    def _build(self):
        # ── Top Header ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=22, padx=28)
        header.pack(fill="x")

        top_row = tk.Frame(header, bg=BG_DARK)
        top_row.pack(fill="x")

        title_col = tk.Frame(top_row, bg=BG_DARK)
        title_col.pack(side="left")

        tk.Label(
            title_col,
            text="System Overview & Storage Analytics",
            font=FONT_H1,
            fg=FG_PRIMARY,
            bg=BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text="Content-based application discovery & deterministic SHA-256 deduplication",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 0))

        # Top Right Action Button
        PrimaryButton(
            top_row,
            text="⚡ 1-Click Scan",
            command=lambda: self._trigger_preset("sample_apps"),
        ).pack(side="right")

        # ── 4 Rich Stat Cards ────────────────────────────────────────────────
        cards_frame = tk.Frame(self, bg=BG_DARK, padx=28)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="c")

        self._card_apps = StatCard(
            cards_frame,
            label="Total Apps",
            value="0",
            subtitle="Indexed in database",
            colour=INFO,
            icon="📦",
        )
        self._card_apps.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._card_groups = StatCard(
            cards_frame,
            label="Duplicate Groups",
            value="0",
            subtitle="Matching content sets",
            colour=WARNING,
            icon="📋",
        )
        self._card_groups.grid(row=0, column=1, sticky="ew", padx=8)

        self._card_copies = StatCard(
            cards_frame,
            label="Redundant Copies",
            value="0",
            subtitle="Safe candidates to clean",
            colour=DANGER,
            icon="⚠️",
        )
        self._card_copies.grid(row=0, column=2, sticky="ew", padx=8)

        self._card_space = StatCard(
            cards_frame,
            label="Reclaimable Space",
            value="0.0 B",
            subtitle="100% Safe to Reclaim",
            colour=SUCCESS,
            icon="🛡️",
        )
        self._card_space.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        # ── Quick Action Hero Banner ─────────────────────────────────────────
        hero_frame = tk.Frame(
            self,
            bg=BG_CARD,
            padx=24,
            pady=20,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        hero_frame.pack(fill="x", padx=28, pady=(0, 20))

        hero_left = tk.Frame(hero_frame, bg=BG_CARD)
        hero_left.pack(side="left", fill="both", expand=True)

        tk.Label(
            hero_left,
            text="Instant Directory & Package Deduplication",
            font=FONT_TITLE,
            fg=FG_PRIMARY,
            bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            hero_left,
            text="Multi-stage cryptographic verification pipeline: Size filtration → Partial Hash → Full SHA-256 → Byte Verification.",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(anchor="w", pady=(4, 14))

        presets_row = tk.Frame(hero_left, bg=BG_CARD)
        presets_row.pack(anchor="w")

        PrimaryButton(
            presets_row,
            text="📦 Scan Sample Apps",
            command=lambda: self._trigger_preset("sample_apps"),
        ).pack(side="left", padx=(0, 8))

        SecondaryButton(
            presets_row,
            text="📥 User Downloads",
            command=lambda: self._trigger_preset("downloads"),
        ).pack(side="left", padx=8)

        SecondaryButton(
            presets_row,
            text="💻 Program Files",
            command=lambda: self._trigger_preset("program_files"),
        ).pack(side="left", padx=8)

        SecondaryButton(
            presets_row,
            text="📂 Custom Path...",
            command=lambda: self._trigger_preset("custom"),
        ).pack(side="left", padx=8)

        # ── Split Row: Engine Safeguards & Recent Scans ──────────────────────
        split_row = tk.Frame(self, bg=BG_DARK, padx=28)
        split_row.pack(fill="both", expand=True)
        split_row.columnconfigure((0, 1), weight=1, uniform="split")

        # Left Box: Engine Safeguards
        sg_box = tk.Frame(
            split_row,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        sg_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        SectionLabel(sg_box, text="Engine Integrity & Safeguards", bg=BG_CARD).pack(
            fill="x", pady=(0, 12)
        )

        safeguards = [
            ("🔒", "Protected OS Directories", "Windows, System32, and ProgramData paths are strictly protected."),
            ("🛡️", "Quarantine-First Safe Architecture", "Redundant items are moved to reversible quarantine before permanent removal."),
            ("⚡", "Deterministic Content Manifests", "Identifies applications by byte content, completely immune to altered names."),
        ]

        for icon, heading, desc in safeguards:
            row = tk.Frame(sg_box, bg=BG_CARD)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=icon, font=FONT_TITLE, bg=BG_CARD, fg=SUCCESS_LIGHT).pack(
                side="left", anchor="n", padx=(0, 10)
            )
            col = tk.Frame(row, bg=BG_CARD)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=heading, font=FONT_BOLD, fg=FG_PRIMARY, bg=BG_CARD).pack(anchor="w")
            tk.Label(col, text=desc, font=FONT_SMALL, fg=FG_MUTED, bg=BG_CARD).pack(anchor="w")

        # Right Box: Recent Scans Summary
        recent_box = tk.Frame(
            split_row,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        recent_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        SectionLabel(recent_box, text="Latest Scan Activity", bg=BG_CARD).pack(
            fill="x", pady=(0, 12)
        )

        self._lbl_recent_id = tk.Label(
            recent_box,
            text="Scan ID: None",
            font=FONT_BOLD,
            fg=FG_PRIMARY,
            bg=BG_CARD,
        )
        self._lbl_recent_id.pack(anchor="w", pady=(0, 4))

        self._lbl_recent_meta = tk.Label(
            recent_box,
            text="No scan records found. Run a scan to populate activity.",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        )
        self._lbl_recent_meta.pack(anchor="w")

    def _trigger_preset(self, preset: str):
        if self._on_navigate:
            self._on_navigate("scan")
        self._on_start_scan(preset)

    def update_stats(self, total_apps: int, total_groups: int,
                     total_copies: int, recoverable_bytes: int,
                     recent_scan: Optional[dict] = None):
        """Update stat card labels and recent scan info with live data."""
        self._card_apps.update_value(str(total_apps), f"{total_apps} apps tracked")
        self._card_groups.update_value(f"{total_groups} Groups", "Exact match sets")
        self._card_copies.update_value(str(total_copies), "Redundant copies")
        self._card_space.update_value(bytes_human(recoverable_bytes), "100% Safe to clean")

        if recent_scan:
            scan_id = recent_scan.get("scan_id", "N/A")
            apps = recent_scan.get("total_apps", 0)
            dups = recent_scan.get("duplicate_groups", 0)
            reclaimed = bytes_human(recent_scan.get("reclaimable_size", 0))
            time_str = recent_scan.get("completed_at", "Recent")

            self._lbl_recent_id.config(text=f"Scan ID: {scan_id}  (Completed)")
            self._lbl_recent_meta.config(
                text=f"Apps Found: {apps}  |  Duplicate Groups: {dups}\nPotential Storage Savings: {reclaimed}\nDate: {time_str}"
            )
