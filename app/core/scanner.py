"""
Application scanner.

Discovers application candidates for the duplicate application detector.

Important:
    This scanner is ONLY responsible for discovering applications.

    It does NOT decide whether applications are duplicates.
    Duplicate detection is performed later using content hashes.

Supported:
    - Standalone .exe applications
    - Folders containing .exe application files

Ignored:
    - .txt
    - .pdf
    - .jpg
    - .png
    - .docx
    - ordinary folders without executables
"""

from __future__ import annotations

import fnmatch
import logging
import os
import sys
from typing import Callable, Generator, List, Optional

from app.config import cfg
from app.data.models import AppRecord

logger = logging.getLogger(__name__)


# ============================================================================
# WINDOWS REGISTRY
# ============================================================================

if sys.platform == "win32":
    import winreg


_REG_UNINSTALL_PATHS = [
    (
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
    (
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
    (
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
] if sys.platform == "win32" else []


# ============================================================================
# CATEGORY
# ============================================================================

def _categorise(name: str) -> str:
    """
    Categorise application according to configured rules.
    """

    lower = name.lower()

    for rule in cfg.category_rules:

        for pattern in rule.get("patterns", []):

            if fnmatch.fnmatch(
                lower,
                pattern.lower(),
            ):
                return rule.get(
                    "category",
                    "Other",
                )

    return "Other"


# ============================================================================
# REGISTRY APPLICATION DISCOVERY
# ============================================================================

def _iter_registry_apps() -> Generator[AppRecord, None, None]:

    """
    Discover installed applications from Windows registry.
    """

    if sys.platform != "win32":
        return

    for hive, subkey_path in _REG_UNINSTALL_PATHS:

        try:

            with winreg.OpenKey(
                hive,
                subkey_path,
            ) as root_key:

                count = winreg.QueryInfoKey(
                    root_key
                )[0]

                for i in range(count):

                    try:

                        subkey_name = winreg.EnumKey(
                            root_key,
                            i,
                        )

                        with winreg.OpenKey(
                            root_key,
                            subkey_name,
                        ) as sub:

                            def _val(
                                name,
                                default="",
                            ):

                                try:

                                    return str(
                                        winreg.QueryValueEx(
                                            sub,
                                            name,
                                        )[0]
                                    )

                                except (
                                    FileNotFoundError,
                                    OSError,
                                ):

                                    return default

                            name = _val(
                                "DisplayName"
                            )

                            install_loc = _val(
                                "InstallLocation"
                            )

                            version = _val(
                                "DisplayVersion"
                            )

                            publisher = _val(
                                "Publisher"
                            )

                            if not name:
                                continue

                            if not install_loc:
                                continue

                            install_loc = (
                                install_loc
                                .strip()
                                .rstrip("\\")
                            )

                            if not os.path.isdir(
                                install_loc
                            ):
                                continue

                            yield AppRecord(
                                name=name,
                                install_path=install_loc,
                                version=version,
                                publisher=publisher,
                                category=_categorise(
                                    name
                                ),
                            )

                    except OSError:
                        continue

        except OSError:
            continue


# ============================================================================
# CHECK IF DIRECTORY CONTAINS EXECUTABLE
# ============================================================================

def _has_executable(
    directory: str,
) -> bool:

    """
    Return True if any .exe exists anywhere inside directory.

    This intentionally searches recursively.
    """

    if not os.path.isdir(directory):
        return False

    try:

        for dirpath, dirnames, filenames in os.walk(
            directory,
            topdown=True,
        ):

            # Prevent scanning known unnecessary directories.
            dirnames[:] = [
                d
                for d in dirnames
                if d.lower()
                not in {
                    "cache",
                    "caches",
                    "temp",
                    "tmp",
                    "logs",
                    "__pycache__",
                    ".git",
                    "node_modules",
                }
            ]

            for filename in filenames:

                if filename.lower().endswith(
                    ".exe"
                ):
                    return True

    except (
        PermissionError,
        OSError,
    ):
        return False

    return False


# ============================================================================
# DIRECTORY SCANNER
# ============================================================================

def _iter_dir_apps(
    root: str,
    max_depth: int = 6,
) -> Generator[AppRecord, None, None]:

    """
    Search a directory for applications.

    Two possibilities are detected:

    1. Standalone executable

        Documents/
            Chrome.exe

    2. Application directory

        Documents/
            Chrome/
                chrome.exe
                chrome.dll

    The scanner recursively searches the selected directory.
    """

    root = os.path.realpath(
        root
    )

    if not os.path.isdir(root):
        return

    logger.info(
        "Starting application discovery in: %s",
        root,
    )

    # Keep track of directories already identified as applications.
    discovered_dirs = set()

    # Keep track of standalone executables.
    discovered_files = set()

    try:

        for dirpath, dirnames, filenames in os.walk(
            root,
            topdown=True,
        ):

            # --------------------------------------------------------------
            # Calculate search depth.
            # --------------------------------------------------------------

            try:

                relative = os.path.relpath(
                    dirpath,
                    root,
                )

                if relative == ".":
                    depth = 0
                else:
                    depth = relative.count(
                        os.sep
                    ) + 1

            except (
                ValueError,
                OSError,
            ):

                continue

            # Stop going too deep.
            if depth > max_depth:

                dirnames[:] = []

                continue

            # --------------------------------------------------------------
            # Skip unnecessary directories.
            # --------------------------------------------------------------

            dirnames[:] = [
                d
                for d in dirnames
                if d.lower()
                not in {
                    "$recycle.bin",
                    "system volume information",
                    "cache",
                    "caches",
                    "temp",
                    "tmp",
                    "logs",
                    "__pycache__",
                    ".git",
                    "node_modules",
                }
            ]

            # --------------------------------------------------------------
            # Check files.
            # --------------------------------------------------------------

            for filename in filenames:

                if not filename.lower().endswith(
                    ".exe"
                ):
                    continue

                full_path = os.path.realpath(
                    os.path.join(
                        dirpath,
                        filename,
                    )
                )

                normalized = os.path.normcase(
                    full_path
                )

                # Ignore Windows system executables.
                if any(
                    system_path in normalized
                    for system_path in (
                        "\\windows\\",
                        "\\system32\\",
                        "\\syswow64\\",
                    )
                ):
                    continue

                # ==========================================================
                # STANDALONE EXE
                # ==========================================================

                if os.path.normcase(
                    dirpath
                ) == os.path.normcase(
                    root
                ):

                    if normalized in discovered_files:
                        continue

                    discovered_files.add(
                        normalized
                    )

                    name = os.path.splitext(
                        filename
                    )[0]

                    logger.info(
                        "Application executable found: %s",
                        full_path,
                    )

                    yield AppRecord(
                        name=name,
                        install_path=full_path,
                        version="",
                        publisher="",
                        category=_categorise(
                            name
                        ),
                    )

                    continue

                # ==========================================================
                # APPLICATION DIRECTORY
                # ==========================================================

                application_dir = os.path.realpath(
                    dirpath
                )

                normalized_dir = os.path.normcase(
                    application_dir
                )

                if normalized_dir in discovered_dirs:
                    continue

                discovered_dirs.add(
                    normalized_dir
                )

                name = os.path.basename(
                    application_dir
                )

                logger.info(
                    "Application directory found: %s",
                    application_dir,
                )

                yield AppRecord(
                    name=name,
                    install_path=application_dir,
                    version="",
                    publisher="",
                    category=_categorise(
                        name
                    ),
                )

    except (
        PermissionError,
        OSError,
    ) as exc:

        logger.warning(
            "Error scanning %s: %s",
            root,
            exc,
        )


# ============================================================================
# SCANNER
# ============================================================================

class Scanner:
    """
    Main application discovery service.
    """

    # ========================================================================
    # FULL SYSTEM SCAN
    # ========================================================================

    def scan_full(
        self,
        progress_cb: Optional[
            Callable[[str], None]
        ] = None,
        cancelled_cb: Optional[
            Callable[[], bool]
        ] = None,
    ) -> List[AppRecord]:

        """
        Scan common application and user locations.
        """

        results: List[AppRecord] = []

        seen_paths: set[str] = set()

        def _add(
            app: AppRecord,
        ):

            normalized = os.path.normcase(
                os.path.realpath(
                    app.install_path
                )
            )

            if normalized in seen_paths:
                return

            seen_paths.add(
                normalized
            )

            results.append(
                app
            )

            if progress_cb:

                progress_cb(
                    f"Found: {app.name}"
                )

        # --------------------------------------------------------------------
        # Registry
        # --------------------------------------------------------------------

        if sys.platform == "win32":

            for app in _iter_registry_apps():

                if (
                    cancelled_cb
                    and cancelled_cb()
                ):
                    return results

                _add(app)

        # --------------------------------------------------------------------
        # Program Files
        # --------------------------------------------------------------------

        roots = [

            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files",
            ),

            os.environ.get(
                "ProgramFiles(x86)",
                r"C:\Program Files (x86)",
            ),

            os.path.join(
                os.environ.get(
                    "LOCALAPPDATA",
                    "",
                ),
                "Programs",
            ),

            os.path.join(
                os.environ.get(
                    "APPDATA",
                    "",
                ),
                "Programs",
            ),
        ]

        # --------------------------------------------------------------------
        # User folders
        # --------------------------------------------------------------------

        user_profile = os.environ.get(
            "USERPROFILE",
            "",
        )

        roots.extend([

            os.path.join(
                user_profile,
                "Desktop",
            ),

            os.path.join(
                user_profile,
                "Documents",
            ),

            os.path.join(
                user_profile,
                "Downloads",
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Desktop",
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Documents",
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Downloads",
            ),

        ])

        # --------------------------------------------------------------------
        # Scan roots
        # --------------------------------------------------------------------

        for root in roots:

            if not root:
                continue

            if not os.path.isdir(root):
                continue

            logger.info(
                "Scanning root: %s",
                root,
            )

            for app in _iter_dir_apps(
                root,
                max_depth=6,
            ):

                if (
                    cancelled_cb
                    and cancelled_cb()
                ):
                    return results

                _add(app)

        logger.info(
            "Full scan found %d application candidates",
            len(results),
        )

        return results

    # ========================================================================
    # SELECTED DIRECTORY SCAN
    # ========================================================================

    def scan_directory(
        self,
        directory: str,
        progress_cb: Optional[
            Callable[[str], None]
        ] = None,
        cancelled_cb: Optional[
            Callable[[], bool]
        ] = None,
    ) -> List[AppRecord]:

        """
        Scan a user-selected directory.

        Example:

            Documents/
                Chrome/
                    chrome.exe

                Chrome Copy/
                    chrome.exe

                notes.txt

        Result:

            Chrome/
            Chrome Copy/

        notes.txt is ignored.
        """

        directory = os.path.realpath(
            directory
        )

        results: List[AppRecord] = []

        seen_paths: set[str] = set()

        def _add(
            app: AppRecord,
        ):

            normalized = os.path.normcase(
                os.path.realpath(
                    app.install_path
                )
            )

            if normalized in seen_paths:
                return

            seen_paths.add(
                normalized
            )

            results.append(
                app
            )

            logger.info(
                "Candidate added: %s -> %s",
                app.name,
                app.install_path,
            )

            if progress_cb:

                progress_cb(
                    f"Found: {app.name}"
                )

        # --------------------------------------------------------------------
        # User accidentally selected an EXE.
        # --------------------------------------------------------------------

        if os.path.isfile(
            directory
        ):

            if directory.lower().endswith(
                ".exe"
            ):

                name = os.path.splitext(
                    os.path.basename(
                        directory
                    )
                )[0]

                _add(
                    AppRecord(
                        name=name,
                        install_path=directory,
                        version="",
                        publisher="",
                        category=_categorise(
                            name
                        ),
                    )
                )

            logger.info(
                "File scan of '%s' found %d application candidates",
                directory,
                len(results),
            )

            return results

        # --------------------------------------------------------------------
        # Validate directory.
        # --------------------------------------------------------------------

        if not os.path.isdir(
            directory
        ):

            logger.warning(
                "Directory does not exist: %s",
                directory,
            )

            return results

        # --------------------------------------------------------------------
        # Scan selected directory.
        # --------------------------------------------------------------------

        logger.info(
            "Scanning selected directory: %s",
            directory,
        )

        for app in _iter_dir_apps(
            directory,
            max_depth=10,
        ):

            if (
                cancelled_cb
                and cancelled_cb()
            ):
                return results

            _add(app)

        logger.info(
            "Directory scan of '%s' found %d candidates",
            directory,
            len(results),
        )

        return results