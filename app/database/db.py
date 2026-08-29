"""SQLite Database initialization and schema management for IADCS."""
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_FILE = "iadcs_data.db"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_FILE
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            root_path TEXT UNIQUE NOT NULL,
            platform TEXT NOT NULL DEFAULT 'windows',
            app_type TEXT NOT NULL,
            total_size INTEGER NOT NULL DEFAULT 0,
            file_count INTEGER NOT NULL DEFAULT 0,
            content_fingerprint TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Other',
            scan_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_apps_fingerprint ON applications(content_fingerprint);
        CREATE INDEX IF NOT EXISTS idx_apps_category ON applications(category);
        CREATE INDEX IF NOT EXISTS idx_apps_root_path ON applications(root_path);

        CREATE TABLE IF NOT EXISTS file_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            relative_path TEXT NOT NULL,
            absolute_path TEXT NOT NULL,
            size INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            partial_hash TEXT,
            file_type TEXT,
            is_readable INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_files_app_id ON file_records(application_id);
        CREATE INDEX IF NOT EXISTS idx_files_sha256 ON file_records(sha256);
        CREATE INDEX IF NOT EXISTS idx_files_size ON file_records(size);

        CREATE TABLE IF NOT EXISTS duplicate_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT UNIQUE NOT NULL,
            application_count INTEGER NOT NULL DEFAULT 0,
            total_size INTEGER NOT NULL DEFAULT 0,
            reclaimable_size INTEGER NOT NULL DEFAULT 0,
            verification_status TEXT NOT NULL DEFAULT 'hash_matched',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            field TEXT NOT NULL,
            operator TEXT NOT NULL,
            value TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 50,
            enabled INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            application_id INTEGER,
            path TEXT NOT NULL,
            hash TEXT,
            size INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            error TEXT,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT UNIQUE NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_apps INTEGER NOT NULL DEFAULT 0,
            duplicate_groups INTEGER NOT NULL DEFAULT 0,
            total_size INTEGER NOT NULL DEFAULT 0,
            reclaimable_size INTEGER NOT NULL DEFAULT 0,
            paths_scanned TEXT NOT NULL
        );
        """)
    conn.close()
