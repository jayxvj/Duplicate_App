"""Extensible application boundary and candidate detectors strictly identifying applications."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.types import AppType

# Known application file extensions
EXECUTABLE_EXTS = {".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".appimage", ".bin", ".run", ".ink"}
PACKAGE_EXTS = {".jar", ".war", ".ear", ".apk", ".deb", ".rpm", ".dmg", ".pkg", ".appx", ".msix"}
SCRIPT_APP_EXTS = {".py", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".vbs", ".js"}


class BaseApplicationDetector(ABC):
    @abstractmethod
    def detect(self, dir_path: Path) -> Optional[Tuple[AppType, str]]:
        """
        Determines if the directory constitutes an application root.
        Returns (AppType, detected_name) or None if not an application.
        """
        pass


class PythonApplicationDetector(BaseApplicationDetector):
    def detect(self, dir_path: Path) -> Optional[Tuple[AppType, str]]:
        try:
            # Virtual environment (pyvenv.cfg or Scripts/python.exe or bin/python)
            if (dir_path / "pyvenv.cfg").exists() or (dir_path / "Scripts" / "python.exe").exists() or (dir_path / "bin" / "python").exists():
                return AppType.PYTHON_ENV, dir_path.name
            # Packaged Python project with manifest
            for manifest in ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile", "environment.yml"]:
                if (dir_path / manifest).exists():
                    return AppType.PYTHON_ENV, dir_path.name
            # Standard Python application entry point in root directory
            for entry_file in ["main.py", "__main__.py", "app.py", "run.py"]:
                if (dir_path / entry_file).exists():
                    return AppType.PYTHON_ENV, dir_path.name
        except (PermissionError, OSError):
            pass
        return None


class JavaApplicationDetector(BaseApplicationDetector):
    def detect(self, dir_path: Path) -> Optional[Tuple[AppType, str]]:
        try:
            jar_files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in PACKAGE_EXTS]
            if jar_files:
                return AppType.JAVA_JAR, jar_files[0].stem
            # Check target, build, lib, or dist subfolders
            for sub in ["target", "build", "lib", "dist"]:
                sub_dir = dir_path / sub
                if sub_dir.is_dir():
                    jars = [f for f in sub_dir.iterdir() if f.is_file() and f.suffix.lower() in PACKAGE_EXTS]
                    if jars:
                        return AppType.JAVA_JAR, dir_path.name
            # Java project build manifests
            if (dir_path / "pom.xml").exists() or (dir_path / "build.gradle").exists():
                return AppType.JAVA_JAR, dir_path.name
        except (PermissionError, OSError):
            pass
        return None


class WindowsApplicationDetector(BaseApplicationDetector):
    def detect(self, dir_path: Path) -> Optional[Tuple[AppType, str]]:
        try:
            # Check bin, App, app, Core, Release, Debug subfolders for executables
            for sub in ["bin", "App", "app", "Core", "Release", "Debug"]:
                sub_dir = dir_path / sub
                if sub_dir.is_dir():
                    sub_exes = [f for f in sub_dir.iterdir() if f.is_file() and f.suffix.lower() in EXECUTABLE_EXTS]
                    if sub_exes:
                        return AppType.WINDOWS_PORTABLE, dir_path.name

            # Look for executables in root of folder
            exe_files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in EXECUTABLE_EXTS]
            if exe_files:
                # If an executable explicitly matches the folder name and there are supporting files/subdirs
                matching_exe = next((e for e in exe_files if e.stem.lower() == dir_path.name.lower()), None)
                if matching_exe:
                    return AppType.WINDOWS_PORTABLE, matching_exe.stem

                # Or if there are subdirectories (e.g. lib, assets, data) supporting a single main exe
                subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
                if len(exe_files) == 1 and subdirs:
                    return AppType.WINDOWS_PORTABLE, exe_files[0].stem
        except (PermissionError, OSError):
            pass
        return None


class GenericApplicationDetector(BaseApplicationDetector):
    def detect(self, dir_path: Path) -> Optional[Tuple[AppType, str]]:
        # Only treat as a generic application bundle if it has standard bundle subdirectories (bin, lib, share)
        try:
            for sub in ["bin", "lib", "share"]:
                sub_dir = dir_path / sub
                if sub_dir.is_dir():
                    for item in sub_dir.iterdir():
                        if item.is_file() and item.suffix.lower() in (EXECUTABLE_EXTS | PACKAGE_EXTS | {".dll", ".so", ".dylib"}):
                            return AppType.GENERIC_FOLDER, dir_path.name
        except (PermissionError, OSError):
            pass
        return None



class CompositeApplicationDetector:
    def __init__(self, detectors: Optional[List[BaseApplicationDetector]] = None):
        self.detectors = detectors or [
            PythonApplicationDetector(),
            JavaApplicationDetector(),
            WindowsApplicationDetector(),
            GenericApplicationDetector(),
        ]

    def detect_application(self, path: Path) -> Optional[Tuple[AppType, str]]:
        """Returns (AppType, name) if path is a valid application candidate, else None."""
        if path.is_file():
            suffix = path.suffix.lower()
            name_lower = path.name.lower()
            if suffix in EXECUTABLE_EXTS:
                return AppType.STANDALONE_BINARY, path.stem
            elif suffix in PACKAGE_EXTS:
                return AppType.JAVA_JAR, path.stem
            elif suffix in SCRIPT_APP_EXTS:
                # Disregard internal Python package init markers
                if name_lower.startswith("__init__"):
                    return None
                if suffix == ".py":
                    return AppType.PYTHON_ENV, path.stem
                return AppType.STANDALONE_BINARY, path.stem
            return None  # Plain files (.txt, .jpg, .doc, etc.) are NOT applications

        for detector in self.detectors:
            result = detector.detect(path)
            if result is not None:
                return result
        return None

