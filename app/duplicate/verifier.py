"""Byte-level verification for guaranteed binary duplicate confirmation."""
from pathlib import Path
from typing import List, Tuple
from app.core.types import Application, FileRecord

CHUNK_SIZE = 64 * 1024  # 64 KB for byte comparison


def verify_files_byte_by_byte(path_a: str | Path, path_b: str | Path) -> bool:
    """Performs an exact byte-level comparison between two files."""
    p_a = Path(path_a)
    p_b = Path(path_b)

    if not p_a.is_file() or not p_b.is_file():
        return False

    try:
        if p_a.stat().st_size != p_b.stat().st_size:
            return False

        with open(p_a, "rb") as f_a, open(p_b, "rb") as f_b:
            while True:
                chunk_a = f_a.read(CHUNK_SIZE)
                chunk_b = f_b.read(CHUNK_SIZE)
                if chunk_a != chunk_b:
                    return False
                if not chunk_a:  # EOF reached and all bytes matched
                    return True
    except (OSError, PermissionError):
        return False


def verify_applications_byte_by_byte(app_a: Application, app_b: Application) -> bool:
    """Verifies that all corresponding files in two applications are byte-for-byte identical."""
    if app_a.total_size != app_b.total_size or app_a.file_count != app_b.file_count:
        return False

    # For standalone single-file applications, verify byte-by-byte directly regardless of filename
    if app_a.file_count == 1 and app_b.file_count == 1:
        if not app_a.files or not app_b.files:
            return False
        return verify_files_byte_by_byte(app_a.files[0].absolute_path, app_b.files[0].absolute_path)

    # For multi-file directory applications, map files by normalized relative path
    def norm(p: str) -> str:
        return p.replace("\\", "/").strip("/").lower()

    files_a = {norm(f.relative_path): f for f in app_a.files if f.is_readable}
    files_b = {norm(f.relative_path): f for f in app_b.files if f.is_readable}

    if set(files_a.keys()) != set(files_b.keys()):
        return False

    for rel_path, rec_a in files_a.items():
        rec_b = files_b[rel_path]
        if not verify_files_byte_by_byte(rec_a.absolute_path, rec_b.absolute_path):
            return False

    return True

