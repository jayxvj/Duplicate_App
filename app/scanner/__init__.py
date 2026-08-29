"""Scanner and application discovery module."""
from app.scanner.directory_scanner import DirectoryScanner
from app.scanner.application_detector import (
    BaseApplicationDetector,
    WindowsApplicationDetector,
    PythonApplicationDetector,
    JavaApplicationDetector,
    GenericApplicationDetector,
    CompositeApplicationDetector,
)
from app.scanner.platform_detector import is_protected_path, get_current_platform, get_protected_paths

__all__ = [
    "DirectoryScanner",
    "BaseApplicationDetector",
    "WindowsApplicationDetector",
    "PythonApplicationDetector",
    "JavaApplicationDetector",
    "GenericApplicationDetector",
    "CompositeApplicationDetector",
    "is_protected_path",
    "get_current_platform",
    "get_protected_paths",
]
