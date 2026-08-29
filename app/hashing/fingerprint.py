"""Application content manifest and deterministic fingerprint generator."""
import hashlib
from typing import List
from app.core.types import FileRecord


def generate_application_fingerprint(files: List[FileRecord]) -> str:
    """
    Constructs a deterministic manifest of all readable files within an application,
    sorted by normalized relative path, and computes the SHA-256 fingerprint.
    
    Manifest entry format per file:
    `<normalized_relative_path>:<file_size>:<file_sha256>\n`
    """
    if not files:
        # Empty application
        return hashlib.sha256(b"EMPTY_APPLICATION").hexdigest()

    valid_files = [f for f in files if f.is_readable and f.sha256]
    if not valid_files:
        return hashlib.sha256(b"NO_READABLE_FILES").hexdigest()

    # For standalone single-file application, fingerprint is based purely on content & size
    # regardless of filename differences (PRD Section 2: Different filenames/paths).
    if len(valid_files) == 1:
        f = valid_files[0]
        return hashlib.sha256(f"standalone:{f.size}:{f.sha256}".encode("utf-8")).hexdigest()

    # Normalize relative path: convert Windows backslashes to forward slashes
    def normalize_rel_path(p: str) -> str:
        return p.replace("\\", "/").strip("/")

    sorted_files = sorted(valid_files, key=lambda f: normalize_rel_path(f.relative_path).lower())

    manifest_lines = []
    for f in sorted_files:
        norm_path = normalize_rel_path(f.relative_path).lower()
        manifest_lines.append(f"{norm_path}:{f.size}:{f.sha256}")

    manifest_content = "\n".join(manifest_lines).encode("utf-8")
    return hashlib.sha256(manifest_content).hexdigest()

