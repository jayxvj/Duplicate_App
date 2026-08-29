"""JSON and formatted summary report generation."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.types import Application, DuplicateGroup, RemovalResult


class ReportGenerator:
    @staticmethod
    def generate_full_report(
        scan_id: str,
        scan_paths: List[str],
        duration_seconds: float,
        applications: List[Application],
        duplicate_groups: List[DuplicateGroup],
        category_counts: Dict[str, int],
        removal_results: Optional[List[RemovalResult]] = None,
    ) -> Dict[str, Any]:
        total_size = sum(app.total_size for app in applications)
        total_reclaimable = sum(g.reclaimable_size for g in duplicate_groups)

        report = {
            "metadata": {
                "report_version": "1.0",
                "system": "Intelligent Application Deduplication & Categorization System (IADCS)",
                "generated_at": datetime.now().isoformat(),
                "scan_id": scan_id,
            },
            "scan_summary": {
                "scan_paths": scan_paths,
                "duration_seconds": round(duration_seconds, 2),
                "total_applications_found": len(applications),
                "total_files_scanned": sum(app.file_count for app in applications),
                "total_storage_bytes": total_size,
                "total_reclaimable_bytes": total_reclaimable,
            },
            "duplicate_summary": {
                "duplicate_groups_count": len(duplicate_groups),
                "groups": [
                    {
                        "group_id": idx + 1,
                        "fingerprint": g.fingerprint,
                        "application_count": g.application_count,
                        "total_size_bytes": g.total_size,
                        "reclaimable_bytes": g.reclaimable_size,
                        "verification_status": g.verification_status,
                        "applications": [
                            {
                                "id": a.id,
                                "name": a.name,
                                "path": a.root_path,
                                "category": a.category,
                                "size_bytes": a.total_size,
                                "file_count": a.file_count,
                            }
                            for a in g.applications
                        ],
                    }
                    for idx, g in enumerate(duplicate_groups)
                ],
            },
            "categorization_summary": {
                "category_breakdown": category_counts,
                "total_categories": len(category_counts),
            },
            "removal_summary": {
                "operations": [
                    {
                        "app_name": r.app_name,
                        "original_path": r.root_path,
                        "action": r.action,
                        "status": r.status,
                        "reclaimed_bytes": r.reclaimed_bytes,
                        "error": r.error_message,
                        "quarantine_path": r.quarantine_path,
                    }
                    for r in (removal_results or [])
                ],
                "total_reclaimed_bytes": sum(r.reclaimed_bytes for r in (removal_results or []) if r.status == "success"),
            },
        }
        return report

    @staticmethod
    def export_to_json(report_data: Dict[str, Any], output_path: str | Path) -> str:
        out = Path(output_path).resolve()
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        return str(out)
