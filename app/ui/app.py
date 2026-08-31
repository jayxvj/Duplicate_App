"""
Root application window — assembles all panels, configures ttk styles,
owns the managers, and routes events between UI and business logic.
"""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from app.config import cfg
from app.data.database import Database
from app.data.models import DuplicateGroup, ScanRecord
from app.data.repository import Repository
from app.manager.report_manager import ReportManager
from app.manager.scan_manager import ScanManager
from app.ui.dashboard import DashboardPanel
from app.ui.history_panel import HistoryPanel
from app.ui.results_panel import ResultsPanel
from app.ui.scan_panel import ScanPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.theme import (
    ACCENT, ACCENT2, BG_CARD, BG_DARK, BG_PANEL, BG_ROW_ALT, BORDER,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER, INFO,
)
from app.ui.widgets import Toast

logger = logging.getLogger(__name__)

_NAV_ITEMS = [
    ("🏠", "Dashboard"),
    ("⚙", "Scan"),
    ("📋", "Results"),
    ("📜", "History"),
    ("⚙", "Settings"),
]


class AppWindow(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Application Duplicate Detector")
        w, h = cfg.window_size
        self.geometry(f"{w}x{h}")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        # Services
        self._db = Database(cfg.db_path)
        self._db.connect()
        self._repo = Repository(self._db)
        self._scan_mgr = ScanManager(self._repo)
        self._report_mgr = ReportManager(self._repo)

        self._current_scan: Optional[ScanRecord] = None
        self._current_groups: List[DuplicateGroup] = []

        self._setup_styles()
        self._build_layout()
        self._refresh_dashboard()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Treeview dark theme
        style.configure("Treeview",
                        background=BG_CARD,
                        foreground=FG_PRIMARY,
                        fieldbackground=BG_CARD,
                        borderwidth=0,
                        rowheight=26,
                        font=FONT_NORMAL)
        style.configure("Treeview.Heading",
                        background=BG_PANEL,
                        foreground=ACCENT,
                        font=FONT_BOLD,
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", ACCENT2)],
                  foreground=[("selected", "#ffffff")])

        # Notebook
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_PANEL,
                        foreground=FG_SECONDARY,
                        padding=[12, 6],
                        font=FONT_NORMAL)
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        # Progressbar
        style.configure("Horizontal.TProgressbar",
                        troughcolor=BG_PANEL,
                        background=ACCENT,
                        darkcolor=ACCENT,
                        lightcolor=ACCENT,
                        bordercolor=BG_PANEL)

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=BG_PANEL,
                        troughcolor=BG_DARK,
                        arrowcolor=FG_MUTED)
        style.configure("Horizontal.TScrollbar",
                        background=BG_PANEL,
                        troughcolor=BG_DARK,
                        arrowcolor=FG_MUTED)

        # PanedWindow sash
        self.option_add("*PanedWindow.sashWidth", 4)
        self.option_add("*PanedWindow.background", BORDER)

    def _build_layout(self):
        # ── Outer paned: nav sidebar | main content ────────────────────
        outer = tk.Frame(self, bg=BG_DARK)
        outer.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = tk.Frame(outer, bg=BG_PANEL, width=200)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # App brand in sidebar
        brand = tk.Frame(self._sidebar, bg=BG_PANEL, pady=20, padx=12)
        brand.pack(fill="x")
        tk.Label(brand, text="🔍", font=("Segoe UI", 22),
                 fg=ACCENT, bg=BG_PANEL).pack(anchor="w")
        tk.Label(brand, text="Duplicate\nDetector", font=FONT_BOLD,
                 fg=FG_PRIMARY, bg=BG_PANEL, justify="left").pack(anchor="w")

        # Separator
        tk.Frame(self._sidebar, bg=BORDER, height=1).pack(fill="x", padx=12)

        # Nav buttons
        self._nav_btns: List[tk.Button] = []
        self._active_nav = tk.IntVar(value=0)
        nav_labels = ["Dashboard", "Scan", "Results", "History", "Settings"]
        nav_icons  = ["🏠", "⚙", "📋", "📜", "⚙"]

        for i, (icon, label) in enumerate(zip(nav_icons, nav_labels)):
            btn = tk.Button(
                self._sidebar,
                text=f"  {icon}  {label}",
                font=FONT_NORMAL,
                fg=FG_SECONDARY if i != 0 else FG_PRIMARY,
                bg=ACCENT if i == 0 else BG_PANEL,
                activeforeground=FG_PRIMARY,
                activebackground=ACCENT,
                relief="flat", bd=0, cursor="hand2",
                anchor="w", padx=12, pady=10,
                command=lambda idx=i: self._switch_tab(idx),
            )
            btn.pack(fill="x")
            self._nav_btns.append(btn)

        # Status bar at bottom of sidebar
        self._status_bar = tk.Label(
            self._sidebar, text="Ready", font=FONT_SMALL,
            fg=FG_MUTED, bg=BG_PANEL, wraplength=180, justify="left", pady=8, padx=12,
        )
        self._status_bar.pack(side="bottom", fill="x")

        # ── Content area (stacked frames, one visible at a time) ─────────
        self._content = tk.Frame(outer, bg=BG_DARK)
        self._content.pack(side="left", fill="both", expand=True)

        self._dashboard = DashboardPanel(
            self._content, on_start_scan=self._quick_scan,
        )
        self._scan_pnl = ScanPanel(
            self._content,
            on_start_full=self._start_full_scan,
            on_start_dir=self._start_dir_scan,
            on_cancel=self._cancel_scan,
        )
        self._results_pnl = ResultsPanel(
            self._content, repo=self._repo,
            on_toast=self._toast,
        )
        self._history_pnl = HistoryPanel(self._content, repo=self._repo)
        self._settings_pnl = SettingsPanel(self._content, on_toast=self._toast)

        self._panels = [
            self._dashboard,
            self._scan_pnl,
            self._results_pnl,
            self._history_pnl,
            self._settings_pnl,
        ]
        for p in self._panels:
            p.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._switch_tab(0)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _switch_tab(self, idx: int):
        for i, (btn, panel) in enumerate(zip(self._nav_btns, self._panels)):
            active = (i == idx)
            btn.config(
                bg=ACCENT if active else BG_PANEL,
                fg=FG_PRIMARY if active else FG_SECONDARY,
            )
            if active:
                panel.lift()

    # ------------------------------------------------------------------
    # Scan orchestration
    # ------------------------------------------------------------------

    def _quick_scan(self, scan_type: str):
        """Called from dashboard quick-action buttons."""
        if scan_type == "full":
            self._start_full_scan()
        else:
            self._switch_tab(1)   # go to scan panel so user picks folder

    def _start_full_scan(self):
        if self._scan_mgr.is_running:
            self._toast("A scan is already running.", "warning")
            return
        self._switch_tab(1)
        self._scan_pnl.clear_log()
        self._scan_pnl.set_scanning(True)
        self._status("Running full system scan…")
        self._scan_mgr.start_full_scan(
            on_progress=self._on_scan_progress,
            on_done=self._on_scan_done,
            on_error=self._on_scan_error,
        )

    def _start_dir_scan(self, directory: str):
        if self._scan_mgr.is_running:
            self._toast("A scan is already running.", "warning")
            return
        self._scan_pnl.clear_log()
        self._scan_pnl.set_scanning(True)
        self._status(f"Scanning: {directory}")
        self._scan_mgr.start_directory_scan(
            directory,
            on_progress=self._on_scan_progress,
            on_done=self._on_scan_done,
            on_error=self._on_scan_error,
        )

    def _cancel_scan(self):
        self._scan_mgr.cancel()
        self._status("Cancelling scan…")

    # ------------------------------------------------------------------
    # Scan callbacks (called from worker thread → safe via after())
    # ------------------------------------------------------------------

    def _on_scan_progress(self, msg: str, done: int, total: int):
        self.after(0, lambda: self._scan_pnl.set_progress(done, total, msg))
        self.after(0, lambda: self._status(msg))

    def _on_scan_done(self, scan: ScanRecord, groups: List[DuplicateGroup]):
        self._current_scan = scan
        self._current_groups = groups

        def _update():
            self._scan_pnl.set_scanning(False)
            self._scan_pnl.log(
                f"\n✓ Scan #{scan.id} complete — "
                f"{scan.apps_found} apps, {scan.duplicates_found} duplicate group(s)"
            )
            self._status(f"Scan done: {scan.apps_found} apps, {scan.duplicates_found} groups")
            self._results_pnl.load_groups(groups)
            self._refresh_dashboard()
            self._history_pnl.refresh()

            # Auto-generate reports
            if groups:
                try:
                    self._report_mgr.generate_all(scan, groups)
                except Exception as exc:
                    logger.warning("Report generation failed: %s", exc)

            if groups:
                self._toast(
                    f"Found {len(groups)} duplicate group(s)! See Results tab.",
                    "warning",
                )
                self._switch_tab(2)
            else:
                self._toast("No duplicate applications found.", "success")

        self.after(0, _update)

    def _on_scan_error(self, msg: str):
        self.after(0, lambda: self._scan_pnl.set_scanning(False))
        self.after(0, lambda: self._status(f"Scan error: {msg}"))
        self.after(0, lambda: messagebox.showerror("Scan Error", msg))

    # ------------------------------------------------------------------
    # Dashboard refresh
    # ------------------------------------------------------------------

    def _refresh_dashboard(self):
        try:
            stats = self._repo.get_stats()
            scans = self._repo.get_all_scans()
            self._dashboard.refresh_stats(stats)
            self._dashboard.refresh_scans(scans)
        except Exception as exc:
            logger.warning("Dashboard refresh failed: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _status(self, msg: str):
        self._status_bar.config(text=msg)

    def _toast(self, msg: str, level: str = "info"):
        Toast(self, msg, level=level)

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def _on_close(self):
        if self._scan_mgr.is_running:
            if not messagebox.askyesno(
                "Scan Running",
                "A scan is currently running. Cancel it and quit?",
            ):
                return
            self._scan_mgr.cancel()
        self._db.close()
        self.destroy()
