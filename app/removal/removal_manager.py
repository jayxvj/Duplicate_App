"""Orchestrator for safe application deletion and quarantine."""
import os
import shutil
from pathlib import Path
from typing import List, Optional

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from app.core.types import Application, RemovalResult
from app.database.repository import Repository
from app.removal.quarantine import QuarantineManager
from app.removal.safety_validator import SafetyValidator


class RemovalManager:
    def __init__(
        self,
        repository: Optional[Repository] = None,
        quarantine_dir: str = ".iadcs_quarantine",
    ):
        self.repo = repository or Repository()
        self.quarantine_mgr = QuarantineManager(quarantine_dir)

    def remove_application(
        self,
        app: Application,
        action: str = "quarantine",  # "quarantine", "trash", or "permanent"
    ) -> RemovalResult:
        # 1. Safety validation
        is_safe, error_msg = SafetyValidator.validate_for_removal(app)
        if not is_safe:
            self.repo.log_operation(
                operation="removal_failed_safety",
                application_id=app.id,
                path=app.root_path,
                content_hash=app.content_fingerprint,
                size=app.total_size,
                status="failed",
                error=error_msg,
            )
            return RemovalResult(
                app_id=app.id or 0,
                app_name=app.name,
                root_path=app.root_path,
                fingerprint=app.content_fingerprint,
                reclaimed_bytes=0,
                action=action,
                status="failed",
                error_message=error_msg,
            )

        target_path = Path(app.root_path)
        quarantine_dest: Optional[str] = None

        try:
            if action == "quarantine":
                dest = self.quarantine_mgr.quarantine_application(app)
                quarantine_dest = str(dest)
            elif action == "trash" and HAS_SEND2TRASH:
                send2trash(str(target_path))
            else:
                # Permanent deletion
                if target_path.is_file():
                    target_path.unlink()
                else:
                    shutil.rmtree(str(target_path))

            # Post-removal verification: target should no longer exist at original path
            if target_path.exists():
                raise RuntimeError(f"Path '{target_path}' still exists after removal attempt.")

            # Remove from repository
            if app.id:
                self.repo.delete_application(app.id)

            self.repo.log_operation(
                operation=f"application_{action}",
                application_id=app.id,
                path=app.root_path,
                content_hash=app.content_fingerprint,
                size=app.total_size,
                status="success",
            )

            return RemovalResult(
                app_id=app.id or 0,
                app_name=app.name,
                root_path=app.root_path,
                fingerprint=app.content_fingerprint,
                reclaimed_bytes=app.total_size,
                action=action,
                status="success",
                quarantine_path=quarantine_dest,
            )

        except Exception as e:
            err = str(e)
            self.repo.log_operation(
                operation=f"application_{action}_error",
                application_id=app.id,
                path=app.root_path,
                content_hash=app.content_fingerprint,
                size=app.total_size,
                status="failed",
                error=err,
            )
            return RemovalResult(
                app_id=app.id or 0,
                app_name=app.name,
                root_path=app.root_path,
                fingerprint=app.content_fingerprint,
                reclaimed_bytes=0,
                action=action,
                status="failed",
                error_message=err,
            )
