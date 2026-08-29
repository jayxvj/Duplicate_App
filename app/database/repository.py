"""Database repository for IADCS."""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.types import (
    Application,
    AppType,
    CategoryRule,
    DuplicateGroup,
    FileRecord,
)
from app.database.db import get_db_connection


class Repository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    # --- Application Operations ---
    def save_application(self, app: Application) -> int:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO applications (
                    name, root_path, platform, app_type, total_size,
                    file_count, content_fingerprint, category, scan_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(root_path) DO UPDATE SET
                    name=excluded.name,
                    platform=excluded.platform,
                    app_type=excluded.app_type,
                    total_size=excluded.total_size,
                    file_count=excluded.file_count,
                    content_fingerprint=excluded.content_fingerprint,
                    category=excluded.category,
                    scan_id=excluded.scan_id,
                    updated_at=excluded.updated_at
                """,
                (
                    app.name,
                    app.root_path,
                    app.platform,
                    app.app_type.value if isinstance(app.app_type, AppType) else str(app.app_type),
                    app.total_size,
                    app.file_count,
                    app.content_fingerprint,
                    app.category,
                    app.scan_id,
                    app.created_at,
                    app.updated_at,
                ),
            )
            app_id = cur.lastrowid
            if app_id == 0 or app_id is None:
                cur.execute("SELECT id FROM applications WHERE root_path = ?", (app.root_path,))
                row = cur.fetchone()
                app_id = row["id"] if row else 0

            # Delete old file records if updating
            cur.execute("DELETE FROM file_records WHERE application_id = ?", (app_id,))

            # Batch insert file records
            if app.files:
                records = [
                    (
                        app_id,
                        f.relative_path,
                        f.absolute_path,
                        f.size,
                        f.sha256,
                        f.partial_hash,
                        f.file_type,
                        1 if f.is_readable else 0,
                    )
                    for f in app.files
                ]
                cur.executemany(
                    """
                    INSERT INTO file_records (
                        application_id, relative_path, absolute_path,
                        size, sha256, partial_hash, file_type, is_readable
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
        conn.close()
        return app_id

    def get_application_by_id(self, app_id: int) -> Optional[Application]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        app = self._row_to_app(row)
        cur.execute("SELECT * FROM file_records WHERE application_id = ?", (app_id,))
        app.files = [self._row_to_file(r) for r in cur.fetchall()]
        conn.close()
        return app

    def get_all_applications(self, scan_id: Optional[str] = None) -> List[Application]:
        conn = self._get_conn()
        cur = conn.cursor()
        if scan_id:
            cur.execute("SELECT * FROM applications WHERE scan_id = ? ORDER BY name ASC", (scan_id,))
        else:
            cur.execute("SELECT * FROM applications ORDER BY name ASC")
        rows = cur.fetchall()
        apps = [self._row_to_app(r) for r in rows]
        conn.close()
        return apps

    def delete_application(self, app_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            deleted = cur.rowcount > 0
        conn.close()
        return deleted

    # --- Duplicate Group Operations ---
    def save_duplicate_group(self, group: DuplicateGroup) -> int:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO duplicate_groups (
                    fingerprint, application_count, total_size,
                    reclaimable_size, verification_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    application_count=excluded.application_count,
                    total_size=excluded.total_size,
                    reclaimable_size=excluded.reclaimable_size,
                    verification_status=excluded.verification_status
                """,
                (
                    group.fingerprint,
                    group.application_count,
                    group.total_size,
                    group.reclaimable_size,
                    group.verification_status,
                    group.created_at,
                ),
            )
            group_id = cur.lastrowid
            if group_id == 0 or group_id is None:
                cur.execute("SELECT id FROM duplicate_groups WHERE fingerprint = ?", (group.fingerprint,))
                row = cur.fetchone()
                group_id = row["id"] if row else 0
        conn.close()
        return group_id

    def get_all_duplicate_groups(self) -> List[DuplicateGroup]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM duplicate_groups WHERE application_count > 1 ORDER BY reclaimable_size DESC")
        groups = []
        for row in cur.fetchall():
            grp = DuplicateGroup(
                id=row["id"],
                fingerprint=row["fingerprint"],
                application_count=row["application_count"],
                total_size=row["total_size"],
                reclaimable_size=row["reclaimable_size"],
                verification_status=row["verification_status"],
                created_at=row["created_at"],
            )
            # Fetch associated applications
            cur.execute("SELECT * FROM applications WHERE content_fingerprint = ?", (grp.fingerprint,))
            grp.applications = [self._row_to_app(r) for r in cur.fetchall()]
            groups.append(grp)
        conn.close()
        return groups

    def clear_duplicate_groups(self) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute("DELETE FROM duplicate_groups")
        conn.close()

    # --- Rule Operations ---
    def save_rule(self, rule: CategoryRule) -> int:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            if rule.id:
                cur.execute(
                    """
                    UPDATE category_rules
                    SET category = ?, field = ?, operator = ?, value = ?, priority = ?, enabled = ?
                    WHERE id = ?
                    """,
                    (rule.category, rule.field, rule.operator, rule.value, rule.priority, 1 if rule.enabled else 0, rule.id),
                )
                rule_id = rule.id
            else:
                cur.execute(
                    """
                    INSERT INTO category_rules (category, field, operator, value, priority, enabled)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (rule.category, rule.field, rule.operator, rule.value, rule.priority, 1 if rule.enabled else 0),
                )
                rule_id = cur.lastrowid or 0
        conn.close()
        return rule_id

    def get_all_rules(self) -> List[CategoryRule]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM category_rules ORDER BY priority DESC")
        rules = [
            CategoryRule(
                id=r["id"],
                category=r["category"],
                field=r["field"],
                operator=r["operator"],
                value=r["value"],
                priority=r["priority"],
                enabled=bool(r["enabled"]),
            )
            for r in cur.fetchall()
        ]
        conn.close()
        return rules

    def delete_rule(self, rule_id: int) -> bool:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))
            deleted = cur.rowcount > 0
        conn.close()
        return deleted

    # --- Scan History Operations ---
    def record_scan(
        self,
        scan_id: str,
        started_at: str,
        completed_at: str,
        total_apps: int,
        duplicate_groups: int,
        total_size: int,
        reclaimable_size: int,
        paths_scanned: List[str],
    ) -> int:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO scans (
                    scan_id, started_at, completed_at, total_apps,
                    duplicate_groups, total_size, reclaimable_size, paths_scanned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_id,
                    started_at,
                    completed_at,
                    total_apps,
                    duplicate_groups,
                    total_size,
                    reclaimable_size,
                    json.dumps(paths_scanned),
                ),
            )
            scan_row_id = cur.lastrowid or 0
        conn.close()
        return scan_row_id

    def get_latest_scan(self) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row["id"],
            "scan_id": row["scan_id"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "total_apps": row["total_apps"],
            "duplicate_groups": row["duplicate_groups"],
            "total_size": row["total_size"],
            "reclaimable_size": row["reclaimable_size"],
            "paths_scanned": json.loads(row["paths_scanned"] or "[]"),
        }

    # --- Audit Log Operations ---
    def log_operation(
        self,
        operation: str,
        application_id: Optional[int],
        path: str,
        content_hash: Optional[str] = None,
        size: int = 0,
        status: str = "success",
        error: Optional[str] = None,
    ) -> int:
        conn = self._get_conn()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_logs (
                    operation, application_id, path, hash, size, status, error, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation,
                    application_id,
                    path,
                    content_hash,
                    size,
                    status,
                    error,
                    datetime.now().isoformat(),
                ),
            )
            log_id = cur.lastrowid or 0
        conn.close()
        return log_id

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    # --- Helpers ---
    @staticmethod
    def _row_to_app(row: sqlite3.Row) -> Application:
        return Application(
            id=row["id"],
            name=row["name"],
            root_path=row["root_path"],
            platform=row["platform"],
            app_type=AppType(row["app_type"]) if row["app_type"] in AppType.__members__.values() else AppType.GENERIC_FOLDER,
            total_size=row["total_size"],
            file_count=row["file_count"],
            content_fingerprint=row["content_fingerprint"],
            category=row["category"],
            scan_id=row["scan_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_file(row: sqlite3.Row) -> FileRecord:
        return FileRecord(
            id=row["id"],
            application_id=row["application_id"],
            relative_path=row["relative_path"],
            absolute_path=row["absolute_path"],
            size=row["size"],
            sha256=row["sha256"] or "",
            partial_hash=row["partial_hash"] or "",
            file_type=row["file_type"] or "",
            is_readable=bool(row["is_readable"]),
        )
