"""
ScanManager — orchestrates the complete scan lifecycle.

Flow:
    1. Create ScanRecord
    2. Discover application candidates
    3. Insert/update each application
    4. Collect application files
    5. Attach the REAL database app_id to every FileRecord
    6. Save FileRecords
    7. Hash files
    8. Build application content signature
    9. Compare application signatures
    10. Persist duplicate groups
    11. Finish scan
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, List, Optional

from app.core.comparator import Comparator
from app.core.hasher import Hasher
from app.core.scanner import Scanner
from app.core.signature import SignatureBuilder
from app.data.models import AppRecord, DuplicateGroup, ScanRecord
from app.data.repository import Repository

logger = logging.getLogger(__name__)


class ScanManager:

    def __init__(self, repo: Repository):

        self.repo = repo

        self._cancelled = threading.Event()

        self._thread: Optional[
            threading.Thread
        ] = None

        self._lock = threading.Lock()

    # ======================================================================
    # PUBLIC API
    # ======================================================================

    def start_full_scan(
        self,
        on_progress: Optional[
            Callable[[str, int, int], None]
        ] = None,

        on_done: Optional[
            Callable[
                [ScanRecord, List[DuplicateGroup]],
                None
            ]
        ] = None,

        on_error: Optional[
            Callable[[str], None]
        ] = None,
    ):

        self._launch(
            "full",
            "",
            on_progress,
            on_done,
            on_error,
        )

    def start_directory_scan(
        self,
        directory: str,

        on_progress: Optional[
            Callable[[str, int, int], None]
        ] = None,

        on_done: Optional[
            Callable[
                [ScanRecord, List[DuplicateGroup]],
                None
            ]
        ] = None,

        on_error: Optional[
            Callable[[str], None]
        ] = None,
    ):

        self._launch(
            "directory",
            directory,
            on_progress,
            on_done,
            on_error,
        )

    def cancel(self):

        logger.info(
            "Scan cancellation requested"
        )

        self._cancelled.set()

    @property
    def is_running(self) -> bool:

        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    # ======================================================================
    # THREAD LAUNCH
    # ======================================================================

    def _launch(
        self,
        scan_type,
        root_path,
        on_progress,
        on_done,
        on_error,
    ):

        with self._lock:

            if self.is_running:

                logger.warning(
                    "Scan already running"
                )

                return

            self._cancelled.clear()

            self._thread = threading.Thread(
                target=self._run,

                args=(
                    scan_type,
                    root_path,
                    on_progress,
                    on_done,
                    on_error,
                ),

                daemon=True,

                name="ScanWorker",
            )

            self._thread.start()

    # ======================================================================
    # CANCELLATION
    # ======================================================================

    def _cancelled_cb(self) -> bool:

        return self._cancelled.is_set()

    # ======================================================================
    # MAIN SCAN
    # ======================================================================

    def _run(
        self,
        scan_type,
        root_path,
        on_progress,
        on_done,
        on_error,
    ):

        scan_rec = None

        try:

            # ==============================================================
            # STEP 1 — CREATE SCAN RECORD
            # ==============================================================

            scan_rec = self.repo.create_scan(
                scan_type,
                root_path,
            )

            scanner = Scanner()

            hasher = Hasher(
                self.repo
            )

            comparator = Comparator()

            # ==============================================================
            # PROGRESS HELPER
            # ==============================================================

            def _progress(
                msg: str,
                done: int = 0,
                total: int = 0,
            ):

                logger.debug(
                    "[scan] %s (%d/%d)",
                    msg,
                    done,
                    total,
                )

                if on_progress:

                    on_progress(
                        msg,
                        done,
                        total,
                    )

            # ==============================================================
            # STEP 2 — DISCOVER APPLICATIONS
            # ==============================================================

            _progress(
                "Discovering applications…"
            )

            if scan_type == "full":

                candidates = scanner.scan_full(

                    progress_cb=lambda msg:
                        _progress(
                            msg,
                            0,
                            0,
                        ),

                    cancelled_cb=
                    self._cancelled_cb,
                )

            else:

                candidates = scanner.scan_directory(

                    root_path,

                    progress_cb=lambda msg:
                        _progress(
                            msg,
                            0,
                            0,
                        ),

                    cancelled_cb=
                    self._cancelled_cb,
                )

            # ==============================================================
            # CANCELLATION
            # ==============================================================

            if self._cancelled_cb():

                self._finish(
                    scan_rec,
                    "cancelled",
                    0,
                    0,
                    [],
                    on_done,
                )

                return

            # ==============================================================
            # APPLICATION COUNT
            # ==============================================================

            total_apps = len(
                candidates
            )

            logger.info(
                "Scanner returned %d application candidates",
                total_apps,
            )

            _progress(
                f"Found {total_apps} application candidates",
                0,
                total_apps,
            )

            # Applications that successfully received signatures
            processed_apps: List[
                AppRecord
            ] = []

            # ==============================================================
            # STEP 3 — PROCESS APPLICATIONS
            # ==============================================================

            for idx, candidate in enumerate(
                candidates
            ):

                if self._cancelled_cb():
                    break

                _progress(
                    f"Processing: {candidate.name}",
                    idx + 1,
                    total_apps,
                )

                # ==========================================================
                # 3A — SAVE APPLICATION FIRST
                # ==========================================================

                candidate.scan_id = scan_rec.id

                app = self.repo.upsert_app(
                    candidate
                )

                if not app or not app.id:

                    logger.warning(
                        "Could not obtain database ID for %s",
                        candidate.name,
                    )

                    continue

                logger.info(
                    "Application saved: %s | app_id=%s | path=%s",
                    app.name,
                    app.id,
                    app.install_path,
                )

                # ==========================================================
                # 3B — COLLECT FILES
                # ==========================================================

                builder = SignatureBuilder(
                    app.id,
                    app.install_path,
                )

                file_records, total_bytes = (
                    builder.collect_files(
                        cancelled_cb=
                        self._cancelled_cb
                    )
                )

                logger.info(
                    "%s: collected %d files (%d bytes)",
                    app.name,
                    len(file_records),
                    total_bytes,
                )

                if not file_records:

                    logger.warning(
                        "No files found for %s",
                        app.install_path,
                    )

                    continue

                # ==========================================================
                # 3C — CRITICAL FIX
                #
                # Force every FileRecord to use the REAL database app_id.
                #
                # This prevents the FOREIGN KEY constraint failure.
                # ==========================================================

                for file_record in file_records:

                    file_record.app_id = app.id

                # ==========================================================
                # 3D — SAVE FILE RECORDS
                # ==============================================================

                self.repo.bulk_upsert_files(
                    file_records
                )

                logger.info(
                    "Saved %d file records for app_id=%s",
                    len(file_records),
                    app.id,
                )

                # ==========================================================
                # 3E — REFRESH FILES FROM DATABASE
                # ==============================================================

                db_files = (
                    self.repo.get_files_for_app(
                        app.id
                    )
                )

                if not db_files:

                    logger.warning(
                        "Database returned no files for app_id=%s",
                        app.id,
                    )

                    continue

                # ==========================================================
                # 3F — HASH FILES
                # ==============================================================

                hashes = hasher.hash_files(

                    db_files,

                    progress_cb=lambda d, t,
                    app_name=app.name,
                    app_index=idx + 1:
                        _progress(
                            f"Hashing {app_name} ({d}/{t} files)",
                            app_index,
                            total_apps,
                        ),

                    cancelled_cb=
                    self._cancelled_cb,
                )

                logger.info(
                    "%s: hashed %d files",
                    app.name,
                    len(hashes),
                )

                # ==========================================================
                # 3G — BUILD APPLICATION SIGNATURE
                # ==============================================================

                sig = builder.compute_signature(
                    db_files,
                    hashes,
                )

                if not sig:

                    logger.warning(
                        "No application signature generated for %s",
                        app.name,
                    )

                    continue

                # ==========================================================
                # 3H — UPDATE APPLICATION
                # ==============================================================

                app.disk_size_bytes = (
                    total_bytes
                )

                app.app_signature = sig

                self.repo.upsert_app(
                    app
                )

                logger.info(
                    "Application signature generated: %s | %s",
                    app.name,
                    sig[:16] + "...",
                )

                processed_apps.append(
                    app
                )

            # ==============================================================
            # CANCELLATION
            # ==============================================================

            if self._cancelled_cb():

                self._finish(
                    scan_rec,
                    "cancelled",
                    len(processed_apps),
                    0,
                    [],
                    on_done,
                )

                return

            # ==============================================================
            # STEP 4 — COMPARE SIGNATURES
            # ==============================================================

            _progress(
                "Comparing application signatures…",
                total_apps,
                total_apps,
            )

            logger.info(
                "Sending %d processed applications to comparator",
                len(processed_apps),
            )

            groups = comparator.find_duplicates(
                processed_apps,
                scan_id=scan_rec.id,
            )

            logger.info(
                "Comparator found %d duplicate groups",
                len(groups),
            )

            # ==============================================================
            # STEP 5 — SAVE DUPLICATE GROUPS
            # ==============================================================

            self.repo.delete_duplicate_groups_for_scan(
                scan_rec.id
            )

            saved_groups: List[
                DuplicateGroup
            ] = []

            for group in groups:

                saved = (
                    self.repo.create_duplicate_group(
                        group
                    )
                )

                saved_groups.append(
                    saved
                )

            # ==============================================================
            # STEP 6 — FINISH
            # ==============================================================

            self._finish(

                scan_rec,

                "done",

                len(processed_apps),

                len(saved_groups),

                saved_groups,

                on_done,
            )

        except Exception as exc:

            logger.exception(
                "Scan failed: %s",
                exc,
            )

            if scan_rec:

                try:

                    self.repo.finish_scan(
                        scan_rec.id,
                        "error",
                        0,
                        0,
                    )

                except Exception:

                    logger.exception(
                        "Could not mark scan as failed"
                    )

            if on_error:

                on_error(
                    str(exc)
                )

    # ======================================================================
    # FINISH
    # ======================================================================

    def _finish(
        self,
        scan_rec: ScanRecord,
        status: str,
        apps_found: int,
        duplicates_found: int,
        groups: List[
            DuplicateGroup
        ],
        on_done,
    ):

        self.repo.finish_scan(

            scan_rec.id,

            status,

            apps_found,

            duplicates_found,
        )

        scan_rec.status = status

        scan_rec.apps_found = (
            apps_found
        )

        scan_rec.duplicates_found = (
            duplicates_found
        )

        scan_rec.finished_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        logger.info(

            "Scan #%d finished: status=%s apps=%d duplicates=%d",

            scan_rec.id,

            status,

            apps_found,

            duplicates_found,
        )

        if on_done:

            on_done(
                scan_rec,
                groups,
            )