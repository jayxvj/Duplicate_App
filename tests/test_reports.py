"""Tests for machine-readable JSON report structure and export."""
import json
from pathlib import Path
from app.core.types import Application, DuplicateGroup
from app.reporting.report_generator import ReportGenerator


def test_report_generator_schema_and_export(tmp_path: Path):
    apps = [
        Application(id=1, name="AppA", root_path="C:/Apps/AppA", total_size=1000, file_count=2, category="Development"),
        Application(id=2, name="AppA_Copy", root_path="D:/Apps/AppA_Copy", total_size=1000, file_count=2, category="Development"),
    ]
    groups = [
        DuplicateGroup(
            id=1,
            fingerprint="sha256_fp_sample",
            application_count=2,
            total_size=2000,
            reclaimable_size=1000,
            applications=apps,
        )
    ]
    cat_counts = {"Development": 2}

    report = ReportGenerator.generate_full_report(
        scan_id="test_scan_01",
        scan_paths=["C:/Apps", "D:/Apps"],
        duration_seconds=1.23,
        applications=apps,
        duplicate_groups=groups,
        category_counts=cat_counts,
    )

    assert report["metadata"]["scan_id"] == "test_scan_01"
    assert report["scan_summary"]["total_applications_found"] == 2
    assert report["scan_summary"]["total_reclaimable_bytes"] == 1000
    assert report["duplicate_summary"]["duplicate_groups_count"] == 1

    out_file = tmp_path / "report.json"
    ReportGenerator.export_to_json(report, out_file)
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["metadata"]["scan_id"] == "test_scan_01"
