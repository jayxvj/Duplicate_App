"""
SHA-256 file hasher with:
  - Chunked reading (no memory overflow on large files)
  - ThreadPoolExecutor for parallelism
  - SQLite cache reuse (via Repository)
  - Progress callback for UI updates
"""
from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from app.config import cfg
from app.data.models import FileHashRecord
from app.data.repository import Repository

logger = logging.getLogger(__name__)


def hash_file(path: str, chunk_size: int | None = None) -> str:
    """
    Compute SHA-256 of a single file.
    Reads in chunks to handle files of any size.
    Raises OSError if the file cannot be read.
    """
    if chunk_size is None:
        chunk_size = cfg.chunk_size
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


class Hasher:
    """
    Hashes a list of files in parallel, checking the DB cache first
    to avoid redundant hashing of unchanged files.
    """

    def __init__(self, repo: Repository):
        self.repo = repo
        self._chunk_size = cfg.chunk_size
        self._max_workers = cfg.max_workers

    def hash_files(
        self,
        file_records,                               # List[FileRecord]
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancelled_cb: Optional[Callable[[], bool]] = None,
    ) -> Dict[int, str]:
        """
        Hash a list of FileRecord objects.

        Args:
            file_records: list of FileRecord (must have .id, .absolute_path,
                          .file_size set)
            progress_cb: called with (done, total) during processing
            cancelled_cb: called each iteration; return True to abort

        Returns:
            dict mapping file_id -> sha256
        """
        results: Dict[int, str] = {}
        to_hash: List = []

        total = len(file_records)
        done = 0

        # --- Phase 1: check cache ---
        for fr in file_records:
            if cancelled_cb and cancelled_cb():
                break
            try:
                stat = os.stat(fr.absolute_path)
                mtime = stat.st_mtime
                size = stat.st_size
            except OSError:
                continue

            cached = self.repo.get_cached_hash(fr.id, size, mtime)
            if cached:
                results[fr.id] = cached
                done += 1
                if progress_cb:
                    progress_cb(done, total)
            else:
                to_hash.append((fr, size, mtime))

        # --- Phase 2: hash in parallel ---
        new_hash_records: List[FileHashRecord] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            future_map = {
                pool.submit(hash_file, fr.absolute_path, self._chunk_size): (fr, size, mtime)
                for fr, size, mtime in to_hash
            }
            for future in as_completed(future_map):
                if cancelled_cb and cancelled_cb():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                fr, size, mtime = future_map[future]
                try:
                    sha = future.result()
                    results[fr.id] = sha
                    new_hash_records.append(FileHashRecord(
                        file_id=fr.id,
                        sha256=sha,
                        file_size=size,
                        mtime=mtime,
                        computed_at=datetime.now(timezone.utc).isoformat(),
                    ))
                except Exception as exc:
                    logger.warning("Could not hash %s: %s", fr.absolute_path, exc)
                finally:
                    done += 1
                    if progress_cb:
                        progress_cb(done, total)

        # --- Persist new hashes ---
        if new_hash_records:
            self.repo.bulk_save_hashes(new_hash_records)
            logger.debug("Cached %d new file hashes", len(new_hash_records))

        return results
