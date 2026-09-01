# app/core/__init__.py
"""Core models and shared constants for IADCS."""
try:
    from app.core.types import (
        AppType,
        MatchType,
        VerificationStatus,
        FileRecord,
        Application,
        DuplicateGroup,
        CategoryRule,
        ScanProgress,
        RemovalResult,
    )

    __all__ = [
        "AppType",
        "MatchType",
        "VerificationStatus",
        "FileRecord",
        "Application",
        "DuplicateGroup",
        "CategoryRule",
        "ScanProgress",
        "RemovalResult",
    ]
except ImportError:
    pass
