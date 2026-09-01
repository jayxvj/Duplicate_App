"""
Data models — plain dataclasses that flow between all layers.
No ORM, no DB-specific types; pure Python.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class AppRecord:
    """Represents a discovered application instance."""
    id: Optional[int] = None
    name: str = ""
    install_path: str = ""
    version: str = ""
    publisher: str = ""
    category: str = "Other"
    app_signature: Optional[str] = None   # SHA-256 composite of core files
    scan_id: Optional[int] = None
    first_seen: Optional[str] = None
    last_scanned: Optional[str] = None
    disk_size_bytes: int = 0              # total size of all files in install_path


@dataclass
class FileRecord:
    """Represents a single file belonging to an application."""
    id: Optional[int] = None
    app_id: Optional[int] = None
    relative_path: str = ""
    absolute_path: str = ""
    file_size: int = 0
    is_volatile: bool = False
    is_core: bool = False


@dataclass
class FileHashRecord:
    """Cached hash for a file — invalidated when size or mtime changes."""
    file_id: int = 0
    sha256: str = ""
    file_size: int = 0
    mtime: float = 0.0
    computed_at: str = ""


@dataclass
class DuplicateGroup:
    """A group of applications with identical content signatures."""
    id: Optional[int] = None
    group_signature: str = ""
    match_type: str = "exact"           # always 'exact' in v1
    similarity: float = 1.0
    reference_app_id: Optional[int] = None   # user-designated "keep" copy
    scan_id: Optional[int] = None
    created_at: Optional[str] = None
    members: List[AppRecord] = field(default_factory=list)


@dataclass
class ScanRecord:
    """Lifecycle record for a single scan run."""
    id: Optional[int] = None
    scan_type: str = "directory"         # 'full' | 'directory'
    root_path: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str = "running"              # 'running'|'done'|'cancelled'|'error'
    apps_found: int = 0
    duplicates_found: int = 0


@dataclass
class ReportRecord:
    """Metadata for a generated report file."""
    id: Optional[int] = None
    scan_id: Optional[int] = None
    format: str = "json"                 # 'json' | 'html' | 'csv'
    file_path: str = ""
    created_at: Optional[str] = None
