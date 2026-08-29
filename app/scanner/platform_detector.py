"""Platform detection and protected system directories guard."""
import os
import platform
from pathlib import Path
from typing import Set


def get_current_platform() -> str:
    return platform.system().lower()


def get_protected_paths() -> Set[str]:
    """Returns a set of normalized absolute paths that should NEVER be scanned or deleted."""
    protected = set()
    current_os = get_current_platform()

    if current_os == "windows":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        sysdrive = os.environ.get("SystemDrive", "C:")
        progdata = os.environ.get("ProgramData", "C:\\ProgramData")

        protected.add(str(Path(windir).resolve()).lower())
        protected.add(str(Path(f"{windir}\\System32").resolve()).lower())
        protected.add(str(Path(f"{windir}\\SysWOW64").resolve()).lower())
        protected.add(str(Path(f"{sysdrive}\\$Recycle.Bin").resolve()).lower())
        protected.add(str(Path(f"{sysdrive}\\System Volume Information").resolve()).lower())
        protected.add(str(Path(f"{progdata}\\Microsoft").resolve()).lower())
    else:
        # Unix/Linux/macOS protected roots
        for p in ["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/etc", "/dev", "/proc", "/sys", "/var/run"]:
            try:
                protected.add(str(Path(p).resolve()).lower())
            except Exception:
                protected.add(p.lower())

    return protected


def is_protected_path(path: str | Path) -> bool:
    """Checks if a path is inside or equals any protected system directory."""
    try:
        resolved = str(Path(path).resolve()).lower()
    except Exception:
        resolved = str(path).lower()

    for prot in get_protected_paths():
        if resolved == prot or resolved.startswith(prot + os.sep) or resolved.startswith(prot + "/"):
            return True
    return False
