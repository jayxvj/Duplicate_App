"""
Settings panel — view and edit configuration without touching JSON files manually.
Changes are written back to the JSON files and the config singleton is reloaded.
"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Dict

from app.config import cfg
from app.ui.theme import (
    ACCENT, BG_CARD, BG_DARK, BG_PANEL, BORDER,
    FG_MUTED, FG_PRIMARY, FG_SECONDARY,
    FONT_BOLD, FONT_MONO, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
    SUCCESS,
)
from app.ui.widgets import IconButton, PrimaryButton, SectionLabel

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class SettingsPanel(tk.Frame):
    def __init__(self, parent, on_toast, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._on_toast = on_toast
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=BG_DARK, pady=16, padx=24)
        header.pack(fill="x")
        tk.Label(header, text="⚙  Settings",
                 font=(FONT_TITLE[0], 16, "bold"), fg=ACCENT, bg=BG_DARK).pack(anchor="w")
        tk.Label(header, text="Edit configuration. Changes are saved to config/*.json.",
                 font=FONT_NORMAL, fg=FG_SECONDARY, bg=BG_DARK).pack(anchor="w")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Tab 1: settings.json
        self._settings_tab = self._build_json_tab(nb, "settings.json")
        nb.add(self._settings_tab, text="  settings.json  ")

        # Tab 2: volatile_patterns.json
        self._volatile_tab = self._build_json_tab(nb, "volatile_patterns.json")
        nb.add(self._volatile_tab, text="  volatile_patterns.json  ")

        # Tab 3: categories.json
        self._categories_tab = self._build_json_tab(nb, "categories.json")
        nb.add(self._categories_tab, text="  categories.json  ")

    def _build_json_tab(self, parent, filename: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG_DARK)

        path = _CONFIG_DIR / filename
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            content = "{}"

        editor = tk.Text(frame, font=FONT_MONO, fg="#a0ffc0", bg="#050510",
                         insertbackground=ACCENT, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER)
        editor.pack(fill="both", expand=True, padx=12, pady=12)
        editor.insert("1.0", content)

        def _save():
            text = editor.get("1.0", "end-1c")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                messagebox.showerror("Invalid JSON", str(exc))
                return
            path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False),
                            encoding="utf-8")
            cfg.reload()
            self._on_toast(f"Saved {filename}", "success")

        def _reload():
            try:
                content = path.read_text(encoding="utf-8")
                editor.delete("1.0", "end")
                editor.insert("1.0", content)
            except Exception as exc:
                messagebox.showerror("Error", str(exc))

        btn_row = tk.Frame(frame, bg=BG_DARK)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        PrimaryButton(btn_row, "💾  Save", command=_save).pack(side="left", padx=(0, 8))
        IconButton(btn_row, "↺  Reload from disk", command=_reload,
                   bg=BG_PANEL).pack(side="left")
        tk.Label(btn_row, text=str(path), font=FONT_SMALL,
                 fg=FG_MUTED, bg=BG_DARK).pack(side="right")

        return frame
