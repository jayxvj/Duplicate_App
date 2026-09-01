"""
History & Quarantine Panel:
  - Safe Quarantine Vault with 1-click restore functionality
  - Past scan audit logs & JSON export
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, List, Optional

from app.data.models import ScanRecord
from app.data.repository import Repository
from app.removal.quarantine import QuarantineManager
from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_INPUT, BG_PANEL, BG_ROW_ALT, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO,
    PURPLE,
    SUCCESS, SUCCESS_LIGHT, SUCCESS_SURFACE,
    WARNING, WARNING_LIGHT,
    bytes_human,
)
from app.ui.widgets import (
    DangerButton, IconButton, PillBadge, PrimaryButton, SecondaryButton, SectionLabel, SuccessButton,
)


class HistoryPanel(tk.Frame):
    """
    History & Quarantine Panel:
      - Quarantine Vault with 1-click restoration
      - Scan execution audit records
    """

    def __init__(self, parent, repo: Repository, on_toast: Callable[[str, str], None], **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._repo = repo
        self._qm = QuarantineManager()
        self._on_toast = on_toast
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=20, padx=28)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Quarantine Vault & Scan History",
            font=FONT_H1,
            fg=FG_PRIMARY,
            bg=BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Inspect isolated applications, restore files with 1-click, and review historical scan audit logs",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 0))

        # ── Quarantine Vault Section ──────────────────────────────────────────
        q_frame = tk.Frame(
            self,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        q_frame.pack(fill="both", expand=True, padx=28, pady=(0, 16))

        q_head = tk.Frame(q_frame, bg=BG_CARD)
        q_head.pack(fill="x", pady=(0, 10))

        SectionLabel(q_head, text="🛡️ Safe Quarantine Vault", bg=BG_CARD).pack(
            side="left"
        )

        SecondaryButton(
            q_head,
            text="🔄 Refresh Vault",
            command=self.refresh_quarantine,
        ).pack(side="right")

        # Treeview for Quarantined Apps
        q_tree_frame = tk.Frame(q_frame, bg=BG_CARD)
        q_tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        self._q_tree = ttk.Treeview(
            q_tree_frame,
            columns=("status", "size", "original_path", "date"),
            show="headings",
            selectmode="browse",
            height=6,
        )
        self._q_tree.heading("status", text="Status", anchor="center")
        self._q_tree.heading("size", text="Size", anchor="e")
        self._q_tree.heading("original_path", text="Original File Path", anchor="w")
        self._q_tree.heading("date", text="Isolation Date", anchor="w")

        self._q_tree.column("status", width=130, anchor="center")
        self._q_tree.column("size", width=100, anchor="e")
        self._q_tree.column("original_path", width=360)
        self._q_tree.column("date", width=160)

        q_vsb = ttk.Scrollbar(q_tree_frame, orient="vertical", command=self._q_tree.yview)
        self._q_tree.configure(yscrollcommand=q_vsb.set)
        self._q_tree.pack(side="left", fill="both", expand=True)
        q_vsb.pack(side="right", fill="y")

        # Vault Action Bar
        q_actions = tk.Frame(q_frame, bg=BG_CARD)
        q_actions.pack(fill="x")

        SuccessButton(
            q_actions,
            text="↺ Restore Selected Application",
            command=self._restore_selected_quarantine,
        ).pack(side="left")

        # ── Scan History Log Section ──────────────────────────────────────────
        h_frame = tk.Frame(
            self,
            bg=BG_CARD,
            padx=20,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        h_frame.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        h_head = tk.Frame(h_frame, bg=BG_CARD)
        h_head.pack(fill="x", pady=(0, 10))

        SectionLabel(h_head, text="📜 Past Scan Audit Records", bg=BG_CARD).pack(
            side="left"
        )

        SecondaryButton(
            h_head,
            text="📥 Export History (JSON)",
            command=self._export_history_json,
        ).pack(side="right")

        h_tree_frame = tk.Frame(h_frame, bg=BG_CARD)
        h_tree_frame.pack(fill="both", expand=True)

        self._h_tree = ttk.Treeview(
            h_tree_frame,
            columns=("scan_id", "type", "apps", "groups", "status", "completed"),
            show="headings",
            selectmode="browse",
            height=5,
        )
        self._h_tree.heading("scan_id", text="Scan ID", anchor="w")
        self._h_tree.heading("type", text="Type", anchor="w")
        self._h_tree.heading("apps", text="Apps Found", anchor="e")
        self._h_tree.heading("groups", text="Duplicate Groups", anchor="e")
        self._h_tree.heading("status", text="Status", anchor="center")
        self._h_tree.heading("completed", text="Timestamp", anchor="w")

        self._h_tree.column("scan_id", width=90)
        self._h_tree.column("type", width=110)
        self._h_tree.column("apps", width=100, anchor="e")
        self._h_tree.column("groups", width=130, anchor="e")
        self._h_tree.column("status", width=100, anchor="center")
        self._h_tree.column("completed", width=200)

        h_vsb = ttk.Scrollbar(h_tree_frame, orient="vertical", command=self._h_tree.yview)
        self._h_tree.configure(yscrollcommand=h_vsb.set)
        self._h_tree.pack(side="left", fill="both", expand=True)
        h_vsb.pack(side="right", fill="y")

    # ── Refresh & Actions ────────────────────────────────────────────────────

    def refresh_quarantine(self):
        self._q_tree.delete(*self._q_tree.get_children())
        records = self._qm.list_quarantined()

        for idx, r in enumerate(records):
            orig_path = r.get("original_path", "")
            size_str = bytes_human(r.get("total_size", 0))
            date_str = r.get("quarantined_at", "Recent")
            row_id = f"q_{idx}_{orig_path}"
            self._q_tree.insert(
                "",
                "end",
                iid=row_id,
                values=("🛡️ QUARANTINED", size_str, orig_path, date_str),
            )

    def refresh_history(self):
        self._h_tree.delete(*self._h_tree.get_children())
        try:
            records = self._repo.get_all_scans() or []
        except Exception:
            records = []

        # Show newest 30 scans
        for s in records[:30]:
            scan_id = str(getattr(s, "id", getattr(s, "scan_id", "N/A")))
            scan_type = getattr(s, "scan_type", "Directory")
            apps_cnt = str(getattr(s, "apps_found", getattr(s, "total_apps", 0)))
            dups_cnt = str(getattr(s, "duplicates_found", getattr(s, "duplicate_groups", 0)))
            status = str(getattr(s, "status", "done")).upper()
            time_str = getattr(s, "finished_at", getattr(s, "started_at", getattr(s, "completed_at", "Recent")))

            self._h_tree.insert(
                "",
                "end",
                iid=f"scan_row_{scan_id}",
                values=(
                    f"#{scan_id}",
                    scan_type,
                    apps_cnt,
                    dups_cnt,
                    status,
                    time_str,
                ),
            )

    def _restore_selected_quarantine(self):
        selected = self._q_tree.selection()
        if not selected:
            self._on_toast("Please select a quarantined item to restore.", "warning")
            return

        row_id = selected[0]
        # Look up item from values
        item_values = self._q_tree.item(row_id, "values")
        if not item_values or len(item_values) < 3:
            return
        orig_path = item_values[2]

        success = self._qm.restore_application(orig_path)
        if success:
            self._on_toast(f"Restored application to '{orig_path}' successfully!", "success")
            self.refresh_quarantine()
        else:
            self._on_toast("Restore failed: destination path already exists or file missing.", "error")

    def _export_history_json(self):
        try:
            records = self._repo.get_all_scans() or []
        except Exception:
            records = []

        data = [
            {
                "id": getattr(s, "id", getattr(s, "scan_id", None)),
                "scan_type": getattr(s, "scan_type", "directory"),
                "root_path": getattr(s, "root_path", ""),
                "started_at": getattr(s, "started_at", None),
                "finished_at": getattr(s, "finished_at", getattr(s, "completed_at", None)),
                "status": getattr(s, "status", "done"),
                "apps_found": getattr(s, "apps_found", getattr(s, "total_apps", 0)),
                "duplicates_found": getattr(s, "duplicates_found", getattr(s, "duplicate_groups", 0)),
            }
            for s in records[:100]
        ]

        save_path = filedialog.asksaveasfilename(
            title="Save Scan Audit History",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="iadcs_scan_history.json",
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._on_toast(f"Exported {len(data)} scan records to JSON!", "success")
