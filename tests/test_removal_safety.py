"""Tests for pre-removal safety checks, protected directory guards, and quarantine round-trip."""
from pathlib import Path
from app.core.types import Application, FileRecord
from app.hashing.fingerprint import generate_application_fingerprint
from app.hashing.sha256 import compute_sha256
from app.removal.safety_validator import SafetyValidator
from app.removal.quarantine import QuarantineManager


def test_safety_validator_missing_path(tmp_path: Path):
    missing_app = Application(name="GhostApp", root_path=str(tmp_path / "NonExistent"))
    is_safe, error = SafetyValidator.validate_for_removal(missing_app)
    assert is_safe is False
    assert "does not exist" in (error or "")


def test_safety_validator_detects_drift(tmp_path: Path):
    app_dir = tmp_path / "DriftingApp"
    app_dir.mkdir()
    target_f = app_dir / "data.bin"
    target_f.write_bytes(b"ORIGINAL_BYTES")

    f_rec = FileRecord(
        relative_path="data.bin",
        absolute_path=str(target_f),
        size=14,
        sha256=compute_sha256(target_f) or "",
        is_readable=True,
    )
    app = Application(
        name="DriftingApp",
        root_path=str(app_dir),
        files=[f_rec],
        content_fingerprint=generate_application_fingerprint([f_rec]),
    )

    # Modify file content on disk unexpectedly
    target_f.write_bytes(b"MODIFIED_BYTES_OUTSIDE_SYSTEM")

    is_safe, error = SafetyValidator.validate_for_removal(app)
    assert is_safe is False
    assert "fingerprint changed" in (error or "")


def test_quarantine_and_restore_round_trip(tmp_path: Path):
    quarantine_dir = tmp_path / "quarantine_vault"
    app_dir = tmp_path / "OriginalApp"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("print('quarantine me')")

    app = Application(
        name="OriginalApp",
        root_path=str(app_dir),
        total_size=20,
        content_fingerprint="abc12345fp",
    )

    q_mgr = QuarantineManager(str(quarantine_dir))
    q_dest = q_mgr.quarantine_application(app)

    assert not app_dir.exists()
    assert q_dest.exists()
    assert len(q_mgr.list_quarantined()) == 1

    # Restore
    restored = q_mgr.restore_application(str(app_dir))
    assert restored is True
    assert app_dir.exists()
    assert (app_dir / "main.py").exists()
    assert len(q_mgr.list_quarantined()) == 0
