"""Tests for streaming SHA-256, partial hashing, and deterministic fingerprints."""
import hashlib
import tempfile
from pathlib import Path

from app.core.types import FileRecord
from app.hashing.sha256 import compute_sha256
from app.hashing.partial_hash import compute_partial_hash
from app.hashing.fingerprint import generate_application_fingerprint


def test_sha256_streaming(tmp_path: Path):
    test_file = tmp_path / "test.bin"
    content = b"Deterministic application content block " * 1000
    test_file.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    actual = compute_sha256(test_file)
    assert actual == expected


def test_partial_hash_small_and_large(tmp_path: Path):
    small_file = tmp_path / "small.txt"
    small_file.write_bytes(b"small content")
    p_small = compute_partial_hash(small_file)
    assert p_small is not None

    large_file = tmp_path / "large.bin"
    large_file.write_bytes(b"X" * (2 * 1024 * 1024))
    p_large = compute_partial_hash(large_file, size_threshold=1024 * 1024)
    assert p_large is not None
    assert len(p_large) == 64


def test_application_fingerprint_deterministic_and_path_independent():
    # Two installations of the same app in different directories
    app1_files = [
        FileRecord(relative_path="bin/app.exe", absolute_path="C:/Apps/AppA/bin/app.exe", size=1024, sha256="hash_exe", is_readable=True),
        FileRecord(relative_path="config.json", absolute_path="C:/Apps/AppA/config.json", size=256, sha256="hash_cfg", is_readable=True),
    ]

    app2_files = [
        # Note reverse order and Windows backslashes
        FileRecord(relative_path="config.json", absolute_path="D:/Backup/AppB/config.json", size=256, sha256="hash_cfg", is_readable=True),
        FileRecord(relative_path="bin\\app.exe", absolute_path="D:/Backup/AppB/bin/app.exe", size=1024, sha256="hash_exe", is_readable=True),
    ]

    fp1 = generate_application_fingerprint(app1_files)
    fp2 = generate_application_fingerprint(app2_files)

    assert fp1 == fp2
    assert len(fp1) == 64
