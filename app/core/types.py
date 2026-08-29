"""Core domain models and types for IADCS."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AppType(str, Enum):
    WINDOWS_PORTABLE = "windows_portable"
    WINDOWS_INSTALLED = "windows_installed"
    PYTHON_ENV = "python_app"
    JAVA_JAR = "java_app"
    GENERIC_FOLDER = "generic_folder"
    STANDALONE_BINARY = "standalone_binary"


class MatchType(str, Enum):
    EXACT_CONTENT = "Exact Content"
    VERIFIED_BINARY = "Verified Binary"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    HASH_MATCHED = "hash_matched"
    BYTE_VERIFIED = "byte_verified"
    FAILED = "failed"


@dataclass
class FileRecord:
    id: Optional[int] = None
    application_id: Optional[int] = None
    relative_path: str = ""
    absolute_path: str = ""
    size: int = 0
    sha256: str = ""
    partial_hash: str = ""
    file_type: str = ""
    is_readable: bool = True


@dataclass
class Application:
    id: Optional[int] = None
    name: str = ""
    root_path: str = ""
    platform: str = "windows"
    app_type: AppType = AppType.GENERIC_FOLDER
    total_size: int = 0
    file_count: int = 0
    content_fingerprint: str = ""
    category: str = "Other"
    scan_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    files: List[FileRecord] = field(default_factory=list)


@dataclass
class DuplicateGroup:
    id: Optional[int] = None
    fingerprint: str = ""
    application_count: int = 0
    total_size: int = 0
    reclaimable_size: int = 0
    verification_status: str = VerificationStatus.HASH_MATCHED.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applications: List[Application] = field(default_factory=list)


@dataclass
class CategoryRule:
    id: Optional[int] = None
    category: str = "Other"
    field: str = "name"  # name, executable, path, app_type, size
    operator: str = "contains"  # contains, equals, starts_with, ends_with, regex, gt, lt
    value: str = ""
    priority: int = 50
    enabled: bool = True


@dataclass
class ScanProgress:
    phase: str = "idle"  # discovering, inventorying, hashing, fingerprinting, grouping, categorizing, complete
    current_path: str = ""
    files_scanned: int = 0
    apps_found: int = 0
    bytes_processed: int = 0
    total_bytes: int = 0
    error_count: int = 0
    percent: float = 0.0


@dataclass
class RemovalResult:
    app_id: int
    app_name: str
    root_path: str
    fingerprint: str
    reclaimed_bytes: int
    action: str  # quarantine or delete
    status: str  # success or failed
    error_message: Optional[str] = None
    quarantine_path: Optional[str] = None
