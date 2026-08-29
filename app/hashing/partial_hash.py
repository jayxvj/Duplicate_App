"""Partial chunk hashing for quick non-match elimination."""
import hashlib
from pathlib import Path
from typing import Optional

PARTIAL_CHUNK_BYTES = 4096  # 4 KB
SIZE_THRESHOLD = 1024 * 1024  # 1 MB


def compute_partial_hash(
    file_path: str | Path,
    chunk_bytes: int = PARTIAL_CHUNK_BYTES,
    size_threshold: int = SIZE_THRESHOLD,
) -> Optional[str]:
    """Calculates header + middle + footer chunk hash for fast size/early rejection."""
    path = Path(file_path)
    if not path.is_file():
        return None

    try:
        size = path.stat().st_size
        if size == 0:
            return hashlib.sha256(b"").hexdigest()

        # For smaller files, standard partial hash is simply the entire file or up to chunk_bytes
        if size <= size_threshold:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            # 1. Header chunk
            hasher.update(f.read(chunk_bytes))

            # 2. Middle chunk
            mid_offset = max(0, (size // 2) - (chunk_bytes // 2))
            f.seek(mid_offset)
            hasher.update(f.read(chunk_bytes))

            # 3. Footer chunk
            foot_offset = max(0, size - chunk_bytes)
            f.seek(foot_offset)
            hasher.update(f.read(chunk_bytes))

        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None
