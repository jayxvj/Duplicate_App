"""
Root Application Window for IADCS Sentinel Desktop:
Assembles all panels, configures dark styles, owns managers,
and routes events seamlessly across views via thread-safe queue.
"""
from __future__ import annotations

import logging
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional

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
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_INPUT, BG_PANEL, BG_ROW_ALT, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO,
    PURPLE,
    SUCCESS, SUCCESS_LIGHT, SUCCESS_SURFACE,
    WARNING, WARNING_LIGHT,
)
from app.ui.widgets import Toast

logger = logging.getLogger(__name__)

_NAV_ITEMS = [
    ("📊", "Overview", "dashboard"),
    ("🔍", "Scan Folders", "scan"),
    ("📋", "Duplicate Review", "results"),
    ("🛡️", "Quarantine Vault", "quarantine"),
    ("📜", "Scan History", "history"),
    ("⚙️", "Settings", "settings"),
]


class AppWindow(tk.Tk):
    """Main Desktop Application Window."""

    def __init__(self):
        super().__init__()
        self.title("IADCS Sentinel — Intelligent Application Deduplication & System Optimizer")
        w, h = getattr(cfg, "window_size", (1140, 740))
        self.geometry(f"{w}x{h}")
        self.minsize(980, 640)
        self.configure(bg=BG_DARK)

        # Services
        self._db = Database(cfg.db_path)
        self._db.connect()
        self._repo = Repository(self._db)
        self._scan_mgr = ScanManager(self._repo)
        self._report_mgr = ReportManager(self._repo)

        self._event_queue: queue.Queue = queue.Queue()
        self._current_scan: Optional[ScanRecord] = None
        self._current_groups: List[DuplicateGroup] = []

        self._setup_styles()
        self._build_layout()
        self._refresh_dashboard()

        # Start thread-safe event queue listener
        self._poll_events()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Top level container
        root_container = tk.Frame(self, bg=BG_DARK)
        root_container.pack(fill="both", expand=True)

        # ── Left Navigation Sidebar ───────────────────────────────────────────
        self._sidebar = tk.Frame(
            root_container,
            bg=BG_SURFACE,
            width=240,
            padx=14,
            pady=20,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Sidebar Header
        sb_head = tk.Frame(self._sidebar, bg=BG_SURFACE)
        sb_head.pack(fill="x", pady=(0, 20))

        logo_row = tk.Frame(sb_head, bg=BG_SURFACE)
        logo_row.pack(anchor="w")

        # Logo icon box
        logo_box = tk.Label(
            logo_row,
            text="⚡",
            font=(FONT_H1[0], 14, "bold"),
            fg="#ffffff",
            bg=ACCENT,
            padx=8,
            pady=4,
        )
        logo_box.pack(side="left", padx=(0, 10))

        title_col = tk.Frame(logo_row, bg=BG_SURFACE)
        title_col.pack(side="left")

        tk.Label(
            title_col,
            text="IADCS Sentinel",
            font=(FONT_BOLD[0], 12, "bold"),
            fg=FG_PRIMARY,
            bg=BG_SURFACE,
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text="DEDUPLICATOR PRO",
            font=(FONT_SMALL[0], 8, "bold"),
            fg=ACCENT_LIGHT,
            bg=BG_SURFACE,
        ).pack(anchor="w")

        # Navigation Buttons
        self._nav_buttons: Dict[str, tk.Button] = {}
        self._nav_frame = tk.Frame(self._sidebar, bg=BG_SURFACE)
        self._nav_frame.pack(fill="x", expand=True, anchor="n")

        for icon, label, key in _NAV_ITEMS:
            btn = tk.Button(
                self._nav_frame,
                text=f"  {icon}  {label}",
                font=FONT_BOLD,
                fg=FG_SECONDARY,
                bg=BG_SURFACE,
                activeforeground="#ffffff",
                activebackground=ACCENT_SURFACE,
                relief="flat",
                bd=0,
                anchor="w",
                padx=12,
                pady=10,
                cursor="hand2",
                command=lambda k=key: self._switch_panel(k),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[key] = btn

        # Sidebar Footer
        sb_foot = tk.Frame(self._sidebar, bg=BG_SURFACE)
        sb_foot.pack(side="bottom", fill="x")

        status_box = tk.Frame(
            sb_foot,
            bg=BG_CARD,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        status_box.pack(fill="x", pady=(0, 10))

        tk.Label(
            status_box,
            text="● Safe Mode: Active",
            font=(FONT_SMALL[0], 9, "bold"),
            fg=SUCCESS_LIGHT,
            bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            status_box,
            text="SHA-256 Byte Verified",
            font=FONT_SMALL,
            fg=FG_MUTED,
            bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            sb_foot,
            text="v2.0 Pro • Obsidian Logic",
            font=FONT_SMALL,
            fg=FG_MUTED,
            bg=BG_SURFACE,
        ).pack(anchor="w")

        # ── Main Content Area ─────────────────────────────────────────────────
        self._content = tk.Frame(root_container, bg=BG_DARK)
        self._content.pack(side="left", fill="both", expand=True)

        # Panels
        self._panel_dashboard = DashboardPanel(
            self._content,
            on_start_scan=self._on_quick_scan,
            on_navigate=self._switch_panel,
        )
        self._panel_scan = ScanPanel(
            self._content,
            on_start_full=self._on_start_full_scan,
            on_start_dir=self._on_start_dir_scan,
            on_cancel=self._on_cancel_scan,
        )
        self._panel_results = ResultsPanel(
            self._content,
            repo=self._repo,
            on_toast=self._show_toast,
        )
        self._panel_history = HistoryPanel(
            self._content,
            repo=self._repo,
            on_toast=self._show_toast,
        )
        self._panel_settings = SettingsPanel(
            self._content,
            on_toast=self._show_toast,
        )

        self._panels = {
            "dashboard":  self._panel_dashboard,
            "scan":       self._panel_scan,
            "results":    self._panel_results,
            "quarantine": self._panel_history,
            "history":    self._panel_history,
            "settings":   self._panel_settings,
        }

        self._active_key = "dashboard"
        self._switch_panel("dashboard")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=8, troughcolor=BG_PANEL, background=SUCCESS)

    def _switch_panel(self, key: str):
        for p in self._panels.values():
            p.pack_forget()

        # Update button highlights
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.config(bg=ACCENT_SURFACE, fg="#ffffff", relief="flat")
            else:
                btn.config(bg=BG_SURFACE, fg=FG_SECONDARY)

        panel = self._panels.get(key, self._panel_dashboard)
        panel.pack(fill="both", expand=True)
        self._active_key = key

        if key == "dashboard":
            self._refresh_dashboard()
        elif key in ("history", "quarantine"):
            self._panel_history.refresh_quarantine()
            self._panel_history.refresh_history()

    # ── Scan Event Handling ──────────────────────────────────────────────────

    def _on_quick_scan(self, preset: str):
        self._panel_scan.set_target_path(preset)
        self._switch_panel("scan")
        self._panel_scan._handle_start_scan()

    def _on_start_full_scan(self):
        self._run_scan(None)

    def _on_start_dir_scan(self, path: str):
        self._run_scan(path)

    def _on_cancel_scan(self):
        self._scan_mgr.cancel()
        self._panel_scan.log("Cancellation requested by user...", "WARNING")

    def _run_scan(self, target_path: Optional[str] = None):
        self._panel_scan.set_scanning(True)
        target_display = target_path or "Full System"
        self._panel_scan.log(f"Starting scan for: {target_display}...", "INFO")

        def _on_progress(stage: str, cur: int, tot: int):
            self._event_queue.put(("progress", stage, cur, tot))

        def _on_done(scan_record: Optional[ScanRecord], groups: List[DuplicateGroup]):
            self._event_queue.put(("done", scan_record, groups))

        def _on_error(err_msg: str):
            self._event_queue.put(("error", err_msg))

        if target_path:
            self._scan_mgr.start_directory_scan(
                directory=target_path,
                on_progress=_on_progress,
                on_done=_on_done,
                on_error=_on_error,
            )
        else:
            self._scan_mgr.start_full_scan(
                on_progress=_on_progress,
                on_done=_on_done,
                on_error=_on_error,
            )

    def _poll_events(self):
        """Thread-safe queue listener on main GUI loop."""
        try:
            while not self._event_queue.empty():
                evt = self._event_queue.get_nowait()
                action = evt[0]

                if action == "progress":
                    _, stage, cur, tot = evt
                    self._panel_scan.set_progress(cur, tot, stage)
                    if stage:
                        self._panel_scan.log(stage, "INFO")
                elif action == "done":
                    _, scan_record, groups = evt
                    self._scan_finished(scan_record, groups)
                elif action == "error":
                    _, err_msg = evt
                    self._panel_scan.log(f"Error: {err_msg}", "DANGER")
                    self._panel_scan.set_scanning(False)
                    self._show_toast(f"Scan error: {err_msg}", "error")
        except Exception as e:
            logger.warning("Error processing event queue: %s", e)

        self.after(50, self._poll_events)

    def _scan_finished(self, scan_record: Optional[ScanRecord], groups: List[DuplicateGroup]):
        self._panel_scan.set_scanning(False)
        self._current_scan = scan_record
        self._current_groups = groups

        if scan_record:
            apps_cnt = getattr(scan_record, "apps_found", getattr(scan_record, "total_apps", len(groups)))
            dups_cnt = getattr(scan_record, "duplicates_found", getattr(scan_record, "duplicate_groups", len(groups)))
            self._show_toast(
                f"Scan Complete! Found {apps_cnt} apps, {dups_cnt} duplicate groups.",
                "success",
            )
            self._panel_results.load_groups(groups)
            self._refresh_dashboard()
            self._switch_panel("results")
        else:
            self._show_toast("Scan completed with no records or was cancelled.", "info")

    def _refresh_dashboard(self):
        try:
            stats = self._repo.get_stats()
            total_apps = stats.get("total_apps", 0)
            total_groups = stats.get("duplicate_groups", 0)
            total_copies = stats.get("duplicate_copies", 0)
            recoverable = stats.get("recoverable_bytes", 0)

            recent_scans = self._repo.get_all_scans()
            recent_dict = None
            if recent_scans:
                s = recent_scans[0]
                recent_dict = {
                    "scan_id": s.id,
                    "total_apps": s.apps_found,
                    "duplicate_groups": s.duplicates_found,
                    "reclaimable_size": recoverable,
                    "completed_at": s.finished_at or s.started_at,
                }

            self._panel_dashboard.update_stats(
                total_apps=total_apps,
                total_groups=total_groups,
                total_copies=total_copies,
                recoverable_bytes=recoverable,
                recent_scan=recent_dict,
            )
        except Exception as e:
            logger.warning("Failed to refresh dashboard stats: %s", e)

    def _show_toast(self, message: str, level: str = "info"):
        Toast(self, message=message, level=level)

    def _on_close(self):
        try:
            self._db.close()
        except Exception:
            pass
        self.destroy()


