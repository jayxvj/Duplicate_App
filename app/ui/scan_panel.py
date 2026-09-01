"""
Scan panel — controls for starting, cancelling, and monitoring scans.
Includes progress bar, live log feed, and post-scan summary.
"""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from app.ui.theme import (
    ACCENT, BG_CARD, BG_DARK, BG_PANEL, BORDER,
    FG_PRIMARY, FG_SECONDARY, FG_MUTED,
    FONT_BOLD, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER, INFO,
)
from app.ui.widgets import (
    PrimaryButton, DangerButton, IconButton, SectionLabel,
)

_MAX_LOG_LINES = 500


class ScanPanel(tk.Frame):
    """
    Controls:
      - Full-system scan button
      - Directory picker + scan button
      - Progress bar (indeterminate → determinate)
      - Live status text
      - Scrolling log feed
      - Cancel button
    Callbacks:
      on_start_full()
      on_start_dir(path: str)
      on_cancel()
    """

    def __init__(self, parent,
                 on_start_full: Callable,
                 on_start_dir: Callable[[str], None],
                 on_cancel: Callable,
                 **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_start_full = on_start_full
        self._on_start_dir  = on_start_dir
        self._on_cancel     = on_cancel
        self._selected_dir  = tk.StringVar()
        self._log_queue: queue.Queue = queue.Queue()
        self._build()
        self._poll_log()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        pad = {"padx": 24, "pady": 10}

        # ── Header ──────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=20, padx=24)
        header.pack(fill="x")
        tk.Label(header, text="⚙  Scan", font=(FONT_TITLE[0], 16, "bold"),
                 fg=ACCENT, bg=BG_DARK).pack(anchor="w")
        tk.Label(header, text="Discover and analyse application installations",
                 font=FONT_NORMAL, fg=FG_SECONDARY, bg=BG_DARK).pack(anchor="w")

        # ── Scan options ─────────────────────────────────────────────────
        opts = tk.Frame(self, bg=BG_DARK, padx=24, pady=4)
        opts.pack(fill="x")

        SectionLabel(opts, "Scan Type", bg=BG_DARK).pack(fill="x", pady=(0, 10))

        full_card = tk.Frame(opts, bg=BG_CARD, pady=12, padx=16,
                             highlightthickness=1, highlightbackground=BORDER)
        full_card.pack(fill="x", pady=(0, 8))

        tk.Label(full_card, text="🖥  Full System Scan",
                 font=FONT_BOLD, fg=FG_PRIMARY, bg=BG_CARD).pack(anchor="w")
        tk.Label(full_card, text="Scans Windows registry and all standard install directories.",
                 font=FONT_SMALL, fg=FG_SECONDARY, bg=BG_CARD).pack(anchor="w", pady=(2, 8))

        self._btn_full = PrimaryButton(full_card, "Start Full Scan",
                                       command=self._start_full)
        self._btn_full.pack(anchor="w")

        dir_card = tk.Frame(opts, bg=BG_CARD, pady=12, padx=16,
                            highlightthickness=1, highlightbackground=BORDER)
        dir_card.pack(fill="x")

        tk.Label(dir_card, text="📁  Directory Scan",
                 font=FONT_BOLD, fg=FG_PRIMARY, bg=BG_CARD).pack(anchor="w")
        tk.Label(dir_card, text="Scan a specific folder for duplicate application installs.",
                 font=FONT_SMALL, fg=FG_SECONDARY, bg=BG_CARD).pack(anchor="w", pady=(2, 8))

        dir_row = tk.Frame(dir_card, bg=BG_CARD)
        dir_row.pack(fill="x")

        self._dir_entry = tk.Entry(dir_row, textvariable=self._selected_dir,
                                   font=FONT_NORMAL, fg=FG_PRIMARY, bg=BG_PANEL,
                                   insertbackground=ACCENT, relief="flat",
                                   highlightthickness=1, highlightbackground=BORDER)
        self._dir_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        IconButton(dir_row, "Browse…", command=self._browse_dir,
                   bg=BG_PANEL).pack(side="left", padx=(0, 8))
        self._btn_dir = PrimaryButton(dir_row, "Scan Folder",
                                      command=self._start_dir)
        self._btn_dir.pack(side="left")

        # ── Progress ─────────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=BG_DARK, padx=24, pady=10)
        prog_frame.pack(fill="x")

        SectionLabel(prog_frame, "Progress", bg=BG_DARK).pack(fill="x", pady=(0, 8))

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(prog_frame, textvariable=self._status_var,
                 font=FONT_NORMAL, fg=FG_PRIMARY, bg=BG_DARK,
                 anchor="w").pack(fill="x")

        self._progress_var = tk.DoubleVar(value=0)
        self._progress = ttk.Progressbar(
            prog_frame, variable=self._progress_var,
            maximum=100, mode="indeterminate", length=400,
        )
        self._progress.pack(fill="x", pady=(6, 0))

        self._pct_var = tk.StringVar(value="")
        tk.Label(prog_frame, textvariable=self._pct_var,
                 font=FONT_SMALL, fg=FG_MUTED, bg=BG_DARK,
                 anchor="e").pack(fill="x")

        self._btn_cancel = DangerButton(prog_frame, "✕  Cancel",
                                        command=self._on_cancel)
        self._btn_cancel.pack(anchor="w", pady=(8, 0))
        self._btn_cancel.config(state="disabled")

        # ── Live log ──────────────────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG_DARK, padx=24, pady=6)
        log_frame.pack(fill="both", expand=True)

        SectionLabel(log_frame, "Live Log", bg=BG_DARK).pack(fill="x", pady=(0, 6))

        self._log_text = tk.Text(
            log_frame, font=FONT_MONO, fg="#a0ffa0", bg="#050510",
            relief="flat", bd=0, state="disabled",
            highlightthickness=1, highlightbackground=BORDER,
            wrap="word",
        )
        vsb = ttk.Scrollbar(log_frame, orient="vertical",
                             command=self._log_text.yview)
        self._log_text.config(yscrollcommand=vsb.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select folder to scan")
        if d:
            self._selected_dir.set(d)

    def _start_full(self):
        self._on_start_full()

    def _start_dir(self):
        d = self._selected_dir.get().strip()
        if not d:
            self._browse_dir()
            d = self._selected_dir.get().strip()
        if d:
            self._on_start_dir(d)

    # ------------------------------------------------------------------
    # Public API called by main app
    # ------------------------------------------------------------------

    def set_scanning(self, scanning: bool):
        """Enable/disable controls when a scan starts or ends."""
        state = "disabled" if scanning else "normal"
        self._btn_full.config(state=state)
        self._btn_dir.config(state=state)
        self._btn_cancel.config(state="normal" if scanning else "disabled")
        if scanning:
            self._progress.config(mode="indeterminate")
            self._progress.start(12)
        else:
            self._progress.stop()
            self._progress.config(mode="determinate")
            self._progress_var.set(100 if scanning is False else 0)

    def set_progress(self, done: int, total: int, msg: str = ""):
        if total > 0:
            self._progress.stop()
            self._progress.config(mode="determinate")
            pct = min(100.0, done / total * 100)
            self._progress_var.set(pct)
            self._pct_var.set(f"{done}/{total}  ({pct:.0f}%)")
        self._status_var.set(msg or "Scanning…")
        self.log(msg)

    def log(self, msg: str):
        """Thread-safe log append (via queue)."""
        self._log_queue.put(msg)

    def clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _poll_log(self):
        """Drain the log queue into the Text widget on the main thread."""
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._log_text.config(state="normal")
                self._log_text.insert("end", msg + "\n")
                # Keep only last N lines
                lines = int(self._log_text.index("end-1c").split(".")[0])
                if lines > _MAX_LOG_LINES:
                    self._log_text.delete("1.0", f"{lines - _MAX_LOG_LINES}.0")
                self._log_text.see("end")
                self._log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)
