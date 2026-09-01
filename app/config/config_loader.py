"""
Config loader — reads and validates the three JSON config files.
Provides a single ConfigLoader singleton that the rest of the app imports.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Resolve the project root regardless of where the script is launched from.
_HERE = Path(__file__).resolve().parent.parent.parent   # project root
_CONFIG_DIR = _HERE / "config"


def _load_json(filename: str) -> Dict[str, Any]:
    path = _CONFIG_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.warning("Config file not found: %s — using defaults", path)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("Bad JSON in %s: %s", path, exc)
        return {}


class ConfigLoader:
    """Lazy-loads and caches all JSON config files."""

    _instance: "ConfigLoader | None" = None

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _ensure_loaded(self):
        if not self._loaded:
            self.reload()

    def reload(self):
        self._settings = _load_json("settings.json")
        self._categories = _load_json("categories.json")
        self._volatile = _load_json("volatile_patterns.json")
        self._loaded = True
        logger.info("Configuration loaded from %s", _CONFIG_DIR)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    @property
    def settings(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._settings

    def get(self, *keys, default=None):
        """Deep-get from settings. get('scan', 'max_workers', default=4)"""
        self._ensure_loaded()
        node = self._settings
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    # ------------------------------------------------------------------
    # Category rules
    # ------------------------------------------------------------------

    @property
    def category_rules(self) -> list:
        self._ensure_loaded()
        return self._categories.get("rules", [])

    # ------------------------------------------------------------------
    # Volatile file patterns
    # ------------------------------------------------------------------

    @property
    def volatile_patterns(self) -> list:
        self._ensure_loaded()
        return self._volatile.get("exclude_patterns", [])

    @property
    def volatile_dirs(self) -> list:
        self._ensure_loaded()
        return [d.lower() for d in self._volatile.get("exclude_dirs", [])]

    # ------------------------------------------------------------------
    # Core-file extensions / manifests
    # ------------------------------------------------------------------

    @property
    def core_extensions(self) -> list:
        self._ensure_loaded()
        return self.get("scan", "core_extensions", default=[
            ".exe", ".dll", ".so", ".dylib", ".jar"
        ])

    @property
    def manifest_filenames(self) -> list:
        self._ensure_loaded()
        return self.get("scan", "manifest_filenames", default=[
            "package.json", "setup.py", "setup.cfg"
        ])

    # ------------------------------------------------------------------
    # Derived paths (resolved to absolute)
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> Path:
        rel = self.get("database", "path", default="data/duplicates.db")
        return _HERE / rel

    @property
    def log_path(self) -> Path:
        rel = self.get("logging", "path", default="logs/app.log")
        return _HERE / rel

    @property
    def reports_dir(self) -> Path:
        rel = self.get("reports", "output_dir", default="reports")
        return _HERE / rel

    @property
    def system_exclusions(self) -> list:
        return self.get("scan", "system_exclusions", default=[])

    @property
    def max_workers(self) -> int:
        return int(self.get("scan", "max_workers", default=8))

    @property
    def chunk_size(self) -> int:
        return int(self.get("scan", "chunk_size", default=65536))

    @property
    def ui_theme(self) -> str:
        return self.get("ui", "theme", default="darkly")

    @property
    def window_size(self) -> tuple:
        w = self.get("ui", "window_width", default=1280)
        h = self.get("ui", "window_height", default=800)
        return (w, h)


# Module-level singleton
cfg = ConfigLoader()
