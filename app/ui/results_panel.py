"""
Results panel — interactive duplicate review workspace.
Features:
  - Select one or multiple files with interactive checkboxes [✓] / [ ]
  - Spacebar or click to toggle selection
  - 1-Click Refresh button to reload latest duplicate groups from database
  - Smart bulk selectors (Auto-Select, Keep Newest, Keep Oldest, Select All, Deselect All)
  - Detail Inspector side-panel with single-file action & Explorer integration
  - Safe Quarantine & Trash actions
"""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Set

from app.data.models import AppRecord, DuplicateGroup
from app.data.repository import Repository
from app.removal.quarantine import QuarantineManager
from app.ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SURFACE,
    BG_CARD, BG_CARD_HOVER, BG_DARK, BG_INPUT, BG_PANEL, BG_ROW_ALT, BG_SURFACE,
    BORDER, BORDER_ACTIVE, BORDER_LIGHT,
    DANGER, DANGER_LIGHT, DANGER_SURFACE,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_H1, FONT_H2, FONT_MONO, FONT_MONO_BOLD, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    INFO, INFO_SURFACE,
    PURPLE, PURPLE_SURFACE,
    SUCCESS, SUCCESS_LIGHT, SUCCESS_SURFACE,
    WARNING, WARNING_LIGHT, WARNING_SURFACE,
    bytes_human,
)
from app.ui.widgets import (
    DangerButton, IconButton, PillBadge, PrimaryButton, SecondaryButton, SectionLabel, SuccessButton,
)


def _get_group_apps(grp: DuplicateGroup) -> List[AppRecord]:
    return getattr(grp, "members", getattr(grp, "applications", [])) or []


def _get_group_fp(grp: DuplicateGroup) -> str:
    return getattr(grp, "group_signature", getattr(grp, "fingerprint", "")) or str(id(grp))


def _get_group_name(grp: DuplicateGroup) -> str:
    apps = _get_group_apps(grp)
    return getattr(grp, "primary_name", "") or (apps[0].name if apps else "Unknown Application")


def _get_app_size(app: AppRecord) -> int:
    return getattr(app, "disk_size_bytes", getattr(app, "total_size", 0)) or 0


def _get_group_reclaimable(grp: DuplicateGroup) -> int:
    reclaim = getattr(grp, "reclaimable_size", None)
    if reclaim is not None:
        return reclaim
    apps = _get_group_apps(grp)
    if len(apps) <= 1:
        return 0
    sizes = [_get_app_size(a) for a in apps]
    return sum(sizes) - max(sizes)


class ResultsPanel(tk.Frame):
    """Interactive Duplicate Review Workspace with Single and Multi-Select."""

    def __init__(self, parent, repo: Repository, on_toast: Callable[[str, str], None], on_refresh: Optional[Callable] = None, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._repo = repo
        self._qm = QuarantineManager()
        self._on_toast = on_toast
        self._on_refresh = on_refresh
        self._groups: List[DuplicateGroup] = []
        self._selected_group: Optional[DuplicateGroup] = None
        self._selected_app: Optional[AppRecord] = None
        self._keep_map: Dict[str, AppRecord] = {}  # group_fp -> keep AppRecord
        self._selected_app_ids: Set[int] = set()
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=18, padx=28)
        header.pack(fill="x")

        head_top = tk.Frame(header, bg=BG_DARK)
        head_top.pack(fill="x")

        title_col = tk.Frame(head_top, bg=BG_DARK)
        title_col.pack(side="left")

        tk.Label(
            title_col,
            text="Duplicate Applications Review & Selection",
            font=FONT_H1,
            fg=FG_PRIMARY,
            bg=BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text="Select one or multiple duplicate files to quarantine. Press Spacebar or click items to toggle selection.",
            font=FONT_NORMAL,
            fg=FG_SECONDARY,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 0))

        # Top Right Header Buttons
        btn_box = tk.Frame(head_top, bg=BG_DARK)
        btn_box.pack(side="right")

        SecondaryButton(
            btn_box,
            text="🔄 Refresh Data",
            command=self.refresh_from_db,
        ).pack(side="left", padx=(0, 8))

        SuccessButton(
            btn_box,
            text="🛡️ Quarantine Selected",
            command=self._quarantine_selected,
        ).pack(side="left")

        # ── Action & Filter Toolbar Card ──────────────────────────────────────
        toolbar = tk.Frame(
            self,
            bg=BG_CARD,
            padx=20,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        toolbar.pack(fill="x", padx=28, pady=(0, 12))

        # Top row: Search + Selection Counter
        t_top = tk.Frame(toolbar, bg=BG_CARD)
        t_top.pack(fill="x", pady=(0, 8))

        tk.Label(t_top, text="🔍 Filter:", font=FONT_BOLD, fg=FG_SECONDARY, bg=BG_CARD).pack(
            side="left", padx=(0, 8)
        )

        self._ent_search = tk.Entry(
            t_top,
            font=FONT_NORMAL,
            bg=BG_INPUT,
            fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        self._ent_search.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 16))
        self._ent_search.bind("<KeyRelease>", self._on_search_changed)

        self._lbl_selection_summary = tk.Label(
            t_top,
            text="Selected: 0 files (0.0 B)",
            font=FONT_BOLD,
            fg=SUCCESS_LIGHT,
            bg=SUCCESS_SURFACE,
            padx=12,
            pady=4,
        )
        self._lbl_selection_summary.pack(side="right")

        # Bottom row: Smart Selection Buttons
        t_bot = tk.Frame(toolbar, bg=BG_CARD)
        t_bot.pack(fill="x")

        SecondaryButton(
            t_bot,
            text="⚡ Auto-Select All Duplicates",
            command=self._auto_select_duplicates,
        ).pack(side="left", padx=(0, 6))

        SecondaryButton(
            t_bot,
            text="⏱️ Select Older Copies",
            command=self._keep_newest,
        ).pack(side="left", padx=6)

        SecondaryButton(
            t_bot,
            text="🕰️ Select Newer Copies",
            command=self._keep_oldest,
        ).pack(side="left", padx=6)

        SecondaryButton(
            t_bot,
            text="✓ Select All in View",
            command=self._select_all_visible,
        ).pack(side="left", padx=6)

        SecondaryButton(
            t_bot,
            text="✕ Deselect All",
            command=self._deselect_all,
        ).pack(side="left", padx=6)

        # ── Main Split View: Treeview (Left) & Inspector (Right) ─────────────
        split_frame = tk.Frame(self, bg=BG_DARK, padx=28)
        split_frame.pack(fill="both", expand=True, pady=(0, 16))
        split_frame.columnconfigure(0, weight=3)
        split_frame.columnconfigure(1, weight=2)
        split_frame.rowconfigure(0, weight=1)

        # Left: Treeview
        tree_container = tk.Frame(
            split_frame,
            bg=BG_CARD,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        tree_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=BG_CARD,
            foreground=FG_PRIMARY,
            fieldbackground=BG_CARD,
            rowheight=28,
            font=FONT_NORMAL,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=BG_PANEL,
            foreground=FG_SECONDARY,
            font=FONT_BOLD,
            relief="flat",
        )
        style.map("Treeview", background=[("selected", ACCENT_SURFACE)], foreground=[("selected", "#ffffff")])

        self._tree = ttk.Treeview(
            tree_container,
            columns=("select", "status", "size", "category", "path"),
            show="tree headings",
            selectmode="extended",
        )
        self._tree.heading("#0", text="Application Set / Copy", anchor="w")
        self._tree.heading("select", text="Select", anchor="center")
        self._tree.heading("status", text="Safety Role", anchor="center")
        self._tree.heading("size", text="Size", anchor="e")
        self._tree.heading("category", text="Category", anchor="w")
        self._tree.heading("path", text="Folder Path", anchor="w")

        self._tree.column("#0", width=200, minwidth=130)
        self._tree.column("select", width=65, anchor="center")
        self._tree.column("status", width=125, anchor="center")
        self._tree.column("size", width=85, anchor="e")
        self._tree.column("category", width=95)
        self._tree.column("path", width=220)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Bindings for selection & toggles
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<space>", self._on_space_toggle)
        self._tree.bind("<Double-1>", self._on_double_click_toggle)

        # Right: Detail Inspector Card
        self._detail_frame = tk.Frame(
            split_frame,
            bg=BG_CARD,
            padx=20,
            pady=18,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._detail_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_detail_inspector()

    def _build_detail_inspector(self):
        SectionLabel(self._detail_frame, text="Selected File Inspector", bg=BG_CARD).pack(
            fill="x", pady=(0, 14)
        )

        self._lbl_insp_badge = PillBadge(self._detail_frame, text="CLICK A FILE TO INSPECT", level="info")
        self._lbl_insp_badge.pack(anchor="w", pady=(0, 10))

        self._lbl_insp_name = tk.Label(
            self._detail_frame,
            text="No File Selected",
            font=FONT_TITLE,
            fg=FG_PRIMARY,
            bg=BG_CARD,
            wraplength=320,
            justify="left",
        )
        self._lbl_insp_name.pack(anchor="w", pady=(0, 6))

        # Metadata rows
        self._insp_meta_frame = tk.Frame(self._detail_frame, bg=BG_CARD)
        self._insp_meta_frame.pack(fill="x", pady=(0, 14))

        self._lbl_insp_path = tk.Label(
            self._insp_meta_frame,
            text="Path: -",
            font=FONT_MONO,
            fg=FG_SECONDARY,
            bg=BG_CARD,
            wraplength=320,
            justify="left",
        )
        self._lbl_insp_path.pack(anchor="w", pady=2)

        self._lbl_insp_size = tk.Label(
            self._insp_meta_frame, text="Size: -", font=FONT_SMALL, fg=FG_MUTED, bg=BG_CARD
        )
        self._lbl_insp_size.pack(anchor="w", pady=2)

        self._lbl_insp_hash = tk.Label(
            self._insp_meta_frame,
            text="SHA-256: -",
            font=FONT_MONO,
            fg=INFO,
            bg=BG_CARD,
            wraplength=320,
            justify="left",
        )
        self._lbl_insp_hash.pack(anchor="w", pady=2)

        # Selection Toggle Button
        self._btn_toggle_item = SecondaryButton(
            self._detail_frame,
            text="☐ Select this File for Quarantine",
            command=self._toggle_current_app_selection,
        )
        self._btn_toggle_item.pack(fill="x", pady=(0, 8))

        # Action Buttons
        self._insp_actions = tk.Frame(self._detail_frame, bg=BG_CARD)
        self._insp_actions.pack(fill="x", pady=(4, 0))

        SecondaryButton(
            self._insp_actions,
            text="📂 Open in File Explorer",
            command=self._open_in_explorer,
        ).pack(fill="x", pady=(0, 8))

        self._btn_mark_keep = PrimaryButton(
            self._insp_actions,
            text="⭐ Set as Reference Original (Keep)",
            command=self._mark_as_keep,
        )
        self._btn_mark_keep.pack(fill="x", pady=(0, 8))

        DangerButton(
            self._insp_actions,
            text="🛡️ Quarantine This Single File Now",
            command=self._quarantine_single_current,
        ).pack(fill="x")

    # ── Data Loading & Rendering ─────────────────────────────────────────────

    def load_groups(self, groups: List[DuplicateGroup]):
        self._groups = groups
        self._init_keep_map()
        self._populate_tree()

    def refresh_from_db(self):
        """Reload latest duplicate groups and scans directly from the database."""
        try:
            groups = self._repo.get_all_duplicate_groups()
            self.load_groups(groups)
            if self._on_refresh:
                self._on_refresh()
            self._on_toast(f"Refreshed: Loaded {len(groups)} duplicate groups from database.", "success")
        except Exception as e:
            self._on_toast(f"Refresh failed: {e}", "error")

    def _init_keep_map(self):
        self._keep_map.clear()
        for g in self._groups:
            apps = _get_group_apps(g)
            if apps:
                fp = _get_group_fp(g)
                ref_id = getattr(g, "reference_app_id", None)
                chosen = next((a for a in apps if a.id == ref_id), apps[0])
                self._keep_map[fp] = chosen

    def _populate_tree(self, filter_text: str = ""):
        self._tree.delete(*self._tree.get_children())
        q = filter_text.lower().strip()

        for g_idx, g in enumerate(self._groups):
            apps = _get_group_apps(g)
            fp = _get_group_fp(g)
            grp_name = _get_group_name(g)
            keep_app = self._keep_map.get(fp)

            if q and not any(
                q in (a.name.lower() or "") or q in (a.install_path.lower() or "") or q in (a.category.lower() or "")
                for a in apps
            ):
                continue

            grp_id = f"grp_{g_idx}_{getattr(g, 'id', g_idx)}"
            reclaim_str = bytes_human(_get_group_reclaimable(g))
            cat_str = apps[0].category if apps else "General"

            self._tree.insert(
                "",
                "end",
                iid=grp_id,
                text=f"📦 {grp_name} ({len(apps)} copies)",
                values=("", "Exact Match", reclaim_str, cat_str, ""),
                open=True,
            )

            for a_idx, app in enumerate(apps):
                app_iid = f"app_{getattr(app, 'id', a_idx)}_{g_idx}_{a_idx}"
                is_keep = (keep_app and app.id == keep_app.id)
                status_text = "⭐ KEEP (ORIGINAL)" if is_keep else "⚠️ DUPLICATE"
                is_checked = (app.id in self._selected_app_ids)
                check_icon = "⭐" if is_keep else ("☑️ [✓]" if is_checked else "☐ [ ]")

                self._tree.insert(
                    grp_id,
                    "end",
                    iid=app_iid,
                    text=f"  📄 {app.name}",
                    values=(
                        check_icon,
                        status_text,
                        bytes_human(_get_app_size(app)),
                        app.category,
                        app.install_path,
                    ),
                )

        self._update_selection_summary()

    def _on_search_changed(self, event=None):
        self._populate_tree(self._ent_search.get())

    def _on_tree_select(self, event):
        selected = self._tree.selection()
        if not selected:
            return
        iid = selected[0]

        if iid.startswith("app_"):
            parts = iid.split("_")
            app_id = int(parts[1])
            app = self._find_app_by_id(app_id)
            if app:
                self._selected_app = app
                self._update_inspector_app(app)
        elif iid.startswith("grp_"):
            parts = iid.split("_")
            g_idx = int(parts[1])
            if 0 <= g_idx < len(self._groups):
                grp = self._groups[g_idx]
                self._selected_group = grp
                self._update_inspector_group(grp)

    def _on_space_toggle(self, event):
        """Toggle checkbox for all selected items on Spacebar press."""
        selected = self._tree.selection()
        for iid in selected:
            if iid.startswith("app_"):
                parts = iid.split("_")
                app_id = int(parts[1])
                app = self._find_app_by_id(app_id)
                if app and app.id is not None:
                    grp = next((g for g in self._groups if any(a.id == app.id for a in _get_group_apps(g))), None)
                    is_keep = False
                    if grp:
                        keep_app = self._keep_map.get(_get_group_fp(grp))
                        is_keep = (keep_app and keep_app.id == app.id)

                    if not is_keep:
                        if app_id in self._selected_app_ids:
                            self._selected_app_ids.remove(app_id)
                        else:
                            self._selected_app_ids.add(app_id)
        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        return "break"

    def _on_double_click_toggle(self, event):
        """Toggle checkbox on double click."""
        item = self._tree.identify('item', event.x, event.y)
        if item and item.startswith("app_"):
            parts = item.split("_")
            app_id = int(parts[1])
            app = self._find_app_by_id(app_id)
            if app and app.id is not None:
                grp = next((g for g in self._groups if any(a.id == app.id for a in _get_group_apps(g))), None)
                is_keep = False
                if grp:
                    keep_app = self._keep_map.get(_get_group_fp(grp))
                    is_keep = (keep_app and keep_app.id == app.id)

                if not is_keep:
                    if app_id in self._selected_app_ids:
                        self._selected_app_ids.remove(app_id)
                    else:
                        self._selected_app_ids.add(app_id)
                    self._populate_tree(self._ent_search.get())
                    self._update_inspector_app(app)

    def _toggle_current_app_selection(self):
        if not self._selected_app or self._selected_app.id is None:
            return
        app_id = self._selected_app.id
        grp = next((g for g in self._groups if any(a.id == app_id for a in _get_group_apps(g))), None)
        if grp:
            keep_app = self._keep_map.get(_get_group_fp(grp))
            if keep_app and keep_app.id == app_id:
                self._on_toast("Cannot select the protected reference original copy.", "warning")
                return

        if app_id in self._selected_app_ids:
            self._selected_app_ids.remove(app_id)
        else:
            self._selected_app_ids.add(app_id)

        self._populate_tree(self._ent_search.get())
        self._update_inspector_app(self._selected_app)

    def _update_inspector_app(self, app: AppRecord):
        grp = next((g for g in self._groups if any(a.id == app.id for a in _get_group_apps(g))), None)
        is_keep = False
        if grp:
            fp = _get_group_fp(grp)
            keep_app = self._keep_map.get(fp)
            is_keep = (keep_app and keep_app.id == app.id)

        is_checked = (app.id in self._selected_app_ids)

        if is_keep:
            self._lbl_insp_badge.config(text="  ⭐ PROTECTED REFERENCE COPY  ", fg=SUCCESS_LIGHT, bg=SUCCESS_SURFACE)
            self._btn_toggle_item.config(text="⭐ Protected Reference (Cannot Select)", state="disabled")
        elif is_checked:
            self._lbl_insp_badge.config(text="  ☑️ SELECTED FOR REMOVAL  ", fg=SUCCESS_LIGHT, bg=SUCCESS_SURFACE)
            self._btn_toggle_item.config(text="☑️ Selected (Click to Uncheck)", state="normal", bg=SUCCESS_SURFACE)
        else:
            self._lbl_insp_badge.config(text="  ⚠️ REDUNDANT COPY  ", fg=WARNING_LIGHT, bg=WARNING_SURFACE)
            self._btn_toggle_item.config(text="☐ Check to Select for Quarantine", state="normal", bg=BG_CARD)

        self._lbl_insp_name.config(text=app.name)
        self._lbl_insp_path.config(text=f"Path: {app.install_path}")
        size_str = bytes_human(_get_app_size(app))
        self._lbl_insp_size.config(text=f"Size: {size_str} • Category: {app.category}")
        sig = getattr(app, "app_signature", getattr(app, "sha256_hash", "N/A"))
        self._lbl_insp_hash.config(text=f"SHA-256: {sig or 'N/A'}")

    def _update_inspector_group(self, grp: DuplicateGroup):
        apps = _get_group_apps(grp)
        grp_name = _get_group_name(grp)
        fp = _get_group_fp(grp)
        self._lbl_insp_badge.config(text="  📦 DUPLICATE GROUP  ", fg=ACCENT_LIGHT, bg=ACCENT_SURFACE)
        self._lbl_insp_name.config(text=f"{grp_name} ({len(apps)} instances)")
        self._lbl_insp_path.config(text=f"Fingerprint: {fp[:16]}...")
        self._lbl_insp_size.config(text=f"Reclaimable Storage: {bytes_human(_get_group_reclaimable(grp))}")
        self._lbl_insp_hash.config(text="Status: 100% SHA-256 Byte Verified")
        self._btn_toggle_item.config(text="Select Individual Files Below", state="disabled")

    # ── Smart Selection Helpers ──────────────────────────────────────────────

    def _auto_select_duplicates(self):
        self._selected_app_ids.clear()
        for g in self._groups:
            fp = _get_group_fp(g)
            keep_app = self._keep_map.get(fp)
            apps = _get_group_apps(g)
            for a in apps:
                if not keep_app or a.id != keep_app.id:
                    if a.id is not None:
                        self._selected_app_ids.add(a.id)
        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        self._on_toast(f"Auto-selected {len(self._selected_app_ids)} duplicate copies (preserved originals).", "success")

    def _keep_newest(self):
        self._selected_app_ids.clear()
        for g in self._groups:
            apps = _get_group_apps(g)
            if apps:
                fp = _get_group_fp(g)
                sorted_apps = sorted(apps, key=lambda a: getattr(a, "last_scanned", "") or getattr(a, "installed_at", "") or "", reverse=True)
                self._keep_map[fp] = sorted_apps[0]
                for a in sorted_apps[1:]:
                    if a.id is not None:
                        self._selected_app_ids.add(a.id)
        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        self._on_toast("Designated newest installs as originals and selected older copies.", "info")

    def _keep_oldest(self):
        self._selected_app_ids.clear()
        for g in self._groups:
            apps = _get_group_apps(g)
            if apps:
                fp = _get_group_fp(g)
                sorted_apps = sorted(apps, key=lambda a: getattr(a, "first_seen", "") or getattr(a, "installed_at", "") or "")
                self._keep_map[fp] = sorted_apps[0]
                for a in sorted_apps[1:]:
                    if a.id is not None:
                        self._selected_app_ids.add(a.id)
        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        self._on_toast("Designated oldest installs as originals and selected newer copies.", "info")

    def _select_all_visible(self):
        """Select all visible duplicate copies in search filter."""
        q = self._ent_search.get().lower().strip()
        for g in self._groups:
            apps = _get_group_apps(g)
            fp = _get_group_fp(g)
            keep_app = self._keep_map.get(fp)

            if q and not any(
                q in (a.name.lower() or "") or q in (a.install_path.lower() or "") or q in (a.category.lower() or "")
                for a in apps
            ):
                continue

            for a in apps:
                if not keep_app or a.id != keep_app.id:
                    if a.id is not None:
                        self._selected_app_ids.add(a.id)

        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        self._on_toast(f"Selected all {len(self._selected_app_ids)} candidate duplicate files.", "success")

    def _deselect_all(self):
        self._selected_app_ids.clear()
        self._populate_tree(self._ent_search.get())
        if self._selected_app:
            self._update_inspector_app(self._selected_app)
        self._on_toast("Cleared all selections.", "info")

    def _update_selection_summary(self):
        count = len(self._selected_app_ids)
        total_reclaim = sum(
            _get_app_size(a)
            for g in self._groups
            for a in _get_group_apps(g)
            if a.id in self._selected_app_ids
        )
        self._lbl_selection_summary.config(
            text=f"Selected: {count} files ({bytes_human(total_reclaim)})"
        )

    def _mark_as_keep(self):
        if not self._selected_app or self._selected_app.id is None:
            return
        grp = next((g for g in self._groups if any(a.id == self._selected_app.id for a in _get_group_apps(g))), None)
        if grp:
            fp = _get_group_fp(grp)
            self._keep_map[fp] = self._selected_app
            self._selected_app_ids.discard(self._selected_app.id)
            self._populate_tree(self._ent_search.get())
            self._update_inspector_app(self._selected_app)
            self._on_toast(f"Marked '{self._selected_app.name}' as the protected reference copy.", "success")

    def _open_in_explorer(self):
        if not self._selected_app:
            return
        path = self._selected_app.install_path
        if os.path.exists(path):
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
        else:
            self._on_toast("Directory path does not exist on disk.", "warning")

    def _quarantine_single_current(self):
        """Quarantine just the single selected file in the inspector."""
        if not self._selected_app:
            self._on_toast("Please select a file to quarantine.", "warning")
            return

        grp = next((g for g in self._groups if any(a.id == self._selected_app.id for a in _get_group_apps(g))), None)
        if grp:
            keep_app = self._keep_map.get(_get_group_fp(grp))
            if keep_app and keep_app.id == self._selected_app.id:
                self._on_toast("Cannot quarantine the protected original reference copy.", "warning")
                return

        confirm = messagebox.askyesno(
            "Confirm Single File Quarantine",
            f"Are you sure you want to isolate this copy?\n\nFile: {self._selected_app.name}\nPath: {self._selected_app.install_path}\n\nYou can restore it at any time from the Quarantine Vault.",
            icon="question",
        )
        if not confirm:
            return

        success = self._qm.quarantine_application(self._selected_app.install_path, app_name=self._selected_app.name)
        if success:
            self._selected_app_ids.discard(self._selected_app.id)
            self._on_toast(f"Successfully quarantined '{self._selected_app.name}'!", "success")
            self.refresh_from_db()
        else:
            self._on_toast("Failed to quarantine file (path might not exist).", "error")

    def _quarantine_selected(self):
        """Quarantine all checked / selected files."""
        if not self._selected_app_ids:
            self._on_toast("Please select at least 1 duplicate copy using the checkboxes or Auto-Select.", "warning")
            return

        apps_to_q = [
            a for g in self._groups for a in _get_group_apps(g) if a.id in self._selected_app_ids
        ]
        count = len(apps_to_q)

        confirm = messagebox.askyesno(
            "Confirm Safe Quarantine",
            f"Are you sure you want to move {count} selected files to the Safe Quarantine Vault?\n\nYou can restore them back to their exact original locations at any time with 1-click.",
            icon="question",
        )
        if not confirm:
            return

        quarantined = 0
        for a in apps_to_q:
            success = self._qm.quarantine_application(a.install_path, app_name=a.name)
            if success:
                quarantined += 1

        self._on_toast(f"Safely moved {quarantined} items to Quarantine Vault!", "success")
        self._selected_app_ids.clear()
        self.refresh_from_db()

    def _find_app_by_id(self, app_id: int) -> Optional[AppRecord]:
        for g in self._groups:
            for a in _get_group_apps(g):
                if a.id == app_id:
                    return a
        return None
