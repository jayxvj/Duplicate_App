"""
IADCS Web Server & REST API Bridge
Serves the web UI and provides full REST API endpoints connected to the Python backend.
Zero extra dependencies (built with Python standard library http.server).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Remove 'app' directory from sys.path if Python added it, to prevent shadowing standard library 'logging'
_app_dir = str(Path(__file__).resolve().parent)
while _app_dir in sys.path:
    sys.path.remove(_app_dir)

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Standard library imports
import json
import logging
import os
import threading
import time
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

# Project imports
from app.database.db import init_db
from app.database.repository import Repository
from app.scanner.directory_scanner import DirectoryScanner
from app.duplicate.candidate_matcher import CandidateMatcher
from app.duplicate.duplicate_detector import DuplicateDetector
from app.categorization.category_manager import CategoryManager
from app.removal.removal_manager import RemovalManager
from app.removal.quarantine import QuarantineManager
from app.reporting.report_generator import ReportGenerator

WEB_DIR = _project_root / "web"

_scan_lock = threading.Lock()
_scan_state = {
    "is_scanning": False,
    "progress": 0,
    "stage": "idle",
    "last_result": None,
    "error": None
}


class IADCSApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw)
        except Exception:
            pass
        return {}

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/status":
            self.handle_get_status()
        elif path == "/api/dashboard":
            self.handle_get_dashboard()
        elif path == "/api/duplicates":
            self.handle_get_duplicates()
        elif path == "/api/categories":
            self.handle_get_categories()
        elif path == "/api/quarantine":
            self.handle_get_quarantine()
        elif path == "/api/report":
            self.handle_get_report()
        elif path == "/api/audit-logs":
            self.handle_get_audit_logs()
        elif path == "/api/scan/status":
            self._send_json(_scan_state)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/scan":
            self.handle_post_scan()
        elif path == "/api/quarantine":
            self.handle_post_quarantine()
        elif path == "/api/restore":
            self.handle_post_restore()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def handle_get_status(self):
        self._send_json({
            "status": "online",
            "system": "IADCS Sentinel Backend",
            "version": "1.0.0",
            "scanning": _scan_state["is_scanning"]
        })

    def handle_get_dashboard(self):
        try:
            init_db()
            repo = Repository()
            apps = repo.get_all_applications()
            dup_groups = repo.get_all_duplicate_groups()
            latest_scan = repo.get_latest_scan()

            total_apps = len(apps)
            total_dup_groups = len(dup_groups)
            total_reclaimable = sum(getattr(g, 'reclaimable_size', 0) for g in dup_groups)
            total_size = sum(a.total_size for a in apps)

            cat_counts: Dict[str, int] = {}
            for a in apps:
                cat = a.category or "Other"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            categories = [{"name": k, "count": v} for k, v in cat_counts.items()]
            if not categories:
                categories = [{"name": "Development", "count": 0}, {"name": "Utilities", "count": 0}]

            self._send_json({
                "totalApps": total_apps,
                "duplicateGroupsCount": total_dup_groups,
                "totalSize": total_size,
                "reclaimableSize": total_reclaimable,
                "categories": categories,
                "latestScan": latest_scan
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_get_duplicates(self):
        try:
            init_db()
            repo = Repository()
            groups = repo.get_all_duplicate_groups()
            result = []

            for idx, g in enumerate(groups, 1):
                instances = []
                for i_idx, app in enumerate(g.applications):
                    is_orig = (i_idx == 0)
                    date_val = str(app.created_at) if app.created_at else time.strftime("%Y-%m-%d")
                    if len(date_val) > 10 and ("T" in date_val or " " in date_val):
                        date_val = date_val[:10]

                    instances.append({
                        "id": app.id or (idx * 100 + i_idx),
                        "path": app.root_path,
                        "name": app.name,
                        "isOriginal": is_orig,
                        "size": self._format_bytes(app.total_size),
                        "totalSizeBytes": app.total_size,
                        "date": date_val,
                        "hash": (app.content_fingerprint[:16] + "...") if app.content_fingerprint else "N/A"
                    })

                fp = getattr(g, 'fingerprint', '') or getattr(g, 'content_fingerprint', '')
                rec_size = getattr(g, 'reclaimable_size', 0)
                tot_size = getattr(g, 'total_size', sum(a.total_size for a in g.applications))

                result.append({
                    "id": g.id or idx,
                    "name": g.applications[0].name if g.applications else "Duplicate Application Group",
                    "category": g.applications[0].category if g.applications else "General",
                    "fingerprint": fp,
                    "totalSize": tot_size,
                    "reclaimableSize": rec_size,
                    "instances": instances
                })

            self._send_json(result)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_get_categories(self):
        try:
            init_db()
            repo = Repository()
            apps = repo.get_all_applications()
            cat_map: Dict[str, List[Dict[str, Any]]] = {}

            for a in apps:
                cat = a.category or "Other"
                if cat not in cat_map:
                    cat_map[cat] = []
                cat_map[cat].append({
                    "id": a.id,
                    "name": a.name,
                    "path": a.root_path,
                    "size": self._format_bytes(a.total_size)
                })

            categories = [{"name": k, "count": len(v), "apps": v} for k, v in cat_map.items()]
            self._send_json(categories)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_get_quarantine(self):
        try:
            qm = QuarantineManager()
            quarantined = qm.list_quarantined()
            self._send_json(quarantined)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_get_report(self):
        try:
            init_db()
            repo = Repository()
            generator = ReportGenerator(repo)
            report = generator.generate_full_report()
            self._send_json(report)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_get_audit_logs(self):
        try:
            init_db()
            repo = Repository()
            logs = repo.get_audit_logs(limit=100)
            self._send_json(logs)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_post_scan(self):
        if _scan_state["is_scanning"]:
            self._send_json({"error": "A scan is already in progress"}, status=409)
            return

        body = self._read_json_body()
        target_path = body.get("path")
        if not target_path:
            target_path = str(_project_root / "sample_apps")

        thread = threading.Thread(target=self._run_scan_pipeline, args=(target_path,))
        thread.daemon = True
        thread.start()

        self._send_json({
            "message": "Scan started",
            "target": target_path,
            "status": "running"
        })

    def _run_scan_pipeline(self, target_path: str):
        with _scan_lock:
            _scan_state["is_scanning"] = True
            _scan_state["progress"] = 10
            _scan_state["stage"] = "Discovering application packages..."
            _scan_state["error"] = None

            try:
                init_db()
                repo = Repository()
                scan_id = str(uuid.uuid4())[:8]

                time.sleep(0.3)
                _scan_state["progress"] = 30
                _scan_state["stage"] = "Scanning directories and computing fingerprints..."

                scanner = DirectoryScanner()
                scan_dir = Path(target_path)
                if not scan_dir.exists():
                    scan_dir = _project_root / "sample_apps"

                apps = scanner.scan_directories([scan_dir])

                _scan_state["progress"] = 55
                _scan_state["stage"] = "Matching candidate fingerprints..."
                matcher = CandidateMatcher()
                apps = matcher.process_applications(apps)

                _scan_state["progress"] = 75
                _scan_state["stage"] = "Applying rule-based categorization..."
                cat_mgr = CategoryManager(repo)
                apps = cat_mgr.categorize_applications(apps)

                for app in apps:
                    app.scan_id = scan_id
                    repo.save_application(app)

                _scan_state["progress"] = 90
                _scan_state["stage"] = "Detecting duplicate groups and byte verification..."
                detector = DuplicateDetector(auto_verify_bytes=True)
                dup_groups = detector.detect_duplicates(apps)

                repo.clear_duplicate_groups()
                for grp in dup_groups:
                    repo.save_duplicate_group(grp)

                reclaimable = sum(getattr(g, 'reclaimable_size', 0) for g in dup_groups)
                repo.record_scan(
                    scan_id=scan_id,
                    started_at=time.ctime(),
                    completed_at=time.ctime(),
                    total_apps=len(apps),
                    duplicate_groups=len(dup_groups),
                    total_size=sum(a.total_size for a in apps),
                    reclaimable_size=reclaimable,
                    paths_scanned=[str(scan_dir)],
                )

                _scan_state["progress"] = 100
                _scan_state["stage"] = "Complete! Verified duplicate groups."
                _scan_state["last_result"] = {
                    "scan_id": scan_id,
                    "apps_found": len(apps),
                    "duplicate_groups": len(dup_groups),
                    "reclaimable_bytes": reclaimable
                }
            except Exception as e:
                _scan_state["error"] = str(e)
                _scan_state["stage"] = f"Failed: {e}"
            finally:
                _scan_state["is_scanning"] = False

    def handle_post_quarantine(self):
        body = self._read_json_body()
        app_ids = body.get("app_ids", [])
        paths = body.get("paths", [])

        try:
            init_db()
            repo = Repository()
            rem_mgr = RemovalManager(repo)
            quarantined_count = 0
            reclaimed = 0
            errors = []

            all_apps = repo.get_all_applications()
            targets = []

            for a in all_apps:
                if a.id in app_ids or a.root_path in paths:
                    targets.append(a)

            for a in targets:
                res = rem_mgr.remove_application(a, action="quarantine")
                if res.status == "success":
                    quarantined_count += 1
                    reclaimed += res.reclaimed_bytes
                else:
                    errors.append(f"{a.name}: {res.error_message}")

            self._send_json({
                "status": "success" if not errors else "partial",
                "quarantined_count": quarantined_count,
                "reclaimed_bytes": reclaimed,
                "errors": errors
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def handle_post_restore(self):
        body = self._read_json_body()
        original_path = body.get("original_path")
        if not original_path:
            self._send_json({"error": "original_path is required"}, status=400)
            return

        try:
            qm = QuarantineManager()
            success = qm.restore_application(original_path)
            self._send_json({"status": "restored" if success else "failed"})
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    @staticmethod
    def _format_bytes(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


def run_server(port: int = 8080):
    init_db()
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, IADCSApiHandler)
    print(f"[*] IADCS Full-Stack Web Server listening on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
