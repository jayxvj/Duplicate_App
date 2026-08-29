"""Streaming incremental SHA-256 hashing."""
import hashlib
from pathlib import Path
from typing import Optional

DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


def compute_sha256(file_path: str | Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Optional[str]:
    """Calculates full SHA-256 of a file using streaming reads."""
    path = Path(file_path)
    if not path.is_file():
        return None

    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None
