"""Structured JSON audit logger for IADCS."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    def __init__(self, log_file: str = "iadcs_audit.log"):
        self.log_file = Path(log_file).resolve()
        self.logger = logging.getLogger("IADCS_Audit")
        self.logger.setLevel(logging.INFO)

        # File handler for structured JSON lines
        if not self.logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding="utf-8")
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(fh)

    def log(
        self,
        operation: str,
        application_name: Optional[str] = None,
        path: Optional[str] = None,
        content_hash: Optional[str] = None,
        size: int = 0,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "application": application_name,
            "path": path,
            "content_hash": content_hash,
            "size": size,
            "status": status,
            "details": details or {},
            "error": error,
        }
        self.logger.info(json.dumps(entry))
        return entry
