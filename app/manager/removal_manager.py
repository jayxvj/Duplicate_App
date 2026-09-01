"""
RemovalManager — safe removal of duplicate application installs.

Uses send2trash to move items to the Recycle Bin / Trash rather than
permanently deleting them. The user always retains the ability to recover.

Removal flow:
  1. Validate that the app is NOT the user-designated "keep" copy
  2. Show confirmation (handled by the UI layer before calling here)
  3. send2trash the install directory
  4. Remove the AppRecord and its FileRecords from the DB
  5. If all non-reference members of a group are removed, remove the group too
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from app.data.models import AppRecord, DuplicateGroup
from app.data.repository import Repository

logger = logging.getLogger(__name__)

try:
    from send2trash import send2trash as _send2trash
    _TRASH_AVAILABLE = True
except ImportError:
    _TRASH_AVAILABLE = False
    logger.warning(
        "send2trash not installed — falling back to permanent deletion! "
        "Run: pip install send2trash"
    )


class RemovalManager:
    def __init__(self, repo: Repository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_remove(self, app: AppRecord, group: DuplicateGroup) -> tuple[bool, str]:
        """
        Check whether this app may be removed.
        Returns (ok, reason_if_not).
        """
        if group.reference_app_id == app.id:
            return False, "This is the designated 'Keep' copy — mark another copy as 'Keep' first."
        if group.reference_app_id is None:
            return False, "No 'Keep' copy has been designated for this group yet."
        return True, ""

    def remove_app(
        self,
        app: AppRecord,
        group: DuplicateGroup,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """
        Move the application's install directory to the Recycle Bin.

        Args:
            app: The AppRecord to remove.
            group: The DuplicateGroup it belongs to.
            dry_run: If True, log what would happen but don't act.

        Returns:
            (success, message)
        """
        ok, reason = self.can_remove(app, group)
        if not ok:
            return False, reason

        path = app.install_path
        if not os.path.exists(path):
            # Path already gone — clean up DB
            self._cleanup_db(app, group)
            return True, f"Path already missing: {path} (DB cleaned up)"

        if dry_run:
            logger.info("[DRY RUN] Would trash: %s", path)
            return True, f"[Dry run] Would send to Recycle Bin: {path}"

        try:
            if _TRASH_AVAILABLE:
                _send2trash(path)
                logger.info("Sent to Recycle Bin: %s", path)
            else:
                # Fallback: we will NOT silently delete. Raise so the UI warns.
                raise RuntimeError(
                    "send2trash is not available. Install it with: pip install send2trash"
                )
        except Exception as exc:
            logger.error("Failed to trash %s: %s", path, exc)
            return False, str(exc)

        self._cleanup_db(app, group)
        return True, f"Sent to Recycle Bin: {path}"

    def remove_all_except_reference(
        self,
        group: DuplicateGroup,
        dry_run: bool = False,
    ) -> List[tuple[AppRecord, bool, str]]:
        """
        Remove all members of the group except the reference (keep) copy.

        Returns a list of (app, success, message) tuples.
        """
        results = []
        for member in group.members:
            if member.id == group.reference_app_id:
                continue
            ok, msg = self.remove_app(member, group, dry_run=dry_run)
            results.append((member, ok, msg))
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_db(self, app: AppRecord, group: DuplicateGroup):
        """Remove app from DB and update the group accordingly."""
        self.repo.delete_app(app.id)
        logger.debug("Removed app_id=%d from DB", app.id)

        # Reload group members; if only one remains, the group is moot
        # (But keep the group record so history is preserved)
