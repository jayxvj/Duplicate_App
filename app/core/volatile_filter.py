"""
Volatile file filter — determines whether a given file path should be
excluded from the application content signature.

Volatile files: logs, caches, temp files, user data, crash dumps, etc.
These change frequently and must not influence duplicate detection.
"""
from __future__ import annotations

import fnmatch
import logging
import os
from pathlib import Path
from typing import List

from app.config import cfg

logger = logging.getLogger(__name__)


class VolatileFilter:
    """
    Tests a file path (relative to the app root) against the configured
    volatile patterns and directory names.
    """

    def __init__(self):
        self._patterns: List[str] = cfg.volatile_patterns
        self._volatile_dirs: List[str] = cfg.volatile_dirs

    def reload(self):
        """Re-read patterns from config (called after settings change)."""
        cfg.reload()
        self._patterns = cfg.volatile_patterns
        self._volatile_dirs = cfg.volatile_dirs

    def is_volatile(self, relative_path: str) -> bool:
        """
        Return True if *relative_path* (relative to app install root,
        using forward slashes) matches any volatile pattern or sits
        inside a volatile directory.

        Examples:
            is_volatile("logs/app.log")  → True
            is_volatile("app.exe")        → False
        """
        # Normalise to forward-slash, lowercase for matching
        norm = relative_path.replace("\\", "/").strip("/")
        parts = norm.split("/")

        # 1. Check if any path segment matches a volatile directory name
        for part in parts[:-1]:  # all dirs, not the filename itself
            if part.lower() in self._volatile_dirs:
                return True

        # 2. Check filename against glob patterns
        filename = parts[-1]
        for pattern in self._patterns:
            if pattern.endswith("/**"):
                # Directory-prefix pattern like "logs/**"
                prefix = pattern[:-3].lower()
                if parts[0].lower() == prefix or (len(parts) > 1 and "/".join(parts[:-1]).lower().startswith(prefix)):
                    return True
            elif "/" in pattern:
                # Path-relative pattern
                if fnmatch.fnmatch(norm, pattern):
                    return True
            else:
                # Filename-only pattern
                if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                    return True

        return False

    def is_volatile_abs(self, abs_path: str, install_root: str) -> bool:
        """Convenience: compute relative path from absolute paths first."""
        try:
            rel = os.path.relpath(abs_path, install_root)
        except ValueError:
            # Different drive on Windows
            rel = abs_path
        return self.is_volatile(rel)
