"""
History panel — shows past scans with report open buttons.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from typing import List

from app.data.models import ReportRecord, ScanRecord
from app.data.repository import Repository
from app.ui.theme import (
    ACCENT, BG_DARK, BG_PANEL, BORDER,
    FG_PRIMARY, FG_SECONDARY, FG_MUTED,
    FONT_BOLD, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER, INFO,
)
from app.ui.widgets import IconButton, SectionLabel


class HistoryPanel(tk.Frame):
    def __init__(self, parent, repo: Repository, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._repo = repo
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=BG_DARK, pady=16, padx=24)
        header.pack(fill="x")
        tk.Label(header, text="📜  Scan History",
                 font=(FONT_TITLE[0], 16, "bold"), fg=ACCENT, bg=BG_DARK).pack(anchor="w")
        tk.Label(header, text="Review past scans and open generated reports.",
                 font=FONT_NORMAL, fg=FG_SECONDARY, bg=BG_DARK).pack(anchor="w")

        toolbar = tk.Frame(self, bg=BG_DARK, padx=24)
        toolbar.pack(fill="x", pady=(0, 8))
        IconButton(toolbar, "🔄  Refresh", command=self.refresh, bg=BG_PANEL).pack(side="left")

        # ── Scans table ──────────────────────────────────────────────────
        scans_f = tk.Frame(self, bg=BG_DARK, padx=24)
        scans_f.pack(fill="both", expand=True)

        SectionLabel(scans_f, "Scans", bg=BG_DARK).pack(fill="x", pady=(0, 6))

        cols = ("ID", "Type", "Root", "Status", "Apps", "Groups", "Started", "Duration")
        self._scan_tree = ttk.Treeview(scans_f, columns=cols, show="headings",
                                       height=10, selectmode="browse")
        for col in cols:
            self._scan_tree.heading(col, text=col)
        self._scan_tree.column("ID",       width=40,  anchor="center")
        self._scan_tree.column("Type",     width=80,  anchor="center")
        self._scan_tree.column("Root",     width=200)
        self._scan_tree.column("Status",   width=80,  anchor="center")
        self._scan_tree.column("Apps",     width=50,  anchor="center")
        self._scan_tree.column("Groups",   width=60,  anchor="center")
        self._scan_tree.column("Started",  width=150)
        self._scan_tree.column("Duration", width=90,  anchor="center")

        vsb = ttk.Scrollbar(scans_f, orient="vertical", command=self._scan_tree.yview)
        self._scan_tree.config(yscrollcommand=vsb.set)
        self._scan_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self._scan_tree.tag_configure("done",      foreground=SUCCESS)
        self._scan_tree.tag_configure("error",     foreground=DANGER)
        self._scan_tree.tag_configure("cancelled", foreground=WARNING)

        self._scan_tree.bind("<<TreeviewSelect>>", self._on_scan_select)

        # ── Reports for selected scan ─────────────────────────────────────
        rep_f = tk.Frame(self, bg=BG_DARK, padx=24, pady=8)
        rep_f.pack(fill="x")

        SectionLabel(rep_f, "Reports for Selected Scan", bg=BG_DARK).pack(fill="x", pady=(0, 6))

        rep_row = tk.Frame(rep_f, bg=BG_DARK)
        rep_row.pack(fill="x")

        self._report_buttons_frame = rep_row
        self._no_reports_label = tk.Label(rep_row, text="Select a scan above.",
                                          font=FONT_SMALL, fg=FG_MUTED, bg=BG_DARK)
        self._no_reports_label.pack(anchor="w")

        self.refresh()

    def refresh(self):
        scans = self._repo.get_all_scans()
        for row in self._scan_tree.get_children():
            self._scan_tree.delete(row)
        for s in scans:
            # Compute duration
            dur = "—"
            if s.started_at and s.finished_at:
                try:
                    from datetime import datetime, timezone
                    fmt = "%Y-%m-%dT%H:%M:%S"
                    t1 = datetime.fromisoformat(s.started_at.split("+")[0].split(".")[0])
                    t2 = datetime.fromisoformat(s.finished_at.split("+")[0].split(".")[0])
                    secs = int((t2 - t1).total_seconds())
                    dur = f"{secs}s"
                except Exception:
                    pass
            root_disp = (s.root_path[:35] + "…") if len(s.root_path) > 35 else (s.root_path or "Full System")
            self._scan_tree.insert(
                "", "end", iid=str(s.id),
                values=(s.id, s.scan_type.title(), root_disp,
                        s.status.upper(), s.apps_found, s.duplicates_found,
                        (s.started_at or "")[:19], dur),
                tags=(s.status,),
            )

    def _on_scan_select(self, _event=None):
        sel = self._scan_tree.selection()
        for w in self._report_buttons_frame.winfo_children():
            w.destroy()
        if not sel:
            return
        scan_id = int(sel[0])
        reports = self._repo.get_reports_for_scan(scan_id)
        if not reports:
            tk.Label(self._report_buttons_frame,
                     text="No reports generated for this scan.",
                     font=FONT_SMALL, fg=FG_MUTED, bg=BG_DARK).pack(anchor="w")
            return
        for r in reports:
            def _open(path=r.file_path):
                if os.path.exists(path):
                    if sys.platform == "win32":
                        os.startfile(path)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", path])
                    else:
                        subprocess.Popen(["xdg-open", path])
            ext = r.format.upper()
            IconButton(self._report_buttons_frame,
                       f"📄 Open {ext} Report",
                       command=_open, bg=BG_PANEL).pack(side="left", padx=(0, 8))
