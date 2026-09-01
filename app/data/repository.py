"""
Repository — all CRUD operations against the SQLite database.
The rest of the application only talks to this module; it never calls
sqlite3 directly.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.data.database import Database
from app.data.models import (
    AppRecord, FileRecord, FileHashRecord,
    DuplicateGroup, ScanRecord, ReportRecord,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db: Database):
        self.db = db

    # ======================================================================
    # Scans
    # ======================================================================

    def create_scan(self, scan_type: str, root_path: str) -> ScanRecord:
        now = _now()
        cur = self.db.execute(
            "INSERT INTO scans(scan_type, root_path, started_at, status) VALUES(?,?,?,?)",
            (scan_type, root_path, now, "running"),
        )
        self.db.commit()
        rec = ScanRecord(id=cur.lastrowid, scan_type=scan_type, root_path=root_path,
                         started_at=now, status="running")
        logger.debug("Created scan %d", rec.id)
        return rec

    def finish_scan(self, scan_id: int, status: str, apps_found: int, duplicates_found: int):
        self.db.execute(
            "UPDATE scans SET finished_at=?, status=?, apps_found=?, duplicates_found=? WHERE id=?",
            (_now(), status, apps_found, duplicates_found, scan_id),
        )
        self.db.commit()

    def get_all_scans(self) -> List[ScanRecord]:
        rows = self.db.execute(
            "SELECT * FROM scans ORDER BY id DESC"
        ).fetchall()
        return [self._row_to_scan(r) for r in rows]

    def get_scan(self, scan_id: int) -> Optional[ScanRecord]:
        row = self.db.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        return self._row_to_scan(row) if row else None

    @staticmethod
    def _row_to_scan(row) -> ScanRecord:
        return ScanRecord(
            id=row["id"], scan_type=row["scan_type"], root_path=row["root_path"],
            started_at=row["started_at"], finished_at=row["finished_at"],
            status=row["status"], apps_found=row["apps_found"],
            duplicates_found=row["duplicates_found"],
        )

    # ======================================================================
    # Apps
    # ======================================================================

    def upsert_app(self, app: AppRecord) -> AppRecord:
        """
        Insert a new application or update an existing application.

        IMPORTANT:
        We do NOT use cursor.lastrowid after an UPSERT because when the
        install_path already exists, SQLite performs UPDATE instead of INSERT
        and lastrowid is not guaranteed to be the application's actual ID.

        Instead, after the UPSERT we explicitly query the database for the
        application's real primary key.
        """

        now = _now()

        self.db.execute(
            """
            INSERT INTO apps(
                name,
                install_path,
                version,
                publisher,
                category,
                app_signature,
                disk_size_bytes,
                scan_id,
                first_seen,
                last_scanned
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)

            ON CONFLICT(install_path) DO UPDATE SET
                name=excluded.name,
                version=excluded.version,
                publisher=excluded.publisher,
                category=excluded.category,
                app_signature=excluded.app_signature,
                disk_size_bytes=excluded.disk_size_bytes,
                scan_id=excluded.scan_id,
                last_scanned=excluded.last_scanned
            """,
            (
                app.name,
                app.install_path,
                app.version,
                app.publisher,
                app.category,
                app.app_signature,
                app.disk_size_bytes,
                app.scan_id,
                now,
                now,
            ),
        )

        self.db.commit()

        # ---------------------------------------------------------------
        # IMPORTANT:
        # Always retrieve the REAL database ID using install_path.
        # This works for BOTH:
        #
        #   1. New application INSERT
        #   2. Existing application UPDATE
        # ---------------------------------------------------------------

        row = self.db.execute(
            """
            SELECT id
            FROM apps
            WHERE install_path=?
            """,
            (app.install_path,),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                f"Application was upserted but could not be found in database: "
                f"{app.install_path}"
            )

        # Force the Python object to use the actual DB primary key.
        app.id = row["id"]

        return app

    def get_app(self, app_id: int) -> Optional[AppRecord]:
        row = self.db.execute("SELECT * FROM apps WHERE id=?", (app_id,)).fetchone()
        return self._row_to_app(row) if row else None

    def get_all_apps(self) -> List[AppRecord]:
        rows = self.db.execute("SELECT * FROM apps ORDER BY name").fetchall()
        return [self._row_to_app(r) for r in rows]

    def get_apps_by_scan(self, scan_id: int) -> List[AppRecord]:
        rows = self.db.execute(
            "SELECT * FROM apps WHERE scan_id=? ORDER BY name", (scan_id,)
        ).fetchall()
        return [self._row_to_app(r) for r in rows]

    def delete_app(self, app_id: int):
        self.db.execute("DELETE FROM apps WHERE id=?", (app_id,))
        self.db.commit()

    @staticmethod
    def _row_to_app(row) -> AppRecord:
        return AppRecord(
            id=row["id"], name=row["name"], install_path=row["install_path"],
            version=row["version"], publisher=row["publisher"],
            category=row["category"], app_signature=row["app_signature"],
            disk_size_bytes=row["disk_size_bytes"], scan_id=row["scan_id"],
            first_seen=row["first_seen"], last_scanned=row["last_scanned"],
        )

    # ======================================================================
    # Files
    # ======================================================================

    def upsert_file(self, f: FileRecord) -> FileRecord:
        cur = self.db.execute(
            """
            INSERT INTO files(app_id, relative_path, absolute_path, file_size, is_volatile, is_core)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(absolute_path) DO UPDATE SET
                app_id=excluded.app_id,
                relative_path=excluded.relative_path,
                file_size=excluded.file_size,
                is_volatile=excluded.is_volatile,
                is_core=excluded.is_core
            """,
            (f.app_id, f.relative_path, f.absolute_path, f.file_size,
             int(f.is_volatile), int(f.is_core)),
        )
        if f.id is None:
            f.id = cur.lastrowid
        return f

    def bulk_upsert_files(self, files: List[FileRecord]):
        self.db.executemany(
            """
            INSERT INTO files(app_id, relative_path, absolute_path, file_size, is_volatile, is_core)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(absolute_path) DO UPDATE SET
                app_id=excluded.app_id,
                relative_path=excluded.relative_path,
                file_size=excluded.file_size,
                is_volatile=excluded.is_volatile,
                is_core=excluded.is_core
            """,
            [(f.app_id, f.relative_path, f.absolute_path, f.file_size,
              int(f.is_volatile), int(f.is_core)) for f in files],
        )
        self.db.commit()

    def get_files_for_app(self, app_id: int) -> List[FileRecord]:
        rows = self.db.execute(
            "SELECT * FROM files WHERE app_id=? ORDER BY relative_path", (app_id,)
        ).fetchall()
        return [self._row_to_file(r) for r in rows]

    @staticmethod
    def _row_to_file(row) -> FileRecord:
        return FileRecord(
            id=row["id"], app_id=row["app_id"],
            relative_path=row["relative_path"], absolute_path=row["absolute_path"],
            file_size=row["file_size"],
            is_volatile=bool(row["is_volatile"]),
            is_core=bool(row["is_core"]),
        )

    # ======================================================================
    # File Hashes (cache)
    # ======================================================================

    def get_cached_hash(self, file_id: int, file_size: int, mtime: float) -> Optional[str]:
        """Return cached SHA-256 if the file hasn't changed since last hash."""
        row = self.db.execute(
            "SELECT sha256, file_size, mtime FROM file_hashes WHERE file_id=?",
            (file_id,),
        ).fetchone()
        if row and row["file_size"] == file_size and abs(row["mtime"] - mtime) < 0.001:
            return row["sha256"]
        return None

    def save_hash(self, record: FileHashRecord):
        self.db.execute(
            """
            INSERT INTO file_hashes(file_id, sha256, file_size, mtime, computed_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(file_id) DO UPDATE SET
                sha256=excluded.sha256,
                file_size=excluded.file_size,
                mtime=excluded.mtime,
                computed_at=excluded.computed_at
            """,
            (record.file_id, record.sha256, record.file_size, record.mtime, record.computed_at),
        )
        # Caller is responsible for committing in bulk for performance

    def bulk_save_hashes(self, records: List[FileHashRecord]):
        self.db.executemany(
            """
            INSERT INTO file_hashes(file_id, sha256, file_size, mtime, computed_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(file_id) DO UPDATE SET
                sha256=excluded.sha256,
                file_size=excluded.file_size,
                mtime=excluded.mtime,
                computed_at=excluded.computed_at
            """,
            [(r.file_id, r.sha256, r.file_size, r.mtime, r.computed_at) for r in records],
        )
        self.db.commit()

    # ======================================================================
    # Duplicate Groups
    # ======================================================================

    def create_duplicate_group(self, group: DuplicateGroup) -> DuplicateGroup:
        now = _now()
        cur = self.db.execute(
            """
            INSERT INTO duplicate_groups(group_signature, match_type, similarity,
                                         reference_app_id, scan_id, created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (group.group_signature, group.match_type, group.similarity,
             group.reference_app_id, group.scan_id, now),
        )
        group.id = cur.lastrowid
        group.created_at = now
        # Insert members
        self.db.executemany(
            "INSERT OR IGNORE INTO duplicate_group_members(group_id, app_id, is_reference) VALUES(?,?,?)",
            [(group.id, m.id, 0) for m in group.members],
        )
        self.db.commit()
        return group

    def set_reference_app(self, group_id: int, app_id: int):
        """Mark one member as the user-designated 'keep' copy."""
        # Clear existing reference in the group
        self.db.execute(
            "UPDATE duplicate_group_members SET is_reference=0 WHERE group_id=?",
            (group_id,),
        )
        # Set new reference
        self.db.execute(
            "UPDATE duplicate_group_members SET is_reference=1 WHERE group_id=? AND app_id=?",
            (group_id, app_id),
        )
        # Also update the group record
        self.db.execute(
            "UPDATE duplicate_groups SET reference_app_id=? WHERE id=?",
            (app_id, group_id),
        )
        self.db.commit()

    def get_duplicate_groups_for_scan(self, scan_id: int) -> List[DuplicateGroup]:
        rows = self.db.execute(
            "SELECT * FROM duplicate_groups WHERE scan_id=? ORDER BY id",
            (scan_id,),
        ).fetchall()
        groups = []
        for row in rows:
            group = DuplicateGroup(
                id=row["id"], group_signature=row["group_signature"],
                match_type=row["match_type"], similarity=row["similarity"],
                reference_app_id=row["reference_app_id"],
                scan_id=row["scan_id"], created_at=row["created_at"],
            )
            # Load members
            member_rows = self.db.execute(
                """
                SELECT a.*, dgm.is_reference
                FROM duplicate_group_members dgm
                JOIN apps a ON a.id = dgm.app_id
                WHERE dgm.group_id=?
                """,
                (group.id,),
            ).fetchall()
            group.members = [self._row_to_app(r) for r in member_rows]
            groups.append(group)
        return groups

    def get_all_duplicate_groups(self) -> List[DuplicateGroup]:
        rows = self.db.execute(
            "SELECT * FROM duplicate_groups ORDER BY id DESC"
        ).fetchall()
        groups = []
        for row in rows:
            group = DuplicateGroup(
                id=row["id"], group_signature=row["group_signature"],
                match_type=row["match_type"], similarity=row["similarity"],
                reference_app_id=row["reference_app_id"],
                scan_id=row["scan_id"], created_at=row["created_at"],
            )
            member_rows = self.db.execute(
                """
                SELECT a.*, dgm.is_reference
                FROM duplicate_group_members dgm
                JOIN apps a ON a.id = dgm.app_id
                WHERE dgm.group_id=?
                """,
                (group.id,),
            ).fetchall()
            group.members = [self._row_to_app(r) for r in member_rows]
            groups.append(group)
        return groups

    def delete_duplicate_groups_for_scan(self, scan_id: int):
        self.db.execute("DELETE FROM duplicate_groups WHERE scan_id=?", (scan_id,))
        self.db.commit()

    # ======================================================================
    # Reports
    # ======================================================================

    def save_report(self, report: ReportRecord) -> ReportRecord:
        cur = self.db.execute(
            "INSERT INTO reports(scan_id, format, file_path, created_at) VALUES(?,?,?,?)",
            (report.scan_id, report.format, report.file_path, _now()),
        )
        self.db.commit()
        report.id = cur.lastrowid
        return report

    def get_reports_for_scan(self, scan_id: int) -> List[ReportRecord]:
        rows = self.db.execute(
            "SELECT * FROM reports WHERE scan_id=? ORDER BY id DESC", (scan_id,)
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    @staticmethod
    def _row_to_report(row) -> ReportRecord:
        return ReportRecord(
            id=row["id"], scan_id=row["scan_id"], format=row["format"],
            file_path=row["file_path"], created_at=row["created_at"],
        )

    # ======================================================================
    # Stats helpers
    # ======================================================================

    def get_stats(self) -> dict:
        total_apps = self.db.execute("SELECT COUNT(*) FROM apps").fetchone()[0]
        total_scans = self.db.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        total_groups = self.db.execute("SELECT COUNT(*) FROM duplicate_groups").fetchone()[0]
        total_duplicates = self.db.execute(
            "SELECT COUNT(*) FROM duplicate_group_members WHERE is_reference=0"
        ).fetchone()[0]
        # Recoverable space: sum of non-reference members' disk sizes
        recoverable = self.db.execute(
            """
            SELECT COALESCE(SUM(a.disk_size_bytes), 0)
            FROM duplicate_group_members dgm
            JOIN apps a ON a.id = dgm.app_id
            WHERE dgm.is_reference = 0
            """
        ).fetchone()[0]
        return {
            "total_apps": total_apps,
            "total_scans": total_scans,
            "duplicate_groups": total_groups,
            "duplicate_copies": total_duplicates,
            "recoverable_bytes": recoverable,
        }
