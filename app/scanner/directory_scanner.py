"""Recursive directory scanner strictly targeting application candidates."""
import os
from pathlib import Path
from typing import Callable, List, Optional, Set

from app.core.types import Application, AppType, FileRecord, ScanProgress
from app.scanner.application_detector import CompositeApplicationDetector
from app.scanner.platform_detector import is_protected_path, get_current_platform


class DirectoryScanner:
    def __init__(
        self,
        exclusions: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ):
        self.exclusions = set(exclusions or [])
        self.progress_callback = progress_callback
        self.detector = CompositeApplicationDetector()
        self.current_platform = get_current_platform()
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def scan_directories(self, scan_paths: List[str | Path]) -> List[Application]:
        self._is_cancelled = False
        applications: List[Application] = []
        progress = ScanProgress(phase="discovering")

        valid_roots: List[Path] = []
        for p in scan_paths:
            path_obj = Path(p).resolve()
            if not path_obj.exists():
                continue
            if is_protected_path(path_obj):
                continue
            valid_roots.append(path_obj)

        for root in valid_roots:
            if self._is_cancelled:
                break
            self._discover_applications_recursive(root, applications, progress, is_scan_root=True)

        return applications

    def _discover_applications_recursive(
        self,
        current_path: Path,
        applications: List[Application],
        progress: ScanProgress,
        is_scan_root: bool = False,
    ) -> None:
        if self._is_cancelled:
            return

        if self._should_exclude(current_path) or is_protected_path(current_path):
            return

        # 1. If it's a standalone file, test if it is an executable/application binary
        if current_path.is_file():
            detection = self.detector.detect_application(current_path)
            if detection:
                app_type, app_name = detection
                app = self._build_standalone_file_app(current_path, app_type, app_name)
                if app:
                    applications.append(app)
                    progress.apps_found += 1
                    if self.progress_callback:
                        self.progress_callback(progress)
            return

        # 2. If it's a directory (and not the top-level user scan container), check if it constitutes a complete application root
        if not is_scan_root:
            detection = self.detector.detect_application(current_path)
            if detection:
                app_type, app_name = detection
                app = self._build_folder_app(current_path, app_type, app_name, progress)
                if app and app.file_count > 0:
                    applications.append(app)
                    progress.apps_found += 1
                    if self.progress_callback:
                        self.progress_callback(progress)
                # Once an application root is captured, its subfolders belong to this application
                return

        # 3. If current directory is not an application itself (e.g. C:\Apps or D:\Downloads or user scan root),
        # iterate its direct children to find application subfolders or standalone binaries

        try:
            entries = list(current_path.iterdir())
        except (PermissionError, OSError):
            progress.error_count += 1
            return

        for entry in entries:
            if self._is_cancelled:
                break
            self._discover_applications_recursive(entry, applications, progress)

    def _should_exclude(self, path: Path) -> bool:
        name = path.name.lower()
        path_str = str(path).lower()
        for excl in self.exclusions:
            excl_lower = excl.lower()
            if excl_lower == name or excl_lower in path_str:
                return True
        return False

    def _build_standalone_file_app(self, file_path: Path, app_type: AppType, name: str) -> Optional[Application]:
        try:
            stat = file_path.stat()
            file_rec = FileRecord(
                relative_path=file_path.name,
                absolute_path=str(file_path),
                size=stat.st_size,
                file_type=file_path.suffix.lower(),
                is_readable=True,
            )
            return Application(
                name=name,
                root_path=str(file_path),
                platform=self.current_platform,
                app_type=app_type,
                total_size=stat.st_size,
                file_count=1,
                files=[file_rec],
            )
        except (PermissionError, OSError):
            return None

    def _build_folder_app(
        self,
        folder_path: Path,
        app_type: AppType,
        app_name: str,
        progress: ScanProgress,
    ) -> Optional[Application]:
        files: List[FileRecord] = []
        total_size = 0

        for root_dir, dirnames, filenames in os.walk(folder_path, topdown=True, followlinks=False):
            if self._is_cancelled:
                break

            # Filter excluded subdirectories
            dirnames[:] = [
                d for d in dirnames
                if not self._should_exclude(Path(root_dir) / d) and not is_protected_path(Path(root_dir) / d)
            ]

            for filename in filenames:
                if self._is_cancelled:
                    break
                full_path = Path(root_dir) / filename
                if self._should_exclude(full_path):
                    continue

                try:
                    rel_p = str(full_path.relative_to(folder_path))
                    stat = full_path.stat()
                    file_size = stat.st_size
                    total_size += file_size
                    files.append(
                        FileRecord(
                            relative_path=rel_p,
                            absolute_path=str(full_path),
                            size=file_size,
                            file_type=full_path.suffix.lower(),
                            is_readable=True,
                        )
                    )
                except (PermissionError, OSError):
                    progress.error_count += 1
                    try:
                        rel_p = str(full_path.relative_to(folder_path))
                    except Exception:
                        rel_p = filename
                    files.append(
                        FileRecord(
                            relative_path=rel_p,
                            absolute_path=str(full_path),
                            size=0,
                            file_type=full_path.suffix.lower(),
                            is_readable=False,
                        )
                    )

                progress.files_scanned += 1
                progress.current_path = str(full_path)
                if progress.files_scanned % 50 == 0 and self.progress_callback:
                    self.progress_callback(progress)

        return Application(
            name=app_name,
            root_path=str(folder_path),
            platform=self.current_platform,
            app_type=app_type,
            total_size=total_size,
            file_count=len(files),
            files=files,
        )
