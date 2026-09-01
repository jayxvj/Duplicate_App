"""
ReportManager — generates scan reports in JSON, HTML, and CSV formats.
"""
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.config import cfg
from app.data.models import DuplicateGroup, ReportRecord, ScanRecord
from app.data.repository import Repository

logger = logging.getLogger(__name__)


def _bytes_human(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


class ReportManager:
    def __init__(self, repo: Repository):
        self.repo = repo
        self._out_dir = cfg.reports_dir
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def _report_path(self, scan_id: int, fmt: str) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return self._out_dir / f"scan_{scan_id}_{ts}.{fmt}"

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def generate_json(self, scan: ScanRecord, groups: List[DuplicateGroup]) -> ReportRecord:
        path = self._report_path(scan.id, "json")
        data = {
            "scan": {
                "id": scan.id,
                "type": scan.scan_type,
                "root_path": scan.root_path,
                "started_at": scan.started_at,
                "finished_at": scan.finished_at,
                "status": scan.status,
                "apps_found": scan.apps_found,
                "duplicates_found": scan.duplicates_found,
            },
            "duplicate_groups": [
                {
                    "group_id": g.id,
                    "signature": g.group_signature,
                    "match_type": g.match_type,
                    "member_count": len(g.members),
                    "reference_app_id": g.reference_app_id,
                    "members": [
                        {
                            "app_id": m.id,
                            "name": m.name,
                            "install_path": m.install_path,
                            "version": m.version,
                            "publisher": m.publisher,
                            "category": m.category,
                            "disk_size": m.disk_size_bytes,
                            "disk_size_human": _bytes_human(m.disk_size_bytes),
                            "is_reference": m.id == g.reference_app_id,
                        }
                        for m in g.members
                    ],
                }
                for g in groups
            ],
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        rec = self.repo.save_report(ReportRecord(
            scan_id=scan.id, format="json", file_path=str(path),
        ))
        logger.info("JSON report saved: %s", path)
        return rec

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def generate_csv(self, scan: ScanRecord, groups: List[DuplicateGroup]) -> ReportRecord:
        path = self._report_path(scan.id, "csv")
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "group_id", "signature_prefix", "app_id", "name",
                "install_path", "version", "publisher", "category",
                "disk_size_bytes", "disk_size_human", "is_reference",
            ])
            for g in groups:
                for m in g.members:
                    writer.writerow([
                        g.id, g.group_signature[:16] + "...", m.id,
                        m.name, m.install_path, m.version, m.publisher,
                        m.category, m.disk_size_bytes,
                        _bytes_human(m.disk_size_bytes),
                        "YES" if m.id == g.reference_app_id else "NO",
                    ])

        rec = self.repo.save_report(ReportRecord(
            scan_id=scan.id, format="csv", file_path=str(path),
        ))
        logger.info("CSV report saved: %s", path)
        return rec

    # ------------------------------------------------------------------
    # HTML
    # ------------------------------------------------------------------

    def generate_html(self, scan: ScanRecord, groups: List[DuplicateGroup]) -> ReportRecord:
        path = self._report_path(scan.id, "html")

        rows_html = ""
        for g in groups:
            for i, m in enumerate(g.members):
                is_ref = m.id == g.reference_app_id
                badge = '<span class="badge keep">KEEP</span>' if is_ref else ""
                rows_html += f"""
                <tr class="{'ref-row' if is_ref else ''}">
                    <td>{g.id}</td>
                    <td><code>{g.group_signature[:16]}…</code></td>
                    <td>{m.id}</td>
                    <td>{m.name} {badge}</td>
                    <td title="{m.install_path}">{m.install_path[:60]}{'…' if len(m.install_path)>60 else ''}</td>
                    <td>{m.version}</td>
                    <td>{m.category}</td>
                    <td>{_bytes_human(m.disk_size_bytes)}</td>
                </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Duplicate Detector — Scan #{scan.id} Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f0f1a; color:#e0e0f0; margin:0; padding:24px; }}
  h1 {{ color:#7c6fff; }} h2 {{ color:#9090c0; border-bottom:1px solid #333; padding-bottom:6px; }}
  .meta {{ background:#1a1a2e; border-radius:8px; padding:16px; margin-bottom:24px; display:flex; gap:32px; flex-wrap:wrap; }}
  .meta span {{ font-size:13px; color:#aaa; }} .meta strong {{ color:#fff; font-size:15px; display:block; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th {{ background:#1e1e3a; color:#9090c0; text-align:left; padding:8px 12px; }}
  td {{ border-bottom:1px solid #1e1e2e; padding:7px 12px; vertical-align:top; }}
  tr:hover td {{ background:#1a1a30; }}
  .ref-row td {{ background:#0d2020; }}
  .badge.keep {{ background:#16a34a; color:#fff; border-radius:4px; padding:2px 7px; font-size:11px; }}
  code {{ color:#7c6fff; background:#1a1a2e; padding:1px 4px; border-radius:3px; }}
</style>
</head>
<body>
<h1>🔍 Duplicate Detector — Scan Report</h1>
<div class="meta">
  <div><span>Scan ID</span><strong>#{scan.id}</strong></div>
  <div><span>Type</span><strong>{scan.scan_type.title()}</strong></div>
  <div><span>Root</span><strong>{scan.root_path or 'Full System'}</strong></div>
  <div><span>Status</span><strong>{scan.status.upper()}</strong></div>
  <div><span>Apps Scanned</span><strong>{scan.apps_found}</strong></div>
  <div><span>Duplicate Groups</span><strong>{scan.duplicates_found}</strong></div>
  <div><span>Started</span><strong>{scan.started_at}</strong></div>
  <div><span>Finished</span><strong>{scan.finished_at}</strong></div>
</div>
<h2>Duplicate Groups ({len(groups)})</h2>
<table>
  <thead><tr>
    <th>Group</th><th>Signature</th><th>App ID</th><th>Name</th>
    <th>Install Path</th><th>Version</th><th>Category</th><th>Size</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</body>
</html>"""

        with path.open("w", encoding="utf-8") as fh:
            fh.write(html)

        rec = self.repo.save_report(ReportRecord(
            scan_id=scan.id, format="html", file_path=str(path),
        ))
        logger.info("HTML report saved: %s", path)
        return rec

    # ------------------------------------------------------------------
    # Generate all three at once
    # ------------------------------------------------------------------

    def generate_all(
        self, scan: ScanRecord, groups: List[DuplicateGroup]
    ) -> List[ReportRecord]:
        return [
            self.generate_json(scan, groups),
            self.generate_csv(scan, groups),
            self.generate_html(scan, groups),
        ]
