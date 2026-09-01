"""
Application-level content signature builder.

The SignatureBuilder creates a deterministic SHA-256 signature
representing an application's content.

Duplicate identity does NOT depend on:

    - installation path
    - folder name
    - filename
    - timestamps

It DOES depend on the cryptographic hashes of the application's
core executable content.

Supported application forms:

    1. Standalone executable

        Chrome.exe

    2. Application directory

        Chrome/
            chrome.exe
            chrome.dll
            resources/
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import cfg
from app.core.volatile_filter import VolatileFilter
from app.data.models import FileRecord

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

_ALWAYS_SKIP_DIRS = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "program data",
}

_MAX_FILE_SIZE = 536_870_912  # 512 MB


# ============================================================================
# SIGNATURE BUILDER
# ============================================================================

class SignatureBuilder:
    """
    Builds a deterministic content signature for one application.
    """

    def __init__(
        self,
        app_id: int,
        install_path: str,
    ):

        self.app_id = app_id

        self.install_path = Path(
            install_path
        )

        self._volatile_filter = VolatileFilter()

        self._core_exts = {
            ext.lower()
            for ext in cfg.core_extensions
        }

        self._manifest_names = {
            name.lower()
            for name in cfg.manifest_filenames
        }

    # ========================================================================
    # FILE COLLECTION
    # ========================================================================

    def collect_files(
        self,
        progress_cb=None,
        cancelled_cb=None,
    ) -> Tuple[List[FileRecord], int]:

        """
        Collect files belonging to the application.

        Supports both:

            Application.exe

        and:

            Application/
                Application.exe
                Application.dll
                ...
        """

        records: List[FileRecord] = []

        total_bytes = 0

        root = self.install_path

        # ====================================================================
        # CASE 1: STANDALONE APPLICATION FILE
        # ====================================================================

        if root.is_file():

            try:

                stat = root.stat()

                if stat.st_size > _MAX_FILE_SIZE:

                    logger.warning(
                        "Skipping oversized application file: %s",
                        root,
                    )

                    return records, 0

                filename = root.name

                ext = root.suffix.lower()

                is_core = (
                    ext in self._core_exts
                    or self._matches_manifest(filename)
                )

                # A standalone .exe is always considered core.
                if ext == ".exe":
                    is_core = True

                records.append(
                    FileRecord(
                        app_id=self.app_id,
                        relative_path=filename,
                        absolute_path=str(root),
                        file_size=stat.st_size,
                        is_volatile=False,
                        is_core=is_core,
                    )
                )

                total_bytes = stat.st_size

                if progress_cb:
                    progress_cb(1)

            except OSError as exc:

                logger.warning(
                    "Unable to read application file %s: %s",
                    root,
                    exc,
                )

            return records, total_bytes

        # ====================================================================
        # CASE 2: APPLICATION DIRECTORY
        # ====================================================================

        if not root.is_dir():

            logger.warning(
                "Install path does not exist: %s",
                root,
            )

            return records, 0

        # ====================================================================
        # WALK DIRECTORY
        # ====================================================================

        try:

            for dirpath, dirnames, filenames in os.walk(
                root,
                topdown=True,
            ):

                if cancelled_cb and cancelled_cb():
                    break

                # ------------------------------------------------------------
                # Remove directories that should never be scanned.
                # ------------------------------------------------------------

                dirnames[:] = [
                    d
                    for d in dirnames
                    if not self._skip_dir(
                        dirpath,
                        d,
                        root,
                    )
                ]

                # ------------------------------------------------------------
                # Process files.
                # ------------------------------------------------------------

                for fname in filenames:

                    abs_path = os.path.join(
                        dirpath,
                        fname,
                    )

                    try:

                        stat = os.stat(
                            abs_path
                        )

                    except OSError:
                        continue

                    # Skip extremely large files.
                    if stat.st_size > _MAX_FILE_SIZE:
                        continue

                    try:

                        rel_path = os.path.relpath(
                            abs_path,
                            root,
                        )

                    except ValueError:

                        continue

                    # Determine whether file is volatile.
                    is_volatile = (
                        self._volatile_filter.is_volatile(
                            rel_path
                        )
                    )

                    # Determine whether file is core.
                    is_core = (
                        not is_volatile
                        and self._is_core_file(fname)
                    )

                    records.append(
                        FileRecord(
                            app_id=self.app_id,
                            relative_path=rel_path,
                            absolute_path=abs_path,
                            file_size=stat.st_size,
                            is_volatile=is_volatile,
                            is_core=is_core,
                        )
                    )

                    total_bytes += stat.st_size

                    if progress_cb:
                        progress_cb(
                            len(records)
                        )

        except PermissionError as exc:

            logger.warning(
                "Permission denied walking %s: %s",
                root,
                exc,
            )

        return records, total_bytes

    # ========================================================================
    # APPLICATION SIGNATURE
    # ========================================================================

    def compute_signature(
        self,
        file_records: List[FileRecord],
        file_hashes: Dict[int, str],
    ) -> Optional[str]:

        """
        Create the application's content signature.

        Only core file content hashes are used.

        Installation path and filenames are NOT part of the identity.

        Example:

            Chrome.exe
                SHA256 = ABC

            Chrome Copy.exe
                SHA256 = ABC

        Both produce the same application signature.
        """

        core_hashes: List[Tuple[str, str]] = []

        # --------------------------------------------------------------------
        # Collect hashes of core application files.
        # --------------------------------------------------------------------

        for fr in file_records:

            if not fr.is_core:
                continue

            file_hash = file_hashes.get(
                fr.id
            )

            if not file_hash:
                continue

            # Use file extension only as a type identifier.
            #
            # The filename and installation path are deliberately ignored.
            extension = Path(
                fr.relative_path
            ).suffix.lower()

            core_hashes.append(
                (
                    extension,
                    file_hash.lower(),
                )
            )

        # --------------------------------------------------------------------
        # No core files means we cannot safely identify the application.
        # --------------------------------------------------------------------

        if not core_hashes:

            logger.warning(
                "No hashable core files for app_id=%d at %s",
                self.app_id,
                self.install_path,
            )

            return None

        # --------------------------------------------------------------------
        # Sort deterministically.
        # --------------------------------------------------------------------

        core_hashes.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        # --------------------------------------------------------------------
        # Build content-only representation.
        # --------------------------------------------------------------------

        composite = "\n".join(
            f"{file_type}:{file_hash}"
            for file_type, file_hash
            in core_hashes
        )

        # --------------------------------------------------------------------
        # Final application SHA-256.
        # --------------------------------------------------------------------

        signature = hashlib.sha256(
            composite.encode("utf-8")
        ).hexdigest()

        logger.debug(
            "Signature for app_id=%d: %s "
            "(from %d core files)",
            self.app_id,
            signature[:16] + "...",
            len(core_hashes),
        )

        return signature

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _skip_dir(
        self,
        dirpath: str,
        dirname: str,
        root: Path,
    ) -> bool:

        """
        Return True if a directory should be completely skipped.
        """

        lower = dirname.lower()

        # Always skip known system directories.
        if lower in _ALWAYS_SKIP_DIRS:
            return True

        # Check volatile directory rules.
        try:

            rel = os.path.relpath(
                os.path.join(
                    dirpath,
                    dirname,
                ),
                root,
            )

        except ValueError:

            return True

        return self._volatile_filter.is_volatile(
            rel + "/placeholder"
        )

    # ========================================================================

    def _is_core_file(
        self,
        filename: str,
    ) -> bool:

        """
        Determine whether a file is part of the application's core.
        """

        lower = filename.lower()

        extension = os.path.splitext(
            lower
        )[1]

        # Core executable/library extensions.
        if extension in self._core_exts:
            return True

        # Manifest files.
        return self._matches_manifest(
            filename
        )

    # ========================================================================

    def _matches_manifest(
        self,
        filename: str,
    ) -> bool:

        """
        Check whether a filename matches a configured manifest pattern.
        """

        import fnmatch

        lower = filename.lower()

        for pattern in self._manifest_names:

            if fnmatch.fnmatch(
                lower,
                pattern,
            ):
                return True

        return False