"""
Scan panel — controls for configuring, launching, and monitoring
multi-stage scans. Includes 4-stage pipeline stepper, live progress bar,
and dark terminal log feed.
"""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_INPUT, BG_PANEL, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO,
    PURPLE,
    SUCCESS, SUCCESS_LIGHT,
    WARNING, WARNING_LIGHT,
)
from app.ui.widgets import (
    DangerButton, IconButton, PrimaryButton, SecondaryButton, SectionLabel,
)

_MAX_LOG_LINES = 600


class ScanPanel(tk.Frame):
    """
    Scan Panel featuring:
      - Directory picker with native browse dialog
      - Quick preset chips
      - 4-Stage Pipeline Stepper visualizer
      - Progress bar & live item counters
      - Colored dark terminal log feed
      - Start / Cancel execution controls
    """

    def __init__(
        self,
        parent,
        on_start_full: Callable,
        on_start_dir: Callable[[str], None],
        on_cancel: Callable,
        **kw,
    ):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_start_full = on_start_full
        self._on_start_dir = on_start_dir
        self._on_cancel = on_cancel
        self._selected_dir = tk.StringVar(value="")
        self._log_queue: queue.Queue = queue.Queue()
        self._build()
        self._poll_log()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=22, padx=28)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Scan Manager & Pipeline Execution",
            font=FONT_H1,
            fg=FG_PRIMARY,
            bg=BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Select directories to traverse recursively, calculate SHA-256 digests, and identify duplicates",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 0))

        # ── Configuration Card ────────────────────────────────────────────────
        config_card = tk.Frame(
            self,
            bg=BG_CARD,
            padx=24,
            pady=20,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        config_card.pack(fill="x", padx=28, pady=(0, 16))

        SectionLabel(config_card, text="Target Directory Configuration", bg=BG_CARD).pack(
            fill="x", pady=(0, 12)
        )

        input_row = tk.Frame(config_card, bg=BG_CARD)
        input_row.pack(fill="x", pady=(0, 12))

        self._ent_dir = tk.Entry(
            input_row,
            textvariable=self._selected_dir,
            font=FONT_NORMAL,
            bg=BG_INPUT,
            fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        self._ent_dir.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

        SecondaryButton(
            input_row,
            text="📂 Browse Folder...",
            command=self._on_browse,
        ).pack(side="left", padx=(0, 8))

        self._btn_start = PrimaryButton(
            input_row,
            text="🚀 Start Pipeline Scan",
            command=self._handle_start_scan,
        )
        self._btn_start.pack(side="left")

        # Quick preset buttons row
        presets_row = tk.Frame(config_card, bg=BG_CARD)
        presets_row.pack(fill="x")

        tk.Label(
            presets_row,
            text="Quick Presets:",
            font=(FONT_SMALL[0], 9, "bold"),
            fg=FG_MUTED,
            bg=BG_CARD,
        ).pack(side="left", padx=(0, 8))

        SecondaryButton(
            presets_row,
            text="📦 Sample Apps",
            command=lambda: self.set_target_path("sample_apps"),
        ).pack(side="left", padx=4)

        SecondaryButton(
            presets_row,
            text="📥 Downloads",
            command=lambda: self.set_target_path("downloads"),
        ).pack(side="left", padx=4)

        SecondaryButton(
            presets_row,
            text="💻 Program Files",
            command=lambda: self.set_target_path("program_files"),
        ).pack(side="left", padx=4)

        # ── Pipeline Stepper Visualizer ───────────────────────────────────────
        step_card = tk.Frame(
            self,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        step_card.pack(fill="x", padx=28, pady=(0, 16))

        # Status row
        status_row = tk.Frame(step_card, bg=BG_CARD)
        status_row.pack(fill="x", pady=(0, 10))

        self._lbl_status = tk.Label(
            status_row,
            text="Scanner idle. Ready to analyze directories.",
            font=FONT_BOLD,
            fg=FG_PRIMARY,
            bg=BG_CARD,
        )
        self._lbl_status.pack(side="left")

        self._lbl_pct = tk.Label(
            status_row,
            text="0%",
            font=FONT_BOLD,
            fg=ACCENT_LIGHT,
            bg=BG_CARD,
        )
        self._lbl_pct.pack(side="right")

        # Progress bar
        self._pbar = ttk.Progressbar(step_card, orient="horizontal", mode="determinate")
        self._pbar.pack(fill="x", pady=(0, 14))

        # 4 Stage Steppers
        steppers_row = tk.Frame(step_card, bg=BG_CARD)
        steppers_row.pack(fill="x")
        steppers_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="step")

        self._steps = []
        step_labels = [
            "1. Discovery & Inventory",
            "2. SHA-256 Hashing",
            "3. Rule Categorization",
            "4. Duplicate Verification",
        ]
        for i, text in enumerate(step_labels):
            lbl = tk.Label(
                steppers_row,
                text=text,
                font=FONT_SMALL,
                fg=FG_MUTED,
                bg=BG_PANEL,
                padx=10,
                pady=6,
                highlightthickness=1,
                highlightbackground=BORDER,
            )
            lbl.grid(row=0, column=i, sticky="ew", padx=4)
            self._steps.append(lbl)

        # ── Live Terminal Console ─────────────────────────────────────────────
        console_frame = tk.Frame(
            self,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        console_frame.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        c_header = tk.Frame(console_frame, bg=BG_CARD)
        c_header.pack(fill="x", pady=(0, 8))

        SectionLabel(c_header, text="Pipeline Live Stream Log", bg=BG_CARD).pack(
            side="left"
        )

        self._btn_cancel = DangerButton(
            c_header,
            text="✕ Cancel Scan",
            command=self._on_cancel,
        )
        self._btn_cancel.pack(side="right")
        self._btn_cancel.config(state="disabled")

        # Scrolled Text
        self._txt_log = tk.Text(
            console_frame,
            font=FONT_MONO,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            relief="flat",
            bd=0,
            wrap="word",
            state="disabled",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._txt_log.pack(fill="both", expand=True)

        # Tags for colored logs
        self._txt_log.tag_config("INFO", foreground=INFO)
        self._txt_log.tag_config("SUCCESS", foreground=SUCCESS_LIGHT)
        self._txt_log.tag_config("WARNING", foreground=WARNING_LIGHT)
        self._txt_log.tag_config("DANGER", foreground=DANGER_LIGHT)
        self._txt_log.tag_config("MUTED", foreground=FG_MUTED)

    # ── Logic & Event Handlers ────────────────────────────────────────────────

    def _on_browse(self):
        chosen = filedialog.askdirectory(
            title="Select Target Folder to Scan",
            initialdir=self._selected_dir.get() or None,
        )
        if chosen:
            self._selected_dir.set(chosen)

    def set_target_path(self, preset: str):
        if preset == "sample_apps":
            self._selected_dir.set("sample_apps")
        elif preset == "downloads":
            import os
            self._selected_dir.set(os.path.expanduser("~/Downloads"))
        elif preset == "program_files":
            self._selected_dir.set("C:\\Program Files")
        elif preset == "custom":
            self._on_browse()

    def _handle_start_scan(self):
        path = self._selected_dir.get().strip()
        if path:
            self._on_start_dir(path)
        else:
            self._on_start_full()

    def set_scanning(self, is_scanning: bool):
        """Toggle button states and animation during scan."""
        if is_scanning:
            self._btn_start.config(state="disabled")
            self._btn_cancel.config(state="normal")
            self._lbl_status.config(text="Scanning in progress...", fg=ACCENT_LIGHT)
            self._pbar.config(mode="determinate", value=15)
            self._update_steppers(15)
        else:
            self._btn_start.config(state="normal")
            self._btn_cancel.config(state="disabled")
            self._lbl_status.config(text="Scan completed.", fg=SUCCESS_LIGHT)
            self._pbar.config(value=100)
            self._lbl_pct.config(text="100%")
            self._update_steppers(100)

    def set_progress(self, current: int, total: int, status: str = ""):
        """Update determinate progress bar and pipeline step highlights."""
        if total > 0:
            pct = int((current / total) * 100)
            self._pbar.config(value=pct)
            self._lbl_pct.config(text=f"{pct}%")
            self._update_steppers(pct)
        if status:
            self._lbl_status.config(text=status)

    def _update_steppers(self, pct: int):
        for i, step_lbl in enumerate(self._steps):
            threshold = (i + 1) * 25
            if pct >= threshold:
                step_lbl.config(bg=SUCCESS_SURFACE, fg=SUCCESS_LIGHT, highlightbackground=SUCCESS)
            elif pct >= threshold - 24:
                step_lbl.config(bg=ACCENT_SURFACE, fg=ACCENT_LIGHT, highlightbackground=ACCENT)
            else:
                step_lbl.config(bg=BG_PANEL, fg=FG_MUTED, highlightbackground=BORDER)

    def log(self, message: str, level: str = "INFO"):
        """Enqueue message for thread-safe UI display."""
        self._log_queue.put((message, level.upper()))

    def _poll_log(self):
        """Drain log queue and insert into ScrolledText widget."""
        drained = 0
        while not self._log_queue.empty() and drained < 50:
            msg, level = self._log_queue.get_nowait()
            self._txt_log.config(state="normal")
            tag = level if level in ("INFO", "SUCCESS", "WARNING", "DANGER") else "MUTED"
            self._txt_log.insert("end", f"[{level}] ", tag)
            self._txt_log.insert("end", f"{msg}\n")
            self._txt_log.see("end")
            self._txt_log.config(state="disabled")
            drained += 1

        self.after(60, self._poll_log)
