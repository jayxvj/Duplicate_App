"""
SQLite database — schema creation, migrations, and low-level connection management.
All schema changes live here; the repository layer performs the actual CRUD.
"""
from __future__ import annotations

import sqlite3
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- -------------------------------------------------------------------------
-- Schema version tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

-- -------------------------------------------------------------------------
-- Scan lifecycle
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_type        TEXT NOT NULL,          -- 'full' | 'directory'
    root_path        TEXT NOT NULL DEFAULT '',
    started_at       TEXT,
    finished_at      TEXT,
    status           TEXT NOT NULL DEFAULT 'running',
    apps_found       INTEGER NOT NULL DEFAULT 0,
    duplicates_found INTEGER NOT NULL DEFAULT 0
);

-- -------------------------------------------------------------------------
-- Discovered application instances
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apps (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    install_path   TEXT NOT NULL,
    version        TEXT NOT NULL DEFAULT '',
    publisher      TEXT NOT NULL DEFAULT '',
    category       TEXT NOT NULL DEFAULT 'Other',
    app_signature  TEXT,                     -- SHA-256 composite of core files
    disk_size_bytes INTEGER NOT NULL DEFAULT 0,
    scan_id        INTEGER REFERENCES scans(id) ON DELETE SET NULL,
    first_seen     TEXT,
    last_scanned   TEXT,
    UNIQUE(install_path)
);
CREATE INDEX IF NOT EXISTS idx_apps_signature ON apps(app_signature);
CREATE INDEX IF NOT EXISTS idx_apps_scan_id   ON apps(scan_id);

-- -------------------------------------------------------------------------
-- Files belonging to an application
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id        INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    relative_path TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    file_size     INTEGER NOT NULL DEFAULT 0,
    is_volatile   INTEGER NOT NULL DEFAULT 0,   -- 1 = excluded from signature
    is_core       INTEGER NOT NULL DEFAULT 0,   -- 1 = included in signature
    UNIQUE(absolute_path)
);
CREATE INDEX IF NOT EXISTS idx_files_app_id ON files(app_id);

-- -------------------------------------------------------------------------
-- Cached file hashes — reused across scans when file hasn't changed
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS file_hashes (
    file_id     INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    sha256      TEXT NOT NULL,
    file_size   INTEGER NOT NULL,
    mtime       REAL NOT NULL,
    computed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hashes_sha256 ON file_hashes(sha256);

-- -------------------------------------------------------------------------
-- Duplicate groups (exact match only in v1)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    group_signature  TEXT NOT NULL,
    match_type       TEXT NOT NULL DEFAULT 'exact',
    similarity       REAL NOT NULL DEFAULT 1.0,
    reference_app_id INTEGER REFERENCES apps(id) ON DELETE SET NULL,
    scan_id          INTEGER REFERENCES scans(id) ON DELETE CASCADE,
    created_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_groups_signature ON duplicate_groups(group_signature);

CREATE TABLE IF NOT EXISTS duplicate_group_members (
    group_id     INTEGER NOT NULL REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    app_id       INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    is_reference INTEGER NOT NULL DEFAULT 0,   -- 1 = user-designated "keep"
    PRIMARY KEY (group_id, app_id)
);

-- -------------------------------------------------------------------------
-- Report metadata
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id    INTEGER REFERENCES scans(id) ON DELETE SET NULL,
    format     TEXT NOT NULL,                  -- 'json' | 'html' | 'csv'
    file_path  TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    """Manages a single SQLite connection (WAL mode) for the application."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row
            self._apply_schema()
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        # Keep connection alive across the session; close explicitly on app exit
        pass

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _apply_schema(self):
        conn = self._conn
        assert conn is not None
        try:
            conn.executescript(DDL)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES(?, datetime('now'))",
                (SCHEMA_VERSION,),
            )
            conn.commit()
            logger.info("Database schema applied at %s", self.db_path)
        except sqlite3.Error as exc:
            logger.error("Schema error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        return self.connect().executemany(sql, params_seq)

    def commit(self):
        if self._conn:
            self._conn.commit()

    def rollback(self):
        if self._conn:
            self._conn.rollback()
