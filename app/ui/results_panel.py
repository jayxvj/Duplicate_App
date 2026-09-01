"""
Results panel — displays duplicate groups in a hierarchical Treeview.

Layout:
  Left: Treeview (groups → member apps)
  Right: Detail side-panel (selected app metadata + actions)

User actions available:
  - Mark as Keep (designates reference copy)
  - Remove (safe trash — only allowed if Keep is set and this is not it)
  - Remove All Duplicates (trash all non-Keep members)
  - Open folder in Explorer
"""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional

from app.data.models import AppRecord, DuplicateGroup
from app.data.repository import Repository
from app.manager.removal_manager import RemovalManager
from app.ui.theme import (
    ACCENT, BG_CARD, BG_DARK, BG_PANEL, BG_ROW_ALT, BORDER,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS, WARNING, DANGER, INFO,
    bytes_human,
)
from app.ui.widgets import (
    DangerButton, IconButton, PrimaryButton, SectionLabel,
)


class ResultsPanel(tk.Frame):
    """
    Shows all duplicate groups for the most recent (or selected) scan.
    """

    def __init__(self, parent, repo: Repository,
                 on_toast: Callable[[str, str], None],
                 **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._repo = repo
        self._removal = RemovalManager(repo)
        self._on_toast = on_toast
        self._groups: List[DuplicateGroup] = []
        self._selected_group: Optional[DuplicateGroup] = None
        self._selected_app: Optional[AppRecord] = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        # ── Header ──────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK, pady=16, padx=24)
        header.pack(fill="x")
        tk.Label(header, text="📋  Duplicate Groups",
                 font=(FONT_TITLE[0], 16, "bold"), fg=ACCENT, bg=BG_DARK).pack(anchor="w")

        self._summary_var = tk.StringVar(value="No scan results yet.")
        tk.Label(header, textvariable=self._summary_var,
                 font=FONT_NORMAL, fg=FG_SECONDARY, bg=BG_DARK).pack(anchor="w")

        # ── Toolbar ──────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=BG_DARK, padx=24)
        toolbar.pack(fill="x", pady=(0, 8))

        self._btn_mark_keep = PrimaryButton(
            toolbar, "✔  Mark as Keep",
            command=self._mark_as_keep,
        )
        self._btn_mark_keep.pack(side="left", padx=(0, 8))
        self._btn_mark_keep.config(state="disabled")

        self._btn_remove = DangerButton(
            toolbar, "🗑  Remove Selected",
            command=self._remove_selected,
        )
        self._btn_remove.pack(side="left", padx=(0, 8))
        self._btn_remove.config(state="disabled")

        self._btn_remove_all = DangerButton(
            toolbar, "🗑  Remove All Duplicates",
            command=self._remove_all_in_group,
        )
        self._btn_remove_all.pack(side="left", padx=(0, 8))
        self._btn_remove_all.config(state="disabled")

        self._btn_open = IconButton(
            toolbar, "📂  Open Folder",
            command=self._open_folder,
            bg=BG_PANEL,
        )
        self._btn_open.pack(side="left")
        self._btn_open.config(state="disabled")

        # ── Paned layout (tree | detail) ──────────────────────────────────
        paned = tk.PanedWindow(self, orient="horizontal", bg=BG_DARK,
                               sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Left: tree
        tree_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(tree_frame, minsize=380)

        cols = ("Name", "Path", "Size", "Version", "Status")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="tree headings",
            selectmode="browse",
        )
        self._tree.heading("#0", text="Group / App")
        for col in cols:
            self._tree.heading(col, text=col)
        self._tree.column("#0",     width=30,  stretch=False)
        self._tree.column("Name",   width=180)
        self._tree.column("Path",   width=240)
        self._tree.column("Size",   width=70,  anchor="e")
        self._tree.column("Version",width=70,  anchor="center")
        self._tree.column("Status", width=70,  anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.config(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._tree.tag_configure("group",    font=FONT_BOLD, foreground=ACCENT)
        self._tree.tag_configure("keep",     foreground=SUCCESS)
        self._tree.tag_configure("duplicate",foreground=FG_PRIMARY)
        self._tree.tag_configure("unset",    foreground=WARNING)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._open_folder())

        # Right: detail
        self._detail = DetailSidePanel(paned, bg=BG_DARK)
        paned.add(self._detail, minsize=280)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_groups(self, groups: List[DuplicateGroup]):
        self._groups = groups
        self._repopulate_tree()
        n = len(groups)
        total_members = sum(len(g.members) for g in groups)
        self._summary_var.set(
            f"{n} duplicate group{'s' if n != 1 else ''} · "
            f"{total_members} application instances"
        )

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _repopulate_tree(self):
        for row in self._tree.get_children():
            self._tree.delete(row)

        for g in self._groups:
            ref_id = g.reference_app_id
            grp_label = f"Group {g.id}  ·  {len(g.members)} copies  ·  {g.group_signature[:12]}…"
            grp_iid = f"group_{g.id}"
            self._tree.insert(
                "", "end", iid=grp_iid,
                text="▶", values=(grp_label, "", "", "", ""),
                tags=("group",), open=True,
            )
            for m in g.members:
                is_ref = m.id == ref_id
                no_ref_set = ref_id is None
                tag = "keep" if is_ref else ("unset" if no_ref_set else "duplicate")
                status = "✔ KEEP" if is_ref else ("— set keep" if no_ref_set else "COPY")
                path_disp = m.install_path
                self._tree.insert(
                    grp_iid, "end",
                    iid=f"app_{g.id}_{m.id}",
                    text="",
                    values=(
                        m.name,
                        path_disp,
                        bytes_human(m.disk_size_bytes),
                        m.version or "—",
                        status,
                    ),
                    tags=(tag,),
                )

    # ------------------------------------------------------------------
    # Selection handler
    # ------------------------------------------------------------------

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("group_"):
            self._selected_group = self._find_group(int(iid.split("_")[1]))
            self._selected_app = None
            self._update_buttons(app_selected=False)
            self._detail.clear()
        elif iid.startswith("app_"):
            _, gid, aid = iid.split("_")
            self._selected_group = self._find_group(int(gid))
            self._selected_app = self._find_member(int(aid))
            self._update_buttons(app_selected=True)
            if self._selected_app:
                self._detail.show(self._selected_app, self._selected_group)

    def _update_buttons(self, app_selected: bool):
        grp_sel = self._selected_group is not None
        self._btn_mark_keep.config(state="normal" if app_selected else "disabled")
        self._btn_remove.config(state="normal" if app_selected else "disabled")
        self._btn_remove_all.config(state="normal" if grp_sel else "disabled")
        self._btn_open.config(state="normal" if app_selected else "disabled")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _mark_as_keep(self):
        if not (self._selected_group and self._selected_app):
            return
        self._repo.set_reference_app(self._selected_group.id, self._selected_app.id)
        self._selected_group.reference_app_id = self._selected_app.id
        self._repopulate_tree()
        self._on_toast(f"'{self._selected_app.name}' marked as Keep.", "success")

    def _remove_selected(self):
        if not (self._selected_group and self._selected_app):
            return
        app = self._selected_app
        group = self._selected_group

        ok, reason = self._removal.can_remove(app, group)
        if not ok:
            messagebox.showwarning("Cannot Remove", reason)
            return

        confirmed = messagebox.askyesno(
            "Confirm Removal",
            f"Send to Recycle Bin:\n\n{app.install_path}\n\n"
            "You can recover it from the Recycle Bin if needed.",
            icon="warning",
        )
        if not confirmed:
            return

        success, msg = self._removal.remove_app(app, group)
        if success:
            self._on_toast(msg, "success")
            # Reload groups from DB
            self._reload_from_db(group.scan_id)
        else:
            messagebox.showerror("Removal Failed", msg)

    def _remove_all_in_group(self):
        if not self._selected_group:
            return
        group = self._selected_group
        if group.reference_app_id is None:
            messagebox.showwarning(
                "No Keep Selected",
                "Please mark one copy as 'Keep' before removing the others.",
            )
            return

        non_ref = [m for m in group.members if m.id != group.reference_app_id]
        if not non_ref:
            self._on_toast("Nothing to remove.", "info")
            return

        confirmed = messagebox.askyesno(
            "Confirm Bulk Removal",
            f"Send {len(non_ref)} duplicate(s) to the Recycle Bin?\n\n"
            + "\n".join(m.install_path for m in non_ref[:5])
            + ("\n…" if len(non_ref) > 5 else ""),
            icon="warning",
        )
        if not confirmed:
            return

        results = self._removal.remove_all_except_reference(group)
        successes = sum(1 for _, ok, _ in results if ok)
        self._on_toast(
            f"Removed {successes}/{len(results)} duplicate(s) to Recycle Bin.",
            "success" if successes == len(results) else "warning",
        )
        self._reload_from_db(group.scan_id)

    def _open_folder(self):
        if not self._selected_app:
            return
        path = self._selected_app.install_path
        if not os.path.exists(path):
            messagebox.showwarning("Not Found", f"Path no longer exists:\n{path}")
            return
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_group(self, gid: int) -> Optional[DuplicateGroup]:
        return next((g for g in self._groups if g.id == gid), None)

    def _find_member(self, aid: int) -> Optional[AppRecord]:
        for g in self._groups:
            for m in g.members:
                if m.id == aid:
                    return m
        return None

    def _reload_from_db(self, scan_id):
        if scan_id:
            groups = self._repo.get_duplicate_groups_for_scan(scan_id)
        else:
            groups = self._repo.get_all_duplicate_groups()
        self.load_groups(groups)


# ── Detail side panel ────────────────────────────────────────────────────────

class DetailSidePanel(tk.Frame):
    """Right-hand panel showing selected app metadata."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.config(bg=BG_DARK)
        self._build()

    def _build(self):
        self._canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.config(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG_DARK)
        self._win_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>", self._on_frame_config)
        self._canvas.bind("<Configure>", self._on_canvas_config)

    def _on_frame_config(self, _e=None):
        self._canvas.config(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_config(self, e):
        self._canvas.itemconfig(self._win_id, width=e.width)

    def clear(self):
        for w in self._inner.winfo_children():
            w.destroy()
        tk.Label(self._inner, text="Select an application to see details.",
                 font=FONT_SMALL, fg=FG_MUTED, bg=BG_DARK,
                 wraplength=240).pack(padx=16, pady=24)

    def show(self, app: AppRecord, group: Optional[DuplicateGroup]):
        for w in self._inner.winfo_children():
            w.destroy()

        pad = {"padx": 16, "pady": 4}

        tk.Label(self._inner, text=app.name, font=FONT_BOLD,
                 fg=ACCENT, bg=BG_DARK, wraplength=240).pack(anchor="w", **pad)

        def row(label, value, mono=False):
            f = tk.Frame(self._inner, bg=BG_DARK)
            f.pack(fill="x", **pad)
            tk.Label(f, text=label, font=FONT_SMALL, fg=FG_MUTED,
                     bg=BG_DARK, width=14, anchor="w").pack(side="left")
            tk.Label(f, text=str(value) or "—",
                     font=FONT_MONO if mono else FONT_SMALL,
                     fg=FG_PRIMARY, bg=BG_DARK, wraplength=180,
                     anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        row("Category:", app.category)
        row("Version:", app.version or "—")
        row("Publisher:", app.publisher or "—")
        row("Size:", bytes_human(app.disk_size_bytes))
        row("Install Path:", app.install_path)

        if group:
            is_ref = app.id == group.reference_app_id
            row("Status:", "✔ KEEP (user-designated)" if is_ref else "Duplicate copy")
            row("Signature:", (group.group_signature[:20] + "…") if group.group_signature else "—", mono=True)

        row("First Seen:", (app.first_seen or "—")[:19])
        row("Last Scanned:", (app.last_scanned or "—")[:19])
